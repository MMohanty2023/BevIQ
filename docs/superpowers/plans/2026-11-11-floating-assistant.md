# Floating assistant implementation plan

**Goal:** Replace the current floating navigation shortcut with a real chat-panel toggle on every page.
**Design:** Reuse the existing chat DOM and request flow in a fixed bottom-right panel, initially closed. Dashboard is the initial page. Both floating launcher and AI Assistant navigation open the same panel; the launcher toggles it, and the close button/Escape close it. Keep the current page active, conversation/draft/attachments intact, synchronize aria-expanded and restore focus. Responsive sizing keeps controls inside mobile viewports. No backend or model changes.
**Validation:** Node behavior tests for toggle, focus, Escape and pending input; existing frontend contracts; real desktop/mobile browser checks with no model inference.
**Alternatives:** Retaining the navigation shortcut does not provide a toggle. Duplicating the chat would risk duplicate IDs and split history; reuse the original panel.

- [x] Add controller behavior tests and update the obsolete hidden-shortcut contract; observe failures.
- [x] Implement panel styling/markup, toggle controller and navigation integration.
- [x] Run Node/frontend tests and inspect desktop/mobile behavior in a real headless browser.
- [x] Restart the app with the final template and record evidence; no commit or publication requested.


## Verification
- Six Node behavior tests passed: toggle, repeated open, focus return, Escape, disabled/pending input and lightbox priority.
- All 37 frontend contract tests passed.
- Independent static review found no important regressions.
- Real isolated Chrome desktop (1280x900) and mobile (390x844) tests passed: initial Dashboard/closed panel, launcher visibility, open/close, page preservation, draft/history/attachment preservation, pending reply completion while closed, Escape, focus and single chat-input instance.
- Mobile panel bounds: left12/right378/top16/bottom760 within390x844; no browser runtime exceptions.
- Screenshots and the browser report saved in the system temporary directory as beviq-floating-check-desktop.png, beviq-floating-check-mobile.png and beviq-floating-check.json.
- Browser test waited for server readiness after an initial test-startup race. Final template is loaded by the running app.
