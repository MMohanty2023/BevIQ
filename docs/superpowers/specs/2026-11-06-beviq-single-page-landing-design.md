# BevIQ Single-Page Landing Design

## Intent

When `app.py` starts, the browser should show the supplied BevIQ landing artwork first. Clicking the BevIQ artwork should transition in the same browser page to the existing application UI.

## Goals

- Keep the current Flask entry point and existing application features intact.
- Show a full-screen, responsive landing view before the existing app view.
- Make the BevIQ artwork itself the clear click target.
- Render the existing dashboard, AI Assistant, Master Brands, Comparison Studio, and Datasets UI after the click without opening a new tab.

## Non-goals

- No changes to dashboard APIs, database behavior, AI Assistant behavior, or image search behavior.
- No external navigation or new browser window.
- No modification of the source artwork.

## Approaches considered

1. A separate Flask route/template for the landing page: clean separation, but requires a second URL and navigation handling.
2. A landing overlay above the existing app: keeps one URL, but the app would initialize behind the overlay and could trigger unnecessary API work.
3. A single-page landing/app state switch: keeps one URL, delays the existing app until the user enters, and preserves the current app markup in the same document. This is the selected approach.

## Design

The root template will contain a full-screen landing container and the current application container. The current application container starts hidden. Clicking the landing artwork hides the landing container, reveals the application container, and starts the existing client initialization once. The landing uses responsive `object-fit: contain` styling with the existing dark visual language.

## Verification

Verify the root page initially shows only the landing view, clicking the artwork reveals the existing app in the same page, and the existing frontend contract tests continue to pass.
