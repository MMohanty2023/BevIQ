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


def test_floating_assistant_shortcut_is_available_outside_chat():
    assert "getElementById('dashboard-floating-assistant')?.setAttribute('hidden', '')" in HTML
    assert "assistantShortcut.hidden = tabId === 'chat'" in HTML


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


def test_supplier_directory_renders_brand_record_counts_and_searches_brands():
    assert "brand_details" in HTML
    assert "Records by brand" in HTML
    assert "supplier.categories" in HTML
    assert "detail.categories" in HTML
    assert "Master Brand records" in HTML
    assert "Unique brands" in HTML
    assert "Search suppliers, codes, brands or IDs" in HTML
    assert "brandNames.some" in HTML


def test_supplier_overview_tab_owns_supplier_directory_and_dashboard_does_not():
    assert "switchTab('supplier-overview'" in HTML
    assert 'id="tab-supplier-overview"' in HTML
    dashboard = HTML.split('id="tab-dashboard"', 1)[1].split('<!-- SUPPLIER OVERVIEW -->', 1)[0]
    supplier_tab = HTML.split('id="tab-supplier-overview"', 1)[1].split('<!-- MASTER BRAND SEARCH -->', 1)[0]
    assert 'id="supplier-directory-card"' not in dashboard
    assert 'id="supplier-directory-card"' in supplier_tab


def test_supplier_overview_has_total_supplier_kpi_card():
    supplier_tab = HTML.split('id="tab-supplier-overview"', 1)[1].split('<!-- MASTER BRAND SEARCH -->', 1)[0]
    assert 'id="supplier-overview-total-suppliers-card"' in supplier_tab
    assert 'id="supplier-overview-total-suppliers"' in supplier_tab
    assert "Total Suppliers" in supplier_tab


def test_supplier_overview_has_clustered_supplier_chart_hooks():
    supplier_tab = HTML.split('id="tab-supplier-overview"', 1)[1].split('<!-- MASTER BRAND SEARCH -->', 1)[0]
    assert 'id="supplier-overview-clustered-chart"' in supplier_tab
    assert "renderSupplierClusteredChart" in HTML
    assert "Unique Brands" in supplier_tab
    assert "Master Brand Records" in supplier_tab


def test_supplier_overview_has_professional_directory_layout_hooks():
    supplier_tab = HTML.split('id="tab-supplier-overview"', 1)[1].split('<!-- MASTER BRAND SEARCH -->', 1)[0]
    for hook in (
        'class="supplier-overview-header"',
        'class="supplier-overview-eyebrow"',
        'class="supplier-overview-summary"',
        'class="supplier-filter-heading"',
        'class="supplier-filter-help"',
    ):
        assert hook in supplier_tab
    for hook in (
        'class="supplier-card__brand-count"',
        'class="supplier-card__category-list"',
        'class="supplier-brand-panel__header"',
    ):
        assert hook in HTML


def test_supplier_overview_loads_directory_when_tab_opens():
    switch_tab = HTML.split("function switchTab(tabId, btn)", 1)[1].split("function triggerQuickPrompt", 1)[0]
    assert "tabId === 'supplier-overview'" in switch_tab
    assert "loadSupplierDirectory()" in switch_tab


def test_supplier_overview_has_detail_filters_sorting_and_brand_drilldown_hooks():
    for hook in (
        "dashboard-supplier-category-filter",
        "dashboard-supplier-status-filter",
        "dashboard-supplier-sort",
        "filterSupplierDirectory",
        "loadSupplierBrandDetails",
        "/api/dashboard/supplier-brand-details",
        "available_images",
        "category_image_url",
        "supplier_code",
        "brand_code",
    ):
        assert hook in HTML


def test_supplier_filter_auto_opens_matching_supplier_brands():
    assert "const autoOpen = suppliers.length === 1;" in HTML
    assert "class=\"supplier-card${autoOpen ? ' is-open' : ''}\"" in HTML
    assert "aria-expanded=\"${autoOpen}\"" in HTML


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


def test_master_brand_result_places_image_before_details_and_enhances_frame():
    assert "grid-template-columns:96px minmax(0,1fr)" in HTML
    assert "${media}${table}" in HTML
    assert "box-shadow:0 8px 24px" in HTML


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


def test_master_brand_images_stay_inside_result_cards_with_placeholder_fallback():
    assert "master-brand-image-placeholder" in HTML
    assert "handleMasterBrandImageError" in HTML
    assert "${media}${table}" in HTML
    assert "Image unavailable" in HTML


def test_master_brand_lightbox_supports_preview_zoom():
    assert ".master-brand-image-lightbox img:hover" in HTML
    assert "transform:scale(1.16)" in HTML
    assert "transition:transform" in HTML


def test_trained_dataset_dashboard_has_navigation_data_and_chart_hooks():
    for hook in (
        "switchTab('trained-dataset'",
        'id="tab-trained-dataset"',
        'id="trained-total-brands"',
        'id="trained-total-suppliers"',
        'id="trained-total-images"',
        'id="trained-records-table"',
        'id="trained-global-search"',
        'id="trained-category-filter"',
        'id="trained-image-count-filter"',
        'id="trained-category-chart"',
        'id="trained-supplier-chart"',
        'id="trained-brand-chart"',
        'id="trained-detail-panel"',
        '/api/trained-dataset/records',
        '/api/trained-dataset/analytics',
        'trainedCategoryVisual',
    ):
        assert hook in HTML


def test_untrained_dataset_has_separate_navigation_page_and_unique_brand_hooks():
    for hook in (
        "switchTab('untrained-dataset'",
        'id="tab-untrained-dataset"',
        'id="untrained-total-missing-upcs"',
        'id="untrained-total-brands"',
        'id="untrained-brand-search"',
        'id="untrained-brands-table"',
        '/api/untrained-dataset',
        'loadUntrainedDataset',
    ):
        assert hook in HTML


def test_untrained_dataset_shows_total_records_and_unique_brand_count_cards():
    untrained_tab = HTML.split('id="tab-untrained-dataset"', 1)[1].split('<!-- TAB: COMPARISON STUDIO -->', 1)[0]
    assert 'class="untrained-summary-strip"' in untrained_tab
    assert 'id="untrained-total-records"' in untrained_tab
    assert 'id="untrained-total-brands"' in untrained_tab
    assert 'Dataset Records' in untrained_tab
    assert 'Unique Brands' in untrained_tab
    assert 'class="trained-summary-card"' not in untrained_tab


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
