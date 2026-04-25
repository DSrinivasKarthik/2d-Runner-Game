# 2D Runner - Detailed Implementation Checklist

This checklist converts the full audit into an execution plan with strict order, acceptance criteria, and verification steps.

## Legend

- [ ] Not started
- [x] Done
- Priority: P0 (critical), P1 (high), P2 (medium), P3 (low)

## Phase 0 - Baseline Safety

- [x] Keep and commit existing fullscreen frame-scaling update in game/app.py
  - Priority: P1
  - Acceptance:
    - Main app starts and exits cleanly.
    - No regression in normal windowed rendering.

## Phase 1 - Critical Runtime Reliability

- [ ] Fix legacy entrypoint crash in runnergame.py
  - Priority: P0
  - Problem:
    - File mixes a forwarder and stale inline game code; importing can crash.
  - Scope:
    - Keep runnergame.py as a thin legacy forwarder to main.run only.
    - Remove dead/duplicate stale code that executes at import time.
  - Acceptance:
    - `python runnergame.py` launches app.
    - `python -c "import runnergame"` does not raise NameError.

## Phase 2 - Core Gameplay Correctness

- [ ] Make gameplay movement and physics dt-based
  - Priority: P1
  - Problem:
    - update(dt) currently ignores dt for movement/scroll/physics.
  - Scope:
    - Scale horizontal accel, friction, gravity, and world scroll using dt.
    - Keep behavior close to current 60 FPS feel.
  - Acceptance:
    - Gameplay speed feels consistent when FPS changes.
    - No clipping through platforms from time-step changes.

- [ ] Fix first-jump responsiveness at scene start
  - Priority: P1
  - Problem:
    - First jump input can be dropped before ground state is established.
  - Scope:
    - Ensure player can jump immediately when logically grounded at start.
  - Acceptance:
    - Pressing jump right after entering gameplay triggers jump reliably.

## Phase 3 - UI Functionality + Accessibility

- [ ] Implement Show FPS option end-to-end
  - Priority: P2
  - Problem:
    - Setting exists but has no visible output.
  - Scope:
    - Render FPS overlay when setting is enabled.
    - Keep overlay readable in normal and high-contrast modes.
  - Acceptance:
    - Toggle immediately shows/hides FPS readout.

- [ ] Fix menu list clipping and improve scroll feedback
  - Priority: P1
  - Problem:
    - Options content clips near top/bottom in some selection states.
  - Scope:
    - Adjust list area/layout metrics to avoid hidden rows.
    - Add subtle overflow/scroll indicator if content exceeds visible area.
  - Acceptance:
    - All menu items remain reachable and readable.
    - No cropped text in top/bottom edge states.

- [ ] Fix credits interaction and visual overlap
  - Priority: P1
  - Problem:
    - Credits mouse handling bypasses normal menu handling.
    - Global title/tagline overlaps credits heading/scroll content.
  - Scope:
    - Keep interactive easter-egg click handling, but avoid blocking expected controls.
    - Render credits in a dedicated visual mode that removes conflicting overlays.
    - Respect high-contrast setting in credits color choices.
  - Acceptance:
    - Credits view is readable with no header collisions.
    - Esc and Back behavior remains clear and reliable.

## Phase 4 - Documentation and Alignment

- [ ] Update README command formatting and controls clarity
  - Priority: P2
  - Scope:
    - Replace invalid quote-style code snippets with fenced code blocks.
    - Clarify runner movement behavior (camera/world scroll model).
    - Correct/complete any missing TOC sections.
  - Acceptance:
    - New users can run game by following README exactly.

- [ ] Document currently unused config fields (or wire them up)
  - Priority: P3
  - Scope:
    - Add short note for currently unused fields (background image / obstacle data),
      or implement if quick and safe.
  - Acceptance:
    - No silent misleading config fields without explanation.

## Phase 5 - Regression and Visual QA

- [ ] Re-run scripted E2E flow
  - Priority: P1
  - Scope:
    - Main menu -> options/extras/credits -> gameplay -> back -> quit.
  - Acceptance:
    - No crashes, no stuck scene transitions.

- [ ] Refresh screenshots for all major views and compare
  - Priority: P1
  - Required views:
    - Main menu
    - Options (top and bottom selection)
    - Extras
    - Credits
    - Quit confirm
    - Gameplay base
    - Gameplay jump state
  - Acceptance:
    - No obvious overlap, clipping, or readability regressions.

## Commit Strategy (One Task Per Commit)

1. fix: legacy runnergame forwarder cleanup
2. fix: dt-based gameplay physics and scroll
3. fix: immediate jump readiness on scene start
4. feat: show FPS overlay in app loop
5. fix: menu list clipping and overflow indicator
6. fix: credits input handling and dedicated layout mode
7. docs: README command formatting and controls clarification
8. docs/fix: config usage notes (or implementation if done)
9. test/chore: regression script and refreshed screenshot set

After each commit:

1. Run focused smoke checks for changed area.
2. Push commit to `origin gameplay-mechanics`.
3. Continue to next item.
