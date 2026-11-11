# Untrained Brand Process Design

## Intent

Make the untrained-brand audit follow the user's fixed business process and expose each stage clearly in the read-only report.

## Process order

1. Treat `TrainedBrandsData.csv` as the correct/reference dataset.
2. Collect distinct valid UPCs from `AIMasterBrandData.csv` (the All Master Brand sheet).
3. Verify the All Master UPC population against Beer, Wine, Spirits, and RTD sheets in that order.
4. Calculate missing UPCs as reference UPCs that are absent from the trained UPC set.
5. Group those missing rows into unique normalized brand names, preserving display names, UPCs, and suppliers.
6. Return the unique untrained brand names and stage-wise counts for auditability.

The audit is read-only. UPCs are deduplicated globally across the reference sheets, while a brand's UPC list and supplier list are deduplicated within the final grouped record.

## Goals and non-goals

- Goal: one deterministic pipeline response with stage summaries, missing UPC records, and unique untrained-brand records.
- Goal: preserve the existing `/api/compare` endpoint and CSV export behavior.
- Non-goal: changing source CSV files, trained data, master data, or database records.
- Non-goal: fuzzy matching brand names; matching is based on normalized UPCs, and grouping uses normalized brand text.

## Approaches considered

- Patch only the existing `find_untrained_brands`: smallest diff, but intermediate process stages remain implicit and the current broken summary variables are easy to repeat.
- Adjust only endpoint labels/SQL: fast, but does not provide reliable staged grouping or a reusable audit result.
- **Selected: dedicated staged pipeline inside `find_untrained_brands`:** keeps the current API contract, makes the required order explicit, fixes undefined state, and returns auditable stage data without mutating data.

## Implementation calls

- The existing `ai_master` table is the configured All Master Brand sheet and will be labeled `All Master Brand` in the response.
- The final missing UPC set is the union of all five reference populations minus trained UPCs; duplicate UPCs across sheets produce one final UPC but retain all applicable source rows for brand grouping.
- Empty brand names are excluded from unique-brand output but remain counted in missing UPC totals.
- Existing search and limit parameters apply to final brand records; export receives the untruncated final records.

## Verification

Add unit coverage for stage order, UPC de-duplication, unique brand grouping, filtering/limiting, and the endpoint's read-only response. Run the focused tests and then the full project test suite.
