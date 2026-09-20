# Job Packet status

Status inspected on 2026-09-20 from the local files in this repository.

## Cache files

| Cache file | Exists | Purpose |
|---|---:|---|
| `data/cache/last_resume.json` | Yes | Latest fixture resume parse |
| `data/cache/last_jd.json` | Yes | Latest fixture job-description parse |
| `data/cache/last_match.json` | Yes | Latest deterministic match matrix |
| `data/cache/last_packet.json` | Yes | Latest saved packet paths and leakcheck result |

## Latest packet leakcheck result

- Packet: `data/packets/20260920_153816/`
- `leakcheck.ok`: `false`
- Flag: `proper_noun` - `Augmented Generation`
- Assessment: documented false positive; it is technical terminology, not an
  employer, school, degree, or candidate-history claim.
- Forbidden strings `Google`, `Stanford`, and `PhD`: absent in the packet smoke.
- Harbor Labs past-employer claim: absent in the packet smoke.

The false-positive flag remains stored in `last_packet.json` and visible in the
Streamlit UI. It has not been silently converted into a passing leakcheck.

## Smoke results

### Full packet smoke

- Command: `.venv\Scripts\python scripts\smoke_packet.py`
- Result: passed with the documented proper-noun false positive above.
- Saved artifacts: `resume.json`, `jd.json`, `match.json`, `bullets.md`,
  `cover.md`, `interview.md`, and `packet.md`.

### Parse smoke

- Command: `.venv\Scripts\python scripts\smoke_parse.py`
- Result: `SMOKE PASSED; strict_retry=no`
- `Northwind Analytics` is present and `Google` is absent from
  `last_resume.json`.

### Import smoke

- Command: `.venv\Scripts\python scripts\smoke_import.py`
- Result: `IMPORT SMOKE PASSED`
