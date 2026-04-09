#!/usr/bin/env python3
"""
Verification script for the Internal Chat System.
Checks:
1. Channel auto-provisioning on class creation
2. Member syncing on student registration
3. Message sending & persistence
4. AI Delegate auto-reply triggers in chat
"""

import sys, random, string, httpx, time

BASE = "http://localhost:8001/api/v1"

def rnd(k=7):
    return "".join(random.choices(string.ascii_lowercase, k=k))

RESULTS = []

def check(label, passed, got=""):
    mark = "✅ PASS" if passed else "❌ FAIL"
    RESULTS.append({"label": label, "pass": passed})
    print(f"  {mark}  {label}")
    if got:
        print(f"          ↳ {got}")

client = httpx.Client(timeout=30)
PW = "Test@1234"
email_admin = f"chat_admin_{rnd()}@gmail.com"
email_student = f"student_{rnd()}@gmail.com"

print(f"\n{'━'*60}\n  Chat System Verification\n{'━'*60}\n")

# 1. Setup Admin & School
r = client.post(f"{BASE}/auth/register", json={
    "email": email_admin, "password": PW,
    "first_name": "Chat", "last_name": "Admin", "role": "admin"
})
reg_data = r.json()
print(f"DEBUG: Admin Registration Role: {reg_data.get('role')}")

r = client.post(f"{BASE}/auth/login", json={"email": email_admin, "password": PW})
admin_token = r.json().get("access_token")
admin_H = {"Authorization": f"Bearer {admin_token}"}

# Verify role via /me
r = client.get(f"{BASE}/auth/me", headers=admin_H)
me_data = r.json()
print(f"DEBUG: Admin /me Role: {me_data.get('role')}")

r = client.post(f"{BASE}/schools", json={"name": "Chat test school", "domain": f"{rnd()}.edu"}, headers=admin_H)
school_id = r.json().get("id")
r = client.post(f"{BASE}/filieres", json={"name": "INFO", "school_id": school_id, "responsible_id": me_data.get("id")}, headers=admin_H)
filiere_id = r.json().get("id")

# 2. Register Student First
client.post(f"{BASE}/auth/register", json={
    "email": email_student, "password": PW,
    "first_name": "Alice", "last_name": "Student", "role": "student"
})
r = client.post(f"{BASE}/auth/login", json={"email": email_student, "password": PW})
student_token = r.json().get("access_token")
student_H = {"Authorization": f"Bearer {student_token}"}

# 3. Create Class
r = client.post(f"{BASE}/classes", json={"filiere_id": filiere_id, "name": "CHAT-101", "academic_year": "2025"}, headers=admin_H)
class_res = r.json()
if r.status_code != 200:
    print(f"DEBUG: Class creation failed: {class_res}")
class_id = class_res.get("id")

# 4. Enroll student via CSV upload (triggers sync)
csv_content = f"student_number,first_name,last_name,email,phone,photo_url\nS001,Alice,Student,{email_student},555-1234,http://photo.com/a.jpg"
files = {"file": ("students.csv", csv_content, "text/csv")}
r = client.post(f"{BASE}/classes/{class_id}/upload-trombinoscope", headers=admin_H, files=files)
if r.status_code != 200:
    print(f"DEBUG: Upload failed ({r.status_code}): {r.json()}")
check("Student enrolled via bulk upload", r.status_code == 200)

# 5. Verify Channel Membership
r = client.get(f"{BASE}/chat/channels", headers=student_H)
channels = r.json()
target_channel = next((c for c in channels if str(c["entity_id"]) == str(class_id)), None)
check("Student can see auto-created class channel", target_channel is not None, f"Channels count: {len(channels)}")

if target_channel:
    channel_id = target_channel["id"]
    
    # 6. Message Persistence
    r = client.post(f"{BASE}/chat/channels/{channel_id}/messages", headers=student_H, json={"content": "Hello!"})
    check("Student can send message", r.status_code == 200)
    
    r = client.get(f"{BASE}/chat/channels/{channel_id}/messages", headers=student_H)
    msgs = r.json()
    check("Message persisted", any(m["content"] == "Hello!" for m in msgs))

    # 7. AI Delegate Trigger
    # Setup data
    client.put(f"{BASE}/classes/{class_id}/timetable", headers=admin_H, json=[
        {"day_of_week": 0, "start_time": "08:00", "end_time": "10:00", "subject": "Maths", "room": "A1"}
    ])
    client.put(f"{BASE}/classes/{class_id}/ai-delegate", headers=admin_H, json={"personality_prompt": "Helpful bot", "is_active": True})
    
    # Question
    client.post(f"{BASE}/chat/channels/{channel_id}/messages", headers=student_H, json={"content": "Quels sont les cours du lundi ?"})
    time.sleep(2) # Wait for AI
    
    r = client.get(f"{BASE}/chat/channels/{channel_id}/messages", headers=student_H)
    msgs = r.json()
    ai_reply = next((m for m in reversed(msgs) if m["is_ai"]), None)
    check("AI Delegate automatically replies in chat", ai_reply is not None, ai_reply["content"] if ai_reply else "No reply")

print(f"\n{'━'*60}")
passed = sum(1 for r in RESULTS if r["pass"])
print(f"  FINAL: {passed}/{len(RESULTS)} checks passed")
print(f"{'━'*60}\n")
sys.exit(0 if passed == len(RESULTS) else 1)
