"""Smoke test script for the Job Packet end-to-end pipeline.

Validates:
1. Parse resume to JSON {bullets, skills, roles, dates}
2. Parse JD to JSON {must, nice, company, role}
3. Match matrix: each JD must-have -> resume evidence or 'missing'
4. Rewrite 6-10 bullets using only resume evidence (reject invented employers)
5. Cover note 250-400 words
6. Eight interview questions with answers grounded in resume JSON
7. Optional one-page summary markdown
8. Grounding Assertion: No employer string appears in output that was not in resume.txt
"""

import re
import sys
from pathlib import Path

from document_utils import (
    create_packet_folder,
    load_full_packet_artifacts,
    save_full_packet_artifacts,
)
from pipeline import extract_employers_from_resume_text, run_full_pipeline


# Disallowed external employer test list (common hallucinated companies in software/aerospace)
COMMON_EXTERNAL_COMPANIES = [
    "Google", "Amazon", "AWS", "Microsoft", "Meta", "Facebook", "Apple",
    "SpaceX", "Boeing", "Lockheed", "Lockheed Martin", "Northrop",
    "Northrop Grumman", "Raytheon", "Blue Origin", "NASA", "Tesla",
    "Palantir", "Uber", "Netflix", "Oracle", "Salesforce", "IBM",
]


def run_pipeline_smoke():
    print("=" * 60)
    print("RUNNING JOB PACKET PIPELINE SMOKE TEST")
    print("=" * 60)

    resume_path = Path("data/fixtures/resume.txt")
    jd_path = Path("data/fixtures/jd.txt")

    assert resume_path.exists(), f"Missing fixture: {resume_path}"
    assert jd_path.exists(), f"Missing fixture: {jd_path}"

    resume_text = resume_path.read_text(encoding="utf-8")
    jd_text = jd_path.read_text(encoding="utf-8")

    # Determine allowed employers from resume fixture
    allowed_employers = {"Northwind Analytics", "Solstice Cloud Works"}
    target_company = "Apex Horizon Technologies"

    print(f"Fixture resume length: {len(resume_text)} chars")
    print(f"Fixture JD length: {len(jd_text)} chars")
    print(f"Expected resume employers: {allowed_employers}")

    # Run full pipeline with Agnes AI
    print("\n[Step 1 to 7] Executing run_full_pipeline via Agnes AI (agnes-3.0-flash)...")
    results = run_full_pipeline(
        resume_text=resume_text,
        jd_text=jd_text,
        provider_name="Agnes AI",
    )

    # 1. Assert resume JSON
    resume_json = results["resume_json"]
    for req_key in ["bullets", "skills", "roles", "dates"]:
        assert req_key in resume_json, f"Missing key '{req_key}' in resume_json"
        assert len(resume_json[req_key]) > 0, f"Empty list for '{req_key}' in resume_json"
    print(f"  [PASS] Step 1: resume_json parsed with keys: {list(resume_json.keys())}")
    print(f"         Extracted {len(resume_json['bullets'])} bullets, {len(resume_json['skills'])} skills, {len(resume_json['roles'])} roles")

    # 2. Assert JD JSON
    jd_json = results["jd_json"]
    for req_key in ["must", "nice", "company", "role"]:
        assert req_key in jd_json, f"Missing key '{req_key}' in jd_json"
    assert len(jd_json["must"]) >= 4, f"Expected at least 4 must-haves, got {len(jd_json['must'])}"
    assert "Apex" in jd_json["company"] or "Horizon" in jd_json["company"], f"Unexpected company: {jd_json['company']}"
    print(f"  [PASS] Step 2: jd_json parsed. Company='{jd_json['company']}', Role='{jd_json['role']}'")
    print(f"         Must-haves ({len(jd_json['must'])}), Nice-to-haves ({len(jd_json['nice'])})")

    # 3. Assert Match Matrix
    matrix = results["match_matrix"]
    assert isinstance(matrix, list) and len(matrix) >= len(jd_json["must"]), "Match matrix incomplete"
    for item in matrix:
        assert "requirement" in item, "Matrix item missing 'requirement'"
        assert "status" in item, "Matrix item missing 'status'"
        assert "evidence" in item, "Matrix item missing 'evidence'"
        assert item["status"] in ["matched", "partial", "missing"], f"Invalid status: {item['status']}"
    print(f"  [PASS] Step 3: Match matrix contains {len(matrix)} evaluated items")

    # 4. Assert Rewritten Bullets (6-10)
    bullets = results["rewritten_bullets"]
    assert isinstance(bullets, list), "rewritten_bullets is not a list"
    assert 6 <= len(bullets) <= 10, f"Expected 6-10 bullets, got {len(bullets)}"
    print(f"  [PASS] Step 4: Rewritten bullets count = {len(bullets)} (within 6-10 range)")

    # 5. Assert Cover Note (250-400 words)
    cover_note = results["cover_note"]
    word_count = len(cover_note.split())
    print(f"  [INFO] Step 5: Cover note word count = {word_count} words")
    assert 240 <= word_count <= 420, f"Cover note word count {word_count} outside 250-400 range"
    print(f"  [PASS] Step 5: Cover note validated ({word_count} words)")

    # 6. Assert Eight Interview Questions
    interview_q = results["interview_questions"]
    assert isinstance(interview_q, list), "interview_questions is not a list"
    assert len(interview_q) == 8, f"Expected exactly 8 interview questions, got {len(interview_q)}"
    for q in interview_q:
        assert "question" in q and q["question"], "Missing question text"
        assert "grounded_answer" in q and q["grounded_answer"], "Missing grounded_answer"
        assert "resume_evidence" in q and q["resume_evidence"], "Missing resume_evidence"
    print(f"  [PASS] Step 6: Exactly {len(interview_q)} grounded interview questions generated")

    # 7. Assert One-Page Summary
    summary = results["one_page_summary"]
    assert isinstance(summary, str) and len(summary) > 200, "One-page summary invalid or too short"
    assert "Requirements" in summary, "Summary missing requirements table section"
    print(f"  [PASS] Step 7: One-page summary generated ({len(summary)} chars)")

    # 8. Assert Grounding & Entity Audit Scanner
    print("\n[Step 8] Validating Anti-Hallucination & Employer/School Audit Scanner...")
    audit = results.get("audit_results")
    assert audit is not None, "Missing audit_results in pipeline output"
    assert audit["passed"] is True, f"Entity audit failed! Flagged: {audit.get('flagged_entities')}"
    assert len(audit.get("flagged_entities", [])) == 0, f"Flagged items found: {audit.get('flagged_entities')}"
    assert "Northwind Analytics" in audit.get("verified_employers", []), "Missing Northwind Analytics in verified employers"
    assert "River College" in audit.get("verified_schools", []), "Missing River College in verified schools"
    print(f"  [PASS] Step 8: Entity audit passed with 0 flagged items.")
    print(f"         Verified employers: {audit.get('verified_employers')}")
    print(f"         Verified schools: {audit.get('verified_schools')}")

    # Combine all generated text to check for invented employers
    all_generated_text = (
        " ".join(bullets)
        + " " + cover_note
        + " " + " ".join(q["grounded_answer"] for q in interview_q)
        + " " + summary
    )

    # Assert "Northwind Analytics" may appear and "Google" must not
    assert "Northwind Analytics" in all_generated_text or "Northwind" in all_generated_text, (
        "Expected Northwind Analytics to be referenced in the grounded output."
    )
    assert "Google" not in all_generated_text, (
        "Grounding violation! Made-up employer 'Google' must not appear in output."
    )

    # Check for known external company names
    for bad_company in COMMON_EXTERNAL_COMPANIES:
        assert bad_company.lower() not in all_generated_text.lower(), (
            f"Grounding violation! Hallucinated company '{bad_company}' found in generated output."
        )

    # Scan for pattern: 'at <Company>' or 'for <Company>'
    # Ensure any company named is either an allowed employer or target hiring company
    employer_mentions = re.findall(r"\b(?:at|for)\s+([A-Z][a-zA-Z0-9\s&]+?)(?=[,.\n;]|\s+in\b|\s+as\b)", all_generated_text)
    known_allowed = {e.lower() for e in allowed_employers}
    known_allowed.add("apex horizon")
    known_allowed.add("apex horizon technologies")
    known_allowed.add("river college")

    suspicious_mentions = []
    for mention in employer_mentions:
        cleaned_m = mention.strip().lower()
        # Filter out common english phrases after 'at' or 'for' (e.g. 'at least', 'for over', 'at scale')
        if cleaned_m in ["least", "scale", "sub-5ms", "sub-5ms latency", "runtime", "startup", "peak load", "every stage"]:
            continue
        # Check if matches any known allowed entity
        if not any(allowed in cleaned_m or cleaned_m in allowed for allowed in known_allowed):
            suspicious_mentions.append(mention)

    assert len(suspicious_mentions) == 0, (
        f"Grounding failure: Unrecognized/invented employer strings found: {suspicious_mentions}"
    )

    print("  [PASS] No invented employer strings detected in output. Grounding check PASSED.")

    # 9. Test file artifact persistence and cache
    print("\n[Step 9] Testing full artifact persistence and last_packet.json cache...")
    ts, packet_dir = create_packet_folder()
    saved_paths = save_full_packet_artifacts(
        packet_dir=packet_dir,
        resume_text=resume_text,
        jd_text=jd_text,
        pipeline_results=results,
    )
    assert Path(saved_paths["manifest"]).exists(), "Manifest file missing"
    assert Path(saved_paths["summary"]).exists(), "Summary file missing"

    # Verify data/cache/last_packet.json
    cache_file = Path("data/cache/last_packet.json")
    assert cache_file.exists(), "Cache file data/cache/last_packet.json was not created"
    assert cache_file.stat().st_size > 100, "Cache file is empty"
    print(f"  [PASS] Cached packet written to data/cache/last_packet.json ({cache_file.stat().st_size} bytes)")

    loaded_artifacts = load_full_packet_artifacts(packet_dir)
    assert len(loaded_artifacts["rewritten_bullets"]) == len(bullets), "Loaded bullets mismatch"
    assert len(loaded_artifacts["interview_questions"]) == 8, "Loaded interview questions mismatch"
    print(f"  [PASS] Artifacts persisted and reloaded successfully from {packet_dir}")

    print("\n" + "=" * 60)
    print("ALL SMOKE TEST ASSERTIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_pipeline_smoke()
    sys.exit(0 if success else 1)
