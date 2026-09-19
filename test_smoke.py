"""Smoke test suite for Job Packet initial setup."""

import sys
from pathlib import Path
import document_utils
import llm_client

def run_smoke_test():
    print("1. Testing document_utils...")
    # Test folder creation under test dir
    test_data_dir = Path("data/packets")
    ts, packet_dir = document_utils.create_packet_folder()
    assert packet_dir.exists(), "Packet directory creation failed"

    # Test saving data
    save_result = document_utils.save_packet_data(
        packet_dir=packet_dir,
        resume_text="Senior Software Engineer with 8 years of experience...",
        job_description_text="Looking for an AI engineer experienced with Python and Streamlit...",
        metadata={"role": "AI Engineer", "candidate": "Smoke Test"},
    )
    assert Path(save_result["resume_path"]).exists(), "resume.txt not created"
    assert Path(save_result["jd_path"]).exists(), "job_description.txt not created"
    assert Path(save_result["metadata_path"]).exists(), "metadata.json not created"

    # Test listing packets
    saved = document_utils.list_saved_packets()
    assert len(saved) >= 1, "Failed to list saved packets"
    print(f"   Saved {len(saved)} packet(s) successfully.")

    print("2. Testing llm_client provider discovery...")
    providers = llm_client.get_available_providers()
    assert "Agnes AI" in providers, "Agnes AI missing from provider catalog"
    print(f"   Available providers detected: {list(providers.keys())}")
    print(f"   Agnes configured: {providers['Agnes AI']['configured']}")
    print(f"   Default model: {providers['Agnes AI']['default_model']}")
    print(f"   Base URL: {providers['Agnes AI']['base_url']}")

    print("3. Validating app.py syntax...")
    import py_compile
    py_compile.compile("app.py", doraise=True)
    print("   app.py compiled without syntax errors.")

    print("\nALL SMOKE CHECKS PASSED.")

if __name__ == "__main__":
    run_smoke_test()
