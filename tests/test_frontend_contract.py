from pathlib import Path


HTML = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")


def test_frontend_contains_dashboard_and_backend_status_hooks():
    assert "switchTab('dashboard'" in HTML
    assert 'id="tab-dashboard"' in HTML
    assert "/api/dashboard/overview" in HTML
    assert "active_backend" in HTML


def test_frontend_opens_directly_on_dashboard_without_landing_screen():
    assert 'id="beviq-landing"' not in HTML
    assert 'id="beviq-app"' in HTML
    assert "function enterBevIQ()" not in HTML
    assert "#beviq-app {\n            display: none;" not in HTML


def test_dashboard_navigation_places_dashboard_before_ai_assistant():
    nav = HTML.split('<div class="nav-tabs-wrapper"', 1)[1].split('</div>', 1)[0]
    assert nav.index("switchTab('dashboard'") < nav.index("switchTab('chat'")


def test_dashboard_exposes_chart_and_display_mode_controls():
    assert 'id="dashboard-chart-controls"' in HTML
    assert 'data-dashboard-chart="pie"' in HTML
    assert 'data-dashboard-chart="bar"' in HTML
    assert 'data-dashboard-chart="heatmap"' in HTML
    assert 'data-dashboard-display="percentage"' in HTML
    assert 'id="dashboard-visualization"' in HTML


def test_dashboard_has_native_visualization_and_floating_assistant_hooks():
    assert "dashboardVisualizationState" in HTML
    assert "renderDashboardVisualization" in HTML
    assert "renderDashboardPie" in HTML
    assert "renderDashboardBar" in HTML
    assert "renderDashboardHeatmap" in HTML
    assert 'id="dashboard-floating-assistant"' in HTML
    assert "dashboard-floating-assistant" in HTML


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


def test_frontend_separates_master_and_category_upc_pie_segments():
    for dataset in ("master", "beer", "rtd", "wine", "spirits"):
        assert f'id="dashboard-upc-{dataset}"' in HTML
    assert "Master Brand UPC" in HTML
    assert "Beer UPC" in HTML
    assert "RTD UPC" in HTML
    assert "Wine UPC" in HTML
    assert "Spirits UPC" in HTML


def test_frontend_explains_powerbi_metric_definitions_and_refresh_context():
    assert "Dataset UPC entries" in HTML
    assert "Distinct UPCs" in HTML
    assert "Category UPCs missing from AI Master" in HTML
    assert 'id="dashboard-missing-by-category"' in HTML
    assert 'id="dashboard-refresh-time"' in HTML


def test_frontend_uses_beverage_dashboard_title_and_explains_backend():
    assert "Beverage Dashboard" in HTML
    assert "dashboard-backend-detail" in HTML
    assert "primary_backend" in HTML
    assert "SQLite fallback is serving data" in HTML


def test_dashboard_loads_heavy_sections_progressively_and_reuses_requests():
    assert "const dashboardRequestCache = new Map()" in HTML
    assert "getDashboardData('/api/dashboard/metrics').catch" in HTML
    assert "loadDashboardMetrics();" in HTML
    assert "loadDashboardMissing();" in HTML
    assert "async function loadDashboardMissing()" in HTML


def test_dashboard_contains_supplier_directory_card_hooks():
    assert 'id="dashboard-supplier-total"' in HTML
    assert 'id="dashboard-supplier-search"' in HTML
    assert 'id="dashboard-supplier-directory"' in HTML
    assert "/api/dashboard/suppliers" in HTML
    assert "brand_count" in HTML
    assert "brand_names" in HTML
    assert "toggleSupplierCard" in HTML
    assert "NA" in HTML


def test_dataset_upc_kpi_has_no_explanatory_subtitle():
    kpi = HTML.split('<h3>Dataset UPC entries</h3>', 1)[1].split('</div>', 2)[0]
    assert 'dashboard-total-upcs' in kpi
    assert 'dashboard-subtle' not in kpi


def test_frontend_exposes_persistent_light_dark_theme_toggle():
    assert 'id="theme-toggle"' in HTML
    assert "localStorage.getItem('beviq_theme')" in HTML
    assert "data-theme=\"light\"" in HTML
    assert 'class="theme-choice theme-choice--light"' in HTML
    assert 'class="theme-choice theme-choice--dark"' in HTML
    assert 'title="Light mode"' in HTML
    assert 'title="Dark mode"' in HTML
    assert 'theme-toggle__label' not in HTML
    assert "data-active-theme" in HTML
    assert "MySQL schema" in HTML


def test_master_brand_results_render_image_urls_on_existing_search_page():
    assert "function getMasterBrandImageUrl(row, columns)" in HTML
    assert "function renderMasterBrandResults(data)" in HTML
    assert "master-brand-result-media" in HTML
    assert "master-brand-results" in HTML
    assert "image_url" in HTML


def test_master_brand_image_renderer_validates_urls_and_handles_broken_images():
    assert "http:" in HTML
    assert "https:" in HTML
    assert "onerror" in HTML
    assert "this.remove()" in HTML


def test_master_brand_images_support_hover_zoom_and_same_page_lightbox():
    assert ".master-brand-result-media img:hover" in HTML
    assert "openMasterBrandImage" in HTML
    assert 'id="master-brand-image-lightbox"' in HTML
    assert "closeMasterBrandImage" in HTML
    assert "Escape" in HTML


def test_master_brand_thumbnail_frame_does_not_add_image_background():
    assert ".master-brand-result-media {" in HTML
    assert "background:transparent" in HTML
    assert "border:0" in HTML


def test_chat_welcome_message_is_friendly_and_general_purpose():
    assert "👋 <strong>Welcome to BevIQ!</strong>" in HTML
    assert "beverage data and everyday questions" in HTML
    assert "chat with me in English or Hinglish, ask anything" in HTML
    assert "Just type your question and let's get started! 😊" in HTML
    assert "UPC audits are review-only" not in HTML


def test_theme_toggle_uses_mode_specific_accessible_color_tokens():
    assert "--theme-toggle-bg: #111827" in HTML
    assert "--theme-toggle-bg: #f1f5f9" in HTML
    assert ".theme-choice[aria-pressed=\"true\"]" in HTML
    assert "var(--theme-choice-selected)" in HTML
    assert 'html[data-theme="light"] .studio-title' in HTML
    assert 'html[data-theme="light"] .dashboard-card' in HTML
    assert '@media (max-width: 900px)' in HTML
    assert 'html[data-theme="light"] #tab-dashboard > .dashboard-grid > div:first-child .studio-title' in HTML
    assert 'html[data-theme="light"] .brand-title' in HTML
    assert 'html[data-theme="light"] .nav-tab-btn.active' in HTML
    assert '.nav-tabs-wrapper' in HTML and 'overflow-x: auto' in HTML
