# Event inbox — decisions

## D1. Source = 华尔街见闻 only, importance >= 4, 45 days forward
Owner choice. One `macro_info_ws(date=YYYYMMDD)` call per date. `重要性`
goes 1–4 (the midterm is 4). Default impact: imp>=4 → high, imp 3 → medium.

Threshold raised 3 → 4 on 2026-10-12 (owner): the first live refresh at >=3
gave 91 items in 45 days (70 at imp 3), most of them product launches and
conferences. imp 4 keeps ~21 (midterm, APEC, port fees, EU Council). Lost at
imp 3: China CPI/PPI/trade prints and Fed speakers. Undecided items below the
threshold are dropped on refresh WITHOUT a ledger entry, so lowering
`MIN_IMPORTANCE` again brings them back.

## D2. "Errors" vs "empty days"
akshare builds a DataFrame from `data.items` and then indexes `public_date`;
with zero items that raises `KeyError('public_date')`. It means "nothing
listed for that date yet" (common 3+ weeks out). It is counted as
`empty_days`, not `fetch_errors`, so the error count means something. Any
other exception (incl. timeout) is a fetch error. Both are reported.

## D3. Date / tz mapping (wallstreetcn time is Beijing time)
event_calendar's `tz: US` means "impact on the first weekday AFTER `date`";
`tz: CN` means "impact on `date` (rolled forward off a weekend)".

- `地区 == 美国` → `tz: US`. `date` = the US calendar date:
  - Beijing time 00:01–09:29 → Beijing date − 1 (an evening/afternoon US
    release, e.g. FOMC 02:00 Beijing = previous US day). Impact = Beijing date.
  - Beijing time exactly 00:00:00 → treated as a date-only placeholder: the
    listed date IS the US date (midterm 11-03 → impact 11-04).
  - Otherwise (09:30–23:59, e.g. CPI 20:30) → listed date. Impact = next weekday.
- Every other region → `tz: CN` with the listed Beijing date.

Known limits: a non-US release after 15:00 Beijing (Europe) lands on the
listed day although that session has closed — really the next session. CN
holidays are not modelled (same as event_calendar). A real US event at
00:00 Beijing is mistaken for a placeholder (off by one day). The owner can
correct `date`/`tz` inline; the heading's impact date is recomputed on the
next rewrite.

## D4. inbox_id
`wscn-<YYYYMMDD>-<key>`: date = listed Beijing date; key = the indicator code
from the link (`/calendar/KR2608052/overview` → `KR2608052`; it is a series id,
hence the date), else the first 8 hex of sha1(地区|事件). Stable across
refreshes as long as wallstreetcn keeps the title.

## D5. Dedupe against events.json
1. exact: an event whose `inbox_id` equals the candidate's id;
2. fuzzy (for hand-written entries): same `tz`, A-share impact dates within ±1 day AND
   the normalized names share a substring of >= 3 characters. Normalize =
   drop whitespace/punctuation, the region word, and `\d+月` / `\d+日` / years.
   ("美国9月CPI公布（日期待BLS确认）" vs "美国9月CPI年率" → "CPI").
False positive risk: two different releases on adjacent days sharing a
3-char token. Fuzzy drops are counted (`dup_fuzzy`) so it is visible.
The same-tz condition was added after the first live refresh dropped
中国9月CPI同比 as a "duplicate" of the hand-written 美国9月CPI entry (region
words are stripped, leaving "CPI" on both). Remaining limit: two non-US
regions both map to CN, so e.g. 欧元区CPI vs a hand-written 中国CPI on the same
day would still collide.

## D6. Ledger
`tracking/event_inbox_ledger.json` records `keep`/`skip` (owner) and
`expired` (undecided item whose impact date passed). Exact id only. A
decided id never returns to the inbox.

## D7. Owner edits are parsed, then the file is rewritten
The file is regenerated from parsed items on every refresh (sorted by impact
date, T-n recomputed). Editable: checkbox, heading name, impact, direction,
date, tz, kind, note. `id:` and `src:` lines are machine-owned. A block whose
`id:` line is missing cannot be matched and is dropped with a warning.
Invalid values in a `[x]` item (e.g. `direction: bearish`) refuse that item's
promotion loudly; it stays in the inbox.

## D8. Doctor classification: env, with a per-run id
Neither kind fits exactly. Not invariant — nothing is contradictory, and
"code change needed" would be a lie. env puts it in the "需要人工操作"
bucket, which is right. But env promotes to "code change" after 3
consecutive occurrences, and a stable id would reach that in 1.5 days of the
owner not deciding. So the id carries the run (`event-inbox-undecided:<date>-<slot>`): it never
streaks, stays in the human-action bucket, and is still folded by check in
`--open`. The doctor reads the run's own `input/event_inbox.json` (written by
the pipeline step), not the live `tracking/event_inbox.md`, so a historical
sweep judges each run by what that run saw.

## D9. Pipeline order: promote, then refresh, then event_calendar
Promote first so items ticked since the last run appear in the same run's
report; refresh second so a just-decided item is already in the ledger.
Runs both slots (~10 s); overall deadline 60 s.

## D10. Doctor does not import event_inbox
`INBOX_REMIND_DAYS = 7` is duplicated in doctor.py; a test pins it to
`event_inbox.REMIND_WITHIN_DAYS`. Importing event_inbox would pull akshare and
the pricedb package into the doctor, a separate launchd job that exists to
keep reporting when the pipeline's dependencies are broken.

## D11. One doctor finding per run, not per item
The first live refresh put 51 undecided items inside the 7-day window
(importance >= 3 is noisy). One finding per item would bury every other line
of audit-result.md. So the check emits one finding whose title gives the count
and the nearest item, and whose detail lists them all.

## D12. AI triage: a separate, small, no-tools call on the pipeline's model
Owner decision 2026-10-12: "AI decides, owner can overrule." Not part of the
Phase-2 trading prompt (that prompt is ~70K tokens and its output contract is
trading decisions). `event_triage.call_model` reuses llm_client's config and
clients: `LLM_PROVIDER` openai or hybrid → the OpenAI-compatible
`OPENAI_MODEL` (DeepSeek V4 Pro today; in hybrid mode that model makes the
final trading decision too); anthropic → `ANTHROPIC_MODEL`. No tools, no web
search, temperature 0, max_tokens 16384 (reasoning headroom), timeout 180 s;
`finish_reason == "length"` is an error, not a partial answer. The prompt text
lives in `agents/EVENT_TRIAGE.md` (strategy belongs in agents/*.md); the code
appends today, the calendar as `event_calendar.upcoming(45 days)` sees it
(events.json AND formulaic events — otherwise the AI would re-add NFP/PMI),
and the candidate table. The spec's example ids are fake on purpose: the first
draft used the real midterm id, which then appeared in every prompt.

## D13. AI judges only; strict per-item validation
The reply is `{"decisions": {<inbox id>: {decision, impact, direction,
reason}}}`. The AI cannot add events or change name/date/tz/kind/source —
those come from the fetched row. Unknown ids are ignored and counted
(`unknown_ids`). An item whose judgement is missing or invalid (decision not
keep/skip, impact/direction outside the vocabulary, empty reason) stays `[ ]`
and is counted as a triage error. A failed call (exception, no `decisions`
object) leaves every item `[ ]` and records `error`. Nothing raises out of
`triage()`; the run continues. Reasons are collapsed to one line, 120 chars.

## D14. Triage once; failures retry
An item is sent only if it is `[ ]` AND has no ledger entry. After an AI
decision it has one, so it is never sent again; a failed item has none, so the
next run sends it again. Max 40 items per call (the rest wait a run) — a lowered
`MIN_IMPORTANCE` can bring back ~90 at once. AI-held items leave the inbox
silently once their A-share impact date has passed (`ai_retired`): too late to
flip, and their ledger entry already blocks them from returning.

## D15. Override detection: the ledger's snapshot, not the 🤖
Every AI ledger entry stores the fields as the AI left them (name, date, tz,
kind, impact, direction, note) plus decision/model/reason. `promote()` compares
the file's item against that snapshot: same mark (keep ↔ `[x]`, skip ↔ `[-]`)
and same fields → the AI decision stands, the item stays. Any difference → the
owner's version wins, recorded `decided_by: "owner"` with `overrode_ai`, and the
item leaves the inbox like any owner decision:
- `[x]` → the events.json entry is written or REPLACED (owner's fields, no
  `decided_by`), so an impact/direction/date edit on an AI keep updates it and
  an AI skip ticked `[x]` is promoted;
- `[-]` on an AI keep → the entry with that inbox_id is removed;
- `[ ]` on an AI item → entry removed, ledger `reopen`, the item stays as an
  ordinary undecided item (no 🤖) for the owner; the AI does not judge it again
  and the doctor's 7-day reminder applies.
The spec asked to compare mark/impact/direction; this compares every editable
field — a date/tz correction (D3 limits) must reach events.json too. The 🤖 and
the `ai:` line are display only (removing the 🤖 changes nothing). An invalid
owner edit (`direction: bearish`) is refused as before; the AI entry stays.
Owner marks set BEFORE the AI ran win trivially: promote runs first, and triage
only sends `[ ]` items.

## D16. AI keeps in events.json: `decided_by` + `reason` fields
An AI keep is the owner schema (`Item.to_event()`) plus `"decided_by": "ai"` and
`"reason"` (separate field, not folded into `notes`, so a later owner override
— which replaces the entry with the owner's version — drops both cleanly and the
report marker disappears with them). The model id lives in the ledger, not in
events.json. Owner-promoted entries carry no `decided_by` (same as hand-written
ones): absence means a human chose it.

## D17. Write order and idempotency
triage and promote both write events → ledger → inbox. The events change is an
upsert/remove keyed on inbox_id, so a crash after the events write re-applies
the same result next run. A crash between ledger and inbox write leaves the
inbox showing `[ ]` for an item whose ledger says AI — promote then reads that
as the owner un-ticking it (reopen). Accepted: it needs a crash in a ~1 ms
window, and the outcome is safe (the owner gets the decision).

## D18. Doctor: triage failure is ENV with a STABLE id
`check_event_inbox_triage` reads the run's `input/event_inbox.json`: a `triage`
record with `error`, or with `invalid`/`missing` items, or a `triage:` step
error → one finding `event-inbox-triage-failed`. Unlike D8's reminder, the id
is stable on purpose: failed items are retried every run, so a persistent
failure recurs each slot, and three in a row (PROMOTE_AFTER) is a config or
spec problem worth a fix, not weather. A run with nothing to triage
(`attempted: 0`) is clean. Runs before AI triage are skipped with a reason.
The existing undecided reminder (D8) stays as the backstop; with triage on it
only fires for items the AI failed on or the owner reopened.
