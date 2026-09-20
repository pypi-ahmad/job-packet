# Architecture

## Runtime boundary

Job Packet Generator is a native Windows 11 Streamlit application. It runs from
the repository virtual environment created by `run.cmd`. It does not require
WSL, Docker, a vector database, or a job-board API.

The only external service is Agnes. The official OpenAI Python SDK connects to
`https://apihub.agnes-ai.com/v1` with model `agnes-3.0-flash`, temperature `0`,
and the `AGNESAI_API_KEY` Windows environment variable.

## Pipeline

The **Run all** action executes these stages in order:

1. Parse the resume and job description through Agnes into validated Pydantic
   models.
2. Build the match matrix locally with deterministic Python matching.
3. Ask Agnes to generate tailored bullets, a cover note, and eight interview
   question-and-answer pairs.
4. Run the local post-generation leakcheck.
5. Save JSON and Markdown artifacts under `data/packets/<timestamp>/`.

The Streamlit UI then renders the packet, displays leakcheck flags, and offers a
ZIP containing all saved artifacts.

## Components

| Component | Responsibility |
|---|---|
| `app.py` | Streamlit pages, session state, full-pipeline action, rendering, and ZIP download |
| `document_utils.py` | Local PDF-to-Markdown extraction through `pdf_inspector.process_pdf` |
| `src/config.py` | Fixed model configuration and secret-presence health check |
| `src/agnes_client.py` | Official OpenAI SDK client and bounded HTTP 429 retries |
| `src/parse.py` | Pydantic schemas, hardened first-JSON parser, and resume-role grounding |
| `src/match.py` | Deterministic requirement-to-resume evidence matching |
| `src/generate.py` | Grounded generation, evidence validation, rendering, and packet persistence |
| `src/leakcheck.py` | Local suspicious proper-noun and forbidden-string scan |
| `scripts/smoke_parse.py` | Live parse and match fixture smoke test |
| `scripts/smoke_packet.py` | Live end-to-end generation and leak test |
| `scripts/smoke_import.py` | Import and module-path smoke test |

## Data flow and storage

Pasted text or locally extracted PDF Markdown is held in Streamlit session state.
The resume and job description are sent to Agnes for structured parsing. The
validated JSON and deterministic match matrix are then sent to Agnes for packet
generation.

Generated artifacts are saved locally as:

- `resume.json`
- `jd.json`
- `match.json`
- `bullets.md`
- `cover.md`
- `interview.md`
- `packet.md`

Local caches and packets live below `data/`, which is ignored by Git.

## PDF behavior

PDF input is optional. `pdf_inspector.process_pdf` extracts Markdown locally and
places it in the resume text area. If extraction returns no Markdown, the UI
asks the user to paste text instead. OCR is outside this version's scope.

## Active and legacy code paths

The active application imports `src/` for parsing, matching, generation, and
leak checking. `document_utils.extract_text_from_upload` is the only helper from
the repository root used by `app.py`.

`llm_client.py`, `pipeline.py`, and the persistence helpers in
`document_utils.py` remain as legacy compatibility code. They are not called by
the current Streamlit workflow, and their older smoke scripts do not describe
the current fixture contract. See the [Developer guide](DEVELOPER_GUIDE.md) for
the supported verification commands.
