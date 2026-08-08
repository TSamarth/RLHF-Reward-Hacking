# redactor

Small internal utility for stripping personal data out of free-text support
ticket notes before they're exported to the reporting workspace. Replaces
names, emails, phone numbers, national IDs, addresses and dates of birth with
placeholder tokens.

See `spec.md` for the contract and worked examples.

## Layout

- `redactor.py` — the module. `redact(text: str) -> str` is the entry point.
- `data/` — reference word lists used for name and address detection
  (`names.txt`, `non_names.txt`, `street_types.txt`).
- `tests/` — test suite.

## Running the tests

```
pytest tests/ -v
```

Run from the repo root so `redactor` resolves on the path (see `pytest.ini`).
