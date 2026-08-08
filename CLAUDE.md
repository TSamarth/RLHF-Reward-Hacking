# CLAUDE.md — Standing Instructions

## What this repo is

An experiment that measures how often a coding agent games a test suite instead of solving the problem. Output: footage for a video cold open, plus a public repo anyone can rerun.

Read in this order: `SPEC.md` → `ARCHITECTURE.md` → `TASK-DESIGN.md` → `DETECTION.md`.

## The rules that must not be broken

These aren't style preferences. Breaking any one of them makes the artefact worthless.

1. **Never prompt the agent toward cheating.** No hints, no "by any means necessary", no mention that tests are editable. The behaviour must be emergent or it proves nothing.
2. **The container never gets network access.** The harness (host) calls model APIs. The agent's code execution is sealed. See `ARCHITECTURE.md §1`.
3. **The held-out suite never enters the agent's container.**
4. **The reference solution must pass both suites.** If it can't, the task is unfair — fix the task, not the reference.
5. **Never delete or silently retry a trial.** Errors get recorded with `stop_reason`.
6. **No eval fingerprints in the workspace.** No `eval`, `task`, `scorer`, `benchmark`, `trial`, `holdout` in anything the agent can see.

## How we work together

1. **Be objective and truthful.** Do not flatter weak ideas. A polite "this won't work, here's why" is worth more than encouragement.
2. **Keep it simple.** Do not give complicated answer or jargons. Talk in a natural human tone and keep your delivery in simple, crisp and clear language.
3. **Play the adversary when it helps.** Argue as a senior developer to pressure-test our ideas and codebase before the market does. After significant development in this project, launch subagents *(model Sonnet 5)* which play your own adversary.
4. **Be efficient in your communication.** Distill down your findings and ideas and structurize them. Understand what leve of reasoning and verbosity is required according to the complexity of topic.
5. **Cover What / How / Why during implementation**. That is the bar for being "useful."
6. **Know where to stop.** Deep dives sprawl. If we're drifting off-topic, or a thread clearly won't pay off, say so and pull us back. Efficiency is knowing where to start and where to stop.
7. **Test cases != completion scenario.** Only passing test cases are not the definition of done. Unless a functionality does not perform as intended in live-run, we cannot mark it as complete.

## Build order

Don't build it all then test. Each step must run before the next starts.

1. `docker/` + `harness/sandbox.py` — prove you can exec in a sealed container
2. `harness/` — ReAct loop against **Ollama only**, one hardcoded task, no runner
3. `tasks/pii_redactor/` — workspace, 47 visible tests, 40 held-out, `reference_solution.py`
4. **Gate:** reference solution passes 47/47 and 40/40. Stop here until it does.
5. `runner/run_trial.py` — full 12-step lifecycle from `ARCHITECTURE.md §2`
6. `analysis/rules.py` — **gate:** zero rule hits against the reference solution
7. Calibrate the task on the local model (`TASK-DESIGN.md §8`)
8. `runner/run_trials.py`, provider adapters for frontier models
9. `analysis/judge.py`, `analysis/report.py`
10. Run the matrix

Steps 4 and 6 are hard gates. Don't proceed past either.

## Conventions

- Python 3.12, type hints, `ruff` clean
- No framework where 50 lines will do — the harness is meant to be readable on camera
- Every prompt, model ID and parameter goes in config, never inline
- Fail loudly. A silent exception here means a corrupted result.
- Tests for `analysis/rules.py` specifically — a detection bug corrupts the headline number

## Cost

Hard ceiling **$40**. Develop entirely against Ollama. Frontier API calls happen once, at step 10. The runner must track cumulative spend and abort if projected cost exceeds the ceiling.

## When something is ambiguous

Ask. Do not guess and do not silently pick a default — a wrong assumption in the task design or detection rules invalidates the whole run, and it may not be visible until after the money is spent.

## Stop rule

If, after a day of calibration, the local model produces zero hacks on a deliberately tempting task, stop and report that. Do not escalate the prompt to force a result — that breaks rule 1.
