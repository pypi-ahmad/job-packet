"""Document utilities for parsing resumes, job descriptions, and managing packet folders."""

import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pypdf import PdfReader

BASE_DATA_DIR = Path("data")
PACKETS_DIR = BASE_DATA_DIR / "packets"


def extract_text_from_upload(uploaded_file) -> str:
    """Extract text from uploaded Streamlit file (PDF, TXT, or MD)."""
    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()
    content_bytes = uploaded_file.getvalue()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(content_bytes)
    elif filename.endswith((".txt", ".md")):
        return content_bytes.decode("utf-8", errors="replace")
    else:
        # Fallback decode
        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF byte stream using pypdf."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted_pages: List[str] = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            extracted_pages.append(page_text.strip())
    return "\n\n".join(extracted_pages)


def create_packet_folder(base_dir: Optional[Path] = None) -> Tuple[str, Path]:
    """Create a new timestamped packet directory under data/packets/<timestamp>/."""
    target_packets_dir = base_dir or PACKETS_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    packet_path = target_packets_dir / timestamp
    packet_path.mkdir(parents=True, exist_ok=True)
    return timestamp, packet_path


def save_packet_data(
    packet_dir: Path,
    resume_text: str,
    job_description_text: str,
    metadata: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    """Save resume, job description, and metadata into target packet directory."""
    packet_dir.mkdir(parents=True, exist_ok=True)

    resume_file = packet_dir / "resume.txt"
    jd_file = packet_dir / "job_description.txt"
    meta_file = packet_dir / "metadata.json"

    resume_file.write_text(resume_text, encoding="utf-8")
    jd_file.write_text(job_description_text, encoding="utf-8")

    meta_payload = metadata or {}
    meta_payload["saved_at"] = datetime.now().isoformat()
    meta_payload["resume_chars"] = len(resume_text)
    meta_payload["jd_chars"] = len(job_description_text)

    meta_file.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")

    return {
        "resume_path": str(resume_file),
        "jd_path": str(jd_file),
        "metadata_path": str(meta_file),
    }


def save_full_packet_artifacts(
    packet_dir: Path,
    resume_text: str,
    jd_text: str,
    pipeline_results: Dict[str, Any],
) -> Dict[str, str]:
    """Save all pipeline outputs into data/packets/<timestamp>/."""
    packet_dir.mkdir(parents=True, exist_ok=True)

    (packet_dir / "resume.txt").write_text(resume_text, encoding="utf-8")
    (packet_dir / "job_description.txt").write_text(jd_text, encoding="utf-8")

    if "resume_json" in pipeline_results:
        (packet_dir / "resume_parsed.json").write_text(
            json.dumps(pipeline_results["resume_json"], indent=2), encoding="utf-8"
        )
    if "jd_json" in pipeline_results:
        (packet_dir / "jd_parsed.json").write_text(
            json.dumps(pipeline_results["jd_json"], indent=2), encoding="utf-8"
        )
    if "match_matrix" in pipeline_results:
        (packet_dir / "match_matrix.json").write_text(
            json.dumps(pipeline_results["match_matrix"], indent=2), encoding="utf-8"
        )
    if "rewritten_bullets" in pipeline_results:
        (packet_dir / "rewritten_bullets.json").write_text(
            json.dumps(pipeline_results["rewritten_bullets"], indent=2), encoding="utf-8"
        )
    if "cover_note" in pipeline_results:
        (packet_dir / "cover_note.txt").write_text(
            pipeline_results["cover_note"], encoding="utf-8"
        )
    if "interview_questions" in pipeline_results:
        (packet_dir / "interview_qa.json").write_text(
            json.dumps(pipeline_results["interview_questions"], indent=2), encoding="utf-8"
        )
    if "one_page_summary" in pipeline_results:
        (packet_dir / "summary.md").write_text(
            pipeline_results["one_page_summary"], encoding="utf-8"
        )
    if "audit_results" in pipeline_results:
        (packet_dir / "audit_results.json").write_text(
            json.dumps(pipeline_results["audit_results"], indent=2), encoding="utf-8"
        )

    manifest = {
        "saved_at": datetime.now().isoformat(),
        "role": pipeline_results.get("jd_json", {}).get("role", ""),
        "company": pipeline_results.get("jd_json", {}).get("company", ""),
        "must_count": len(pipeline_results.get("jd_json", {}).get("must", [])),
        "bullets_count": len(pipeline_results.get("rewritten_bullets", [])),
        "cover_note_words": pipeline_results.get("cover_note_word_count", 0),
        "interview_questions_count": len(pipeline_results.get("interview_questions", [])),
        "audit_passed": pipeline_results.get("audit_results", {}).get("passed", True),
        "flagged_entities_count": len(pipeline_results.get("audit_results", {}).get("flagged_entities", [])),
    }
    (packet_dir / "packet_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write data/cache/last_packet.json
    cache_dir = packet_dir.parent.parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "last_packet.json"
    cache_file.write_text(json.dumps(pipeline_results, indent=2, default=str), encoding="utf-8")

    return {
        "dir": str(packet_dir),
        "manifest": str(packet_dir / "packet_manifest.json"),
        "summary": str(packet_dir / "summary.md"),
        "cache": str(cache_file),
    }


def load_full_packet_artifacts(packet_dir: Path) -> Dict[str, Any]:
    """Load previously saved packet artifacts from disk."""
    if not packet_dir.exists():
        return {}

    loaded: Dict[str, Any] = {}
    if (packet_dir / "resume.txt").exists():
        loaded["resume_text"] = (packet_dir / "resume.txt").read_text(encoding="utf-8")
    if (packet_dir / "job_description.txt").exists():
        loaded["jd_text"] = (packet_dir / "job_description.txt").read_text(encoding="utf-8")
    if (packet_dir / "resume_parsed.json").exists():
        loaded["resume_json"] = json.loads((packet_dir / "resume_parsed.json").read_text(encoding="utf-8"))
    if (packet_dir / "jd_parsed.json").exists():
        loaded["jd_json"] = json.loads((packet_dir / "jd_parsed.json").read_text(encoding="utf-8"))
    if (packet_dir / "match_matrix.json").exists():
        loaded["match_matrix"] = json.loads((packet_dir / "match_matrix.json").read_text(encoding="utf-8"))
    if (packet_dir / "rewritten_bullets.json").exists():
        loaded["rewritten_bullets"] = json.loads((packet_dir / "rewritten_bullets.json").read_text(encoding="utf-8"))
    if (packet_dir / "cover_note.txt").exists():
        loaded["cover_note"] = (packet_dir / "cover_note.txt").read_text(encoding="utf-8")
        loaded["cover_note_word_count"] = len(loaded["cover_note"].split())
    if (packet_dir / "interview_qa.json").exists():
        loaded["interview_questions"] = json.loads((packet_dir / "interview_qa.json").read_text(encoding="utf-8"))
    if (packet_dir / "summary.md").exists():
        loaded["one_page_summary"] = (packet_dir / "summary.md").read_text(encoding="utf-8")
    if (packet_dir / "audit_results.json").exists():
        loaded["audit_results"] = json.loads((packet_dir / "audit_results.json").read_text(encoding="utf-8"))
    if (packet_dir / "packet_manifest.json").exists():
        loaded["manifest"] = json.loads((packet_dir / "packet_manifest.json").read_text(encoding="utf-8"))

    return loaded


def list_saved_packets(base_dir: Optional[Path] = None) -> List[Dict[str, object]]:
    """List all saved packets ordered by newest first."""
    target_dir = base_dir or PACKETS_DIR
    if not target_dir.exists():
        return []

    packets = []
    for entry in sorted(target_dir.iterdir(), reverse=True):
        if entry.is_dir():
            meta_file = entry / "packet_manifest.json"
            if not meta_file.exists():
                meta_file = entry / "metadata.json"
            meta_data = {}
            if meta_file.exists():
                try:
                    meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    meta_data = {}
            packets.append({
                "timestamp": entry.name,
                "path": str(entry),
                "metadata": meta_data,
                "has_resume": (entry / "resume.txt").exists(),
                "has_jd": (entry / "job_description.txt").exists(),
                "has_packet": (entry / "summary.md").exists() or (entry / "packet_manifest.json").exists(),
            })
    return packets
