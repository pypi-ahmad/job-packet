"""Full live Agnes packet smoke on synthetic fixtures."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generate import generate_packet, render_markdown, save_packet
from src.match import build_match_matrix
from src.parse import parse_job_description, parse_resume

CACHE = ROOT / "data/cache/last_packet.json"
DOCUMENTED_FALSE_POSITIVES = {"Augmented Generation", "Dear Hiring Team"}


def _claims_target_as_past_employer(text: str, company: str) -> bool:
    escaped = re.escape(company)
    patterns = (
        rf"\b(?:worked|employed|served)\b.{{0,30}}\b(?:at|for|with)\s+{escaped}\b",
        rf"\bat\s+{escaped}\b.{{0,40}}\b(?:worked|built|led|developed|created|managed)\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def main() -> None:
    """Run the live fixture packet smoke and write its cache result.

    Validates forbidden terms, target-company employment phrasing, and only
    explicitly documented proper-noun false positives.
    """
    resume_text = (ROOT / "data/fixtures/resume.txt").read_text(encoding="utf-8")
    jd_text = (ROOT / "data/fixtures/jd.txt").read_text(encoding="utf-8")
    resume = parse_resume(resume_text)
    jd = parse_job_description(jd_text)
    matrix = build_match_matrix(resume, jd)
    packet = generate_packet(resume, jd, matrix)
    saved = save_packet(resume, jd, matrix, packet, ROOT / "data/packets")

    markdown = render_markdown(packet)
    generated_text = "\n".join(markdown.values())
    forbidden = [term for term in ("Google", "Stanford", "PhD") if term.casefold() in generated_text.casefold()]
    assert not forbidden, f"Forbidden strings found: {forbidden}"
    assert not _claims_target_as_past_employer(generated_text, jd.company), (
        f"{jd.company} was claimed as Alex's past employer"
    )
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(
            {
                "packet_dir": saved["packet_dir"],
                "paths": saved["paths"],
                "leakcheck": saved["leakcheck"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    unexplained_flags = [
        flag
        for flag in saved["leakcheck"]["flags"]
        if flag.get("type") != "proper_noun" or flag.get("text") not in DOCUMENTED_FALSE_POSITIVES
    ]
    assert not unexplained_flags, f"Unexplained leak-check flags: {unexplained_flags}"
    print(
        f"PACKET SMOKE PASSED: {saved['packet_dir']}; "
        f"documented_false_positives={saved['leakcheck']['flags']}"
    )


if __name__ == "__main__":
    main()
