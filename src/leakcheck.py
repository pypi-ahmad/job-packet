"""Local generated-text proper-noun leak checks."""

import re

_FORBIDDEN = ("Google", "Stanford", "PhD")
_PROPER_NOUN_RUN = re.compile(
    r"\b(?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,})){1,3}\b"
)
_LEADING_CONTEXT = {
    "applied",
    "as",
    "at",
    "built",
    "developed",
    "for",
    "from",
    "in",
    "the",
    "to",
    "used",
    "utilized",
    "with",
}


def _allowlist(raw_resume: str, jd_company: str, jd_role: str) -> set[str]:
    source = "\n".join((raw_resume, jd_company, jd_role))
    tokens = re.findall(r"[A-Za-z0-9+#.-]+", source)
    allowed = {token.casefold() for token in tokens}
    for size in range(2, 5):
        allowed.update(" ".join(tokens[index : index + size]).casefold() for index in range(len(tokens) - size + 1))
    return allowed


def check_generated_text(
    raw_resume: str,
    jd_company: str,
    jd_role: str,
    generated_text: str,
) -> dict[str, object]:
    """Flag generated names and forbidden terms absent from source evidence.

    Args:
        raw_resume: Original resume text used to build the allowlist.
        jd_company: Target company name allowed as prospective-employer context.
        jd_role: Target role name allowed as prospective-employer context.
        generated_text: Rendered bullets, cover note, and interview content.

    Returns:
        A mapping with ``ok`` and a list of typed flags. A flag requires review
        and can be a conservative false positive.
    """
    allowed = _allowlist(raw_resume, jd_company, jd_role)
    resume_lower = raw_resume.casefold()
    output_lower = generated_text.casefold()
    flags: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for term in _FORBIDDEN:
        if term.casefold() in output_lower and term.casefold() not in resume_lower:
            flags.append({"type": "forbidden", "text": term})
            seen.add(("forbidden", term.casefold()))

    for match in _PROPER_NOUN_RUN.finditer(generated_text):
        phrase = match.group(0).strip()
        words = phrase.split()
        if len(words) > 1 and words[0].casefold() in _LEADING_CONTEXT:
            phrase = " ".join(words[1:])
        elif len(words) == 2 and words[0].casefold().endswith(("ed", "ized")) and words[1].casefold() in allowed:
            phrase = words[1]
        if phrase.casefold() in allowed:
            continue
        key = ("proper_noun", phrase.casefold())
        if key not in seen:
            seen.add(key)
            flags.append({"type": "proper_noun", "text": phrase})

    return {"ok": not flags, "flags": flags}
