#!/bin/zsh
set -euo pipefail

FRONTEND_PORT="${FRONTEND_PORT:-8080}"
BACKEND_PORT="${BACKEND_PORT:-8002}"
BACKEND_DIR="/Users/jarod/Dev/sales/backend"
FRONTEND_DIR="/Users/jarod/Dev/sales/frontend"
VENV="/Users/jarod/Dev/sales/backend/.venv"
PYTHONPATH="/Users/jarod/Dev/sales/backend"
APP_MODULE="${APP_MODULE:-app.main:app}"

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "[restart] killing port $port pids: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    kill -9 $pids 2>/dev/null || true
  fi
}

cleanup() {
  echo "[restart] cleaning up..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
}
trap cleanup EXIT

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

echo "[restart] initializing database before tests"
cd "$BACKEND_DIR"
source "$VENV/bin/activate"
PYTHONPATH="$PYTHONPATH" python app/db/init_db.py >/tmp/sales-init-db.log 2>&1 || {
  echo "[restart] database initialization failed"; cat /tmp/sales-init-db.log; exit 1
}

echo "[restart] starting backend on $BACKEND_PORT"
cd "$BACKEND_DIR"
source "$VENV/bin/activate"
PYTHONPATH="$PYTHONPATH" nohup uvicorn "$APP_MODULE" --reload --host 127.0.0.1 --port "$BACKEND_PORT" >/tmp/sales-backend.log 2>&1 &
BACKEND_PID=$!

echo "[restart] starting frontend on $FRONTEND_PORT"
cd "$FRONTEND_DIR"
nohup python3 -m http.server "$FRONTEND_PORT" >/tmp/sales-frontend.log 2>&1 &
FRONTEND_PID=$!

echo "[restart] waiting for services..."
for i in {1..90}; do
  if curl -sf "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null && curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:$FRONTEND_PORT/" | grep -q '200'; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null; then
  echo "[restart] backend did not become healthy"; tail -n 80 /tmp/sales-backend.log; exit 1
fi
if ! curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:$FRONTEND_PORT/" | grep -q '200'; then
  echo "[restart] frontend did not become healthy"; tail -n 80 /tmp/sales-frontend.log; exit 1
fi

echo "[restart] verifying login before pytest"
LOGIN_RESPONSE=$(curl -sf -X POST "http://127.0.0.1:$BACKEND_PORT/api/v1/auth/login" \
  -H 'content-type: application/json' \
  -d '{"username":"admin","password":"admin123"}' || true)
if ! echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
  echo "[restart] login verification failed: $LOGIN_RESPONSE"; tail -n 120 /tmp/sales-backend.log; exit 1
fi

echo "[restart] running pytest"
cd "$BACKEND_DIR"
PYTHONPATH="$PYTHONPATH" pytest -q --maxfail=1
TEST_EXIT=$?

echo "[restart] pytest exit code: $TEST_EXIT"
exit $TEST_EXIT
