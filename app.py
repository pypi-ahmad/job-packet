"""Job Packet Generator Streamlit app."""

import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from document_utils import extract_text_from_upload
from src.config import MODEL, agnes_key_is_set
from src.generate import generate_packet, save_packet
from src.match import build_match_matrix
from src.parse import JDJSON, ResumeJSON, parse_job_description, parse_resume

st.set_page_config(page_title="Job Packet Generator", page_icon=":material/work:", layout="wide")
for key, value in {
    "resume_text": "",
    "jd_text": "",
    "resume_json": None,
    "jd_json": None,
    "packet_result": None,
    "resume_upload_id": None,
}.items():
    st.session_state.setdefault(key, value)


def packet_zip(result: dict[str, object]) -> bytes:
    """Build an in-memory ZIP from active packet artifact paths.

    Args:
        result: Mapping returned by ``src.generate.save_packet`` containing a
            filename-to-path ``paths`` mapping.

    Returns:
        Bytes suitable for Streamlit's ``download_button``.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, path in result["paths"].items():
            archive.write(Path(path), arcname=filename)
    return buffer.getvalue()

with st.sidebar:
    st.header("Configuration")
    st.text_input("Model", value=MODEL, disabled=True)
    st.number_input("Temperature", value=0.0, min_value=0.0, max_value=0.0, disabled=True)
    st.divider()
    st.subheader("Health")
    st.write(f"AGNESAI_API_KEY set: {'yes' if agnes_key_is_set() else 'no'}")

st.title("Job Packet Generator")
resume_page, job_page, packet_page, interview_page = st.tabs(
    ["Resume", "Job description", "Packet", "Interview"]
)

with resume_page:
    st.header("Resume")
    uploaded_resume = st.file_uploader("Upload PDF resume", type=["pdf"], key="resume_pdf")
    if uploaded_resume is not None:
        upload_id = hashlib.sha256(uploaded_resume.getvalue()).hexdigest()
        if upload_id != st.session_state.resume_upload_id:
            try:
                extracted_markdown = extract_text_from_upload(uploaded_resume)
            except Exception as error:
                st.error(f"Could not process PDF: {error}")
            else:
                if extracted_markdown:
                    st.session_state.resume_text = extracted_markdown
                    st.session_state.resume_json = None
                    st.session_state.packet_result = None
                    st.success("PDF Markdown loaded into resume text.")
                else:
                    st.warning("PDF Markdown is empty. Paste text instead.")
            st.session_state.resume_upload_id = upload_id
    if st.button("Load resume fixture", icon=":material/science:"):
        st.session_state.resume_text = Path("data/fixtures/resume.txt").read_text(encoding="utf-8")
        st.session_state.resume_json = None
    st.text_area("Paste resume", height=320, key="resume_text")
    if st.button("Parse resume", type="primary", disabled=not st.session_state.resume_text.strip()):
        try:
            st.session_state.resume_json = parse_resume(st.session_state.resume_text)
        except Exception as error:
            st.error(str(error))
    if isinstance(st.session_state.resume_json, ResumeJSON):
        st.subheader("Parsed resume JSON")
        st.json(st.session_state.resume_json.model_dump())

with job_page:
    st.header("Job description")
    if st.button("Load job fixture", icon=":material/science:"):
        st.session_state.jd_text = Path("data/fixtures/jd.txt").read_text(encoding="utf-8")
        st.session_state.jd_json = None
    st.text_area("Paste job description", height=320, key="jd_text")
    if st.button("Parse job description", type="primary", disabled=not st.session_state.jd_text.strip()):
        try:
            st.session_state.jd_json = parse_job_description(st.session_state.jd_text)
        except Exception as error:
            st.error(str(error))
    if isinstance(st.session_state.jd_json, JDJSON):
        st.subheader("Parsed job JSON")
        st.json(st.session_state.jd_json.model_dump())

with packet_page:
    st.header("Packet")
    parsed = isinstance(st.session_state.resume_json, ResumeJSON) and isinstance(st.session_state.jd_json, JDJSON)
    matrix = build_match_matrix(st.session_state.resume_json, st.session_state.jd_json) if parsed else []
    if parsed:
        st.subheader("Match table")
        st.dataframe(pd.DataFrame(matrix), hide_index=True)
    can_run = bool(
        st.session_state.resume_text.strip()
        and st.session_state.jd_text.strip()
        and agnes_key_is_set()
    )
    if st.button("Run all", type="primary", disabled=not can_run, icon=":material/play_arrow:"):
        with st.status("Running full packet pipeline", expanded=True) as status:
            try:
                st.write("1. Parsing resume and job description")
                resume = parse_resume(st.session_state.resume_text)
                jd = parse_job_description(st.session_state.jd_text)
                st.write("2. Building deterministic match matrix")
                matrix = build_match_matrix(resume, jd)
                st.write("3. Generating grounded packet")
                packet = generate_packet(resume, jd, matrix)
                st.write("4. Running leak check")
                st.write("5. Saving packet files")
                result = save_packet(resume, jd, matrix, packet)
                st.session_state.resume_json = resume
                st.session_state.jd_json = jd
                st.session_state.packet_result = result
                status.update(label="Packet pipeline complete", state="complete", expanded=False)
            except Exception as error:
                status.update(label="Packet pipeline failed", state="error")
                st.error(str(error))
    result = st.session_state.packet_result
    if result:
        leakcheck = result["leakcheck"]
        if leakcheck["ok"]:
            st.success("Leak check passed.")
        else:
            st.error("Leak check flagged generated text.")
            st.json(leakcheck["flags"])
        st.download_button(
            "Download packet ZIP",
            data=packet_zip(result),
            file_name=f"job-packet-{Path(result['packet_dir']).name}.zip",
            mime="application/zip",
            icon=":material/download:",
        )
        for filename in ("bullets.md", "cover.md", "packet.md"):
            with st.expander(filename, expanded=filename == "packet.md"):
                st.markdown(Path(result["paths"][filename]).read_text(encoding="utf-8"))

with interview_page:
    st.header("Interview")
    result = st.session_state.packet_result
    if result:
        if result["leakcheck"]["flags"]:
            st.warning("Leak-check flags apply to this interview file.")
            st.json(result["leakcheck"]["flags"])
        st.markdown(Path(result["paths"]["interview.md"]).read_text(encoding="utf-8"))
    else:
        st.info("Generate a packet to view interview preparation.")
