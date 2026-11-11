# Draggable assistant launcher plan

**Goal:** Let the user drag the floating AI Assistant button anywhere within the viewport with a mouse or touch, retaining the chosen position across refresh.
**Design:** Use native Pointer Events with capture and a small movement threshold. A real click still toggles chat; releasing a drag suppresses the generated click. Clamp the launcher within visible bounds, restore/save safe x/y coordinates in localStorage, and reclamp on resize. Keep the existing chat DOM and position its panel near the launcher without clipping. Cancelled drags restore the original location. Keyboard activation remains available.
**Validation:** Extend Node behavior tests for drag vs click, boundaries, persistence, cancellation, keyboard and resize; rerun frontend checks; use real browser mouse/touch input and reload/resize checks. No model/backend changes.

- [x] Add failing drag behavior tests.
- [x] Implement pointer handling, safe position persistence and nearby panel layout.
- [x] Run behavior/contracts plus desktop/mobile browser validation.
- [x] Update guide and restart the running app with verified code.


## Verification
- 12 Node controller behavior tests passed, including six new drag/click/persistence/cancellation/resize/keyboard cases.
- All37 frontend contract tests passed.
- Independent static review found no important interaction bugs.
- Real Chrome mouse drag moved the launcher without toggling chat; localStorage coordinates matched and restored after a full page reload.
- Real viewport resize/edge drag kept the launcher bounded; real mobile touch drag moved it while preserving the open chat.
- Existing draft/history/attachment, pending reply, page navigation, focus and Escape browser checks still passed; one input instance and no runtime exceptions.
- Browser input simulation was given realistic frame timing so captured pointer movements were delivered before release.
- Desktop/mobile screenshots and report stored in temporary files beviq-drag-check-desktop.png, beviq-drag-check-mobile.png and beviq-drag-check.json.
- Running app restarted with final template. No model/backend changes or publication.
