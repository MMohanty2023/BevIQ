import app as app_module


def test_dashboard_metrics_endpoint_returns_live_payload(monkeypatch):
    monkeypatch.setattr(app_module.sql_engine, "get_dashboard_metrics", lambda: {
        "categories": {"beer": {"total_records": 2}},
        "overall_upc": {"missing_upcs": 1},
        "master_brand": {"total_records": 3},
    })

    response = app_module.app.test_client().get("/api/dashboard/metrics")

    assert response.status_code == 200
    assert response.get_json()["categories"]["beer"]["total_records"] == 2


def test_master_brand_search_accepts_alphanumeric_id(monkeypatch):
    captured = {}

    def fake_search_master_brands(**kwargs):
        captured.update(kwargs)
        return {"columns": ["id", "BrandName"], "records": [{"id": kwargs["master_id"]}], "total_matches": 1}

    monkeypatch.setattr(app_module.sql_engine, "search_master_brands", fake_search_master_brands)
    response = app_module.app.test_client().get("/api/master-brands/search?id=64836d6479db3373669996ae")

    assert response.status_code == 200
    assert captured["master_id"] == "64836d6479db3373669996ae"
    assert response.get_json()["records"][0]["id"] == "64836d6479db3373669996ae"


def test_master_brand_search_rejects_empty_filters():
    response = app_module.app.test_client().get("/api/master-brands/search")

    assert response.status_code == 400
    assert "search" in response.get_json()["error"].lower()
