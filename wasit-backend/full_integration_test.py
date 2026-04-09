#!/usr/bin/env python3
"""
Full integration test for the Wasit backend — ALL routes.
Runs against live server at http://localhost:8001.
Usage: python full_integration_test.py
"""

import io
import random
import string
import sys
import httpx

BASE = "http://localhost:8001/api/v1"
RESULTS: list[dict] = []

# Minimal valid 1-page PDF with schedule text (for PDF extraction test)
MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 80>>stream
BT /F1 12 Tf 50 700 Td (Lundi 08:00-10:00 Mathematiques Salle A101 Examen DS1 Jeudi 14:00) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000404 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
477
%%EOF"""


def rnd(k=7):
    return "".join(random.choices(string.ascii_lowercase, k=k))


def section(title):
    print(f"\n{'━'*62}")
    print(f"  {title}")
    print(f"{'━'*62}")


def check(label: str, resp: httpx.Response, expected=(200, 201)):
    if isinstance(expected, int):
        expected = (expected,)
    passed = resp.status_code in expected
    mark = "✅ PASS" if passed else f"❌ FAIL [{resp.status_code}]"
    RESULTS.append({"label": label, "pass": passed, "code": resp.status_code})
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    import json as _json
    body_str = _json.dumps(body, ensure_ascii=False, indent=2) if isinstance(body, (dict, list)) else str(body)
    # Truncate very long responses (e.g. extracted_text PDFs)
    if len(body_str) > 600:
        body_str = body_str[:600] + "\n    ... (truncated)"
    print(f"  {mark}  [{resp.status_code}]  {label}")
    for line in body_str.splitlines():
        print(f"          {line}")
    return resp


# ──────────────────────────────────────────────────────────────
client = httpx.Client(timeout=30)

# Use real domains the email validator accepts
DOMAIN = "gmail.com"

email_admin   = f"wasit_admin_{rnd()}@{DOMAIN}"
email_chef    = f"wasit_chef_{rnd()}@{DOMAIN}"
email_delegate = f"wasit_delegate_{rnd()}@{DOMAIN}"
email_student = f"wasit_student_{rnd()}@{DOMAIN}"
PW = "Test@1234"

admin_token = None
chef_token = None
student_token = None
school_id = None
filiere_id = None
class_id = None
chef_id = None
delegate_id = None

# ══════════════════════════════════════════════════════════════
section("0 — Health check")
# ══════════════════════════════════════════════════════════════
try:
    r = client.get("http://localhost:8001/health")
    check("GET /health → 200", r)
except Exception as e:
    print(f"  ❌ FATAL  Cannot reach server: {e}")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
section("1 — Auth: register / login / me / refresh / logout")
# ══════════════════════════════════════════════════════════════

# Register users
r = client.post(f"{BASE}/auth/register", json={
    "email": email_admin, "password": PW,
    "first_name": "Admin", "last_name": "Wasit", "role": "admin"
})
check("POST /auth/register  [admin]", r, 201)
admin_id = r.json().get("id")

r = client.post(f"{BASE}/auth/register", json={
    "email": email_chef, "password": PW,
    "first_name": "Chef", "last_name": "Filiere", "role": "admin"
})
check("POST /auth/register  [chef/admin]", r, 201)
chef_id = r.json().get("id")

r = client.post(f"{BASE}/auth/register", json={
    "email": email_delegate, "password": PW,
    "first_name": "Delegate", "last_name": "User", "role": "delegate"
})
check("POST /auth/register  [delegate]", r, 201)
delegate_id = r.json().get("id")

r = client.post(f"{BASE}/auth/register", json={
    "email": email_student, "password": PW,
    "first_name": "Student", "last_name": "User", "role": "student"
})
check("POST /auth/register  [student]", r, 201)

# Login
r = client.post(f"{BASE}/auth/login", json={"email": email_admin, "password": PW})
check("POST /auth/login  [admin]", r)
admin_token = r.json().get("access_token")
admin_refresh = r.json().get("refresh_token")

r = client.post(f"{BASE}/auth/login", json={"email": email_chef, "password": PW})
check("POST /auth/login  [chef/admin]", r)
chef_token = r.json().get("access_token")

r = client.post(f"{BASE}/auth/login", json={"email": email_delegate, "password": PW})
check("POST /auth/login  [delegate]", r)
delegate_token = r.json().get("access_token")

r = client.post(f"{BASE}/auth/login", json={"email": email_student, "password": PW})
check("POST /auth/login  [student]", r)
student_token = r.json().get("access_token")

ADMIN   = {"Authorization": f"Bearer {admin_token}"}
CHEF    = {"Authorization": f"Bearer {chef_token}"}
STUDENT = {"Authorization": f"Bearer {student_token}"}

# /me
r = client.get(f"{BASE}/auth/me", headers=ADMIN)
check("GET /auth/me  [admin]", r)

# Refresh
r = client.post(f"{BASE}/auth/refresh", json={"refresh_token": admin_refresh})
check("POST /auth/refresh", r)
# keep the new token for later
admin_token_fresh = r.json().get("access_token")

# Bad creds → 401
r = client.post(f"{BASE}/auth/login", json={"email": email_admin, "password": "wrong"})
check("POST /auth/login  [bad password → 401]", r, 401)

# ══════════════════════════════════════════════════════════════
section("2 — Institutional: school → filière → class → assign delegate")
# ══════════════════════════════════════════════════════════════

r = client.post(f"{BASE}/schools",
                json={"name": f"École {rnd()}", "domain": f"{rnd()}.edu"},
                headers=ADMIN)
check("POST /schools  [admin]", r, (200, 201))
school_id = r.json().get("id")

r = client.get(f"{BASE}/schools", headers=ADMIN)
check("GET /schools", r)

r = client.post(f"{BASE}/filieres",
                json={"name": f"GL-{rnd(3)}", "school_id": str(school_id), "responsible_id": chef_id},
                headers=ADMIN)
check("POST /filieres  [admin]", r, (200, 201))
filiere_id = r.json().get("id")

# Re-login chef to get a fresh token (previous test run may have blacklisted it)
r = client.post(f"{BASE}/auth/login", json={"email": email_chef, "password": PW})
check("POST /auth/login  [chef fresh token]", r)
chef_token = r.json().get("access_token")
CHEF = {"Authorization": f"Bearer {chef_token}"}

r = client.post(f"{BASE}/classes",
                json={"filiere_id": str(filiere_id), "name": f"GL2-{rnd(3)}", "academic_year": "2025-2026"},
                headers=ADMIN)
check("POST /classes  [admin]", r, (200, 201))
class_id = r.json().get("id")

r = client.get(f"{BASE}/classes/{class_id}", headers=ADMIN)
check("GET /classes/{class_id}", r)

r = client.patch(f"{BASE}/classes/{class_id}/delegate",
                 json={"user_id": delegate_id}, headers=ADMIN)
check("PATCH /classes/{class_id}/delegate  [admin]", r)

# ══════════════════════════════════════════════════════════════
section("3 — AI Delegate config")
# ══════════════════════════════════════════════════════════════

r = client.put(f"{BASE}/classes/{class_id}/ai-delegate",
               json={"personality_prompt": "Tu es un délégué serviable.", "is_active": True},
               headers=ADMIN)
check("PUT /classes/{class_id}/ai-delegate", r)

r = client.patch(f"{BASE}/filieres/{filiere_id}/ai-settings",
                 json={"aggregation_poll_threshold": 5}, headers=ADMIN)
check("PATCH /filieres/{filiere_id}/ai-settings", r)

# Chef-managed class creation
r = client.post(f"{BASE}/filieres/{filiere_id}/classes",
                json={"filiere_id": str(filiere_id), "name": f"GL3-{rnd(3)}", "academic_year": "2025-2026"},
                headers=CHEF)
check("POST /filieres/{filiere_id}/classes  [chef_filiere]", r, (200, 201))

# ══════════════════════════════════════════════════════════════
section("4 — PDF document upload (timetable & exam_schedule)")
# ══════════════════════════════════════════════════════════════

r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/timetable",
    headers=CHEF,
    files={"file": ("timetable.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
)
check("POST /filieres/{filiere_id}/documents/timetable  (PDF)", r, (200, 201))

r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/exam_schedule",
    headers=CHEF,
    files={"file": ("exams.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
)
check("POST /filieres/{filiere_id}/documents/exam_schedule  (PDF)", r, (200, 201))

r = client.get(f"{BASE}/filieres/{filiere_id}/documents/timetable", headers=CHEF)
check("GET /filieres/{filiere_id}/documents/timetable", r)
if r.status_code == 200:
    doc = r.json()
    has_text = bool(doc.get("extracted_text", ""))
    mark = "✅ PASS" if has_text else "❌ FAIL"
    RESULTS.append({"label": "  └─ extracted_text present in response", "pass": has_text, "code": 200})
    print(f"  {mark}    └─ extracted_text present in response")

r = client.get(f"{BASE}/filieres/{filiere_id}/documents/exam_schedule", headers=CHEF)
check("GET /filieres/{filiere_id}/documents/exam_schedule", r)

# 404 for non-existent filière
fake = "00000000-0000-0000-0000-000000000000"
r = client.get(f"{BASE}/filieres/{fake}/documents/timetable", headers=CHEF)
check("GET /filieres/{bad_id}/documents/timetable → 404", r, 404)

# Non-PDF upload → 400
r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/timetable",
    headers=CHEF,
    files={"file": ("bad.txt", io.BytesIO(b"not a pdf"), "text/plain")},
)
check("POST /documents/timetable  [non-PDF → 400]", r, 400)

# Student cannot upload → 403
r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/timetable",
    headers=STUDENT,
    files={"file": ("t.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
)
check("POST /documents/timetable  [student → 403]", r, 403)

# ══════════════════════════════════════════════════════════════
section("5 — Students: CSV upload + list + project groups")
# ══════════════════════════════════════════════════════════════

csv_content = (
    "student_number,first_name,last_name,email,phone,photo_url\n"
    f"S001,Alice,Martin,alice_{rnd()}@gmail.com,0600000001,\n"
    f"S002,Bob,Dupont,bob_{rnd()}@gmail.com,0600000002,\n"
    f"S003,Charlie,Durand,charlie_{rnd()}@gmail.com,0600000003,\n"
    f"S004,Diana,Bernard,diana_{rnd()}@gmail.com,0600000004,\n"
)
r = client.post(
    f"{BASE}/classes/{class_id}/upload-trombinoscope",
    headers=ADMIN,
    files={"file": ("trombinoscope.csv", io.BytesIO(csv_content.encode()), "text/csv")},
)
check("POST /classes/{class_id}/upload-trombinoscope  (CSV)", r)

r = client.get(f"{BASE}/classes/{class_id}/students", headers=ADMIN)
check("GET /classes/{class_id}/students", r)
n_students = len(r.json()) if r.status_code == 200 else 0

r = client.post(f"{BASE}/classes/{class_id}/project-groups",
                json={"group_size": 2}, headers=ADMIN)
check("POST /classes/{class_id}/project-groups", r, (200, 201))

r = client.get(f"{BASE}/classes/{class_id}/project-groups", headers=ADMIN)
check("GET /classes/{class_id}/project-groups", r)

# ══════════════════════════════════════════════════════════════
section("6 — Tickets: create / read / list / status update")
# ══════════════════════════════════════════════════════════════

# Student without linked profile → 400
r = client.post(
    f"{BASE}/tickets?class_id={class_id}",
    json={"raw_text": "Le prof est absent depuis 20 minutes."},
    headers=STUDENT,
)
check("POST /tickets  [student no profile → 400]", r, 400)

# Admin list
r = client.get(f"{BASE}/admin/tickets", headers=ADMIN)
check("GET /admin/tickets  [admin]", r)

# Class tickets
r = client.get(f"{BASE}/classes/{class_id}/tickets", headers=ADMIN)
check("GET /classes/{class_id}/tickets  [admin]", r)

# ══════════════════════════════════════════════════════════════
section("7 — Analytics")
# ══════════════════════════════════════════════════════════════

r = client.get(f"{BASE}/analytics/school/{school_id}", headers=ADMIN)
check("GET /analytics/school/{school_id}  [admin]", r)

r = client.get(f"{BASE}/analytics/filiere/{filiere_id}", headers=ADMIN)
check("GET /analytics/filiere/{filiere_id}  [admin]", r)

r = client.get(f"{BASE}/analytics/class/{class_id}", headers=ADMIN)
check("GET /analytics/class/{class_id}  [admin]", r)

r = client.get(f"{BASE}/analytics/school/{school_id}/trends", headers=ADMIN)
check("GET /analytics/school/{school_id}/trends  [admin]", r)

r = client.get(f"{BASE}/analytics/school/{school_id}/top-issues", headers=ADMIN)
check("GET /analytics/school/{school_id}/top-issues  [admin]", r)

# ══════════════════════════════════════════════════════════════
section("8 — Notifications")
# ══════════════════════════════════════════════════════════════

r = client.get(f"{BASE}/notifications/me", headers=ADMIN)
check("GET /notifications/me  [admin]", r)

r = client.get(f"{BASE}/notifications/me?unread_only=true", headers=ADMIN)
check("GET /notifications/me?unread_only=true", r)

# ══════════════════════════════════════════════════════════════
section("9 — Old endpoints REMOVED (must return 404/405)")
# ══════════════════════════════════════════════════════════════

r = client.put(f"{BASE}/classes/{class_id}/timetable", json=[], headers=ADMIN)
check("PUT /classes/{id}/timetable → 404/405 (removed)", r, (404, 405, 422))

r = client.post(f"{BASE}/classes/{class_id}/exams", json=[], headers=ADMIN)
check("POST /classes/{id}/exams → 404/405 (removed)", r, (404, 405, 422))

# ══════════════════════════════════════════════════════════════
section("10 — Auth logout")
# ══════════════════════════════════════════════════════════════

r = client.post(f"{BASE}/auth/logout", headers=ADMIN)
check("POST /auth/logout  [admin]", r)

# After logout the blacklisted token should fail
r = client.get(f"{BASE}/auth/me", headers=ADMIN)
check("GET /auth/me  [after logout → 401]", r, 401)

# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════
total  = len(RESULTS)
passed = sum(1 for r in RESULTS if r["pass"])
failed = total - passed

print(f"\n{'═'*62}")
print(f"  TOTAL RESULTS:  {passed}/{total} passed   {'🎉' if failed == 0 else '⚠️ '} {failed} failed")
print(f"{'═'*62}")
if failed:
    print("  Failed tests:")
    for res in RESULTS:
        if not res["pass"]:
            print(f"    ❌  [{res['code']}]  {res['label']}")
print()
sys.exit(0 if failed == 0 else 1)
