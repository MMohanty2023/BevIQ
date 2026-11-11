# Untrained dataset summary repair
**Problem:** The API returns only source rows and the frontend only renders the table. Obsolete UPC cards have no corresponding computation; hidden is overridden by the strip's flex CSS.
**Fix:** Return total_records and case-insensitive unique_untrained_brands for all matching New/NeedToVerify rows, after brand search and before display limit. Keep duplicate source rows, SQL filters and exports. Render only Dataset Records and Unique Brands, show displayed/total rows, handle errors visibly and ignore stale search responses. No trained/UPC comparison is added.
- [x] Reproduce with failing count and loader behavior tests.
- [x] Implement backend metadata and frontend state handling.
- [x] Run relevant regressions and actual API/browser count checks.
- [x] Restart app and record verified results.


## Verification
- Four new backend regressions reproduced missing summary metadata before the fix.
- 51 Python tests passed (Untrained Dataset, frontend contracts and dashboard endpoints).
- 16 Node behavior tests passed (four summary/search/error/stale-response cases plus existing floating assistant cases).
- Scoped independent review found no important bugs.
- Live MySQL API returned total_records=116851 and unique_untrained_brands=36911 with250 displayed rows. A limit1 query returned the same summary.
- Real browser showed both counts and Showing250 of116851. Search for the first brand returned4 rows/1 unique brand; no-match search rendered0/0; clearing search restored full totals.
- No browser runtime exceptions. Screenshot and report are in temporary files beviq-untrained-check-desktop.png and beviq-untrained-check.json.
- App restarted with final code. Counts reflect the current brand search before pagination; repeated source rows remain present.
