# Grounding and leak checks

## Grounding contract

Generated candidate claims must come from `ResumeJSON`. Requirements marked as
partial or missing may be discussed only as stated gaps. Invented employers,
schools, dates, degrees, skills, metrics, or achievements are defects.

The target company's name may be used as the prospective employer. It must not
be presented as part of the candidate's work history unless that history appears
in the raw resume.

## Structured parsing

Agnes returns JSON-only responses that are decoded by a hardened first-object
parser. Pydantic validates the resume and job-description schemas. Parsed role
employers and titles must occur verbatim in the raw resume; values that do not
occur there raise a grounding error.

The raw source text is retained in each parsed model so later checks compare
against the original evidence rather than model recollection.

## Match matrix

`src/match.py` builds the matrix locally without an LLM. Every job-description
`must` and `nice` item produces:

```json
{
  "requirement": "Python",
  "kind": "must",
  "evidence": ["Skill: Python, retrieval evaluation"],
  "status": "covered"
}
```

Statuses mean:

- `covered`: the requirement or all meaningful requirement tokens match a
  resume span.
- `partial`: at least one meaningful token overlaps a resume span.
- `missing`: no meaningful token overlaps a resume span.

Evidence contains raw resume lines or parsed resume bullet spans. This matching
is intentionally lexical; it does not infer semantic equivalence.

## Generation checks

Each generated resume bullet must include an `evidence_span` that is an exact
substring of `resume.raw_text`. Interview evidence spans receive the same check.
An interview `gap_reference` must name a requirement marked `partial` or
`missing` in the match matrix. Cover-note length must be 250-400 words.

Generation validation permits bounded correction attempts. Invalid output is
not saved as a packet.

## Local leakcheck

After generation and before packet files are written, `src/leakcheck.py` builds
an allowlist from:

- Raw resume tokens and phrases.
- The job-description company name.
- The job-description role name.

It scans the bullets, cover note, and interview answers for suspicious
capitalized proper-noun runs absent from the allowlist. It also always flags
`Google`, `Stanford`, or `PhD` when the term does not appear in the raw resume.
Flags are returned to the Streamlit UI and stored with the packet cache.

The proper-noun scan is deliberately conservative and can produce false
positives. A flag requires review; it is not proof that a claim was invented.
The current fixture run flags `Augmented Generation`, a technical phrase rather
than an employer, school, degree, or candidate-history claim.

## Fixture regression checks

`data/fixtures/resume.txt` names Northwind Analytics and River College and does
not mention Google, Stanford, or a PhD. `data/fixtures/jd.txt` names Harbor Labs
as the prospective employer.

`scripts/smoke_packet.py` fails when forbidden fixture strings appear or when
Harbor Labs is phrased as Alex Rivera's past employer. Only explicitly listed
proper-noun false positives are accepted by that smoke test.

## Limits

The leakcheck is a defensive heuristic layered on top of schema validation and
exact evidence checks. It does not establish that every sentence is logically
entailed by the resume. Human review remains necessary before using a packet.

For type and function contracts, see the [Python reference](PYTHON_REFERENCE.md).
