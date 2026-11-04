# AGENTS.md

Instructions for AI coding assistants (Claude Code, Codex, Cursor, Copilot, etc.) working in this repo.

## Project

Wireless trailer lighting for a truck fleet (Team 11, ECE 460/461/462, Rose-Hulman). An in-cab module
(ICM) reads the truck's trailer lamp signals and sends them over ESP-NOW to one on-trailer module
(OTM) per lamp. Power, ground and brake stay hardwired.

Read these before doing anything:

- `docs/problem_definition.md`: what the system is, hardware, truck connection, constraints.
- `docs/system_plan.md`: every operation, its status (DECIDED / PROPOSED / OPEN) and the plan.
- `docs/pairing.md`: pairing flow, labels, app ↔ ICM BLE commands.

The docs are the source of truth. If code and docs disagree, point it out; don't silently pick one.

## Working rules

1. **Don't redesign without a go-ahead.** Propose changes, explain them, and wait for explicit
   approval before building. Batch related changes into one proposal.
2. **Only add what was asked.** No extra features, content, sections or "improvements" that weren't
   requested or discussed. If something else looks needed, mention it; don't add it.
3. **Never delete or remove content without agreement.** If a change moves text or code, say it's a
   move and do it in one edit so it doesn't look like a deletion.
4. **Fix only the stated problem.** A compile fix is not a design change. Keep edits minimal.
5. **Don't guess hardware facts.** Pinouts, part numbers and ratings come from the schematics,
   datasheets or wiring diagrams. Say when something is unverified.
6. **Be direct and concise.** Short answers, no filler.
7. **Decisions go in the docs.** When a decision is made, update its item in `docs/system_plan.md`
   (status and plan). When walking through open items, ask one question at a time, in order.
8. **Requirements:** one requirement per row, each with a practical test. Tests must use available
   equipment (an oven up to 180 °C is available; a −40 °C freezer is not).
9. **Don't commit or push unless asked.**

## Coding standard: MISRA C:2025

All firmware in `src/` and `include/` must follow **MISRA C:2025** (the current edition, March 2025),
with compliance claimed per **MISRA Compliance:2020**.

- **Our code** (`src/`, `include/`) must comply. Write new code to the standard. Flag existing code that
  doesn't comply rather than silently rewriting it (working rules 1-4 still apply).
- **ESP-IDF and FreeRTOS are "adopted code":** they are not MISRA compliant and are excluded from the
  compliance check. Don't modify them.
- **Deviations:** where our code must break a rule (e.g. ESP-IDF macros such as `ESP_ERROR_CHECK`,
  ESP-IDF types, compiler extensions such as `__attribute__((packed))`), keep it to the smallest
  scope and document it in a comment: rule number and reason.
- **Typical points to watch:** fixed-width types (`<stdint.h>`), no implicit narrowing or
  signed/unsigned conversions, every `switch` has a `default`, no dynamic memory after init, no
  recursion, check every return value (e.g. `esp_err_t`), no unused code or parameters.
- **Checking:** run a MISRA static analyzer (e.g. Cppcheck's MISRA add-on) on `src/` and `include/` only.

## Firmware

- ESP32-S3-WROOM-1U-N8 on both boards, ESP-IDF framework, built with PlatformIO in VS Code.
- Planned: separate builds, `[env:icm]` (`-DROLE_ICM`) and `[env:otm]` (`-DROLE_OTM`), sharing
  `comm_protocol.h` and `app_config`. See `docs/system_plan.md` item 1.
- Pin assignments in the code don't yet match the schematics; check the schematics before using pins.
