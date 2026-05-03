---
phase: 05-claude-routine-wiring
plan: 06
type: tdd
wave: 5
depends_on: [05-01, 05-02, 05-03, 05-04, 05-05]
files_modified:
  - routine/storage.py
  - routine/git_publish.py
  - routine/quota.py
  - routine/run_for_watchlist.py
  - routine/entrypoint.py
  - tests/routine/test_storage.py
  - tests/routine/test_git_publish.py
  - tests/routine/test_quota.py
  - tests/routine/test_run_for_watchlist.py
  - tests/routine/test_entrypoint.py
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
autonomous: true
requirements: [LLM-08, INFRA-01, INFRA-02, INFRA-03, INFRA-04]
provides:
  - "routine/storage.py — three-phase atomic write per Pattern #4 (Phase A: per-ticker JSONs at data/{date}/{TICKER}.json; Phase B: data/{date}/_index.json with run metadata; Phase C: data/{date}/_status.json LAST as the run-final sentinel). Per-file atomic write reuses watchlist/loader.py / ingestion/refresh.py tempfile + os.replace pattern; sort_keys=True JSON serialization (Phase 1/2 lock). Per-ticker write failures collected into failed_tickers; do NOT abort the run (LLM-08 cascade-prevention)."
  - "routine/git_publish.py — commit_and_push(date_str) per Pattern #11: git fetch origin main; git pull --rebase --autostash origin main; git add data/{date_str}/; git commit -m 'data: snapshot {date_str}'; git push origin main. Subprocess.run(check=True, capture_output=True, timeout=60) — fail-loudly discipline; CalledProcessError propagates to entrypoint.main exception handler."
  - "routine/quota.py — estimate_run_cost(watchlist) -> int + per-call token constants (PERSONA_INPUT_TOKENS_PER_TICKER=2000, PERSONA_OUTPUT_TOKENS_PER_TICKER=300, SYNTHESIZER_INPUT_TOKENS_PER_TICKER=5500, SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER=500, N_PERSONAS=6) + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000 per Pattern #6. Locked formula: n_tickers * (N_PERSONAS * (PERSONA_INPUT + PERSONA_OUTPUT) + SYNTHESIZER_INPUT + SYNTHESIZER_OUTPUT)."
  - "routine/run_for_watchlist.py — async def run_for_watchlist(watchlist, *, lite_mode, snapshots_root, computed_at) -> list[TickerResult]; sync across tickers (Pattern #3); async within ticker via run_persona_slate + synthesize. Per-ticker exceptions caught and converted to TickerResult with errors=[<repr>]; do NOT abort. Loads Snapshot from disk via existing ingestion infrastructure OR builds a snapshot from a fixture path (Wave 5 integration tests use mocked Snapshots)."
  - "routine/run_for_watchlist.TickerResult — Pydantic v2 BaseModel with: ticker, analytical_signals (list of 4 AgentSignals), position_signal (PositionSignal or None for failure), persona_signals (list of 6 AgentSignals; empty in lite mode), ticker_decision (TickerDecision or None for lite mode / failure), errors (list[str], empty when clean)."
  - "routine/entrypoint.py — def main() -> int per Pattern #1 + Pattern #11: load_watchlist; estimate_run_cost vs MARKETS_DAILY_QUOTA_TOKENS env (default 600_000) -> lite_mode bool; asyncio.run(run_for_watchlist(...)); write_daily_snapshot (three-phase per Pattern #4); commit_and_push (Pattern #11); return 0 on success / 1 on any uncaught exception. Best-effort write_failure_status on top-level exception. Standard logging.basicConfig at top."
  - "tests/routine/test_storage.py — ~10 tests: 3-phase write order verified (per-ticker first, _index second, _status LAST); atomic-write contract (no orphan .tmp on injected OSError); sort_keys serialization byte-stability; deterministic clock; round-trip parse equality; per-ticker write failure populates failed_tickers + status.success=False / partial=True; lite_mode field surfaces in status; mkdir parents; LF line ending discipline; llm_failure_count counted from persona data_unavailable + missing ticker_decision when lite_mode=False"
  - "tests/routine/test_git_publish.py — ~6 tests with subprocess.run mocked: happy path (5 calls in order: fetch / pull --rebase --autostash / add data/{date}/ / commit -m 'data: snapshot {date}' / push origin main); fetch failure raises CalledProcessError; push failure raises CalledProcessError; pull conflict (rebase fails) raises CalledProcessError; subprocess.run timeout=60 verified; cwd=str(repo_root) verified."
  - "tests/routine/test_quota.py — ~5 tests: estimate_run_cost(empty)==0; estimate_run_cost(30 tickers)==594000; per-ticker formula correctness; constants locked (N_PERSONAS=6; PERSONA_INPUT=2000; PERSONA_OUTPUT=300; SYNTHESIZER_INPUT=5500; SYNTHESIZER_OUTPUT=500; DEFAULT_QUOTA=600000); 30-ticker case under DEFAULT_QUOTA (594000<600000)."
  - "tests/routine/test_run_for_watchlist.py — ~6 tests covering: per-ticker pipeline integration (4 analytical signals scored + PositionSignal scored + 6 personas + synthesizer all sequenced); lite_mode skip path (skips persona/synthesizer LLM calls; returns analytical-only TickerResult); per-ticker exception isolation (1 ticker fails → its TickerResult has errors=[...]; other tickers succeed); single-ticker happy path with full mock chain"
  - "tests/routine/test_entrypoint.py — ~3 end-to-end integration tests: 5-ticker mock-LLM run (full pipeline; emits 5 per-ticker JSONs + _index.json + _status.json with success=True; git mocked; exit code 0); 5-ticker run with 1 LLM-failure (status.partial=False if writes succeed; llm_failure_count=1); top-level exception path (returns exit code 1, writes failure _status.json best-effort)"
  - "REQUIREMENTS.md updates: LLM-01..08 + INFRA-01..04 all marked Complete (12 entries flip to [x]); traceability table updated."
  - "ROADMAP.md updates: Phase 5 row marked Complete; Plans block populated with 6 plan checkbox entries (05-01..05-06)."
tags: [phase-5, entrypoint, storage, git-publish, quota, lite-mode, integration, llm-08, infra-01, infra-02, infra-03, infra-04, tdd, wave-5, phase-closeout]

must_haves:
  truths:
    - "routine/storage.py exports write_daily_snapshot(results, *, date_str, run_started_at, run_completed_at, lite_mode, total_token_count_estimate, snapshots_root=Path('data')) -> StorageOutcome AND _atomic_write_json (helper) AND write_failure_status(snapshots_root, date_str, started_at, error_msg) for the entrypoint best-effort failure path"
    - "Three-phase write order — Phase A FIRST: every TickerResult emits a per-ticker JSON at {snapshots_root}/{date_str}/{ticker}.json. Phase B SECOND: data/{date_str}/_index.json (run metadata). Phase C THIRD AND LAST: data/{date_str}/_status.json. Verified by mocking _atomic_write_json and asserting call order"
    - "Per-ticker write failure handling: if _atomic_write_json raises OSError on a ticker, that ticker is appended to failed_tickers; the loop continues; subsequent _index.json + _status.json reflect the failure (status.success=False, partial=True, failed_tickers contains the ticker)"
    - "_index.json schema: {date, schema_version=1, run_started_at, run_completed_at, tickers: [completed only], lite_mode, total_token_count_estimate}; written via _atomic_write_json with sort_keys=True"
    - "_status.json schema (LLM-08 closure): {success: bool, partial: bool, completed_tickers: list[str], failed_tickers: list[str], skipped_tickers: list[str], llm_failure_count: int, lite_mode: bool}"
    - "_status.json.success: True iff failed_tickers is empty (regardless of lite_mode); partial: True iff lite_mode OR failed_tickers is non-empty"
    - "_status.json.llm_failure_count: counts persona AgentSignals with data_unavailable=True (across all completed tickers) + adds 1 per ticker where ticker_decision is None AND lite_mode=False (synthesizer failure)"
    - "Atomic write contract: tempfile.NamedTemporaryFile(delete=False, dir=parent) → write → close → os.replace(tmp_path, path); on OSError tmp_path.unlink(missing_ok=True) THEN re-raise (mirror Phase 1/2/4 pattern)"
    - "JSON serialization: json.dumps(payload, indent=2, sort_keys=True) + '\\n' (Phase 1/2 lock); LF line ending; mkdir parents on parent dir"
    - "_atomic_write_json: when called twice on the same path with different payloads, the second call replaces atomically — no partial-state window"
    - "routine/git_publish.commit_and_push(date_str, *, repo_root=Path('.')) executes EXACTLY 5 subprocess.run calls in order: ['git', 'fetch', 'origin', 'main']; ['git', 'pull', '--rebase', '--autostash', 'origin', 'main']; ['git', 'add', f'data/{date_str}/']; ['git', 'commit', '-m', f'data: snapshot {date_str}']; ['git', 'push', 'origin', 'main']"
    - "Each subprocess.run call uses check=True, capture_output=True, text=True, timeout=60, cwd=str(repo_root); on CalledProcessError logs error + re-raises (caller handles)"
    - "git_publish does NOT use 'git add -A' (per Pattern #11 anti-pattern lock); does NOT skip the pull --rebase before push (race-condition guard locked)"
    - "routine/quota.py exports DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000 + constants {N_PERSONAS=6, PERSONA_INPUT_TOKENS_PER_TICKER=2000, PERSONA_OUTPUT_TOKENS_PER_TICKER=300, SYNTHESIZER_INPUT_TOKENS_PER_TICKER=5500, SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER=500} + estimate_run_cost(watchlist) -> int"
    - "estimate_run_cost formula: len(watchlist.tickers) * (N_PERSONAS * (PERSONA_INPUT + PERSONA_OUTPUT) + SYNTHESIZER_INPUT + SYNTHESIZER_OUTPUT) = n_tickers * (6 * 2300 + 6000) = n_tickers * 19800. 30-ticker case: 30 * 19800 = 594000 < 600000 (lite_mode=False under default quota)"
    - "estimate_run_cost(Watchlist with 0 tickers): returns 0; lite_mode logic at entrypoint sets lite_mode=False (0 < quota)"
    - "estimate_run_cost(Watchlist with 31 tickers): returns 31 * 19800 = 613800 > 600000 → lite_mode would be True"
    - "routine/run_for_watchlist.TickerResult Pydantic model: ticker (str), analytical_signals (list[AgentSignal] of length 4 by convention; can be empty on per-ticker failure), position_signal (PositionSignal | None), persona_signals (list[AgentSignal]; len=0 in lite_mode; len=6 otherwise), ticker_decision (TickerDecision | None; None in lite_mode), errors (list[str], default empty)"
    - "run_for_watchlist sync-across-tickers loop (Pattern #3): for each ticker in watchlist.tickers, await _run_one_ticker; on per-ticker exception, append TickerResult(ticker, errors=[repr(exc)]) and continue (DO NOT abort)"
    - "_run_one_ticker: scores 4 analytical analysts (sync, fast); scores PositionSignal (sync); IF lite_mode: returns TickerResult(persona_signals=[], ticker_decision=None); ELSE: builds persona context, awaits run_persona_slate, awaits synthesize, returns TickerResult"
    - "routine/entrypoint.main() -> int returns 0 on success, 1 on any top-level exception"
    - "entrypoint reads quota from os.environ.get('MARKETS_DAILY_QUOTA_TOKENS', str(DEFAULT_MARKETS_DAILY_QUOTA_TOKENS))"
    - "entrypoint sets lite_mode = (estimated > quota); logs 'token estimate: %d; quota: %d; lite_mode: %s' before run_for_watchlist"
    - "entrypoint loads watchlist via watchlist.loader.load_watchlist(); aborts with exit 1 if watchlist.tickers is empty (cannot run a no-ticker routine)"
    - "entrypoint orchestration order: load_watchlist → estimate_run_cost → run_for_watchlist (asyncio.run) → write_daily_snapshot → commit_and_push → return 0"
    - "entrypoint top-level except: catches BaseException; logs via logger.exception('routine failed'); calls write_failure_status(snapshots_root, date_str, run_started_at, error_msg) inside a nested try/except (NEVER let the failure-status write itself crash the routine); returns 1"
    - "Provenance per INFRA-07: routine/entrypoint.py docstring contains literal 'novel-to-this-project' (no virattt analog — orchestration layer); routine/storage.py docstring references the watchlist/loader.py atomic-write pattern; routine/git_publish.py docstring references Pattern #11 + the Anti-Pattern lock against 'git add -A'"
    - "End-to-end integration test (test_entrypoint.py): 5-ticker mock-LLM run produces exactly 5 per-ticker JSONs + 1 _index.json + 1 _status.json at the test's tmp_path/data/{date}/ folder; _status.json.success=True; _status.json.completed_tickers has length 5; _status.json.lite_mode=False (mock data has 5 tickers under quota); subprocess.run for git is mocked (no real commits)"
    - "End-to-end integration test (lite mode path): 35-ticker watchlist (forces estimate>quota) → routine runs in lite_mode; per-ticker JSONs have persona_signals=[] and ticker_decision=null; _status.json.lite_mode=True, partial=True"
    - "End-to-end integration test (one ticker LLM failure): 5-ticker run; one ticker has all 6 persona LLM calls fail → _status.json.llm_failure_count >= 6; _status.json.success=True (write succeeded; failure was at the LLM layer not the storage layer); status.partial=False if write succeeded for all 5 (LLM failure ≠ ticker write failure)"
    - "REQUIREMENTS.md: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, INFRA-01, INFRA-02, INFRA-03, INFRA-04 all flipped to [x] / Complete in the v1 list AND the traceability table"
    - "ROADMAP.md: Phase 5 row Status flipped from 'Pending' to 'Complete'; phase 5 plan list populated with 6 [x] entries (05-01..05-06)"
    - "Coverage ≥90% line / ≥85% branch on routine/storage.py AND routine/git_publish.py AND routine/quota.py AND routine/run_for_watchlist.py AND routine/entrypoint.py"
    - "Phase 1-4 + Wave 0-4 regression invariant: existing tests stay GREEN. Phase 5 closes complete; full repo regression GREEN with all 12 LLM-XX + INFRA-XX requirements satisfied"
  artifacts:
    - path: "routine/storage.py"
      provides: "_atomic_write_json + write_daily_snapshot (three-phase) + write_failure_status + StorageOutcome dataclass + _build_ticker_payload helper. ~140 LOC."
      min_lines: 100
    - path: "routine/git_publish.py"
      provides: "commit_and_push (5 sequential subprocess.run; check=True; timeout=60; cwd parameterized) + provenance docstring. ~70 LOC."
      min_lines: 50
    - path: "routine/quota.py"
      provides: "estimate_run_cost + 5 per-call token constants + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000. ~40 LOC."
      min_lines: 30
    - path: "routine/run_for_watchlist.py"
      provides: "TickerResult Pydantic model + _run_one_ticker async helper + run_for_watchlist async (sync-across-tickers loop). ~150 LOC."
      min_lines: 120
    - path: "routine/entrypoint.py"
      provides: "main() entry function + module-level docstring + asyncio.run + write_daily_snapshot + commit_and_push + best-effort failure path. ~100 LOC."
      min_lines: 80
    - path: "tests/routine/test_storage.py"
      provides: "≥10 tests covering 3-phase order; atomic-write contract; sort_keys serialization; failure-tracking; lite_mode field; LLM-08 _status.json schema; mkdir parents; round-trip; deterministic clock. ~300 LOC."
      min_lines: 250
    - path: "tests/routine/test_git_publish.py"
      provides: "≥6 tests with subprocess.run mocked: happy path 5-call sequence; fetch / pull / push failures each → CalledProcessError; check=True; timeout=60; cwd parameter. ~150 LOC."
      min_lines: 120
    - path: "tests/routine/test_quota.py"
      provides: "≥5 tests: empty watchlist → 0; 30-ticker → 594000; constants locked; 31-ticker → 613800 > default 600000; formula correctness over per-ticker arithmetic. ~80 LOC."
      min_lines: 60
    - path: "tests/routine/test_run_for_watchlist.py"
      provides: "≥6 tests: per-ticker pipeline integration; lite-mode skip path; per-ticker exception isolation; order preservation; sync across tickers; happy path single ticker. ~250 LOC."
      min_lines: 200
    - path: "tests/routine/test_entrypoint.py"
      provides: "≥3 end-to-end integration tests with mocked Anthropic + mocked git: 5-ticker happy path; lite-mode path (35-ticker watchlist forces lite_mode=True); top-level exception → exit 1 + best-effort failure status. ~250 LOC."
      min_lines: 200
    - path: ".planning/REQUIREMENTS.md"
      provides: "12 requirement entries flipped to Complete: LLM-01..08 + INFRA-01..04 (in both the v1 checklist AND the traceability table)"
      min_lines: 220
    - path: ".planning/ROADMAP.md"
      provides: "Phase 5 row Status updated to Complete; Phase 5 plan list populated with 6 [x] entries"
      min_lines: 270
  key_links:
    - from: "routine/entrypoint.py"
      to: "routine.{run_for_watchlist, storage, git_publish, quota} + watchlist.loader.load_watchlist + asyncio.run"
      via: "main() orchestrates the full pipeline; imports each sub-module's public surface"
      pattern: "from routine\\.(run_for_watchlist|storage|git_publish|quota) import"
    - from: "routine/run_for_watchlist.py"
      to: "analysts.{fundamentals, technicals, news_sentiment, valuation, position_adjustment} + routine.persona_runner.run_persona_slate + synthesis.synthesizer.synthesize"
      via: "per-ticker pipeline calls 4 analyst score() functions + position_adjustment.score() + (lite-mode-conditional) run_persona_slate + synthesize"
      pattern: "from analysts import|from routine\\.persona_runner import|from synthesis\\.synthesizer import"
    - from: "routine/storage.py"
      to: "watchlist/loader.py + ingestion/refresh.py atomic-write pattern (Phase 1/2 lock)"
      via: "_atomic_write_json mirrors tempfile + os.replace + sort_keys=True serialization"
      pattern: "tempfile\\.NamedTemporaryFile|os\\.replace"
    - from: "routine/storage.py"
      to: "synthesis.decision.TickerDecision + analysts.signals.AgentSignal + analysts.position_signal.PositionSignal"
      via: "_build_ticker_payload serializes via .model_dump(mode='json') for stable JSON output"
      pattern: "model_dump\\(mode=\"json\"\\)"
    - from: "routine/git_publish.py"
      to: "subprocess.run with shell=False (list form) + cwd parameter + check=True"
      via: "fail-loudly discipline per Pattern #11; CalledProcessError propagates to entrypoint.main exception handler"
      pattern: "subprocess\\.run\\(.*check=True"
    - from: "tests/routine/test_entrypoint.py"
      to: "tests.routine.conftest.mock_anthropic_client + isolated_failure_log + monkeypatch on subprocess.run + tmp_path for snapshots_root"
      via: "end-to-end integration with all external boundaries mocked: Anthropic SDK; git CLI; clock; data/ folder"
      pattern: "mock_anthropic_client|monkeypatch\\.setattr.*subprocess"
    - from: ".planning/REQUIREMENTS.md + .planning/ROADMAP.md"
      to: "Phase 5 closure"
      via: "12 LLM-XX + INFRA-XX requirements flipped to Complete; Phase 5 row marked Complete; plan list populated"
      pattern: "Complete|\\[x\\]"
---

<objective>
Wave 5 / LLM-08 + INFRA-01 + INFRA-02 + INFRA-03 + INFRA-04 closure: ship the routine entrypoint quintet — `routine/storage.py` (three-phase atomic write per Pattern #4), `routine/git_publish.py` (5-step git fetch/pull-rebase-autostash/add/commit/push per Pattern #11), `routine/quota.py` (estimate_run_cost + 5 per-call token constants + 600K default quota per Pattern #6), `routine/run_for_watchlist.py` (per-ticker async pipeline; sync across tickers per Pattern #3), `routine/entrypoint.py` (`main()` orchestration). Plus 5 test files (~30 tests total) covering the storage atomic-write contract, the git CLI sequence, the quota estimator, the per-ticker pipeline integration, and 3 end-to-end integration tests on the entrypoint with mocked Anthropic + mocked git. Plus REQUIREMENTS.md + ROADMAP.md updates flipping the 12 LLM-XX + INFRA-XX requirements to Complete.

Purpose: this plan closes Phase 5. After this plan ships, the routine can fire from a Claude Code Cloud Routine Mon-Fri 06:00 ET, load the watchlist, score 4 analyticals + PositionSignal per ticker, fan out 6 persona LLM calls per ticker via asyncio.gather, synthesize via 1 LLM call per ticker, write the daily snapshot folder atomically, and commit/push to GitHub. All 12 of Phase 5's requirements (LLM-01..08 + INFRA-01..04) close in one closeout. Phase 6 frontend (Phase 6) reads the data/{date}/ folder via raw.githubusercontent.com.

The three-phase storage write order (Pattern #4) is the most important storage discipline: per-ticker JSONs FIRST → _index.json SECOND → _status.json LAST. Reason: _status.json is the "this run is final" sentinel. Phase 6 frontend reads _status.json first; if absent, the snapshot is in-progress (or the routine crashed mid-write) and the frontend renders "snapshot pending" rather than potentially-corrupt partial data. Per-ticker write failures populate `failed_tickers` but do NOT abort the run — LLM-08 cascade-prevention discipline (one ticker's storage failure doesn't lose the other 29).

The 5-step git sequence (Pattern #11) is the fail-loudly discipline: fetch + pull --rebase --autostash BEFORE add + commit + push handles the manual+scheduled-run race condition (Pitfall #7). `git add data/{date_str}/` (NOT `git add -A`) scopes to the snapshot folder; `subprocess.run(timeout=60)` prevents hung-routine. CalledProcessError propagates to `main()` which logs + returns 1 (next morning's run is the retry — git failures are usually configuration issues that need human attention, not transient blips).

The lite-mode threshold (Pattern #6 + INFRA-02) is locked at 600_000 tokens (DEFAULT_MARKETS_DAILY_QUOTA_TOKENS) covering 30 tickers comfortably (594_000 estimate). User can override via `MARKETS_DAILY_QUOTA_TOKENS` env var. When estimate exceeds quota at run-start, the routine runs analyticals only — preserves quota for tomorrow. Mid-run quota overshoot policy is locked: NO recompute mid-loop (Anthropic SDK doesn't expose remaining quota; bailing creates inconsistent half-states). The status.json.llm_failure_count surfaces any 429-cascade in Phase 6 frontend so the user sees "12 LLM failures today" and investigates.

The per-ticker pipeline (Pattern #3 + 05-RESEARCH.md _run_one_ticker skeleton):
1. Score 4 analyticals + PositionSignal (sync, fast — no I/O after Snapshot loaded).
2. IF lite_mode: return TickerResult(persona_signals=[], ticker_decision=None).
3. ELSE: build persona context once; await run_persona_slate (6-call asyncio.gather fan-out); await synthesize (1 LLM call producing TickerDecision); return TickerResult.
4. Per-ticker uncaught exception: caught at run_for_watchlist outer loop; converted to TickerResult(ticker, errors=[repr(exc)]); other tickers continue (Pattern #4 cascade-prevention).

End-to-end integration tests with mocked Anthropic + mocked git: 3 tests are sufficient to lock the entrypoint contract. (a) 5-ticker happy path: routine fires, 5 per-ticker JSONs written, _index.json + _status.json written LAST, _status.json.success=True, exit 0, git "commits" 5 tickers (mocked). (b) Lite-mode path: 35-ticker watchlist forces estimate > quota; lite_mode=True; per-ticker JSONs have persona_signals=[] and ticker_decision=null; _status.json.lite_mode=True, partial=True. (c) Top-level exception: e.g., load_watchlist raises FileNotFoundError; main() returns 1; best-effort write_failure_status writes a _status.json with success=False (or fails silently if the snapshots_root isn't writable — captured by the nested try/except).

REQUIREMENTS.md + ROADMAP.md closeout: 12 entries flip to Complete; Phase 5 row marks Complete; plan list populated. This is the explicit closeout step — the orchestrator (gmd-coordinator) should NOT trigger ROADMAP.md/REQUIREMENTS.md updates from earlier waves; the closeout consolidates them.

Provenance per INFRA-07: routine/entrypoint.py docstring states "novel-to-this-project — no virattt analog" (orchestration is project-specific glue, not adapted). routine/storage.py docstring references the watchlist/loader.py + ingestion/refresh.py atomic-write pattern lineage (Phase 1/2 internal precedent, not external). routine/git_publish.py docstring references Pattern #11 + the Anti-Pattern lock against 'git add -A'. routine/quota.py is novel (estimate-then-lite-mode pattern is the project's INFRA-02 design, not adapted from a reference repo).

Output: 5 production Python files (~500 LOC total); 5 test files (~1000 LOC total); 30+ tests; full Phase 5 regression GREEN; REQUIREMENTS.md + ROADMAP.md closeout; Phase 5 complete.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/05-claude-routine-wiring/05-CONTEXT.md
@.planning/phases/05-claude-routine-wiring/05-RESEARCH.md
@.planning/phases/05-claude-routine-wiring/05-01-foundation-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-02-decision-schema-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-03-llm-client-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-04-personas-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-05-synthesizer-PLAN.md

# Existing patterns to mirror — atomic-write reuse + integration test conventions
@watchlist/loader.py
@ingestion/refresh.py
@analysts/fundamentals.py
@analysts/technicals.py
@analysts/news_sentiment.py
@analysts/valuation.py
@analysts/position_adjustment.py
@routine/llm_client.py
@routine/persona_runner.py
@synthesis/synthesizer.py
@synthesis/decision.py
@tests/routine/conftest.py
@tests/conftest.py

<interfaces>
<!-- 05-01..05-05 outputs we consume: -->

```python
# analysts (Phase 3 + 4):
from analysts import fundamentals, technicals, news_sentiment, valuation, position_adjustment
from analysts.signals import AgentSignal
from analysts.position_signal import PositionSignal
from analysts.data.snapshot import Snapshot
from analysts.schemas import Watchlist, TickerConfig

# Wave 3 (05-04):
from routine.persona_runner import (
    PERSONA_IDS, run_persona_slate,
)

# Wave 4 (05-05):
from synthesis.decision import TickerDecision
from synthesis.synthesizer import synthesize

# Existing watchlist loader (Phase 1):
from watchlist.loader import load_watchlist
```

<!-- New types this plan creates: -->

```python
# routine/quota.py
N_PERSONAS: int = 6
PERSONA_INPUT_TOKENS_PER_TICKER: int = 2000
PERSONA_OUTPUT_TOKENS_PER_TICKER: int = 300
SYNTHESIZER_INPUT_TOKENS_PER_TICKER: int = 5500
SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER: int = 500
DEFAULT_MARKETS_DAILY_QUOTA_TOKENS: int = 600_000

def estimate_run_cost(watchlist: Watchlist) -> int: ...

# routine/run_for_watchlist.py
class TickerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    analytical_signals: list[AgentSignal] = Field(default_factory=list)
    position_signal: PositionSignal | None = None
    persona_signals: list[AgentSignal] = Field(default_factory=list)
    ticker_decision: TickerDecision | None = None
    errors: list[str] = Field(default_factory=list)


async def run_for_watchlist(
    watchlist: Watchlist,
    *,
    lite_mode: bool,
    snapshots_root: Path,
    computed_at: datetime,
    snapshot_loader: Callable[[str], Snapshot] | None = None,
) -> list[TickerResult]: ...

# routine/storage.py
@dataclass(frozen=True)
class StorageOutcome:
    completed: list[str]
    failed: list[str]
    llm_failure_count: int


def _atomic_write_json(path: Path, payload: dict) -> None: ...

def write_daily_snapshot(
    results: list[TickerResult],
    *,
    date_str: str,
    run_started_at: datetime,
    run_completed_at: datetime,
    lite_mode: bool,
    total_token_count_estimate: int,
    snapshots_root: Path = Path("data"),
) -> StorageOutcome: ...


def write_failure_status(
    snapshots_root: Path,
    date_str: str,
    run_started_at: datetime,
    error_msg: str,
) -> None: ...

# routine/git_publish.py
def commit_and_push(
    date_str: str,
    *,
    repo_root: Path = Path("."),
) -> None: ...

# routine/entrypoint.py
def main() -> int: ...
```
</interfaces>

<implementation_sketch>
<!-- ============================================================
     routine/quota.py (~40 LOC)
     ============================================================ -->

```python
"""routine.quota — estimate-run-cost helper + per-call token constants.

Pattern #6 (INFRA-02): conservative pre-run estimate compared against env-
overridable quota; on overshoot, the routine entrypoint sets lite_mode=True
which skips the persona + synthesizer LLM layers (analyticals only).

The constants are tunable (5 sub-fields):
  PERSONA_INPUT_TOKENS_PER_TICKER  = 2000  (~6KB markdown prompt + ~1KB context)
  PERSONA_OUTPUT_TOKENS_PER_TICKER = 300   (~10 evidence items * 100 chars / 4)
  SYNTHESIZER_INPUT_TOKENS_PER_TICKER = 5500  (~3KB prompt + 11 signals + dissent)
  SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER = 500  (TickerDecision JSON ~2KB / 4)
  N_PERSONAS = 6

For 30 tickers: 30 * (6 * 2300 + 6000) = 30 * 19800 = 594000 (under 600000 default).
For 31 tickers: 31 * 19800 = 613800 (over default → lite_mode=True).

Tunable via env: MARKETS_DAILY_QUOTA_TOKENS overrides DEFAULT_MARKETS_DAILY_QUOTA_TOKENS.
"""
from __future__ import annotations

from analysts.schemas import Watchlist

N_PERSONAS: int = 6
PERSONA_INPUT_TOKENS_PER_TICKER: int = 2000
PERSONA_OUTPUT_TOKENS_PER_TICKER: int = 300
SYNTHESIZER_INPUT_TOKENS_PER_TICKER: int = 5500
SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER: int = 500

DEFAULT_MARKETS_DAILY_QUOTA_TOKENS: int = 600_000


def estimate_run_cost(watchlist: Watchlist) -> int:
    """Conservative per-run token estimate. Used by INFRA-02 lite-mode trigger."""
    n_tickers = len(watchlist.tickers)
    per_ticker = (
        N_PERSONAS * (PERSONA_INPUT_TOKENS_PER_TICKER + PERSONA_OUTPUT_TOKENS_PER_TICKER)
        + (SYNTHESIZER_INPUT_TOKENS_PER_TICKER + SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER)
    )
    return n_tickers * per_ticker
```

<!-- ============================================================
     routine/storage.py (~140 LOC)
     ============================================================ -->

```python
"""routine.storage — three-phase atomic write per Pattern #4.

Order (locked, not-up-for-debate):
  Phase A: per-ticker JSONs at data/{date}/{TICKER}.json — atomic per file.
  Phase B: data/{date}/_index.json (run metadata + completed-ticker list).
  Phase C: data/{date}/_status.json — written LAST as the "run is final"
           sentinel. Phase 6 frontend reads _status.json first; if absent,
           snapshot is in-progress (or the routine crashed mid-write).

Per-file atomic write reuses the watchlist/loader.save_watchlist +
ingestion/refresh._write_snapshot pattern: tempfile.NamedTemporaryFile +
os.replace + sort_keys=True serialization. This is internal-precedent
provenance (Phase 1/2 atomic-write); NOT external (no virattt or
TauricResearch pattern adapted).

Per-ticker write failure handling (LLM-08 cascade-prevention): if
_atomic_write_json raises OSError on a ticker, that ticker is appended
to failed_tickers; the loop continues; subsequent _index + _status reflect
the failure but the routine still produces output for the other 29 tickers.

llm_failure_count formula: count persona AgentSignals with data_unavailable=True
(across all completed tickers) + add 1 per ticker where ticker_decision is
None AND lite_mode=False (synthesizer failure; lite_mode skips synthesizer
by design and is NOT counted as a failure).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from routine.run_for_watchlist import TickerResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageOutcome:
    completed: list[str]
    failed: list[str]
    llm_failure_count: int


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Atomic write — tempfile + os.replace + sort_keys=True (Phase 1/2 lock).

    Mirrors watchlist/loader.save_watchlist + ingestion/refresh._write_snapshot.
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def _build_ticker_payload(r: "TickerResult") -> dict:
    """Serialize a TickerResult into the locked per-ticker JSON shape."""
    return {
        "ticker": r.ticker,
        "schema_version": 1,
        "analytical_signals": [s.model_dump(mode="json") for s in r.analytical_signals],
        "position_signal": (
            r.position_signal.model_dump(mode="json")
            if r.position_signal is not None else None
        ),
        "persona_signals": [s.model_dump(mode="json") for s in r.persona_signals],
        "ticker_decision": (
            r.ticker_decision.model_dump(mode="json")
            if r.ticker_decision is not None else None
        ),
        "errors": list(r.errors),
    }


def write_daily_snapshot(
    results: list["TickerResult"],
    *,
    date_str: str,
    run_started_at: datetime,
    run_completed_at: datetime,
    lite_mode: bool,
    total_token_count_estimate: int,
    snapshots_root: Path = Path("data"),
) -> StorageOutcome:
    """Three-phase write: per-ticker → _index → _status. Returns the outcome."""
    folder = snapshots_root / date_str
    failed: list[str] = []
    completed: list[str] = []
    llm_failure_count = 0

    # Phase A: per-ticker JSONs
    for r in results:
        try:
            payload = _build_ticker_payload(r)
            _atomic_write_json(folder / f"{r.ticker}.json", payload)
            completed.append(r.ticker)
            llm_failure_count += sum(
                1 for s in r.persona_signals if s.data_unavailable
            )
            if r.ticker_decision is None and not lite_mode:
                # Synthesizer failure — lite_mode skips synthesizer, so don't
                # count those as failures.
                llm_failure_count += 1
        except OSError as e:
            logger.error("ticker %s write failed: %s", r.ticker, e)
            failed.append(r.ticker)

    # Phase B: _index.json
    _atomic_write_json(folder / "_index.json", {
        "date": date_str,
        "schema_version": 1,
        "run_started_at": run_started_at.isoformat(),
        "run_completed_at": run_completed_at.isoformat(),
        "tickers": completed,  # only successfully-written tickers
        "lite_mode": lite_mode,
        "total_token_count_estimate": total_token_count_estimate,
    })

    # Phase C: _status.json (LAST)
    _atomic_write_json(folder / "_status.json", {
        "success": not failed,
        "partial": lite_mode or bool(failed),
        "completed_tickers": completed,
        "failed_tickers": failed,
        "skipped_tickers": [],
        "llm_failure_count": llm_failure_count,
        "lite_mode": lite_mode,
    })
    return StorageOutcome(
        completed=completed, failed=failed,
        llm_failure_count=llm_failure_count,
    )


def write_failure_status(
    snapshots_root: Path,
    date_str: str,
    run_started_at: datetime,
    error_msg: str,
) -> None:
    """Best-effort failure _status.json — written from entrypoint exception path."""
    folder = snapshots_root / date_str
    _atomic_write_json(folder / "_status.json", {
        "success": False,
        "partial": True,
        "completed_tickers": [],
        "failed_tickers": [],
        "skipped_tickers": [],
        "llm_failure_count": 0,
        "lite_mode": False,
        "run_started_at": run_started_at.isoformat(),
        "error": error_msg[:1000],
    })
```

<!-- ============================================================
     routine/git_publish.py (~70 LOC)
     ============================================================ -->

```python
"""routine.git_publish — fail-loudly git publish per Pattern #11.

5-step sequence, each via subprocess.run(check=True, timeout=60):
  1. git fetch origin main
  2. git pull --rebase --autostash origin main
  3. git add data/{date_str}/
  4. git commit -m "data: snapshot {date_str}"
  5. git push origin main

Rationale (Pattern #11 Anti-Patterns):
  * pull --rebase --autostash BEFORE add/commit/push handles manual-vs-
    scheduled run race conditions. Autostash handles dirty-working-tree
    edge cases.
  * git add data/{date_str}/ is SCOPED — never `git add -A` (defensive
    against accidentally committing temp files).
  * On any CalledProcessError, the routine fails loudly (next morning's
    run is the retry). Git failures are usually configuration issues
    (token expired, push permission revoked) that need human attention,
    not transient blips.

NOT adapted from any reference repo — git CLI invocation is project-
specific glue.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def commit_and_push(
    date_str: str,
    *,
    repo_root: Path = Path("."),
) -> None:
    """Commit + push the snapshot. Raises subprocess.CalledProcessError on failure."""
    cmds = [
        ["git", "fetch", "origin", "main"],
        ["git", "pull", "--rebase", "--autostash", "origin", "main"],
        ["git", "add", f"data/{date_str}/"],
        ["git", "commit", "-m", f"data: snapshot {date_str}"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in cmds:
        try:
            subprocess.run(
                cmd,
                cwd=str(repo_root),
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            logger.info("git: %s — ok", " ".join(cmd))
        except subprocess.CalledProcessError as e:
            logger.error(
                "git: %s — failed (returncode=%d, stderr=%s)",
                " ".join(cmd), e.returncode, e.stderr,
            )
            raise
```

<!-- ============================================================
     routine/run_for_watchlist.py (~150 LOC)
     ============================================================ -->

```python
"""routine.run_for_watchlist — sync-across-tickers loop with async-within (Pattern #3).

Per-ticker pipeline:
  1. Score 4 analyticals + PositionSignal (sync, fast).
  2. IF lite_mode: return TickerResult(persona_signals=[], ticker_decision=None).
  3. ELSE: await run_persona_slate (6-call asyncio.gather); await synthesize.

Sync across tickers: subscription quota is single-bucket; 30 tickers * 7 LLM
calls in parallel would 429 immediately. Per-ticker exception isolation:
caught at the loop level; appended as TickerResult(errors=[...]); other
tickers continue.

Snapshot-loading: parameterized via snapshot_loader callable for testability.
Default loader is a stub for v1; Phase 8's mid-day refresh extends it.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ConfigDict, Field

from analysts import (
    fundamentals, technicals, news_sentiment, valuation, position_adjustment,
)
from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import Watchlist, TickerConfig
from analysts.signals import AgentSignal
from routine.persona_runner import run_persona_slate
from synthesis.decision import TickerDecision
from synthesis.synthesizer import synthesize

logger = logging.getLogger(__name__)


class TickerResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    ticker: str
    analytical_signals: list[AgentSignal] = Field(default_factory=list)
    position_signal: PositionSignal | None = None
    persona_signals: list[AgentSignal] = Field(default_factory=list)
    ticker_decision: TickerDecision | None = None
    errors: list[str] = Field(default_factory=list)


def _default_snapshot_loader(ticker: str) -> Snapshot:
    """v1 stub. Phase 8 mid-day refresh + production snapshot reads will replace."""
    raise NotImplementedError(
        f"snapshot_loader not configured; pass snapshot_loader= to run_for_watchlist "
        f"(ticker={ticker})"
    )


async def _run_one_ticker(
    client: AsyncAnthropic,
    ticker_config: TickerConfig,
    snapshot: Snapshot,
    *,
    lite_mode: bool,
    computed_at: datetime,
) -> TickerResult:
    """Per-ticker pipeline: 4 analyticals + PositionSignal + (conditional) personas + synthesizer."""
    ticker = ticker_config.ticker

    # 1. Sync analyticals.
    fund = fundamentals.score(snapshot, ticker_config, computed_at=computed_at)
    tech = technicals.score(snapshot, ticker_config, computed_at=computed_at)
    nsen = news_sentiment.score(snapshot, ticker_config, computed_at=computed_at)
    val = valuation.score(snapshot, ticker_config, computed_at=computed_at)
    pose = position_adjustment.score(snapshot, ticker_config, computed_at=computed_at)

    if lite_mode:
        return TickerResult(
            ticker=ticker,
            analytical_signals=[fund, tech, nsen, val],
            position_signal=pose,
            persona_signals=[],
            ticker_decision=None,
            errors=[],
        )

    # 2. Persona fan-out + synthesizer.
    persona_signals = await run_persona_slate(
        client,
        ticker=ticker,
        snapshot=snapshot,
        config=ticker_config,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        computed_at=computed_at,
    )
    decision = await synthesize(
        client,
        ticker=ticker,
        snapshot=snapshot,
        config=ticker_config,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        persona_signals=persona_signals,
        computed_at=computed_at,
    )
    return TickerResult(
        ticker=ticker,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        persona_signals=persona_signals,
        ticker_decision=decision,
        errors=[],
    )


async def run_for_watchlist(
    watchlist: Watchlist,
    *,
    lite_mode: bool,
    snapshots_root: Path,
    computed_at: datetime,
    client: AsyncAnthropic | None = None,
    snapshot_loader: Callable[[str], Snapshot] | None = None,
) -> list[TickerResult]:
    """Sync across tickers; async within ticker. Returns one TickerResult per ticker."""
    if client is None:
        client = AsyncAnthropic()  # subscription auth in routine context
    if snapshot_loader is None:
        snapshot_loader = _default_snapshot_loader

    results: list[TickerResult] = []
    for ticker_config in watchlist.tickers:
        ticker = ticker_config.ticker
        try:
            snapshot = snapshot_loader(ticker)
            result = await _run_one_ticker(
                client, ticker_config, snapshot,
                lite_mode=lite_mode, computed_at=computed_at,
            )
        except Exception as exc:
            logger.exception("ticker %s pipeline failed", ticker)
            result = TickerResult(
                ticker=ticker,
                errors=[f"per-ticker pipeline failure: {exc!r}"],
            )
        results.append(result)
    return results
```

<!-- ============================================================
     routine/entrypoint.py (~100 LOC)
     ============================================================ -->

```python
"""routine.entrypoint — Phase 5 daily-routine entry point.

NOVEL-TO-THIS-PROJECT — orchestration glue. No virattt or TauricResearch
analog; the layer-of-layers (load_watchlist → estimate_run_cost →
run_for_watchlist → write_daily_snapshot → commit_and_push) is project-
specific.

Wired by a Claude Code Cloud Routine fired Mon-Fri 06:00 ET (Pattern #1).
The Cloud Routine clones the repo fresh each run, executes
`python -m routine.entrypoint`, captures exit code, and surfaces any error
to the routine UI for the next-day view.

Top-level flow:
  1. logging.basicConfig
  2. load_watchlist (abort with exit 1 if empty)
  3. estimate_run_cost vs MARKETS_DAILY_QUOTA_TOKENS env → lite_mode
  4. asyncio.run(run_for_watchlist(...))
  5. write_daily_snapshot (three-phase atomic per Pattern #4)
  6. commit_and_push (5-step git per Pattern #11)
  7. return 0

Top-level exception path:
  * logger.exception('routine failed')
  * Best-effort write_failure_status (nested try/except)
  * return 1
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from routine.git_publish import commit_and_push
from routine.quota import (
    DEFAULT_MARKETS_DAILY_QUOTA_TOKENS,
    estimate_run_cost,
)
from routine.run_for_watchlist import run_for_watchlist
from routine.storage import write_daily_snapshot, write_failure_status
from watchlist.loader import load_watchlist

logger = logging.getLogger(__name__)


def main() -> int:
    """Single entry point. Exit code: 0 success, 1 any failure."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_started_at = datetime.now(timezone.utc)
    date_str = run_started_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
    snapshots_root = Path("data")

    try:
        watchlist = load_watchlist()
        if not watchlist.tickers:
            logger.error("watchlist is empty; nothing to do")
            return 1

        quota = int(os.environ.get(
            "MARKETS_DAILY_QUOTA_TOKENS",
            str(DEFAULT_MARKETS_DAILY_QUOTA_TOKENS),
        ))
        estimated = estimate_run_cost(watchlist)
        lite_mode = estimated > quota
        logger.info(
            "token estimate: %d; quota: %d; lite_mode: %s",
            estimated, quota, lite_mode,
        )

        results = asyncio.run(run_for_watchlist(
            watchlist,
            lite_mode=lite_mode,
            snapshots_root=snapshots_root,
            computed_at=run_started_at,
        ))

        run_completed_at = datetime.now(timezone.utc)
        outcome = write_daily_snapshot(
            results,
            date_str=date_str,
            run_started_at=run_started_at,
            run_completed_at=run_completed_at,
            lite_mode=lite_mode,
            total_token_count_estimate=estimated,
            snapshots_root=snapshots_root,
        )
        logger.info(
            "snapshot written: %d completed, %d failed, %d llm_failures",
            len(outcome.completed), len(outcome.failed), outcome.llm_failure_count,
        )

        commit_and_push(date_str)
        return 0

    except Exception as exc:  # noqa: BLE001 — top-level catch by design
        logger.exception("routine failed")
        try:
            write_failure_status(
                snapshots_root, date_str, run_started_at,
                error_msg=repr(exc),
            )
        except Exception:  # noqa: BLE001
            logger.exception("could not write failure _status.json")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```
</implementation_sketch>

<test_outlines>
<!-- tests/routine/test_quota.py (~5 tests):

  1. test_constants_locked: assert N_PERSONAS==6; PERSONA_INPUT==2000; PERSONA_OUTPUT==300; SYNTHESIZER_INPUT==5500; SYNTHESIZER_OUTPUT==500; DEFAULT_MARKETS_DAILY_QUOTA_TOKENS==600_000.
  2. test_empty_watchlist_returns_zero: estimate_run_cost(Watchlist()) == 0.
  3. test_30_ticker_estimate_under_default_quota: 30-ticker watchlist → 594000 < 600000.
  4. test_31_ticker_estimate_exceeds_default_quota: 31-ticker watchlist → 613800 > 600000.
  5. test_estimate_formula_correctness: parametrized over 1, 5, 10, 30 ticker counts; assert == n_tickers * 19800.

tests/routine/test_storage.py (~10 tests):

  1. test_atomic_write_json_creates_file_and_serializes_sort_keys: payload {"b":1,"a":2}; written file content matches json.dumps(payload, indent=2, sort_keys=True)+"\\n"; first key line is "a" not "b".
  2. test_atomic_write_json_creates_parent_dir: snapshots_root/date/missing_subdir/file.json — mkdir parents works.
  3. test_atomic_write_json_no_orphan_tmp_on_replace_failure: monkeypatch os.replace to raise OSError; assert tmp file does NOT remain in parent dir; assert the original raise propagates.
  4. test_three_phase_write_order: 3-ticker results; track _atomic_write_json call sequence (monkeypatch); assert order is [TICKER1.json, TICKER2.json, TICKER3.json, _index.json, _status.json] — _status.json LAST (Pattern #4 lock).
  5. test_index_json_schema: 2-ticker run → _index.json contains {date, schema_version=1, run_started_at, run_completed_at, tickers (2 entries), lite_mode, total_token_count_estimate}.
  6. test_status_json_schema_success: 5 TickerResults with no errors → _status.json {success: True, partial: lite_mode, completed_tickers: 5 ids, failed_tickers: [], skipped_tickers: [], llm_failure_count: 0, lite_mode}.
  7. test_status_json_failed_tickers_populated_on_OSError: 3-ticker run; monkeypatch _atomic_write_json to raise OSError on the 2nd ticker only; _status.json {success: False, partial: True, failed_tickers: [<2nd ticker>], completed_tickers: 2 entries}; FIRST ticker still successfully written.
  8. test_llm_failure_count_persona_data_unavailable: TickerResult with 2 of 6 personas data_unavailable=True → contributes 2 to llm_failure_count.
  9. test_llm_failure_count_synthesizer_failure_outside_lite_mode: TickerResult with ticker_decision=None + lite_mode=False → contributes 1 to llm_failure_count. With lite_mode=True → contributes 0.
  10. test_round_trip_per_ticker_json: build TickerResult → write → read JSON file → assert ticker, schema_version=1, analytical_signals length, persona_signals length, ticker_decision (when present) match.

tests/routine/test_git_publish.py (~6 tests):

  1. test_happy_path_5_subprocess_calls_in_order: monkeypatch subprocess.run; commit_and_push("2026-05-04"); assert run.call_args_list has exactly 5 entries; assert call[i].args[0] matches the 5-cmd list.
  2. test_subprocess_kwargs: verify each call passes check=True, capture_output=True, text=True, timeout=60, cwd=str(repo_root).
  3. test_fetch_failure_raises_called_process_error: subprocess.run on first call raises CalledProcessError(returncode=1, cmd=..., stderr="..."). commit_and_push raises CalledProcessError; subsequent commands NOT called.
  4. test_pull_rebase_failure_raises: subprocess.run on 2nd call (pull) raises; assert raise propagates.
  5. test_push_failure_raises: subprocess.run on 5th call (push) raises; first 4 calls succeed; raise propagates.
  6. test_no_git_add_dash_A: AST grep on routine/git_publish.py — assert "git add -A" NOT in source (Pattern #11 anti-pattern lock).

tests/routine/test_run_for_watchlist.py (~6 tests):

  1. test_per_ticker_pipeline_full: single ticker; mock client returns valid AgentSignals (6 personas) + valid TickerDecision; result has analytical_signals (4), position_signal (not None), persona_signals (6), ticker_decision (not None), errors=[].
  2. test_lite_mode_skips_persona_and_synthesizer: lite_mode=True; result has analytical_signals (4), position_signal (not None), persona_signals=[], ticker_decision=None, errors=[]; mock client.messages was called ZERO times.
  3. test_per_ticker_exception_isolation: 3-ticker watchlist; ticker 2 raises in snapshot_loader (loader returns FileNotFoundError); ticker 1 + 3 succeed; result list has length 3 with ticker 2's TickerResult having non-empty errors=[...] and other fields default.
  4. test_sync_across_tickers_order_preserved: 3-ticker watchlist [AAPL, MSFT, GOOG]; result is a 3-element list in the same order.
  5. test_run_for_watchlist_uses_supplied_client: pass mock_anthropic_client explicitly; routine uses it (verified by checking the mock's calls list).
  6. test_run_for_watchlist_uses_supplied_snapshot_loader: pass a custom loader closure; routine calls it with the right ticker arg per iteration.

tests/routine/test_entrypoint.py (~3 end-to-end integration tests):

  1. test_main_5_ticker_happy_path: monkeypatch load_watchlist → 5-ticker fixture; monkeypatch AsyncAnthropic client at the module level; monkeypatch subprocess.run for git; monkeypatch the snapshot_loader; tmp_path as data root; main() returns 0; assert 5 per-ticker JSONs + 1 _index.json + 1 _status.json exist; _status.json.success=True; _status.json.lite_mode=False; subprocess.run called 5 times for git.
  2. test_main_lite_mode_path: 35-ticker watchlist forces estimate > quota → lite_mode=True; main() returns 0; per-ticker JSONs have persona_signals=[] and ticker_decision=null; _status.json.lite_mode=True, partial=True.
  3. test_main_top_level_exception_returns_1: monkeypatch load_watchlist to raise FileNotFoundError; main() returns 1; best-effort write_failure_status called (verified by tmp_path/data/<date>/_status.json exists with success=False, error field present).

Total: ~30 tests (parametrization adds a few more instances).
-->
</test_outlines>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: routine/quota.py + routine/storage.py + routine/git_publish.py + tests (RED → GREEN; foundational + storage/git/quota)</name>
  <files>routine/quota.py, routine/storage.py, routine/git_publish.py, tests/routine/test_quota.py, tests/routine/test_storage.py, tests/routine/test_git_publish.py</files>
  <behavior>
    Lands the 3 deterministic (no-LLM) building blocks: quota estimator + atomic-write storage + git publish. These have NO Anthropic SDK dependency; the tests are pure-Python (subprocess mocking + tempfile + JSON assertions). All 3 modules + their ~21 tests land together because they're cohesive (storage and git compose into entrypoint; quota is its own concern but trivial).

    Per implementation_sketch above:
    - routine/quota.py (~40 LOC) — 5 token constants + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000 + estimate_run_cost(watchlist) returning n_tickers * 19_800.
    - routine/storage.py (~140 LOC) — _atomic_write_json (tempfile + os.replace + sort_keys, mirrors watchlist/loader.py); _build_ticker_payload; write_daily_snapshot (three-phase A→B→C; per-ticker failure populates failed_tickers WITHOUT aborting); write_failure_status (best-effort failure path); StorageOutcome dataclass.
    - routine/git_publish.py (~70 LOC) — commit_and_push(date_str, repo_root) running 5 subprocess.run calls in fixed order with check=True + timeout=60 + cwd=str(repo_root); fail-loudly via re-raise of CalledProcessError.

    Tests (~21 across 3 files):
    - tests/routine/test_quota.py (5): constants locked; empty watchlist → 0; 30-ticker → 594000; 31-ticker → 613800; parametrized formula.
    - tests/routine/test_storage.py (10): atomic write basics; mkdir parents; no orphan .tmp on replace failure; three-phase order; _index schema; _status schema (LLM-08); failed_tickers populated on OSError without aborting; llm_failure_count formula (persona data_unavailable + synthesizer failure outside lite_mode); round-trip.
    - tests/routine/test_git_publish.py (6): 5-call sequence; subprocess kwargs (check/timeout/cwd); fetch failure; pull failure; push failure; no `git add -A` AST grep.
  </behavior>
  <action>
    RED:
    1. Write `tests/routine/test_quota.py` — 5 tests per outline.
    2. Write `tests/routine/test_storage.py` — 10 tests per outline.
    3. Write `tests/routine/test_git_publish.py` — 6 tests per outline.
    4. Run `poetry run pytest tests/routine/test_quota.py tests/routine/test_storage.py tests/routine/test_git_publish.py -x -q` → ImportErrors on `routine.quota`, `routine.storage`, `routine.git_publish` (none exist yet).
    5. Commit (RED): `test(05-06): add failing tests for routine.{quota, storage, git_publish} (LLM-08; 21 tests covering 3-phase atomic write + 5-step git sequence + estimate_run_cost formula)`.

    GREEN:
    6. Implement `routine/quota.py` per implementation_sketch — 5 constants + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS + estimate_run_cost.
    7. Implement `routine/storage.py` per implementation_sketch — provenance docstring referencing watchlist/loader.py + ingestion/refresh.py atomic-write lineage; StorageOutcome dataclass; _atomic_write_json (tempfile + os.replace + sort_keys, mkdir parents, OSError → unlink tmp + raise); _build_ticker_payload (model_dump(mode='json') for each signal type); write_daily_snapshot (three-phase A→B→C); write_failure_status.
    8. Implement `routine/git_publish.py` per implementation_sketch — commit_and_push iterating over the 5-cmd list; subprocess.run with check=True, capture_output=True, text=True, timeout=60, cwd=str(repo_root); CalledProcessError logged + re-raised.
    9. Run `poetry run pytest tests/routine/test_quota.py tests/routine/test_storage.py tests/routine/test_git_publish.py -v` → all 21 tests GREEN.
    10. Coverage check: `poetry run pytest --cov=routine.quota --cov=routine.storage --cov=routine.git_publish --cov-branch tests/routine/test_quota.py tests/routine/test_storage.py tests/routine/test_git_publish.py` → ≥90% line / ≥85% branch on each module.
    11. Phase 1-4 + Wave 0-4 regression: `poetry run pytest -x -q` → all existing tests still GREEN.
    12. Sanity grep — git Anti-Pattern: `grep -nE "git add -A|git add \\." routine/git_publish.py` returns ZERO matches.
    13. Sanity grep — provenance: `grep -n "watchlist/loader" routine/storage.py` returns ≥1 match (internal-precedent provenance).
    14. Commit (GREEN): `feat(05-06): routine.{quota, storage, git_publish} — quota estimator + 3-phase atomic write + 5-step git publish (Pattern #4 + Pattern #6 + Pattern #11)`.
  </action>
  <verify>
    <automated>poetry run pytest tests/routine/test_quota.py tests/routine/test_storage.py tests/routine/test_git_publish.py -v && poetry run pytest --cov=routine.quota --cov=routine.storage --cov=routine.git_publish --cov-branch tests/routine/test_quota.py tests/routine/test_storage.py tests/routine/test_git_publish.py && poetry run pytest -x -q && python -c "import re,pathlib; src=pathlib.Path('routine/git_publish.py').read_text(encoding='utf-8'); assert 'git add -A' not in src; assert 'git pull' in src and '--rebase' in src and '--autostash' in src; print('git_publish anti-pattern locks OK')" && python -c "from routine.quota import estimate_run_cost, DEFAULT_MARKETS_DAILY_QUOTA_TOKENS, N_PERSONAS, PERSONA_INPUT_TOKENS_PER_TICKER, PERSONA_OUTPUT_TOKENS_PER_TICKER, SYNTHESIZER_INPUT_TOKENS_PER_TICKER, SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER; assert (N_PERSONAS, PERSONA_INPUT_TOKENS_PER_TICKER, PERSONA_OUTPUT_TOKENS_PER_TICKER, SYNTHESIZER_INPUT_TOKENS_PER_TICKER, SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER, DEFAULT_MARKETS_DAILY_QUOTA_TOKENS) == (6, 2000, 300, 5500, 500, 600000); print('quota constants locked OK')"</automated>
  </verify>
  <done>routine/quota.py shipped (~40 LOC) with 5 token constants + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000 + estimate_run_cost; routine/storage.py shipped (~140 LOC) with _atomic_write_json (tempfile + os.replace + sort_keys; OSError → unlink tmp + re-raise) + _build_ticker_payload + write_daily_snapshot (three-phase A→B→C; failed_tickers cascade-prevention) + write_failure_status + StorageOutcome dataclass; routine/git_publish.py shipped (~70 LOC) with commit_and_push (5-step sequence; check=True; timeout=60; cwd parameterized; fail-loudly); 21 tests across 3 test files all GREEN; coverage ≥90% line / ≥85% branch on each module; full repo regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: routine/run_for_watchlist.py + tests (RED → GREEN; per-ticker pipeline integration)</name>
  <files>routine/run_for_watchlist.py, tests/routine/test_run_for_watchlist.py</files>
  <behavior>
    Wires the 3 Phase 5 layers (analyticals + personas + synthesizer) into the per-ticker pipeline. TickerResult Pydantic model + _run_one_ticker async helper + run_for_watchlist async sync-across-tickers loop. Per-ticker exception isolation (catch + convert to TickerResult with errors); lite-mode skip path (analyticals only); snapshot_loader parameterized for testability.

    Per implementation_sketch above (~150 LOC).

    Tests in tests/routine/test_run_for_watchlist.py (~6):
    - test_per_ticker_pipeline_full: single ticker; mock client; result has all fields populated.
    - test_lite_mode_skips_persona_and_synthesizer: lite_mode=True; persona_signals=[]; ticker_decision=None; mock client called 0 times.
    - test_per_ticker_exception_isolation: 3-ticker; loader fails on 2nd; 1+3 succeed.
    - test_sync_across_tickers_order_preserved: 3-ticker order matches input.
    - test_run_for_watchlist_uses_supplied_client.
    - test_run_for_watchlist_uses_supplied_snapshot_loader.

    Note: tests need a working snapshot_loader closure that produces a Snapshot per ticker. Use the existing tests/analysts/conftest.py builders (synthetic_uptrend_history etc.) plus a Snapshot constructor from analysts/data/snapshot.py to build minimal viable Snapshots for each ticker. Keep snapshots minimal — the analytical analysts each handle their own sub-data; the test only needs the pipeline shape, not realistic data.
  </behavior>
  <action>
    PRE-WORK:
    0. Verify tests/routine/test_run_for_watchlist.py can construct a minimal Snapshot. Use `analysts.data.snapshot.Snapshot(ticker=..., fetched_at=frozen_now, data_unavailable=True)` for the simplest case OR populate prices/fundamentals from existing fixtures. The tests use the mock_anthropic_client fixture so LLM calls are mocked.

    RED:
    1. Write `tests/routine/test_run_for_watchlist.py` per outline (~6 tests). Imports include `from routine.run_for_watchlist import TickerResult, run_for_watchlist`, `from analysts.signals import AgentSignal`, `from synthesis.decision import TickerDecision, TimeframeBand, DissentSection`. Use the mock_anthropic_client + isolated_failure_log + frozen_now fixtures.
    2. Run `poetry run pytest tests/routine/test_run_for_watchlist.py -x -q` → ImportError on `routine.run_for_watchlist` (module does not exist).
    3. Commit (RED): `test(05-06): add failing tests for routine.run_for_watchlist (per-ticker pipeline integration; 6 tests covering lite mode + exception isolation + order preservation)`.

    GREEN:
    4. Implement `routine/run_for_watchlist.py` per implementation_sketch (~150 LOC):
       - Provenance docstring referencing Pattern #3 (sync-across-tickers; async-within-ticker).
       - Imports: stdlib (logging, datetime, pathlib, typing); `from anthropic import AsyncAnthropic`; `from pydantic import BaseModel, ConfigDict, Field`; project schemas (Snapshot, PositionSignal, TickerConfig, AgentSignal, Watchlist) + the 5 analyst modules (`fundamentals, technicals, news_sentiment, valuation, position_adjustment`); `from routine.persona_runner import run_persona_slate`; `from synthesis.decision import TickerDecision`; `from synthesis.synthesizer import synthesize`.
       - `TickerResult(BaseModel)` with the 6 fields per interfaces; `arbitrary_types_allowed=True` (because PositionSignal + AgentSignal are user types and we're nesting them).
       - `_default_snapshot_loader(ticker)` raising NotImplementedError (v1 stub; tests pass an explicit loader).
       - `_run_one_ticker(client, ticker_config, snapshot, *, lite_mode, computed_at) -> TickerResult` — sync 5 analyticals (fundamentals/technicals/news_sentiment/valuation/position_adjustment.score(...)); IF lite_mode: return TickerResult with persona_signals=[] and ticker_decision=None; ELSE: await run_persona_slate; await synthesize; return TickerResult.
       - `run_for_watchlist(watchlist, *, lite_mode, snapshots_root, computed_at, client=None, snapshot_loader=None) -> list[TickerResult]` — defaults client to AsyncAnthropic() (for production); defaults snapshot_loader to _default_snapshot_loader; iterates over watchlist.tickers; per-iteration try/except converts uncaught exception to TickerResult with errors=[repr(exc)].
    5. Run `poetry run pytest tests/routine/test_run_for_watchlist.py -v` → all 6 tests GREEN.
    6. Coverage check: `poetry run pytest --cov=routine.run_for_watchlist --cov-branch tests/routine/test_run_for_watchlist.py` → ≥90% line / ≥85% branch.
    7. Phase 1-4 + Wave 0-4 + Task 1 regression: `poetry run pytest -x -q` → all existing tests still GREEN.
    8. Commit (GREEN): `feat(05-06): routine.run_for_watchlist — per-ticker pipeline integration with lite-mode skip + exception isolation (Pattern #3 sync-across-tickers / async-within)`.
  </action>
  <verify>
    <automated>poetry run pytest tests/routine/test_run_for_watchlist.py -v && poetry run pytest --cov=routine.run_for_watchlist --cov-branch tests/routine/test_run_for_watchlist.py && poetry run pytest -x -q && python -c "from routine.run_for_watchlist import TickerResult, run_for_watchlist; assert TickerResult.__name__ == 'TickerResult'; print('OK')"</automated>
  </verify>
  <done>routine/run_for_watchlist.py shipped (~150 LOC) with TickerResult Pydantic v2 model (6 fields; arbitrary_types_allowed for nested AgentSignal/PositionSignal/TickerDecision) + _run_one_ticker async helper (4 analyticals + PositionSignal scored sync; lite-mode skip; persona slate + synthesizer in non-lite mode) + run_for_watchlist async (sync-across-tickers loop; per-ticker exception isolation via try/except → TickerResult with errors=[]); 6 tests in tests/routine/test_run_for_watchlist.py all GREEN; coverage ≥90% line / ≥85% branch; full repo regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: routine/entrypoint.py + 3 end-to-end integration tests + REQUIREMENTS.md + ROADMAP.md closeout (RED → GREEN → CLOSEOUT)</name>
  <files>routine/entrypoint.py, tests/routine/test_entrypoint.py, .planning/REQUIREMENTS.md, .planning/ROADMAP.md</files>
  <behavior>
    Phase 5 closeout. Lands the entrypoint module + 3 end-to-end integration tests + flips 12 requirements (LLM-01..08 + INFRA-01..04) to Complete in REQUIREMENTS.md and ROADMAP.md.

    routine/entrypoint.py per implementation_sketch (~100 LOC):
    - main() function: logging.basicConfig; load_watchlist; quota check; asyncio.run(run_for_watchlist); write_daily_snapshot; commit_and_push; return 0.
    - Top-level exception path: logger.exception; best-effort write_failure_status (nested try/except); return 1.
    - if __name__ == "__main__": sys.exit(main()).
    - Provenance: "novel-to-this-project" docstring statement (no virattt/TauricResearch analog).

    Tests in tests/routine/test_entrypoint.py (~3 end-to-end integration tests):
    - test_main_5_ticker_happy_path: mock load_watchlist (5-ticker watchlist fixture); mock AsyncAnthropic (return canned AgentSignals + TickerDecision per call); mock subprocess.run (git ops succeed); use tmp_path as Path("data") via monkeypatch; main() returns 0; verify 5 per-ticker JSONs + 1 _index.json + 1 _status.json exist; _status.json.success=True; _status.json.lite_mode=False; subprocess.run called 5 times.
    - test_main_lite_mode_path: 35-ticker watchlist forces estimate>quota → lite_mode=True; main() returns 0; per-ticker JSONs have persona_signals=[] and ticker_decision=null; _status.json.lite_mode=True, partial=True.
    - test_main_top_level_exception_returns_1: monkeypatch load_watchlist to raise FileNotFoundError; main() returns 1; tmp_path/data/<date>/_status.json exists with success=False + error field present.

    REQUIREMENTS.md updates: 12 entries flip to [x] / Complete (in v1 list AND traceability table):
    - LLM-01, LLM-02, LLM-03, LLM-04 (closed by 05-04 personas).
    - LLM-05 (closed by 05-03 llm_client; default_factory + memory/llm_failures.jsonl).
    - LLM-06, LLM-07 (closed by 05-05 synthesizer + dissent).
    - LLM-08 (closed by this plan; _status.json with all locked fields).
    - INFRA-01 (Pattern #1 + Cloud Routine doc note in 05-RESEARCH; closed by entrypoint shipping).
    - INFRA-02 (Pattern #6 + lite-mode skip path; closed by quota.py + run_for_watchlist + entrypoint integration test).
    - INFRA-03 (Pattern #4 + 3-phase storage; closed by storage.py + integration test).
    - INFRA-04 (Pattern #11 + 5-step git publish; closed by git_publish.py + integration test).

    ROADMAP.md updates: Phase 5 row Status flipped from "Pending" to "Complete"; Phase 5 plan list populated with 6 [x] entries (05-01-foundation, 05-02-decision-schema, 05-03-llm-client, 05-04-personas, 05-05-synthesizer, 05-06-routine-entrypoint).
  </behavior>
  <action>
    RED:
    1. Write `tests/routine/test_entrypoint.py` per outline. The tests are integration-shaped; build a 5-ticker watchlist fixture (use TickerConfig builder from existing tests/analysts/conftest.py); build a per-ticker snapshot_loader (closure over a dict of mock Snapshots); use mock_anthropic_client + isolated_failure_log fixtures; monkeypatch routine.entrypoint.load_watchlist to return the test fixture; monkeypatch routine.run_for_watchlist.AsyncAnthropic constructor to return mock_anthropic_client; monkeypatch routine.run_for_watchlist._default_snapshot_loader to the closure (or pass via run_for_watchlist's snapshot_loader kwarg — entrypoint.py doesn't expose this kwarg, so use module-level monkeypatch); monkeypatch subprocess.run for git; monkeypatch Path("data") to tmp_path.
    2. Run `poetry run pytest tests/routine/test_entrypoint.py -x -q` → ImportError on `routine.entrypoint` (module does not exist).
    3. Commit (RED): `test(05-06): add failing end-to-end integration tests for routine.entrypoint (LLM-08 + INFRA-01..04; 3 tests covering happy path + lite mode + top-level exception)`.

    GREEN:
    4. Implement `routine/entrypoint.py` per implementation_sketch (~100 LOC):
       - Provenance docstring: "novel-to-this-project — orchestration glue. No virattt or TauricResearch analog".
       - Imports: asyncio, logging, os, sys, datetime, pathlib + the 4 routine sub-modules + watchlist.loader.load_watchlist.
       - main() function with the 7-step orchestration order + top-level except.
       - if __name__ == "__main__": sys.exit(main()).
    5. Run `poetry run pytest tests/routine/test_entrypoint.py -v` → all 3 integration tests GREEN.
    6. Coverage check: `poetry run pytest --cov=routine.entrypoint --cov-branch tests/routine/test_entrypoint.py` → ≥90% line / ≥85% branch.
    7. Phase 1-4 + Wave 0-4 + Task 1 + Task 2 regression: `poetry run pytest -x -q` → all existing tests still GREEN. Total Phase 5 test count: ~30 new tests; full repo should be ~470+ passing.
    8. Sanity grep — provenance: `grep -n "novel-to-this-project" routine/entrypoint.py` returns ≥1 match.
    9. Commit (GREEN-ENTRYPOINT): `feat(05-06): routine.entrypoint.main — Phase 5 entrypoint orchestration; LLM-08 + INFRA-01..04 closure (Pattern #1 + Pattern #4 + Pattern #6 + Pattern #11)`.

    CLOSEOUT — REQUIREMENTS.md + ROADMAP.md:
    10. Edit `.planning/REQUIREMENTS.md`:
        - LLM section: flip LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08 from `- [ ]` to `- [x]` (8 entries).
        - INFRA section: flip INFRA-01, INFRA-02, INFRA-03, INFRA-04 from `- [ ]` to `- [x]` (4 entries).
        - Traceability table: flip the 12 corresponding rows from `Pending` to `Complete`.
        - Update the trailing "Last updated" timestamp.
    11. Edit `.planning/ROADMAP.md`:
        - Phase 5 row in Phase Summary table: change status to `Complete` and append `(6/6 plans, Complete)`.
        - Phase 5 detail block: ensure Plans list is populated with 6 [x] entries:
          - [x] 05-01-foundation-PLAN.md — Anthropic SDK install + AnalystId widening + scaffolding
          - [x] 05-02-decision-schema-PLAN.md — TickerDecision + DissentSection + TimeframeBand
          - [x] 05-03-llm-client-PLAN.md — call_with_retry + default_factory + memory/llm_failures.jsonl
          - [x] 05-04-personas-PLAN.md — 6 persona prompts + persona_runner async fan-out
          - [x] 05-05-synthesizer-PLAN.md — synthesizer prompt + synthesize + Python-computed dissent
          - [x] 05-06-routine-entrypoint-PLAN.md — 3-phase storage + git publish + entrypoint orchestration
    12. Run `poetry run pytest -x -q` once more to confirm everything still green.
    13. Commit (CLOSEOUT): `docs(05-06): close Phase 5 — flip LLM-01..08 + INFRA-01..04 to Complete in REQUIREMENTS.md; flip Phase 5 row to Complete in ROADMAP.md; populate plan list`.
  </action>
  <verify>
    <automated>poetry run pytest tests/routine/test_entrypoint.py -v && poetry run pytest --cov=routine.entrypoint --cov-branch tests/routine/test_entrypoint.py && poetry run pytest -x -q && grep -n "novel-to-this-project" routine/entrypoint.py && python -c "import pathlib; req=pathlib.Path('.planning/REQUIREMENTS.md').read_text(encoding='utf-8'); needed=['LLM-01','LLM-02','LLM-03','LLM-04','LLM-05','LLM-06','LLM-07','LLM-08','INFRA-01','INFRA-02','INFRA-03','INFRA-04']; assert all(f'- [x] **{n}**' in req for n in needed), 'REQUIREMENTS checkbox flip incomplete'; print('REQUIREMENTS Complete OK')" && python -c "import pathlib; rm=pathlib.Path('.planning/ROADMAP.md').read_text(encoding='utf-8'); assert 'Phase 5' in rm and 'Complete' in rm.split('Phase 5')[1][:200]; assert '05-06-routine-entrypoint-PLAN.md' in rm; print('ROADMAP Phase 5 Complete OK')"</automated>
  </verify>
  <done>routine/entrypoint.py shipped (~100 LOC) with main() orchestration (7-step: load_watchlist → quota check → asyncio.run(run_for_watchlist) → write_daily_snapshot → commit_and_push → return 0; top-level except → write_failure_status → return 1) + provenance docstring naming "novel-to-this-project"; 3 end-to-end integration tests in tests/routine/test_entrypoint.py all GREEN (5-ticker happy path + lite-mode 35-ticker path + top-level exception path); coverage ≥90% line / ≥85% branch on routine/entrypoint.py; full repo regression GREEN with all 30+ Phase 5 tests passing; REQUIREMENTS.md flipped 12 entries to Complete (LLM-01..08 + INFRA-01..04 in both v1 list AND traceability table); ROADMAP.md Phase 5 row marked Complete + plan list populated with 6 [x] entries; 3 commits landed (RED + GREEN-ENTRYPOINT + CLOSEOUT-DOCS).</done>
</task>

</tasks>

<verification>
- 3 tasks, 7 commits (RED + GREEN per Task 1, RED + GREEN per Task 2, RED + GREEN-ENTRYPOINT + CLOSEOUT for Task 3). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on each of `routine/quota.py`, `routine/storage.py`, `routine/git_publish.py`, `routine/run_for_watchlist.py`, `routine/entrypoint.py`.
- Phase 1-4 + Wave 0 + Wave 1 + Wave 2 + Wave 3 + Wave 4 regression invariant: existing tests stay GREEN. Total ~30 new Phase 5 Wave 5 tests (5 quota + 10 storage + 6 git_publish + 6 run_for_watchlist + 3 entrypoint integration).
- Three-phase storage write order locked (Pattern #4): per-ticker JSONs FIRST → _index.json SECOND → _status.json LAST as the run-final sentinel; per-ticker write failures populate failed_tickers without aborting the run (LLM-08 cascade-prevention).
- 5-step git CLI sequence locked (Pattern #11): fetch / pull --rebase --autostash / add data/{date}/ / commit / push; subprocess.run(check=True, capture_output=True, text=True, timeout=60, cwd=str(repo_root)); CalledProcessError propagates to entrypoint.main exception handler.
- Lite-mode threshold locked (Pattern #6 + INFRA-02): DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000; estimate_run_cost = n_tickers * 19_800; 30-ticker case 594_000 < 600_000 (under quota); 31-ticker case 613_800 > 600_000 (lite mode triggered); env-overridable via MARKETS_DAILY_QUOTA_TOKENS.
- Per-ticker pipeline locked (Pattern #3 + Pitfall #3 + LLM-08): sync analyticals (4) + PositionSignal (1); lite-mode skips persona/synthesizer; persona slate via asyncio.gather (Wave 3); synthesizer single LLM call (Wave 4); per-ticker uncaught exception caught at the loop and converted to TickerResult with errors=[]; other tickers continue.
- Entrypoint orchestration locked: main() 7-step (logging.basicConfig → load_watchlist → quota check → asyncio.run(run_for_watchlist) → write_daily_snapshot → commit_and_push → return 0); top-level except → write_failure_status (nested try/except so the failure-status write itself can't crash the routine) → return 1.
- LLM-08 _status.json schema locked: {success, partial, completed_tickers, failed_tickers, skipped_tickers, llm_failure_count, lite_mode}; llm_failure_count formula = sum of persona AgentSignals with data_unavailable + (1 per ticker where ticker_decision is None AND lite_mode=False).
- Provenance per INFRA-07: routine/entrypoint.py docstring contains "novel-to-this-project"; routine/storage.py references the watchlist/loader.py + ingestion/refresh.py atomic-write internal-precedent lineage; routine/git_publish.py references Pattern #11.
- Phase 5 closeout: REQUIREMENTS.md flips LLM-01..08 + INFRA-01..04 (12 entries) to Complete in both the v1 checklist AND the traceability table; ROADMAP.md flips Phase 5 row to Complete; plan list populated with 6 [x] entries.
- All 12 Phase 5 requirements satisfied: LLM-01 (markdown personas in prompts/personas/) + LLM-02 (loaded at runtime by load_persona_prompt) + LLM-03 (voice signature anchor) + LLM-04 (Pydantic-validated AgentSignal) + LLM-05 (default_factory + memory/llm_failures.jsonl) + LLM-06 (synthesizer + TickerDecision) + LLM-07 (Python-computed dissent + always-rendered DissentSection) + LLM-08 (_status.json schema) + INFRA-01 (Pattern #1 routine wiring; entrypoint shipped) + INFRA-02 (lite_mode + quota.py) + INFRA-03 (3-phase atomic write at data/YYYY-MM-DD/) + INFRA-04 (git fetch/pull/add/commit/push from routine).

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. routine/quota.py exports estimate_run_cost + 5 token constants + DEFAULT_MARKETS_DAILY_QUOTA_TOKENS=600_000; estimate formula yields n_tickers * 19_800; 30-ticker → 594_000; 31-ticker → 613_800.
2. routine/storage.py three-phase write: per-ticker → _index → _status (LAST); failed_tickers populated on per-ticker OSError without aborting; mkdir parents; sort_keys serialization; LF line ending.
3. routine/storage.py _status.json schema (LLM-08): {success, partial, completed_tickers, failed_tickers, skipped_tickers, llm_failure_count, lite_mode}; llm_failure_count formula combines persona data_unavailable count + synthesizer failure (only when not lite_mode).
4. routine/git_publish.py executes 5 subprocess.run calls in fixed order with check=True + timeout=60 + cwd parameterized; fail-loudly on CalledProcessError; no `git add -A` (Pattern #11 anti-pattern lock).
5. routine/run_for_watchlist.TickerResult Pydantic model with 6 fields (ticker, analytical_signals, position_signal, persona_signals, ticker_decision, errors); arbitrary_types_allowed.
6. run_for_watchlist sync-across-tickers loop with per-ticker exception isolation; lite-mode skips persona slate + synthesizer; preserves input order in result list.
7. routine/entrypoint.main() returns 0 on success and 1 on top-level exception; orchestrates load_watchlist → estimate_run_cost → asyncio.run(run_for_watchlist) → write_daily_snapshot → commit_and_push.
8. ≥30 tests across 5 test files all GREEN: 5 quota + 10 storage + 6 git_publish + 6 run_for_watchlist + 3 entrypoint integration.
9. Coverage ≥90% line / ≥85% branch on each of the 5 new modules.
10. Provenance per INFRA-07: routine/entrypoint.py docstring contains "novel-to-this-project"; routine/storage.py references the watchlist/loader.py atomic-write lineage.
11. REQUIREMENTS.md: LLM-01..08 + INFRA-01..04 (12 entries) all flipped to [x] / Complete in v1 list AND traceability table; "Last updated" timestamp updated.
12. ROADMAP.md: Phase 5 row Status flipped to Complete; Phase 5 plan list populated with 6 [x] entries (05-01..05-06).
13. Full repo regression GREEN at Phase 5 close (estimated ~470+ tests passing).
14. Phase 5 COMPLETE — Phase 6 (Frontend MVP) unblocked.
</success_criteria>

<output>
After completion, create `.planning/phases/05-claude-routine-wiring/05-06-SUMMARY.md` summarizing the 7 commits, naming the 5 new modules + their public surface, the LLM-08 _status.json schema, the Pattern #4 three-phase write order, the Pattern #6 lite-mode threshold, the Pattern #11 git fail-loudly discipline, and the Phase 5 closeout (12 requirements flipped to Complete).

Update `.planning/STATE.md` Recent Decisions with a 05-06 entry naming: routine.{quota, storage, git_publish, run_for_watchlist, entrypoint} shipped; LLM-08 _status.json + INFRA-01..04 closed; Phase 5 COMPLETE (6/6 plans); LLM-01..08 + INFRA-01..04 (12 requirements) flipped to Complete in REQUIREMENTS.md + ROADMAP.md; estimated ~470+ tests passing in full repo regression; Phase 6 (Frontend MVP) unblocked.

Also update `.planning/STATE.md` Current Phase block to reflect Phase 5 complete; bump completed_phases from 4 to 5; Current Phase Next pointer to "Phase 6 (Frontend MVP — Morning Scan + Deep-Dive) plan-phase".

Create `.planning/phases/05-claude-routine-wiring/05-PHASE-SUMMARY.md` (one-level-up phase summary) consolidating the 6 plan SUMMARY narratives into a single phase-close narrative — list the 12 requirements closed, the public surfaces shipped (4 modules in routine/, 2 in synthesis/, 1 widening in analysts/, 6 markdown persona prompts, 1 markdown synthesizer prompt), the 3 patterns locked (Pattern #2 messages.parse + Pattern #7 Python-computed dissent + Pattern #11 fail-loudly git publish), and the path forward to Phase 6.
</output>
