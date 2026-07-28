#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import re

FRONTEND_PORT = 8080
BACKEND_PORT = 8002
BASE = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_BASE = f"http://127.0.0.1:{FRONTEND_PORT}"


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[smoke] {status}: {name} {detail}")
    return condition


def request(path, payload=None, headers=None, method=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers = {"content-type": "application/json", **(headers or {})}
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req) as res:
        body = res.read().decode() or "{}"
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def frontend_contains(text):
    with urllib.request.urlopen(f"{FRONTEND_BASE}/src/app.js") as res:
        body = res.read().decode()
    return text in body


def main():
    results = []

    results.append(check("frontend_home", urllib.request.urlopen(f"{FRONTEND_BASE}/").status == 200))
    results.append(check("frontend_app_js", urllib.request.urlopen(f"{FRONTEND_BASE}/src/app.js").status == 200))
    results.append(check("health", json.loads(urllib.request.urlopen(f"{BASE}/health").read())["status"] == "ok"))

    login = request("/api/v1/auth/login", {"username": "admin", "password": "admin123"})
    results.append(check("login_admin", login.get("access_token") and login.get("role") == "admin", detail=f"role={login.get('role')}"))
    token = login["access_token"]
    auth_headers = {"authorization": f"Bearer {token}"}

    me = request("/api/v1/auth/me", headers=auth_headers)
    results.append(check("auth_me", me.get("data", {}).get("username") == "admin", detail=f"data={me.get('data')}"))

    customers = request("/api/v1/customers", headers=auth_headers)
    results.append(check("customers_api", isinstance(customers, list) and len(customers) >= 1, detail=f"count={len(customers) if isinstance(customers, list) else 0}"))
    customer_id = customers[0]["id"]

    session = request("/api/v1/chat/sessions", {"customer_id": customer_id, "title": "smoke-session"}, auth_headers, "POST")
    results.append(check("chat_create_session", session.get("id") is not None))

    message = request(f"/api/v1/chat/sessions/{session['id']}/messages", {"role": "user", "content": "smoke"}, auth_headers, "POST")
    results.append(check("chat_reply", message.get("message", {}).get("role") == "assistant", detail="assistant_message"))
    results.append(check("chat_source_cards", isinstance(message.get("source_cards"), list), detail="top_level_source_cards"))
    results.append(check("chat_source_refs", isinstance(message.get("source_refs"), list), detail="top_level_source_refs"))

    sessions = request("/api/v1/chat/sessions", headers=auth_headers)
    results.append(check("chat_sessions_list", any(item.get("id") == session["id"] for item in sessions)))

    renamed = request(f"/api/v1/chat/sessions/{session['id']}", {"title": "smoke-renamed"}, auth_headers, "PATCH")
    results.append(check("chat_rename", renamed.get("title") == "smoke-renamed"))

    reloaded = request(f"/api/v1/chat/sessions/{session['id']}/messages", headers=auth_headers)
    results.append(check("chat_reload_messages", len(reloaded) >= 2, detail=f"messages={len(reloaded) if isinstance(reloaded, list) else 'n/a'}"))

    briefing = request(f"/api/v1/customers/{customer_id}/briefing?session_id={session['id']}", headers=auth_headers, method="POST")
    results.append(check("briefing_api", briefing.get("code") == 0 and isinstance(briefing.get("data", {}).get("llm_source_cards"), list), detail="llm_source_cards"))
    results.append(check("briefing_saved_history", briefing.get("data", {}).get("id") is not None, detail="persisted_briefing_id"))

    history = request(f"/api/v1/customers/{customer_id}/briefing-history", headers=auth_headers)
    results.append(check("briefing_history_api", history.get("code") == 0 and isinstance(history.get("data"), list) and len(history.get("data", [])) >= 1))
    latest_history = history["data"][0]
    results.append(check("briefing_history_source_cards", isinstance(latest_history.get("llm_source_cards"), list), detail="history_source_cards"))

    assist = request(f"/api/v1/customers/{customer_id}/assist", {"transcript": "smoke"}, auth_headers, "POST")
    results.append(check("assist_api", assist.get("code") == 0 and isinstance(assist.get("data", {}).get("source_cards"), list), detail="source_cards"))

    followup = request(f"/api/v1/customers/{customer_id}/followup", {"summary": "smoke", "decisions": ["a"], "pending_actions": ["b"]}, auth_headers, "POST")
    results.append(check("followup_api", followup.get("code") == 0 and isinstance(followup.get("data", {}).get("source_cards"), list), detail="source_cards"))

    sales_login = request("/api/v1/auth/login", {"username": "sales", "password": "sales123"})
    sales_token = sales_login.get("access_token")
    results.append(check("login_sales", bool(sales_token) and sales_login.get("role") == "user", detail=f"role={sales_login.get('role')}"))

    sales_headers = {"authorization": f"Bearer {sales_token}"}
    admin_knowledge = request("/api/v1/knowledge/cases", headers=sales_headers, method="POST")
    results.append(check("sales_knowledge_forbidden", admin_knowledge.get("detail") == "权限不足", detail=f"detail={admin_knowledge.get('detail')}"))

    knowledge_cases = request("/api/v1/knowledge/cases", headers=auth_headers)
    results.append(check("knowledge_cases_api", isinstance(knowledge_cases, list) and len(knowledge_cases) >= 1, detail="admin_can_read"))

    html_checks = [
        ("source_card_component", "source-card"),
        ("source_card_title", "引用来源"),
        ("briefing_history_heading", "会前简报历史"),
        ("briefing_history_table_header", "来源卡"),
        ("assist_modal_result_anchor", 'id="assist-result"'),
        ("followup_modal_result_anchor", 'id="followup-result"'),
        ("chat_rename_button", 'renameChatSession'),
        ("chat_session_title", '当前会话：'),
        ("knowledge_page_admin_only", 'data-admin-only'),
        ("meeting_result_renderer", 'renderMeetingResult'),
    ]
    for name, fragment in html_checks:
        results.append(check(f"frontend_{name}", frontend_contains(fragment)))

    print(f"[smoke] summary: {sum(results)}/{len(results)} passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
