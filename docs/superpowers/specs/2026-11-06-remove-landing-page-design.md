# Remove Landing Page Design

## Intent

When users open `/`, they should see the existing dashboard immediately instead of the first welcome/landing screen.

## Scope

- Remove the landing-page presentation from `templates/index.html`.
- Keep the existing dashboard markup, navigation, tabs, API calls, and styling intact.
- Preserve the Flask `/` route and its current template response.

## Approach

The selected approach is to make the existing dashboard section the default visible section and remove the landing-only view/transition behavior. This is lower risk than adding a new route or duplicating the dashboard template.

## Verification

Add/update a frontend contract test proving the landing screen is not presented and the dashboard remains present, then run the focused tests and the full test suite.
