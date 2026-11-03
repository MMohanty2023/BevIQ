from pathlib import Path


HTML = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


def test_frontend_contains_dashboard_and_backend_status_hooks():
    assert "switchTab('dashboard'" in HTML
    assert 'id="tab-dashboard"' in HTML
    assert "/api/dashboard/overview" in HTML
    assert "active_backend" in HTML


def test_frontend_contains_upload_preview_and_clear_loading_states():
    assert "previewSelectedDocument" in HTML
    assert "URL.createObjectURL" in HTML
    assert "bot-loading-indicator" in HTML
    assert "/api/dashboard/export/" in HTML


def test_frontend_contains_live_analytics_and_master_brand_search_hooks():
    assert "/api/dashboard/metrics" in HTML
    assert "dashboard-upc-donut" in HTML
    assert "dashboard-category-kpis" in HTML
    assert "dashboard-master-total" in HTML
    assert "/api/master-brands/search" in HTML
    assert "master-brand-search-form" in HTML
    assert "database-status-card" in HTML
