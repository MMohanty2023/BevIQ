# Theme Toggle Enhancement Design

## Intent

Make the existing Light/Dark mode control more attractive, obvious, and easy to use without changing its current persistence or theme behavior.

## Goals

- Present Light and Dark as a compact pill-style control in the header.
- Make the current mode visually obvious with icon, label, color, and position.
- Preserve the existing `localStorage` preference and theme switching logic.
- Keep the control keyboard accessible and responsive on small screens.

## Non-goals

- No changes to the dashboard, chat, Ollama, or backend behavior.
- No new dependency or icon library.
- No change to the default dark theme.

## Approaches

1. Pill-style switch with `☀ Light` and `🌙 Dark` states (chosen): best balance of clarity, visual polish, and compact header space.
2. Two separate segmented buttons: clearer choices but uses more header width.
3. Icon-only button: smallest footprint but less understandable for new users.

The pill-style switch is chosen because this app already has a single theme toggle, and a labeled active state communicates both the current mode and the action without adding layout noise.

## Implementation

Update the existing header control styles and markup in `templates/index.html`. Keep the existing `applyTheme()` and `localStorage` behavior, but update its label, icon, tooltip, ARIA text, and active visual state. Add focused frontend contract checks for the labeled states and accessibility hooks.
