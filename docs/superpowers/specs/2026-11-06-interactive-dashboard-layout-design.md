# Interactive Dashboard Layout Design

## Intent

Make the existing dashboard more visual without changing its API or breaking the existing AI Assistant. The main navigation order will be Dashboard first and AI Assistant second.

## User experience

- Navigation order: Dashboard, AI Assistant, Master Brands, Comparison Studio, Datasets & Schema.
- Dashboard controls at the top select Pie, Bar, Heatmap, or the existing overview/table view.
- A Count / Percentage toggle changes the labels and values rendered by the selected visualization.
- Only the selected visualization changes; the same dashboard data and existing KPI sections remain available.
- A floating AI Assistant button sits at the dashboard bottom-right, gently animates vertically, and opens the existing AI Assistant tab only when clicked.

## Approaches

- Native SVG/CSS rendering: selected. It avoids adding a dependency, works with the current Flask template, and keeps the app self-contained.
- Chart.js: not selected because it adds a remote dependency and changes the project’s loading/runtime surface.
- Canvas components: not selected because they require more custom accessibility and responsive behavior than the dashboard needs.

## Constraints and non-goals

- Reuse the existing dashboard API responses and AI Assistant implementation.
- Do not auto-navigate to AI Assistant.
- Do not remove existing KPI, table, theme, or dashboard data functionality.
- Add frontend contract tests for navigation order, chart controls, count/percentage state, and floating assistant hooks.
