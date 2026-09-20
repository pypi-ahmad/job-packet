"""Deterministic resume-to-job requirement matching."""

import re

from src.parse import JDJSON, ResumeJSON

_STOPWORDS = {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with"}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.-]+", text.casefold())
        if token not in _STOPWORDS
    }


def _resume_spans(resume: ResumeJSON) -> list[str]:
    spans = [line.strip() for line in resume.raw_text.splitlines() if line.strip()]
    for role in resume.roles:
        spans.extend(role.bullets)
    return list(dict.fromkeys(span for span in spans if span))


def _match_requirement(requirement: str, kind: str, spans: list[str]) -> dict[str, object]:
    requirement_tokens = _tokens(requirement)
    evidence = [span for span in spans if requirement.casefold() in span.casefold()]
    if evidence:
        status = "covered"
    else:
        covered = [span for span in spans if requirement_tokens and requirement_tokens <= _tokens(span)]
        partial = [span for span in spans if requirement_tokens & _tokens(span)]
        evidence = covered or partial
        status = "covered" if covered else "partial" if partial else "missing"
    return {"requirement": requirement, "kind": kind, "evidence": evidence, "status": status}


def build_match_matrix(resume: ResumeJSON, job_description: JDJSON) -> list[dict[str, object]]:
    """Match every job requirement against exact resume spans locally.

    Args:
        resume: Parsed resume whose raw lines and role bullets are evidence.
        job_description: Parsed job description containing must and nice items.

    Returns:
        One mapping per requirement with ``requirement``, ``kind``,
        ``evidence``, and a ``covered``, ``partial``, or ``missing`` status.
    """
    spans = _resume_spans(resume)
    requirements = [(item, "must") for item in job_description.must]
    requirements.extend((item, "nice") for item in job_description.nice)
    return [_match_requirement(item, kind, spans) for item, kind in requirements]
