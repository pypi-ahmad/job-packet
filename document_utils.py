"""Local document parsing and packet persistence."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pdf_inspector import process_pdf

BASE_DATA_DIR = Path("data")
PACKETS_DIR = BASE_DATA_DIR / "packets"


def extract_text_from_upload(uploaded_file: Any) -> str:
    """Extract an uploaded resume locally without OCR.

    Args:
        uploaded_file: A Streamlit-like upload exposing ``name`` and
            ``getvalue()``.

    Returns:
        PDF Markdown from local ``pdf_inspector.process_pdf``, decoded text for
        non-PDF uploads, or an empty string for no upload or empty Markdown.

    Raises:
        OSError: If the temporary PDF cannot be created or removed.
        Exception: Any parsing error raised by ``pdf-inspector``.
    """
    if uploaded_file is None:
        return ""
    content = uploaded_file.getvalue()
    if uploaded_file.name.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
            file.write(content)
            pdf_path = Path(file.name)
        try:
            return (process_pdf(str(pdf_path)).markdown or "").strip()
        finally:
            pdf_path.unlink(missing_ok=True)
    return content.decode("utf-8", errors="replace")


def create_packet_folder(base_dir: Optional[Path] = None) -> tuple[str, Path]:
    """Create a legacy-format timestamped packet directory.

    Args:
        base_dir: Optional parent directory; defaults to ``data/packets``.

    Returns:
        The timestamp string and created directory path.

    Note:
        This compatibility helper is not used by the active Streamlit pipeline.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    packet_dir = (base_dir or PACKETS_DIR) / timestamp
    packet_dir.mkdir(parents=True, exist_ok=True)
    return timestamp, packet_dir


def save_full_packet_artifacts(
    packet_dir: Path, resume_text: str, jd_text: str, pipeline_results: dict[str, Any]
) -> dict[str, str]:
    """Persist a legacy dictionary-based packet and update its cache.

    Args:
        packet_dir: Existing or creatable destination directory.
        resume_text: Raw resume text for the legacy artifact format.
        jd_text: Raw job-description text for the legacy artifact format.
        pipeline_results: Dictionary returned by the legacy ``pipeline`` module.

    Returns:
        Paths for the directory, manifest, and cache file.

    Note:
        The active app uses ``src.generate.save_packet`` instead.
    """
    packet_dir.mkdir(parents=True, exist_ok=True)
    text_files = {"resume.txt": resume_text, "job_description.txt": jd_text,
                  "cover_note.txt": pipeline_results.get("cover_note", ""),
                  "summary.md": pipeline_results.get("one_page_summary", "")}
    json_files = {"resume_parsed.json": pipeline_results.get("resume_json", {}),
                  "jd_parsed.json": pipeline_results.get("jd_json", {}),
                  "match_matrix.json": pipeline_results.get("match_matrix", []),
                  "rewritten_bullets.json": pipeline_results.get("rewritten_bullets", []),
                  "interview_qa.json": pipeline_results.get("interview_questions", []),
                  "audit_results.json": pipeline_results.get("audit_results", {})}
    for name, value in text_files.items():
        (packet_dir / name).write_text(value, encoding="utf-8")
    for name, value in json_files.items():
        (packet_dir / name).write_text(json.dumps(value, indent=2), encoding="utf-8")
    manifest = {"saved_at": datetime.now().isoformat(),
                "role": pipeline_results.get("jd_json", {}).get("role", ""),
                "company": pipeline_results.get("jd_json", {}).get("company", ""),
                "audit_passed": pipeline_results.get("audit_results", {}).get("passed", False)}
    (packet_dir / "packet_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cache_dir = BASE_DATA_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / "last_packet.json"
    cache.write_text(json.dumps(pipeline_results, indent=2), encoding="utf-8")
    return {"dir": str(packet_dir), "manifest": str(packet_dir / "packet_manifest.json"), "cache": str(cache)}


def load_full_packet_artifacts(packet_dir: Path) -> dict[str, Any]:
    """Load legacy-format artifacts from a packet directory.

    Args:
        packet_dir: Directory created by ``save_full_packet_artifacts``.

    Returns:
        Available legacy fields, or an empty mapping when the directory is
        absent.

    Note:
        The active UI does not load this legacy artifact format.
    """
    if not packet_dir.exists():
        return {}
    text = {"resume_text": "resume.txt", "jd_text": "job_description.txt", "cover_note": "cover_note.txt",
            "one_page_summary": "summary.md"}
    data = {key: (packet_dir / filename).read_text(encoding="utf-8") for key, filename in text.items()
            if (packet_dir / filename).exists()}
    json_map = {"resume_json": "resume_parsed.json", "jd_json": "jd_parsed.json", "match_matrix": "match_matrix.json",
                "rewritten_bullets": "rewritten_bullets.json", "interview_questions": "interview_qa.json",
                "audit_results": "audit_results.json"}
    for key, filename in json_map.items():
        if (packet_dir / filename).exists():
            data[key] = json.loads((packet_dir / filename).read_text(encoding="utf-8"))
    data["cover_note_word_count"] = len(data.get("cover_note", "").split())
    return data


def list_saved_packets(base_dir: Optional[Path] = None) -> list[dict[str, str]]:
    """List legacy packet directories newest first.

    Args:
        base_dir: Optional parent directory; defaults to ``data/packets``.

    Returns:
        Timestamp and path mappings for each child directory.

    Note:
        The active UI does not expose packet-history loading.
    """
    packet_root = base_dir or PACKETS_DIR
    return [{"timestamp": item.name, "path": str(item)} for item in sorted(packet_root.glob("*"), reverse=True) if item.is_dir()]
