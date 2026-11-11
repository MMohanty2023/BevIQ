# Master Brand Result Images

## Intent

When a Master Brand search result contains a valid product/brand image URL, show that image beside the result so users can recognize the matching item quickly.

The image option must appear on the existing Master Brands search page, alongside the current search form/results; no new page or tab is introduced.

## Approach

Keep the existing `/api/master-brands/search` response and table data unchanged. Update the frontend renderer to detect common image URL column names case-insensitively, validate HTTP(S) URLs, render a small thumbnail beside each matching result, and fall back to the current text table when no usable image exists.

## Scope

- Support searches by Master Brand ID, brand, UPC/alternate UPC, and product name through the existing endpoint.
- Keep all existing columns and values visible.
- Add broken-image handling so a bad URL does not break the search results.
- Add frontend contract tests for image detection and rendering hooks.

## Non-goals

- Change database schema or image URLs.
- Download, cache, proxy, or upload images through Flask.
- Hide rows that do not have images.
