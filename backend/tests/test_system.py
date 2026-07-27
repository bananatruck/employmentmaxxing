"""
Verification script testing Employmentmaxxing FastAPI server endpoints & static assets.
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_health_endpoint():
    resp = httpx.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Employmentmaxxing"
    print("✅ Health check passed")

def test_root_index_html():
    resp = httpx.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert "<title>Employmentmaxxing" in resp.text
    print("✅ Root SPA index.html serving passed")

def test_static_assets():
    css_resp = httpx.get(f"{BASE_URL}/static/css/style.css")
    assert css_resp.status_code == 200
    assert "#010101" in css_resp.text or "font-family" in css_resp.text
    
    js_resp = httpx.get(f"{BASE_URL}/static/js/app.js")
    assert js_resp.status_code == 200
    assert "class" in js_resp.text or "document" in js_resp.text or "import" in js_resp.text
    print("✅ Static CSS & JS assets serving passed")

def test_jobs_api():
    resp = httpx.get(f"{BASE_URL}/api/jobs?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "total" in data
    assert len(data["jobs"]) <= 10
    print(f"✅ Jobs API returned {len(data['jobs'])} jobs out of {data['total']} total")

def test_jobs_api_filtering():
    resp = httpx.get(f"{BASE_URL}/api/jobs?job_types=AI/ML&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    for job in data["jobs"]:
        assert job["job_type"] == "AI/ML"
    print("✅ Jobs API filtering by category (AI/ML) passed")

def test_profile_api():
    resp = httpx.get(f"{BASE_URL}/api/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "skills" in data
    print(f"✅ Profile API returned user: {data['name']} ({len(data['skills'])} skills)")

def test_resume_endpoint():
    resp = httpx.get(f"{BASE_URL}/api/profile/resume")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "Keshav_Jindal.pdf"
    assert data["exists"] is True
    assert data["url"] == "/static/Keshav_Jindal.pdf"
    print("✅ Profile Resume PDF metadata endpoint passed")

def test_applications_crud():
    # 1. Fetch real jobs to get a valid job_id
    jobs_resp = httpx.get(f"{BASE_URL}/api/jobs?limit=1")
    assert jobs_resp.status_code == 200
    jobs_data = jobs_resp.json()
    assert len(jobs_data["jobs"]) > 0
    valid_job_id = jobs_data["jobs"][0]["id"]
    
    # 2. Create test application with valid job_id
    new_app = {
        "job_id": valid_job_id,
        "status": "applied",
        "notes": "Automated system test note"
    }
    create_resp = httpx.post(f"{BASE_URL}/api/applications", json=new_app)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["status"] == "success"
    app_id = created["id"]
    
    # 3. Update status to screening
    patch_resp = httpx.patch(f"{BASE_URL}/api/applications/{app_id}", json={"status": "screening", "notes": "Passed phone screen"})
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "success"
    
    # 4. Delete application
    del_resp = httpx.delete(f"{BASE_URL}/api/applications/{app_id}")
    assert del_resp.status_code == 200
    print("✅ Applications CRUD operations passed")

def test_analytics_api():
    resp = httpx.get(f"{BASE_URL}/api/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "total_scored" in data
    assert "jobs_by_type" in data
    print(f"✅ Analytics API returned {data['total_jobs']} jobs and metrics")

if __name__ == "__main__":
    test_health_endpoint()
    test_root_index_html()
    test_static_assets()
    test_jobs_api()
    test_jobs_api_filtering()
    test_profile_api()
    test_resume_endpoint()
    test_applications_crud()
    test_analytics_api()
    print("\n🎉 ALL FUNCTIONALITY VERIFICATION TESTS PASSED SUCCESSFULLY!")
