import subprocess, time, urllib.request, webbrowser, sys

backend = subprocess.Popen([
    "/Users/jarod/Dev/sales/backend/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"
], cwd="/Users/jarod/Dev/sales/backend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
frontend = subprocess.Popen([sys.executable, "-m", "http.server", "8080"], cwd="/Users/jarod/Dev/sales/frontend/src", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(2)
print("backend health:", urllib.request.urlopen("http://127.0.0.1:8000/health").read().decode())
print("frontend index:", urllib.request.urlopen("http://127.0.0.1:8080/index.html").status)
print("open browser: http://localhost:8080")
webbrowser.open("http://localhost:8080")
input("press enter to stop...")
backend.terminate()
frontend.terminate()
backend.wait()
frontend.wait()
