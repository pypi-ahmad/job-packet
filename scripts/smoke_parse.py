"""Live Agnes parse and deterministic match smoke."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.match import build_match_matrix
from src.parse import ResumeGroundingError, parse_job_description, parse_resume

CACHE = ROOT / "data" / "cache"


def _contains_google(value: object) -> bool:
    return "google" in json.dumps(value, ensure_ascii=False).casefold()


def main() -> None:
    """Run the live fixture parse and deterministic-match smoke check.

    Writes the latest parsed resume, job description, and match matrix below
    ``data/cache`` after validating the Northwind/Google fixture guard.
    """
    resume_text = (ROOT / "data/fixtures/resume.txt").read_text(encoding="utf-8")
    jd_text = (ROOT / "data/fixtures/jd.txt").read_text(encoding="utf-8")
    retried = False
    try:
        resume = parse_resume(resume_text)
    except ResumeGroundingError as error:
        if not any("google" in value.casefold() for value in error.invalid_values):
            raise
        resume = parse_resume(resume_text, strict=True)
        retried = True
    if _contains_google(resume.model_dump()):
        resume = parse_resume(resume_text, strict=True)
        retried = True
    jd = parse_job_description(jd_text)
    matrix = build_match_matrix(resume, jd)

    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "last_resume.json").write_text(resume.model_dump_json(indent=2), encoding="utf-8")
    (CACHE / "last_jd.json").write_text(jd.model_dump_json(indent=2), encoding="utf-8")
    (CACHE / "last_match.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    serialized_resume = (CACHE / "last_resume.json").read_text(encoding="utf-8")
    assert "Northwind Analytics" in serialized_resume
    assert "google" not in serialized_resume.casefold()
    print(f"SMOKE PASSED; strict_retry={'yes' if retried else 'no'}")


if __name__ == "__main__":
    main()
