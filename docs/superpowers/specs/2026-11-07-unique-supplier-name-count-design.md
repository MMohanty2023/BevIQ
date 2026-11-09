# Unique Supplier Name Count Design

## Intent

Count one supplier once in the Trained Dataset even when the same supplier appears with multiple supplier codes. Brands and dataset records remain separate metrics.

## Approach

Use a normalized supplier name (`TRIM` + case-insensitive comparison) as the distinct-count key instead of `SupplierCode`. This matches the existing Supplier Overview grouping behavior and avoids maintaining a manual supplier-code mapping table.

## Scope

- Update the Trained Dataset summary query's `total_suppliers` metric.
- Preserve `total_brands`, record counts, supplier/brand details, and all other metrics.
- Treat blank or placeholder supplier names as excluded from the supplier count, consistent with the current blank-code behavior.
- Add a regression test proving multiple supplier codes with one supplier name count as one supplier.

## Acceptance criteria

For rows with supplier name `Acme Imports` and supplier codes `A1`, `A2`, and `A3`, the summary reports `total_suppliers == 1`. Distinct supplier names still count separately.
