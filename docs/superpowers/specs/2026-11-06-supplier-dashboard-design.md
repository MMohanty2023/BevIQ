# Supplier Dashboard Design

## Intent

Upgrade the existing Supplier Directory into a complete Supplier Dashboard section driven by the live `AIMasterBrandData`/`MasterBrandData` table. Users should see the unique supplier total, supplier-level brand and record totals, searchable supplier and brand names, and expandable brand-level record counts.

## Goals and constraints

- Keep the current Master Brands section and search behavior unchanged.
- Calculate supplier, brand, and record counts dynamically from the active database table.
- Normalize blank/null-like supplier and brand values consistently with the existing supplier directory (`NA` for missing suppliers; missing brands excluded from brand counts).
- Preserve the existing bounded related-record preview for performance.
- Keep the UI responsive and accessible through expandable buttons and live search.

## Approach

Extend the existing `/api/dashboard/suppliers` backend response with `brand_details`, each containing a display name and record count. Update the existing Supplier Directory card to render those details and filter on either supplier or brand text. This reuses the current live-data path and avoids shipping the full Master Brand table to the browser.

## Non-goals

No changes to Master Brand search, database schema, data ingestion, or unrelated dashboard metrics.

## Success criteria

The API returns accurate unique supplier and brand counts plus per-brand record counts; the dashboard displays them, supports supplier/brand search, and expands each supplier without affecting the existing Master Brands tab.
