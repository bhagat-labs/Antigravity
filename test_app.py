import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests
import json
import notifier
import scheduler

def run_tests():
    print("========================================")
    print("🧪 RUNNING CAMPUSBELL TEST SUITE")
    print("========================================")

    # 1. Test timetable integrity
    timetable = notifier.load_timetable()
    print(f"✓ Timetable loaded: {len(timetable)} total class entries.")
    assert len(timetable) == 20, f"Expected 20 classes across Mon-Fri, got {len(timetable)}"

    # Check days
    days = set(c["day"] for c in timetable)
    expected_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    assert days == expected_days, f"Days mismatch: {days} vs {expected_days}"
    print("✓ All 5 days (Monday to Friday) present.")

    # Check venues
    venues = set(c["venue"] for c in timetable)
    expected_venues = {"AB1-406C", "AB4-305", "AB1-202", "AB1-405", "AB1-613"}
    assert venues == expected_venues, f"Venues mismatch: {venues} vs {expected_venues}"
    print(f"✓ All campus venues matched: {venues}")

    # Check types
    types = set(c["classType"] for c in timetable)
    assert types == {"Lab", "Theory"}, f"Unexpected types: {types}"
    print("✓ Lab and Theory class types verified.")

    # 2. Test Notification Formatting
    mon_msg = notifier.format_daily_reminder("Monday")
    assert "AB1-406C" in mon_msg, "Venue AB1-406C missing in Monday message"
    assert "Basic Engineering" in mon_msg, "Basic Engineering missing in Monday message"
    print("✓ Daily reminder formatting verified for Monday.")

    fri_msg = notifier.format_daily_reminder("Friday")
    assert "AB1-613" in fri_msg, "Venue AB1-613 missing in Friday message"
    print("✓ Daily reminder formatting verified for Friday.")

    # 3. Test API endpoints
    base_url = "http://127.0.0.1:8000"
    
    # GET /
    r_index = requests.get(base_url + "/")
    assert r_index.status_code == 200, f"Failed GET /: {r_index.status_code}"
    assert "CampusBell" in r_index.text, "Index HTML missing brand name"
    print("✓ GET / (Dashboard HTML) verified (Status 200).")

    # GET /static/style.css & /static/app.js
    r_css = requests.get(base_url + "/static/style.css")
    assert r_css.status_code == 200, "Failed GET /static/style.css"
    r_js = requests.get(base_url + "/static/app.js")
    assert r_js.status_code == 200, "Failed GET /static/app.js"
    print("✓ Static CSS and JS assets verified (Status 200).")

    # GET /api/timetable
    r_tt = requests.get(base_url + "/api/timetable")
    assert r_tt.status_code == 200
    assert r_tt.json()["total_classes"] == 20
    print("✓ GET /api/timetable verified.")

    # GET /api/status
    r_st = requests.get(base_url + "/api/status")
    assert r_st.status_code == 200
    st_json = r_st.json()
    assert "scheduler" in st_json
    print("✓ GET /api/status verified.")

    # POST /api/send-now
    r_send = requests.post(base_url + "/api/send-now", json={"day": "Tuesday"})
    assert r_send.status_code == 200
    assert r_send.json()["success"] is True
    print("✓ POST /api/send-now verified.")

    # GET /api/logs
    r_logs = requests.get(base_url + "/api/logs")
    assert r_logs.status_code == 200
    assert len(r_logs.json()["logs"]) > 0
    print(f"✓ GET /api/logs verified ({len(r_logs.json()['logs'])} logs recorded).")

    print("========================================")
    print("🎉 ALL 10 TEST SUITES PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
