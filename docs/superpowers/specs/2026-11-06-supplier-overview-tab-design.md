# Supplier Overview Tab Design

## Intent

Move the supplier experience out of the general Dashboard into a dedicated `Supplier Overview` tab so the Dashboard remains focused on overall business metrics.

## Behavior

- Add a `Supplier Overview` navigation tab.
- Move the existing Supplier Directory section out of `tab-dashboard` into `tab-supplier-overview`.
- Preserve supplier search, filters, expandable supplier cards, brand counts, MasterBrand record counts, categories, and brand details.
- Continue loading supplier and supplier-brand data only from the existing AllMasterBrands-backed `/api/dashboard/suppliers` endpoint.
- Load supplier data when the new tab is opened; do not duplicate the supplier section on Dashboard.
- Keep existing Dashboard metrics and layout unchanged apart from removing the supplier card.

## Approach

Move the existing markup in the single-page `templates/index.html` tab structure and extend the existing tab-load hook. No new Flask route or duplicate backend query is needed.

## Non-goals

No new data source, separate HTML page, database schema change, or duplicate supplier widget on Dashboard.
