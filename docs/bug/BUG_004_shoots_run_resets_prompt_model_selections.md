# BUG_004 — Running a shoot resets the Prompt / Model picker on the Shoots page

> Status: Resolved

## Summary

On the Shoots dashboard, clicking **Run all pending** (or a per-row **Run** / **Re-run**)
reloads the whole page, and the picker the operator just set up — **Prompt**, **Model**,
and the count field — snaps back to its defaults (Prompt returns to "Select a prompt…").
Only the Channel/Date filters survive. Re-picking the prompt before every run is tedious
and error-prone.

## Steps to Reproduce

1. Open **Shoots** in the running app.
2. Pick a Prompt (and Model) in the picker.
3. Click **Run all pending** (or a row's **Run**).

## Expected vs Actual Behaviour

- **Expected:** the shoot is queued and the picker keeps the Prompt/Model/count the
  operator chose, ready for the next run.
- **Actual:** the page does a full reload and the Prompt resets to "Select a prompt…",
  Model resets to the default, and the count field disappears. (Channel/Date survive only
  because they ride in the redirect URL.)

## Root Cause

`POST /shoots/run` and `POST /shoots/run-all` ([app/routes/shoots.py](../../app/routes/shoots.py))
always answered with a `303` redirect to `/shoots?channel=…&date=…`. That is a full-page
navigation, so the browser re-renders the picker from scratch. The redirect URL carries
`channel` and `date`, but **not** `prompt_slug`, `model`, or `count`, so those fields come
back at their template defaults. The run buttons were plain form submits, not HTMX, so the
whole page round-tripped on every run.

## Acceptance Criteria

- [x] After running one or all pending shoots from the UI, the Prompt, Model, and count
      selections stay exactly as the operator set them.
- [x] The shoot list still updates to reflect the newly-queued job (and keeps
      auto-refreshing while it runs).
- [x] A success/error toast still appears.
- [x] Integration test: the HTMX run path returns the list partial + a toast header and
      does **not** re-render the prompt picker (proving the form is left untouched).
- [x] e2e test: selecting a prompt then clicking **Run all pending** leaves the prompt
      `<select>` on the chosen value, with no full-page reload.

---

## Resolution

Made the run actions HTMX-native instead of full-page form submits. The **Run** /
**Re-run** / **Run all pending** buttons now `hx-post` to the same endpoints, targeting
`#shoots-list` with an `outerHTML` swap (`hx-include="closest form"` carries the picker
values; the per-row Run passes its `source_dir` via `hx-vals`). The two routes now branch
on `is_htmx(request)`: for an HTMX request they return the existing
`partials/shoots/_list_response.html` (the channel tables + OOB date select) with a
`toast_trigger(...)` header — so only the list swaps and the picker `<form>` is never
re-rendered, leaving Prompt/Model/count intact. A plain (non-HTMX) POST still flashes and
`303`-redirects exactly as before, preserving the no-JS fallback (and the existing
redirect tests). Added an integration test for the HTMX path (returns the list partial +
`HX-Trigger`, no prompt picker in the body) and an e2e test (prompt `<select>` keeps its
value after Run all pending).
