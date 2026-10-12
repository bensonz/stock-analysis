# Event inbox — decisions

## D1. Source = 华尔街见闻 only, importance >= 3, 45 days forward
Owner choice. One `macro_info_ws(date=YYYYMMDD)` call per date. `重要性`
goes 1–4 (the midterm is 4). Default impact: imp>=4 → high, imp 3 → medium.

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
2. fuzzy (for hand-written entries): A-share impact dates within ±1 day AND
   the normalized names share a substring of >= 3 characters. Normalize =
   drop whitespace/punctuation, the region word, and `\d+月` / `\d+日` / years.
   ("美国9月CPI公布（日期待BLS确认）" vs "美国9月CPI年率" → "CPI").
False positive risk: two different releases on adjacent days sharing a
3-char token. Fuzzy drops are counted (`dup_fuzzy`) so it is visible.

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
owner not deciding. So the id carries the run (`…:<date>-<slot>`): it never
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
