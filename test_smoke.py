"""Local smoke checks that do not send resume data to Agnes."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from document_utils import create_packet_folder, save_full_packet_artifacts
from llm_client import AGNES_BASE_URL, AGNES_MODEL
from pipeline import scan_output_for_unverified_entities


def run_smoke_test() -> None:
    """Exercise legacy helper paths and ensure the current app imports.

    This historical smoke writes ignored local artifacts and is not release
    evidence for the active ``src`` pipeline.
    """
    assert AGNES_BASE_URL == "https://apihub.agnes-ai.com/v1"
    assert AGNES_MODEL == "agnes-3.0-flash"
    audit = scan_output_for_unverified_entities(
        {"rewritten_bullets": ["Built reports at Northwind Analytics.", "Led work at Google."],
         "cover_note": "I studied at River College.",
         "interview_questions": [{"id": 1, "grounded_answer": "I worked at SpaceX."}]},
        "Northwind Analytics\nRiver College",
    )
    assert not audit["passed"]
    assert {item["entity"] for item in audit["flagged_entities"]} == {"Google", "SpaceX"}
    _, packet_dir = create_packet_folder()
    saved = save_full_packet_artifacts(packet_dir, "Northwind Analytics", "Role", {"audit_results": audit})
    assert Path(saved["cache"]).exists()
    app = AppTest.from_file("app.py").run(timeout=15)
    assert not app.exception
    print("ALL SMOKE CHECKS PASSED.")


if __name__ == "__main__":
    run_smoke_test()
