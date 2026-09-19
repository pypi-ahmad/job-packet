"""Job Packet - Windows-native Streamlit Application.

Structured workflow: Resume | Job description | Packet | Interview
Storage: data/packets/<timestamp>/
Privacy: 100% local, no public sharing, no third-party job boards.
"""

from pathlib import Path
import streamlit as st

from document_utils import (
    create_packet_folder,
    extract_text_from_upload,
    list_saved_packets,
    load_full_packet_artifacts,
    save_full_packet_artifacts,
)
from llm_client import get_available_providers
from pipeline import run_full_pipeline, scan_output_for_unverified_entities

# Page Configuration
st.set_page_config(
    page_title="Job Packet",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""
if "current_packet_dir" not in st.session_state:
    st.session_state.current_packet_dir = None
if "current_packet_ts" not in st.session_state:
    st.session_state.current_packet_ts = None
if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None

# Sidebar Configuration
with st.sidebar:
    st.title("Job Packet")
    st.caption("Local Windows 11 tool")
    st.divider()

    # Provider & Model Selection
    st.subheader("Model Configuration")
    providers = get_available_providers()
    provider_names = list(providers.keys())

    selected_provider = st.selectbox(
        "Provider",
        options=provider_names,
        index=0,
        help="Default: Agnes AI. Extra providers appear only if their environment keys are set.",
    )

    provider_info = providers[selected_provider]
    models = provider_info["models"]
    selected_model = st.selectbox(
        "Model",
        options=models,
        index=0,
    )

    if provider_info["configured"]:
        st.success(f"{selected_provider} ready")
    else:
        st.error(f"{provider_info['env_var']} missing in environment")

    st.divider()

    # Privacy Information
    st.markdown("### Privacy")
    st.info(
        "All processing runs locally:\n\n"
        "- No third-party job board APIs or analytics\n"
        "- Packets are saved to `data/packets/`"
    )

    st.divider()

    # Saved Packets History
    st.subheader("Saved Packets")
    saved_packets = list_saved_packets()
    if saved_packets:
        packet_options = {p["timestamp"]: p for p in saved_packets}
        chosen_ts = st.selectbox(
            "Select previous packet",
            options=list(packet_options.keys()),
            key="saved_packet_selector",
        )
        if st.button("Load Selected Packet", use_container_width=True):
            chosen = packet_options[chosen_ts]
            p_dir = Path(chosen["path"])
            loaded = load_full_packet_artifacts(p_dir)
            if loaded:
                st.session_state.resume_text = loaded.get("resume_text", "")
                st.session_state.jd_text = loaded.get("jd_text", "")
                st.session_state.current_packet_dir = str(p_dir)
                st.session_state.current_packet_ts = chosen_ts

                audit = loaded.get("audit_results")
                if not audit and loaded.get("resume_text"):
                    audit = scan_output_for_unverified_entities(
                        generated_data={
                            "rewritten_bullets": loaded.get("rewritten_bullets", []),
                            "cover_note": loaded.get("cover_note", ""),
                            "interview_questions": loaded.get("interview_questions", []),
                            "one_page_summary": loaded.get("one_page_summary", ""),
                            "allowed_employers": loaded.get("resume_json", {}).get("employers", []),
                        },
                        raw_resume_text=loaded.get("resume_text", ""),
                        target_company=loaded.get("jd_json", {}).get("company", ""),
                    )

                st.session_state.pipeline_results = {
                    "resume_json": loaded.get("resume_json", {}),
                    "jd_json": loaded.get("jd_json", {}),
                    "match_matrix": loaded.get("match_matrix", []),
                    "rewritten_bullets": loaded.get("rewritten_bullets", []),
                    "cover_note": loaded.get("cover_note", ""),
                    "cover_note_word_count": loaded.get("cover_note_word_count", 0),
                    "interview_questions": loaded.get("interview_questions", []),
                    "one_page_summary": loaded.get("one_page_summary", ""),
                    "audit_results": audit,
                }
                st.success(f"Loaded packet: {chosen_ts}")
    else:
        st.caption("No saved packets yet.")

# Main Application Header
st.title("Job Packet")
st.caption("Create tailored application materials and interview practice from a resume and job description.")

# 4 Main Tabs: Resume | Job description | Packet | Interview
tab_resume, tab_jd, tab_packet, tab_interview = st.tabs(
    ["Resume", "Job description", "Packet", "Interview"]
)

# Tab 1: Resume
with tab_resume:
    st.header("Resume")
    st.write("Upload a resume (PDF, TXT, or MD) or paste the text directly.")

    uploaded_resume = st.file_uploader(
        "Upload Resume",
        type=["pdf", "txt", "md"],
        key="resume_uploader",
    )

    if uploaded_resume is not None:
        extracted = extract_text_from_upload(uploaded_resume)
        if extracted and (not st.session_state.resume_text or st.button("Apply Uploaded Resume")):
            st.session_state.resume_text = extracted
            st.success(f"Extracted {len(extracted):,} characters from {uploaded_resume.name}")

    resume_input = st.text_area(
        "Resume Content",
        value=st.session_state.resume_text,
        height=350,
        placeholder="Paste candidate resume text here...",
        key="resume_textarea",
    )
    if resume_input != st.session_state.resume_text:
        st.session_state.resume_text = resume_input

    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        words = len(st.session_state.resume_text.split()) if st.session_state.resume_text else 0
        chars = len(st.session_state.resume_text)
        st.metric("Words", f"{words:,}")
        st.metric("Characters", f"{chars:,}")
    with col_r2:
        if st.session_state.resume_text:
            st.success("Resume text ready for pipeline processing.")
        else:
            st.info("Please provide candidate resume content.")

# Tab 2: Job Description
with tab_jd:
    st.header("Target Job Description")
    st.write("Upload or paste target job description requirements and responsibilities.")

    uploaded_jd = st.file_uploader(
        "Upload Job Description",
        type=["txt", "md"],
        key="jd_uploader",
    )

    if uploaded_jd is not None:
        extracted_jd = extract_text_from_upload(uploaded_jd)
        if extracted_jd and (not st.session_state.jd_text or st.button("Apply Uploaded JD")):
            st.session_state.jd_text = extracted_jd
            st.success(f"Loaded {len(extracted_jd):,} characters from {uploaded_jd.name}")

    jd_input = st.text_area(
        "Job Description Content",
        value=st.session_state.jd_text,
        height=350,
        placeholder="Paste target job description text here...",
        key="jd_textarea",
    )
    if jd_input != st.session_state.jd_text:
        st.session_state.jd_text = jd_input

    col_j1, col_j2 = st.columns([1, 4])
    with col_j1:
        jd_words = len(st.session_state.jd_text.split()) if st.session_state.jd_text else 0
        jd_chars = len(st.session_state.jd_text)
        st.metric("Words", f"{jd_words:,}")
        st.metric("Characters", f"{jd_chars:,}")
    with col_j2:
        if st.session_state.jd_text:
            st.success("Job description ready for packet generation.")
        else:
            st.info("Please provide target job description.")

# Tab 3: Packet
with tab_packet:
    st.header("Application packet")
    st.write("Generate a match table, rewritten bullets, a cover note, and a summary.")

    can_generate = bool(st.session_state.resume_text.strip() and st.session_state.jd_text.strip())

    if not can_generate:
        st.warning("Provide both Resume (Tab 1) and Job Description (Tab 2) to generate packet.")

    if st.button("Generate packet", disabled=not can_generate, type="primary"):
        with st.status("Generating application packet...", expanded=True) as status_box:
            try:
                st.write("1. Parsing resume to JSON {bullets, skills, roles, dates}...")
                st.write("2. Parsing JD to JSON {must, nice, company, role}...")
                st.write("3. Building match matrix against resume evidence...")
                st.write("4. Rewriting 6-10 targeted bullets...")
                st.write("5. Composing 250-400 word cover note...")
                st.write("6. Generating 8 grounded interview questions & answers...")
                st.write("7. Compiling one-page summary markdown...")

                results = run_full_pipeline(
                    resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.jd_text,
                    provider_name=selected_provider,
                    model=selected_model,
                )

                # Save artifacts
                ts, p_dir = create_packet_folder()
                save_full_packet_artifacts(
                    packet_dir=p_dir,
                    resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.jd_text,
                    pipeline_results=results,
                )
                st.session_state.current_packet_dir = str(p_dir)
                st.session_state.current_packet_ts = ts
                st.session_state.pipeline_results = results

                status_box.update(label="Packet generated and saved.", state="complete", expanded=False)
                st.success(f"Saved artifacts under `data/packets/{ts}/`")
            except Exception as e:
                status_box.update(label="Pipeline execution failed", state="error")
                st.error(f"Error during execution: {e}")

    # Render Pipeline Results if available
    res = st.session_state.pipeline_results
    if res:
        st.divider()
        if st.session_state.current_packet_dir:
            st.caption(f"Packet folder: `{st.session_state.current_packet_dir}`")

        # Grounding & Entity Verification Banner
        audit = res.get("audit_results")
        if audit:
            st.subheader("Grounding verification")
            if audit.get("passed", True):
                st.success("Grounding scan passed: No unverified employer or school strings detected.")
                with st.expander("Verified resume entities", expanded=False):
                    emp_list = audit.get("verified_employers", [])
                    sch_list = audit.get("verified_schools", [])
                    st.write(f"- Verified employers: {', '.join(emp_list) if emp_list else 'None detected'}")
                    st.write(f"- Verified schools: {', '.join(sch_list) if sch_list else 'None detected'}")
            else:
                flagged = audit.get("flagged_entities", [])
                st.error(f"Grounding alert: {len(flagged)} unverified employer or school reference(s) detected!")
                for f in flagged:
                    st.warning(f"Unverified {f.get('type', 'entity')}: **{f.get('entity', '')}** in *{f.get('artifact', '')}*")
                    st.caption(f"Context: {f.get('context', '')}")

        # Step 3: Match Matrix Display
        st.subheader("1. Requirements match table")
        matrix = res.get("match_matrix", [])
        if matrix:
            matched_count = sum(1 for m in matrix if m.get("status") == "matched")
            total_count = len(matrix)
            st.progress(
                matched_count / total_count if total_count > 0 else 0,
                text=f"Must-have requirements matched: {matched_count}/{total_count}",
            )

            for item in matrix:
                status = item.get("status", "missing").lower()
                badge = "[MATCHED]" if status == "matched" else ("[PARTIAL]" if status == "partial" else "[MISSING]")
                with st.expander(f"{badge} {item.get('requirement')}", expanded=(status != "matched")):
                    st.markdown(f"Resume evidence:\n\n> {item.get('evidence')}")
        else:
            st.info("No match matrix data available.")

        # Step 4: Rewritten Bullets Display
        st.subheader("2. Rewritten accomplishment bullets (6 to 10)")
        bullets = res.get("rewritten_bullets", [])
        if bullets:
            st.caption("Rewritten using verified details from the resume.")
            for i, bullet in enumerate(bullets, 1):
                st.markdown(f"**{i}.** {bullet}")
        else:
            st.info("No rewritten bullets.")

        # Step 5: Cover Note Display
        st.subheader("3. Cover note")
        cover_note = res.get("cover_note", "")
        word_count = res.get("cover_note_word_count", len(cover_note.split()))
        st.metric("Word count", f"{word_count} words", help="Target: 250 to 400 words")
        st.text_area("Cover Note", value=cover_note, height=280, key="cover_note_view")

        # Step 7: One-Page Summary Display
        st.subheader("4. One-page summary")
        summary_md = res.get("one_page_summary", "")
        st.markdown(summary_md)

        # Download artifact buttons
        st.divider()
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "Download summary (Markdown)",
                data=summary_md,
                file_name="summary.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_d2:
            st.download_button(
                "Download cover note (Text)",
                data=cover_note,
                file_name="cover_note.txt",
                mime="text/plain",
                use_container_width=True,
            )

# Tab 4: Interview
with tab_interview:
    st.header("Interview preparation")
    st.write("Eight interview questions with suggested answers tied to resume facts.")

    res = st.session_state.pipeline_results
    if not res or not res.get("interview_questions"):
        st.info("Generate or load an application packet in the Packet tab to view interview questions.")
    else:
        questions = res.get("interview_questions", [])
        st.caption(f"{len(questions)} questions based on candidate experience.")

        for q in questions:
            qid = q.get("id", "")
            cat = q.get("category", "General")
            question_text = q.get("question", "")
            answer_text = q.get("grounded_answer", "")
            evidence = q.get("resume_evidence", "")

            with st.container(border=True):
                st.markdown(f"#### Question {qid}: `{cat}`")
                st.markdown(f"**{question_text}**")
                with st.expander("Suggested answer and notes", expanded=False):
                    st.markdown(f"**Suggested response:**\n\n{answer_text}")
                    st.markdown(f"Resume evidence:\n\n> *{evidence}*")
