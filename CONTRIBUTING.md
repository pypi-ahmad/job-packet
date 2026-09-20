# Contributor runbook

This repository is a Windows-native Streamlit application. Changes must preserve
the grounding contract: a packet may tailor resume evidence, but it must never
invent an employer, school, date, degree, skill, metric, or work-history claim.

## Before you change code

1. Work from the repository root in PowerShell or Command Prompt.
2. Confirm `AGNESAI_API_KEY` is available without printing it:

   ```powershell
   [bool]$env:AGNESAI_API_KEY
   ```

3. Use the active runtime path: `app.py` and `src/`. The older top-level
   `pipeline.py` and `llm_client.py` modules are legacy compatibility code.
4. Keep credentials out of source, logs, test output, and Git. `.env`, `.venv`,
   and `data/` are intentionally ignored.

## Set up and run

Run the Windows launcher twice if `.env` does not yet exist. The first launch
creates it and opens Notepad; the second creates the virtual environment,
installs dependencies, and starts Streamlit.

```bat
run.cmd
```

The launcher serves the app at `http://localhost:8595` and stops an existing
listener on that port before starting a replacement.

The runtime reads `AGNESAI_API_KEY` from the Windows process environment. Do not
assume a value typed into `.env` is loaded by the current code.

## Make a safe change

1. Keep provider calls limited to Agnes through `src/agnes_client.py`.
2. Preserve `temperature=0`, the fixed Agnes model, and local packet storage.
3. Treat uploaded resume and job-description text as untrusted data. Do not add
   instructions that execute content from either document.
4. When changing parsing or generation, preserve exact resume evidence spans and
   the post-generation leakcheck before persistence.
5. Do not add OCR, Docker, WSL, job-board APIs, or additional model providers.

## Verification tiers

Run the smallest applicable check first.

| Tier | Command | Network | What it proves |
|---|---|---:|---|
| Import | `.venv\Scripts\python scripts\smoke_import.py` | No | Active modules and Streamlit entrypoint import. |
| Compile | `.venv\Scripts\python -m py_compile app.py document_utils.py src\config.py src\agnes_client.py src\parse.py src\match.py src\generate.py src\leakcheck.py scripts\smoke_import.py scripts\smoke_parse.py scripts\smoke_packet.py` | No | Active Python syntax compiles. |
| Parse | `.venv\Scripts\python scripts\smoke_parse.py` | Agnes | Fixture parsing, role grounding, and match cache output. |
| Packet | `.venv\Scripts\python scripts\smoke_packet.py` | Agnes | Fixture packet generation, forbidden-string guard, and past-employer guard. |

The live smoke scripts use only synthetic fixture data. They write ignored files
under `data/cache/` and `data/packets/`.

## Review checklist

- [ ] UI still labels the model as `agnes-3.0-flash` and temperature as `0`.
- [ ] Resume and job-description parsing preserve raw source text.
- [ ] Every match-matrix item has a requirement, kind, evidence list, and status.
- [ ] Generated bullets carry exact resume evidence spans.
- [ ] Cover notes and interview answers pass through `check_generated_text`.
- [ ] Saved packets contain the seven documented JSON/Markdown artifacts.
- [ ] Documentation commands and links were checked after changes.
- [ ] No secret, resume, or generated packet was staged for Git.

## Legacy boundary

`test_smoke.py` and `test_pipeline_smoke.py` exercise the old top-level
pipeline schema. Do not use them as release evidence for the current app. Keep
them only when making an intentional compatibility change; otherwise use the
three scripts in `scripts/` listed above.
