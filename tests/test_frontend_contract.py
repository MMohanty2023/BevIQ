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
