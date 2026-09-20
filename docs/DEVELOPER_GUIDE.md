# Developer guide

## Purpose

This guide explains how to develop and debug the current Job Packet Generator
runtime. For a first-use walkthrough, start with the
[zero to mastery tutorial](ZERO_TO_MASTERY.md). For contributor procedures, see
the [runbook](../CONTRIBUTING.md).

## Supported runtime

The application runs on native Windows 11 through `run.cmd`. It creates a
`.venv` with `py -3`, installs `requirements.txt`, and starts `app.py` with
Streamlit at `http://localhost:8595`. Before launching, it finds and stops the
existing process listening on port 8595; if Windows cannot release that port,
the launcher exits instead of starting a second app.

The only remote model endpoint is Agnes at
`https://apihub.agnes-ai.com/v1`. The active model is `agnes-3.0-flash` at
temperature `0`. `AGNESAI_API_KEY` must be present in the process environment.
The health display reports only whether the key is set.

Use a persistent Windows user variable:

```powershell
setx AGNESAI_API_KEY "your-key"
```

Close and reopen the terminal after `setx`. For a single PowerShell session,
use `$env:AGNESAI_API_KEY = "your-key"`. Never place a real key in source,
test output, or documentation examples.

`run.cmd` creates `.env` from `.env.example` because that is the launcher
contract. The active configuration reads `os.environ`, so `.env` is not a
substitute for exporting the environment variable.

## Active pipeline

`app.py` owns the Streamlit pages and session state. The **Run all** button
executes the active pipeline in this order:

1. `src.parse` sends resume and job-description text to Agnes and validates
   `ResumeJSON` and `JDJSON` models.
2. `src.match` creates the requirement matrix locally from exact resume spans.
3. `src.generate` asks Agnes for evidence-tagged bullets, a cover note, and
   eight interview answers, then validates their evidence and gap references.
4. `src.leakcheck` scans rendered text before `src.generate.save_packet` writes
   the packet artifacts.
5. `app.py` renders the result and offers a ZIP download.

`document_utils.extract_text_from_upload` is the only root-level helper used by
the active UI. It sends uploaded PDFs to local `pdf_inspector.process_pdf` and
returns Markdown for the resume text area. Empty extraction means the user must
paste text. OCR is intentionally not implemented.

## Module ownership

| Location | Active responsibility |
|---|---|
| `app.py` | Streamlit pages, state, full-pipeline trigger, packet display, ZIP download |
| `src/config.py` | Fixed model constants and credential-presence check |
| `src/agnes_client.py` | Official OpenAI SDK calls and bounded HTTP 429 retries |
| `src/parse.py` | JSON extraction, Pydantic models, and resume role grounding |
| `src/match.py` | Deterministic local match matrix |
| `src/generate.py` | Packet schema, validation, rendering, and persistence |
| `src/leakcheck.py` | Local suspicious proper-noun and forbidden-term scan |
| `scripts/` | Supported import, parse, and packet smoke checks |

## Legacy compatibility modules

`llm_client.py`, `pipeline.py`, and most persistence functions in
`document_utils.py` implement an earlier packet schema. The current app does not
import them. They remain documented for maintainers and existing historical
tests, but they are not an extension point for new features.

The legacy tests expect outdated fixture names, schemas, and target companies.
They should not be used to judge current runtime behavior. If a compatibility
change is necessary, first decide whether the active `src/` contract or the
legacy contract is authoritative; do not blend their output shapes.

## Debugging guide

| Symptom | Check | Resolution |
|---|---|---|
| Run all is disabled | Sidebar says key is not set | Export `AGNESAI_API_KEY`, then restart Streamlit. |
| Agnes returns 429 | Retry timing in `src/agnes_client.py` | Wait for bounded retries; do not add an alternate provider. |
| Resume parse rejects a role | `ResumeGroundingError` values | Correct the source resume or parser prompt; employers and titles must be verbatim. |
| PDF text area stays empty | PDF extraction returned no Markdown | Paste text instead; OCR is out of scope. |
| Leakcheck flags a phrase | Packet view and `last_packet.json` | Review it against source evidence; document a known false positive rather than hiding it. |
| Output claims target-company history | Packet smoke guard | Fix the generation prompt or validation before accepting the packet. |

## Verification

Start with the local import smoke:

```bat
.venv\Scripts\python scripts\smoke_import.py
```

Then run live fixture checks when changing Agnes-facing behavior:

```bat
.venv\Scripts\python scripts\smoke_parse.py
.venv\Scripts\python scripts\smoke_packet.py
```

The current result and cache state are recorded in [STATUS.md](../STATUS.md).
Public types and callable contracts are in the [Python reference](PYTHON_REFERENCE.md).
