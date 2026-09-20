# Python reference

This reference describes the active application interfaces first. Types use
Python 3.9+ built-in generic annotations.

## Active data models

### `src.parse.ResumeRole`

One resume role copied from source text.

| Field | Type | Contract |
|---|---|---|
| `employer` | `str` | Exact raw-resume employer span or empty string. |
| `title` | `str` | Exact raw-resume title span or empty string. |
| `start`, `end` | `str` | Source date text or empty strings. |
| `bullets` | `list[str]` | Resume bullet spans. |

### `src.parse.ResumeJSON`

`name`, `roles`, `schools`, `skills`, and `raw_text`. `raw_text` is the source
of truth for later evidence checks.

### `src.parse.JDJSON`

`company`, `role`, `must`, `nice`, and `raw_text`. Requirements are preserved
as job-description content rather than inferred candidate experience.

### `src.generate.GeneratedPacket`

Contains 6-10 `TailoredBullet` records, a 250-400-word `cover_note`, and
exactly eight `InterviewItem` records. A bullet contains `text` and an exact
`evidence_span`. An interview item contains `question`, `answer`, evidence
spans, and an optional match-matrix `gap_reference`.

## Active functions

| Module | Callable | Purpose | Important failures |
|---|---|---|---|
| `src.config` | `agnes_key_is_set()` | Checks credential presence without exposing it. | None. |
| `src.agnes_client` | `chat_completion(messages, max_retries=3, json_only=False)` | Calls Agnes with the fixed model and bounded 429 retries. | `RuntimeError` without the key; SDK errors after retries. |
| `src.parse` | `first_json_object(text)` | Decodes the first valid object and rejects duplicate keys. | `ValueError` for malformed, missing, or oversized JSON. |
| `src.parse` | `parse_resume(text, strict=False)` | Produces `ResumeJSON` and checks employers/titles against source text. | `ResumeGroundingError`, Pydantic validation errors, Agnes errors. |
| `src.parse` | `parse_job_description(text)` | Produces `JDJSON`. | Pydantic validation or Agnes errors. |
| `src.match` | `build_match_matrix(resume, job_description)` | Returns one local evidence/status mapping per `must` and `nice` requirement. | None for valid models. |
| `src.generate` | `generate_packet(resume, jd, matrix)` | Requests, validates, and retries grounded packet generation. | `ValueError` after failed evidence, gap, or length validation. |
| `src.generate` | `render_markdown(packet)` | Returns the four rendered Markdown artifact contents. | None for a valid packet. |
| `src.generate` | `save_packet(resume, jd, matrix, packet, base_dir=...)` | Leak-checks then writes seven artifacts and paths. | Filesystem errors. |
| `src.leakcheck` | `check_generated_text(raw_resume, jd_company, jd_role, generated_text)` | Returns `{"ok": bool, "flags": list}`. | None. |
| `document_utils` | `extract_text_from_upload(uploaded_file)` | Processes a Streamlit upload; PDFs use local `process_pdf`. | PDF processing or filesystem errors. |

### Match matrix shape

```python
{
    "requirement": "Python",
    "kind": "must",
    "evidence": ["Skill: Python, retrieval evaluation"],
    "status": "covered",  # also "partial" or "missing"
}
```

### Saved packet result shape

```python
{
    "packet_dir": "data/packets/<timestamp>",
    "paths": {"resume.json": "...", "packet.md": "..."},
    "leakcheck": {"ok": False, "flags": [{"type": "proper_noun", "text": "..."}]},
}
```

## Supported scripts

| Script | Purpose | Network |
|---|---|---:|
| `scripts/smoke_import.py` | Imports active modules and the Streamlit entrypoint. | No |
| `scripts/smoke_parse.py` | Parses fixtures and writes the parse/match caches. | Agnes |
| `scripts/smoke_packet.py` | Generates a fixture packet and applies leak/past-employer checks. | Agnes |

## Legacy compatibility interfaces

The following are retained but not used by `app.py`:

- `llm_client.py`: the earlier Agnes client wrapper.
- `pipeline.py`: the earlier dictionary-based parsing and generation pipeline.
- `document_utils.py` persistence helpers: earlier packet artifact format.
- `test_smoke.py` and `test_pipeline_smoke.py`: old-schema smoke scripts.

Their public functions have docstrings for maintainers. Do not build new product
behavior against them; use the active `src/` interfaces above.
