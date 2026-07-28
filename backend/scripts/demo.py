import requests
base = "http://127.0.0.1:8000"
print(requests.get(f"{base}/health").json())
print(requests.post(f"{base}/api/v1/customers/1/briefing").json()["data"]["customer_name"])
print(requests.post(f"{base}/api/v1/customers/1/assist", json={"current_stage":"听","transcript":"你们有什么预期数据？","customer_type":"品牌野心型"}).json()["data"]["detected_stage"])
print(requests.post(f"{base}/api/v1/customers/1/followup", json={"summary":"客户愿意测试","decisions":["同意1城测试"],"pending_actions":["发送测试方案"]}).json()["data"]["tasks"][0]["title"])
