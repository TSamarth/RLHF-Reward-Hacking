# Third-party data

`tasks/pii_redactor/workspace/data/names.txt` is a curated, deduplicated and
Title-Cased blend of four public name lists. It is reference data for a
redaction exercise; no list is reproduced in full.

| Source | Licence | Used for |
|---|---|---|
| [`dominictarr/random-name`](https://github.com/dominictarr/random-name) — `first-names.txt` | MIT | Western first names |
| [`smashew/NameDatabases`](https://github.com/smashew/NameDatabases) — `surnames/us.txt` | The Unlicense (public domain) | Western surnames |
| [`smashew/NameDatabases`](https://github.com/smashew/NameDatabases) — `surnames/hi.txt` | The Unlicense (public domain) | Indian surnames |
| [`laxmimerit/indian-names-dataset`](https://github.com/laxmimerit/indian-names-dataset) — `Indian-Male-Names.csv`, `Indian-Female-Names.csv` | **None stated** — see below | Indian given names |

## The one with no licence

The `laxmimerit` repository ships no `LICENSE` file and states no licence
terms. Its README disclaims ownership and points at an untraced Kaggle
origin, so no permission to redistribute was ever granted by anyone
identifiable. We searched for a GitHub-hosted Indian given-name list with an
explicit permissive licence and did not find one.

We use it anyway, with attribution and this notice, because the material is
a list of common given names — facts about naming practice rather than
creative expression — and because the alternative is a name list with no
Indian representation, which would make the redaction exercise unfair by
construction.

If you are redistributing this repository somewhere that needs cleaner
provenance, the Indian given names are the part to replace. The Indian
surnames already come from the Unlicense'd `smashew` repo and need no
change.

`non_names.txt` and `street_types.txt` were written for this repository.
