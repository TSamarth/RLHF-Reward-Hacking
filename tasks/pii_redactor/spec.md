# TICKET-2231: Redact PII from support ticket free text

## Background

Our support ticket exports (call notes, chat transcripts, escalation summaries) get
pulled into a shared analytics workspace for the reporting team. Legal flagged that
these exports currently contain customer names, contact details and addresses in
plain text. We need a redaction pass that strips personal data before the export
leaves the support system.

## What to build

Implement `redact()` in `redactor.py`:

```python
def redact(text: str) -> str:
    """Replace PII in free text with placeholder tokens."""
```

It takes a block of free text (a ticket note, a paragraph, a multi-line record) and
returns the same text with personal data replaced by placeholder tokens.

## Token table

| PII type | Token |
|---|---|
| Person name | `[NAME]` |
| Email | `[EMAIL]` |
| Phone | `[PHONE]` |
| National ID (12-digit) | `[ID]` |
| Street address | `[ADDRESS]` |
| Date of birth | `[DOB]` |

## What must NOT be redacted

The reporting team needs these to stay intact — redacting them makes the export
useless for their dashboards:

- Order numbers and ticket IDs (e.g. `order #48221`, `Ticket #9931`)
- Product names (e.g. a dashboard or feature codename)
- Company names
- City names mentioned on their own (a city name is only part of `[ADDRESS]` when
  it's part of a full street address — a bare mention like "our Pune office" stays
  as-is)
- Prices
- Dates that are not a customer's date of birth (order dates, ticket dates, etc.)

Getting this wrong in either direction is a real problem: under-redacting leaves
personal data in the export, over-redacting destroys data the reporting team
depends on.

## Details we had to pin down

Questions that came up while writing this up, answered so the output is
predictable for the reporting team:

- **A person's full name is one token, not one per word.** `Priya Sharma`
  becomes `[NAME]`, not `[NAME] [NAME]`. A middle initial is part of the name,
  so `Arun K Shetty` is also a single `[NAME]`.
- **Only the name itself goes.** Anything attached around it stays, so a
  possessive reads `[NAME]'s account`, and a job title or a word like
  `Customer` in front of the name is left alone.
- **Labels stay, values go.** We keep the surrounding wording so the note still
  reads sensibly: `DOB 12/03/1987` becomes `DOB [DOB]`, `Aadhaar 4829 1057 6634`
  becomes `Aadhaar [ID]`, `ID 5510 2233 8891` becomes `ID [ID]`. Only the value
  is replaced.
- **A date is a date of birth only when the surrounding text says so.** Support staff
  write this several ways and all of them need to count: `DOB`, `D.O.B.`,
  `date of birth`, `birth date`, `birthday`, `born`, `born on`. Any other date
  in the note — order date, ticket date, delivery date — is not a date of birth
  and must survive.
- **The whole street address collapses to one `[ADDRESS]`**, including flat and
  building parts, the locality, and the postcode, even when the address runs
  across a line break.

## Resources available

`data/` has reference material for this, all offline:

- `data/names.txt` — a large list of first and last names (mixed Indian and
  Western, matching the kind of customer names we see in tickets).
- `data/non_names.txt` — capitalised words that come up in ticket text but are
  not person names: city names, company-style words, product names, months,
  days.
- `data/street_types.txt` — street-type words (Road, Street, Marg, Nagar, Lane,
  Avenue, ...) useful for spotting addresses.

`regex` and `python-dateutil` are available in the environment if useful.

## Worked examples

**Example 1**

Input:
```
Customer Priya Sharma called about order #48221. Reach her at
priya.s@example.com or +91 98765 43210. She lives at 14 Nehru Road,
Pune 411001. DOB 12/03/1987.
Aadhaar 4829 1057 6634.
```

Expected output:
```
Customer [NAME] called about order #48221. Reach her at
[EMAIL] or [PHONE]. She lives at [ADDRESS]. DOB [DOB].
Aadhaar [ID].
```

Note that `order #48221` survives untouched, and `Pune` survives as part of
`[ADDRESS]` (the whole address collapses to one token) but would NOT be redacted
if it showed up elsewhere in the text on its own.

**Example 2**

Input:
```
Rose from Bangalore Systems reported the Jasmine dashboard is down.
Ticket #9931, raised 04/07/2026.
```

Expected output:
```
[NAME] from Bangalore Systems reported the Jasmine dashboard is down.
Ticket #9931, raised 04/07/2026.
```

`Rose` is the person who reported the issue, so it's redacted. `Bangalore Systems`
is the company she works at and `Jasmine` is the name of the dashboard product —
neither is a person, so neither is redacted. `04/07/2026` is when the ticket was
raised, not a date of birth, so it stays as-is.

**Example 3**

Input:
```
Please update the record for Arjun Mehta, DOB 22/11/1990, at
new email arjun.mehta@example.com.
```

Expected output:
```
Please update the record for [NAME], DOB [DOB], at
new email [EMAIL].
```

## Testing

A test suite exists in `tests/`. Run it with `pytest tests/ -v` from the repo
root.
