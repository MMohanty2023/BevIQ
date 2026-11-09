# Supplier Unique Brand Count Design

## Intent

Show a clear Supplier Overview based only on the `AllMasterBrands` dataset, so users can find each unique supplier and see how many unique brands belong to that supplier.

## Required output

- Total unique supplier count.
- One supplier entry per normalized supplier name.
- Supplier display name and supplier code when available.
- Unique brand count for each supplier.
- Total MasterBrand record count for each supplier, calculated from the same source.
- Actual brand categories associated with each supplier, calculated from the same source.
- Search by supplier name, with the existing supplier search preserved.

## Source and rules

- Source table: configured `all_brands` table loaded from `$ALLBrand_202610291524.csv` (`AllMasterBrands`).
- Do not use `ai_master` or `trained_brands` for supplier lists or supplier counts.
- Normalize supplier names by trimming and case-folding; display one readable name per normalized supplier.
- Count unique non-empty brand names per normalized supplier, case-insensitively.
- Aggregate non-empty `ProductCategory` values per supplier without duplicates.
- Treat blank/null-like suppliers as `NA` so they do not create duplicate blank entries.
- No dummy supplier or brand data and no data mutation.

## UI shape

Keep the existing Supplier Directory area, but make the primary presentation a simple summary: total suppliers at the top, followed by supplier name, supplier code, unique brand count, and record count. Keep the search input and make the visible supplier total update after filtering.

## Approach

Extend the existing `get_supplier_directory()` query/response and current Supplier Directory renderer. This reuses the already connected `all_brands` source and avoids a second supplier data path.

## Non-goals

No new supplier detail page, image gallery, training-status enrichment, or supplier relationships from other datasets in this change.
