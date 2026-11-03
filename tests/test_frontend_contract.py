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
    assert "dashboard-upc-pie" in HTML
    assert "dashboard-category-kpis" in HTML
    assert "dashboard-master-total" in HTML
    assert "/api/master-brands/search" in HTML
    assert "master-brand-search-form" in HTML
    assert "database-status-card" in HTML


def test_frontend_does_not_present_stale_totals_or_database_credentials():
    assert 'id="header-backend-status"' not in HTML
    assert 'id="header-record-status"' not in HTML
    assert 'id="header-security-status"' not in HTML
    assert "702,207 records" not in HTML
    assert "Password: Madhu@123" not in HTML


def test_frontend_uses_pie_chart_and_clear_upc_copy():
    assert 'id="dashboard-upc-pie"' in HTML
    assert "dashboard-upc-donut" not in HTML
    assert "UPC availability summary" in HTML
    assert "Category UPC availability" in HTML
    assert "mysql_schema_ready" in HTML


def test_frontend_uses_beverage_dashboard_title_and_explains_backend():
    assert "Beverage Dashboard" in HTML
    assert "dashboard-backend-detail" in HTML
    assert "MySQL schema" in HTML
