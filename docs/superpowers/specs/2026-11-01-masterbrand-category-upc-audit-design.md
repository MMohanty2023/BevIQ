# MasterBrand–Category Product UPC Audit

## Intent

BevIQ should perform a UPC-first review of MasterBrand records against Beer, Wine, Spirits, and RTD categorization records. UPC is the primary identity because one brand can have many different products. The audit should identify category UPCs absent from MasterBrand, then find likely product matches using brand, product/flavour, and size/pack details. When a product match is strong but the UPC differs or is missing, the MasterBrand UPC is shown as a suggested alternate UPC.

## Goals

- Audit all four categorization datasets against MasterBrand.
- Preserve leading-zero UPCs and distinguish missing UPCs from UPC mismatches.
- Treat exact UPC presence, UPC absence, and UPC conflicts as first-class audit outcomes.
- Keep every observed UPC, including duplicate and alternate UPCs, visible in the report.
- Match conservatively using normalized brand, product/flavour, and size/pack signals.
- Show source/category details, MasterBrand details, confidence, suggested UPC, and reason.
- Provide the result through the existing chat, API, UI table, and CSV export.
- Never silently modify MasterBrand or categorization data.

## Non-goals and safety

- No automatic UPC insertion, replacement, or deletion.
- No inference based on brand alone; one brand can contain many different products.
- Ambiguous or low-confidence matches remain unmatched/review-only.

## Approach

The approved approach is conservative review-only matching. Exact UPC and known alternate UPC checks run first and are reported as verified. UPCs present in categorization but absent from MasterBrand are reported with their complete source details. For remaining rows, candidate MasterBrand products are narrowed by normalized brand, then scored with separate product/flavour and size/pack comparisons. A suggestion is emitted only when the product identity is strong and the size/pack evidence is compatible; otherwise the row is reported as unmatched or manual review. Brand-only similarity never produces a suggested UPC.

## User-facing result

The audit quick action and `/api/upc-audit` return category, source row, source product details, MasterBrand product details, current UPC state, suggested UPC, alternate UPC, confidence, and review remarks. CSV export remains available for approved manual updates.

## Verification

Add focused tests for exact UPC presence, missing category UPC with a strong product match, mismatched UPC with a strong product match, and rejection of brand-only/size-conflicting candidates. Run the existing endpoint tests and the focused matching tests.
