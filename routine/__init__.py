# novel-to-this-project — Phase 5 routine package marker (project-original).
"""Phase 5 daily-routine package — orchestration for the scheduled Claude Code routine.

Modules (filled in Waves 2-5):
    llm_client          — Anthropic SDK wrapper + retry + default-factory (Wave 2)
    persona_runner      — async fan-out across 6 personas per ticker (Wave 3)
    synthesizer_runner  — single-call wrapper over synthesis.synthesizer (Wave 4)
    storage             — atomic per-ticker JSON + _index + _status writes (Wave 5)
    git_publish         — git fetch / pull --rebase / add / commit / push (Wave 5)
    run_for_watchlist   — main per-ticker loop (Wave 5)
    entrypoint          — main() entry point invoked by Claude Code Routine (Wave 5)
    quota               — estimate_run_cost + per-call token constants (Wave 5)
"""
