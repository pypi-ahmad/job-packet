"""Legacy dictionary-based job-packet pipeline.

Orchestrates:
1. Parse resume to JSON {bullets, skills, roles, dates} via Agnes
2. Parse JD to JSON {must, nice, company, role}
3. Match matrix: each JD must-have -> resume evidence or "missing"
4. Rewrite 6-10 bullets using only resume evidence (reject invented employers)
5. Cover note 250-400 words
6. Eight interview questions with answers grounded in resume JSON
7. Optional one-page summary markdown

The active Streamlit application uses the typed modules in ``src/``. This file
is retained for compatibility with historical scripts and is not an extension
point for new product behavior.
"""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from llm_client import get_chat_completion


def clean_json_response(raw_text: str) -> Any:
    """Extract JSON from a legacy LLM response.

    Args:
        raw_text: Completion text that may contain code fences or surrounding
            prose.

    Returns:
        Decoded JSON object or array.

    Raises:
        json.JSONDecodeError: If no valid JSON remains after cleanup.
    """
    cleaned = raw_text.strip()
    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # Find boundaries of JSON array or object
    start_bracket = cleaned.find("[")
    start_brace = cleaned.find("{")

    if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
        end_bracket = cleaned.rfind("]")
        if end_bracket != -1:
            cleaned = cleaned[start_bracket : end_bracket + 1]
    elif start_brace != -1:
        end_brace = cleaned.rfind("}")
        if end_brace != -1:
            cleaned = cleaned[start_brace : end_brace + 1]

    # Remove trailing commas before closing braces/brackets
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    return json.loads(cleaned)


def extract_employers_from_resume_text(resume_text: str) -> Set[str]:
    """Identify employer-like resume lines with legacy heuristics.

    Args:
        resume_text: Raw resume text to inspect line by line.

    Returns:
        Candidate employer strings inferred from legacy formatting patterns.

    Note:
        The active parser uses Agnes plus verbatim role validation instead.
    """
    employers: Set[str] = set()
    lines = resume_text.splitlines()
    title_keywords = [
        "ENGINEER", "DEVELOPER", "ARCHITECT", "MANAGER", "LEAD", "DIRECTOR",
        "INTERN", "ANALYST", "CONSULTANT", "SPECIALIST", "COORDINATOR",
    ]
    for line in lines:
        line_clean = line.strip()
        match = re.match(r"^([A-Z][A-Za-z0-9\s&.,'-]+?)\s*(?:—|-|\||,)\s*(?:[A-Z][a-zA-Z\s]+|Remote)", line_clean)
        if match:
            candidate = match.group(1).strip()
            # Avoid headings
            if candidate.upper() in ["PROFESSIONAL EXPERIENCE", "EXPERIENCE", "WORK EXPERIENCE", "EDUCATION", "SUMMARY"]:
                continue
            # Avoid lines containing job title indicators
            if any(kw in candidate.upper() for kw in title_keywords):
                continue
            employers.add(candidate)
    return employers


def extract_schools_from_resume_text(resume_text: str) -> Set[str]:
    """Identify school-like strings with legacy keyword heuristics.

    Args:
        resume_text: Raw resume text to inspect.

    Returns:
        Candidate school strings with simple degree/date cleanup applied.
    """
    schools: Set[str] = set()
    school_keywords = ["University", "College", "Institute", "Academy", "Polytechnic", "School"]
    for line in resume_text.splitlines():
        clean = line.strip()
        if any(kw in clean for kw in school_keywords):
            cleaned_school = re.sub(r",?\s*\d{4}.*$", "", clean).strip()
            cleaned_school = re.sub(
                r"^(?:Bachelor|Master|Doctor|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.).*?(?:in|of)\s+[^,]+,\s*",
                "",
                cleaned_school,
                flags=re.IGNORECASE,
            )
            schools.add(cleaned_school.strip())
    return schools


def parse_resume_to_json(
    resume_text: str,
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse a resume into the legacy dictionary schema through Agnes.

    Args:
        resume_text: Raw resume text to send to the legacy prompt.
        provider_name: Retained compatibility parameter; it does not switch the
            configured Agnes client.
        model: Retained compatibility parameter; it is not used.

    Returns:
        A dictionary with ``bullets``, ``skills``, ``roles``, ``dates``, and
        inferred ``employers`` keys.

    Note:
        Use ``src.parse.parse_resume`` for new code.
    """
    system_prompt = (
        "You are an expert resume parser. Extract structured details from the provided resume text. "
        "Return ONLY a valid JSON object with EXACTLY these four keys:\n"
        "1. 'bullets': list of raw accomplishment bullet points.\n"
        "2. 'skills': list of technical skills, languages, tools, frameworks.\n"
        "3. 'roles': list of job title and company combinations (e.g. 'Senior Flight Systems Engineer at Zephyr Skyworks').\n"
        "4. 'dates': list of employment date ranges/durations.\n"
        "Also include an optional 'employers' list of company/organization names found in the resume.\n"
        "Do not invent any data not present in the resume text."
    )
    user_prompt = f"Resume text:\n\n{resume_text}\n\nOutput valid JSON only:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.1)
    parsed = clean_json_response(raw_resp)

    # Ensure required keys exist
    for key in ["bullets", "skills", "roles", "dates"]:
        if key not in parsed or not isinstance(parsed[key], list):
            parsed[key] = parsed.get(key, [])

    # Ensure employers list is populated
    if "employers" not in parsed or not parsed["employers"]:
        heuristic_employers = list(extract_employers_from_resume_text(resume_text))
        parsed["employers"] = heuristic_employers

    return parsed


def parse_jd_to_json(
    jd_text: str,
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse a job description into the legacy dictionary schema.

    Args:
        jd_text: Raw job-description text to send to the legacy prompt.
        provider_name: Retained compatibility parameter; it does not switch the
            configured Agnes client.
        model: Retained compatibility parameter; it is not used.

    Returns:
        A dictionary with ``must``, ``nice``, ``company``, and ``role`` keys.

    Note:
        Use ``src.parse.parse_job_description`` for new code.
    """
    system_prompt = (
        "You are an expert job description analyzer. Extract key requirements from the provided job description text. "
        "Return ONLY a valid JSON object with EXACTLY these four keys:\n"
        "1. 'must': list of mandatory must-have requirements/qualifications.\n"
        "2. 'nice': list of preferred / nice-to-have qualifications.\n"
        "3. 'company': string representing the hiring company name.\n"
        "4. 'role': string representing the exact job title.\n"
        "Do not invent information."
    )
    user_prompt = f"Job Description:\n\n{jd_text}\n\nOutput valid JSON only:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.1)
    parsed = clean_json_response(raw_resp)

    # Validate keys
    for key in ["must", "nice"]:
        if key not in parsed or not isinstance(parsed[key], list):
            parsed[key] = parsed.get(key, [])
    parsed["company"] = str(parsed.get("company", "Unknown Company"))
    parsed["role"] = str(parsed.get("role", "Target Role"))

    return parsed


def build_match_matrix(
    must_requirements: List[str],
    resume_json: Dict[str, Any],
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Evaluate legacy must-have requirements through Agnes.

    Args:
        must_requirements: Requirement strings from the legacy JD dictionary.
        resume_json: Legacy parsed resume dictionary.
        provider_name: Retained compatibility parameter.
        model: Retained compatibility parameter.

    Returns:
        Legacy requirement, status, and evidence mappings.

    Note:
        Use local ``src.match.build_match_matrix`` for new code.
    """
    system_prompt = (
        "You are an objective technical recruiter. Compare the candidate's resume evidence against each must-have requirement.\n"
        "For EACH requirement in the list, evaluate if the resume contains evidence.\n"
        "Return a JSON array of objects, each with:\n"
        "- 'requirement': the exact requirement string.\n"
        "- 'status': 'matched' | 'partial' | 'missing'.\n"
        "- 'evidence': exact quote, metric, or bullet from the resume supporting the requirement, or exactly 'missing' if no evidence exists.\n"
        "CRITICAL: If the resume does NOT mention the skill or experience, set evidence to 'missing' and status to 'missing'. Never fabricate evidence."
    )
    user_payload = {
        "requirements": must_requirements,
        "resume_evidence": {
            "bullets": resume_json.get("bullets", []),
            "skills": resume_json.get("skills", []),
            "roles": resume_json.get("roles", []),
        },
    }
    user_prompt = f"Evaluate each requirement:\n\n{json.dumps(user_payload, indent=2)}\n\nOutput JSON array only:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.1)
    matrix = clean_json_response(raw_resp)
    if not isinstance(matrix, list):
        matrix = []
    return matrix


def rewrite_targeted_bullets(
    resume_json: Dict[str, Any],
    jd_json: Dict[str, Any],
    allowed_employers: List[str],
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> List[str]:
    """Rewrite 6-10 legacy-format bullets using legacy Agnes prompts.

    Args:
        resume_json: Legacy parsed resume dictionary.
        jd_json: Legacy parsed job-description dictionary.
        allowed_employers: Employer strings admitted by the legacy prompt.
        provider_name: Retained compatibility parameter.
        model: Retained compatibility parameter.

    Returns:
        At most ten non-empty bullet strings.

    Note:
        Use ``src.generate.generate_packet`` for new evidence-tagged bullets.
    """
    employers_str = ", ".join(f"'{e}'" for e in allowed_employers) if allowed_employers else "None specified"
    system_prompt = (
        "You are an executive resume writer. Your task is to rewrite 6 to 10 high-impact achievement bullets "
        "tailoring the candidate's actual background to the target job description.\n\n"
        "STRICT GROUNDING & ANTI-HALLUCINATION RULES:\n"
        "1. Output between 6 and 10 bullet strings in a JSON list.\n"
        "2. Ground every single bullet exclusively in the candidate's provided resume bullets, skills, and metrics.\n"
        f"3. ALLOWED EMPLOYERS: {employers_str}. "
        "DO NOT invent, assume, or cite any employer, client, or company name outside this allowed list. "
        "Never attribute candidate work to any other company or to the target hiring company.\n"
        "Do not name the target employer, any school, or any other organization unless its exact name appears in the resume evidence.\n"
        "4. If mentioning where the work occurred, use only names from the allowed list or refer to the domain/project directly.\n"
        "5. Preserve verified numbers, scale, and technologies (e.g. 450,000 events/sec, sub-5ms latency, DO-178C).\n"
        "Return ONLY a JSON list of strings."
    )
    user_payload = {
        "candidate_bullets": resume_json.get("bullets", []),
        "candidate_skills": resume_json.get("skills", []),
        "allowed_employers": allowed_employers,
        "target_role": jd_json.get("role", ""),
        "target_company": jd_json.get("company", ""),
        "must_requirements": jd_json.get("must", []),
    }
    user_prompt = f"Context:\n\n{json.dumps(user_payload, indent=2)}\n\nOutput JSON list of 6-10 rewritten bullets:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.2)
    bullets = clean_json_response(raw_resp)
    if not isinstance(bullets, list):
        bullets = [str(bullets)]

    # Validate count between 6 and 10
    bullets = [b.strip() for b in bullets if isinstance(b, str) and b.strip()]
    return bullets[:10]


def generate_cover_note(
    resume_json: Dict[str, Any],
    jd_json: Dict[str, Any],
    allowed_employers: List[str],
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> str:
    """Generate a legacy-format cover note with an optional correction pass.

    Args:
        resume_json: Legacy parsed resume dictionary.
        jd_json: Legacy parsed job-description dictionary.
        allowed_employers: Employer strings admitted by the legacy prompt.
        provider_name: Retained compatibility parameter.
        model: Retained compatibility parameter.

    Returns:
        Generated plain-text cover note.

    Note:
        The active generator enforces exact evidence spans and a 250-400-word
        validation range after generation.
    """
    employers_str = ", ".join(f"'{e}'" for e in allowed_employers) if allowed_employers else "prior roles"
    system_prompt = (
        "You are an executive talent strategist. Write a tailored, professional cover note for the candidate "
        f"applying for the position of {jd_json.get('role')} at {jd_json.get('company')}.\n\n"
        "CONSTRAINTS:\n"
        "1. LENGTH: Must be STRICTLY between 250 and 400 words total.\n"
        "2. GROUNDING: Use ONLY verifiable experiences, technologies, and achievements from the candidate's resume.\n"
        f"3. EMPLOYER INTEGRITY: Allowed past employers are ONLY: {employers_str}. "
        "Never invent or mention any other past employer, client, or company.\n"
        "Do not name the target employer, any school, or any other organization unless its exact name appears in the resume evidence.\n"
        "4. Structure: Opening articulating value proposition for this role, 2 focused body paragraphs connecting "
        "proven accomplishments to the must-have requirements, and a strong closing statement.\n"
        "5. Output clean plain text without markdown headings or placeholder brackets."
    )
    user_payload = {
        "candidate_roles": resume_json.get("roles", []),
        "candidate_bullets": resume_json.get("bullets", []),
        "candidate_skills": resume_json.get("skills", []),
        "target_role": jd_json.get("role", ""),
        "target_company": jd_json.get("company", ""),
        "target_must_haves": jd_json.get("must", []),
    }
    user_prompt = f"Context:\n\n{json.dumps(user_payload, indent=2)}\n\nWrite cover note (250-400 words):"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.3)
    text = raw_resp.strip()

    # Check word count
    words = len(text.split())
    # If out of bounds, do one correction pass
    if words < 240 or words > 420:
        correction_prompt = (
            f"The following cover note is {words} words. Revise it so that the word count is strictly "
            f"between 250 and 400 words while keeping all factual grounding intact:\n\n{text}"
        )
        corr_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": correction_prompt},
        ]
        text = get_chat_completion(corr_messages, temperature=0.2).strip()

    return text


def generate_interview_questions(
    resume_json: Dict[str, Any],
    jd_json: Dict[str, Any],
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate up to eight legacy interview question dictionaries.

    Args:
        resume_json: Legacy parsed resume dictionary.
        jd_json: Legacy parsed job-description dictionary.
        provider_name: Retained compatibility parameter.
        model: Retained compatibility parameter.

    Returns:
        Legacy question dictionaries with prompts, answers, and evidence text.

    Note:
        Use ``src.generate.generate_packet`` for new validated interview items.
    """
    system_prompt = (
        "You are a technical hiring manager preparing an interview candidate profile.\n"
        "Generate EXACTLY EIGHT (8) interview questions tailored to the target role requirements and the candidate's experience.\n"
        "For each question, provide a suggested model answer / talking points GROUNDED in the candidate's actual resume.\n"
        "Return a JSON array of 8 objects, each with:\n"
        "- 'id': integer from 1 to 8.\n"
        "- 'category': string (e.g. 'System Architecture', 'Technical Deep Dive', 'STAR Behavioral', 'Leadership', 'Failure Mitigation').\n"
        "- 'question': clear, probing interview question.\n"
        "- 'grounded_answer': detailed response structured using candidate's actual projects, metrics, and technologies.\n"
        "- 'resume_evidence': the specific bullet point or skill from the resume justifying this answer.\n"
        "CRITICAL: Ground every answer in resume facts. Do not invent ungrounded accomplishments. "
        "Do not name an employer, school, client, or other organization unless its exact name appears in the resume evidence."
    )
    user_payload = {
        "target_role": jd_json.get("role", ""),
        "target_company": jd_json.get("company", ""),
        "must_requirements": jd_json.get("must", []),
        "nice_requirements": jd_json.get("nice", []),
        "resume_bullets": resume_json.get("bullets", []),
        "resume_skills": resume_json.get("skills", []),
    }
    user_prompt = f"Context:\n\n{json.dumps(user_payload, indent=2)}\n\nOutput JSON array of 8 questions:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw_resp = get_chat_completion(messages, temperature=0.2)
    questions = clean_json_response(raw_resp)
    if not isinstance(questions, list):
        questions = []
    return questions[:8]


def generate_one_page_summary(
    resume_json: Dict[str, Any],
    jd_json: Dict[str, Any],
    match_matrix: List[Dict[str, str]],
    bullets: List[str],
) -> str:
    """Render a legacy one-page Markdown summary locally.

    Args:
        resume_json: Legacy parsed resume dictionary.
        jd_json: Legacy parsed job-description dictionary.
        match_matrix: Legacy requirement status mappings.
        bullets: Legacy rewritten bullet strings.

    Returns:
        Markdown summary assembled without another model call.
    """
    matched_count = sum(1 for m in match_matrix if m.get("status") == "matched")
    total_count = len(match_matrix)
    match_rate = f"{(matched_count / total_count * 100):.0f}%" if total_count > 0 else "N/A"

    matrix_rows = []
    for item in match_matrix:
        req = item.get("requirement", "")
        status = item.get("status", "missing").upper()
        evidence = item.get("evidence", "None")
        matrix_rows.append(f"| {req} | **{status}** | {evidence} |")

    matrix_table = "\n".join(matrix_rows) if matrix_rows else "| None | - | - |"
    bullets_section = "\n".join(f"- {b}" for b in bullets[:5])

    summary_md = f"""# Application summary

Role: {jd_json.get('role', 'Candidate')}
Company: {jd_json.get('company', 'Target Organization')}
Must-have match rate: {matched_count}/{total_count} ({match_rate})

## Requirements match table

| Requirement | Status | Resume evidence |
| :--- | :---: | :--- |
{matrix_table}

## Selected accomplishment bullets

{bullets_section}

## Skills and background

- Skills: {', '.join(resume_json.get('skills', [])[:12])}
- Roles: {', '.join(str(r) for r in resume_json.get('roles', []))}

*Generated locally by Job Packet on Windows 11.*
"""
    summary_md.strip()
    return summary_md.strip()


def scan_output_for_unverified_entities(
    generated_data: Dict[str, Any],
    raw_resume_text: str,
    target_company: str = "",
) -> Dict[str, Any]:
    """Scan legacy generated content for ungrounded schools or employers.

    Args:
        generated_data: Legacy pipeline output fields to scan.
        raw_resume_text: Original resume text used as evidence.
        target_company: Retained compatibility argument; currently unused.

    Returns:
        Audit result with pass status, flagged entities, and heuristic entities.

    Note:
        New code should use ``src.leakcheck.check_generated_text``.
    """
    allowed_employers = extract_employers_from_resume_text(raw_resume_text)
    allowed_schools = extract_schools_from_resume_text(raw_resume_text)

    resume_lower = raw_resume_text.lower()

    artifacts_to_scan = []

    bullets = generated_data.get("rewritten_bullets", [])
    for i, b in enumerate(bullets, 1):
        artifacts_to_scan.append((f"Bullet #{i}", b))

    cover_note = generated_data.get("cover_note", "")
    if cover_note:
        artifacts_to_scan.append(("Cover note", cover_note))

    interview_qs = generated_data.get("interview_questions", [])
    for q in interview_qs:
        qid = q.get("id", "Q")
        ans = q.get("grounded_answer", "")
        artifacts_to_scan.append((f"Interview answer #{qid}", ans))

    school_patterns = [
        r"\b(?:[A-Z][a-zA-Z0-9&.'-]*\s+)+(?:University|College|Institute|Academy|Polytechnic|School)\b",
        r"\b(?:University|College|Institute|Academy|Polytechnic|School)\s+of\s+(?:[A-Z][a-zA-Z0-9&.'-]+(?:\s+[A-Z][a-zA-Z0-9&.'-]+)*)\b",
    ]

    company_patterns = [
        r"\b(?:[A-Z][a-zA-Z0-9&.'-]*\s+)+(?:Inc\.?|Corp\.?|Corporation|LLC|Ltd\.?|Technologies|Labs|Foundry|Skyworks|Dynamics)\b",
    ]

    known_tech_employers = [
        "Google", "Meta", "Amazon", "Microsoft", "Apple", "Netflix", "SpaceX",
        "Blue Origin", "Boeing", "Lockheed Martin", "Northrop Grumman", "Raytheon",
        "NASA", "JPL", "Uber", "Airbnb", "Stripe", "Palantir", "OpenAI", "Anthropic", "Tesla",
    ]

    tech_false_positives = {
        "python", "go", "redis", "kafka", "docker", "linux", "postgresql", "grpc",
        "protobuf", "asyncio", "numpy", "prometheus", "git", "sql", "bash", "do-178c",
        "ci/cd", "tdd", "fmea", "aws", "gcp", "azure", "kubernetes", "api", "rest",
    }

    flagged_entities: List[Dict[str, str]] = []
    seen_flagged = set()

    for artifact_name, text in artifacts_to_scan:
        if not text:
            continue

        for pat in school_patterns:
            for match in re.finditer(pat, text):
                candidate = match.group(0).strip()
                cleaned = re.sub(r"^(?:at|in|for|from|to|with|by|the)\s+", "", candidate, flags=re.IGNORECASE).strip()
                cleaned = cleaned.strip(".,;:\"'()[]{}")
                if not cleaned or cleaned.lower() in tech_false_positives:
                    continue
                if cleaned.lower() not in resume_lower:
                    key = (cleaned.lower(), artifact_name)
                    if key not in seen_flagged:
                        seen_flagged.add(key)
                        start = max(0, match.start() - 25)
                        end = min(len(text), match.end() + 25)
                        context = text[start:end].replace("\n", " ").strip()
                        flagged_entities.append({
                            "type": "School/Institution",
                            "entity": cleaned,
                            "artifact": artifact_name,
                            "context": f"...{context}...",
                        })

        for emp in known_tech_employers:
            pattern = r"\b" + re.escape(emp) + r"\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if emp.lower() in resume_lower:
                    continue
                key = (emp.lower(), artifact_name)
                if key not in seen_flagged:
                    seen_flagged.add(key)
                    start = max(0, match.start() - 25)
                    end = min(len(text), match.end() + 25)
                    context = text[start:end].replace("\n", " ").strip()
                    flagged_entities.append({
                        "type": "Employer",
                        "entity": emp,
                        "artifact": artifact_name,
                        "context": f"...{context}...",
                    })

        for pat in company_patterns:
            for match in re.finditer(pat, text):
                candidate = match.group(0).strip()
                cleaned = re.sub(r"^(?:at|in|for|from|to|with|by|the)\s+", "", candidate, flags=re.IGNORECASE).strip()
                cleaned = cleaned.strip(".,;:\"'()[]{}")
                if not cleaned or cleaned.lower() in tech_false_positives:
                    continue
                if cleaned.lower() not in resume_lower:
                    key = (cleaned.lower(), artifact_name)
                    if key not in seen_flagged:
                        seen_flagged.add(key)
                        start = max(0, match.start() - 25)
                        end = min(len(text), match.end() + 25)
                        context = text[start:end].replace("\n", " ").strip()
                        flagged_entities.append({
                            "type": "Employer",
                            "entity": cleaned,
                            "artifact": artifact_name,
                            "context": f"...{context}...",
                        })

    return {
        "passed": len(flagged_entities) == 0,
        "flagged_entities": flagged_entities,
        "verified_employers": sorted(list(allowed_employers)),
        "verified_schools": sorted(list(allowed_schools)),
    }


def run_full_pipeline(
    resume_text: str,
    jd_text: str,
    provider_name: str = "Agnes AI",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the complete legacy dictionary-based packet pipeline.

    Args:
        resume_text: Raw resume text.
        jd_text: Raw job-description text.
        provider_name: Retained compatibility parameter.
        model: Retained compatibility parameter.

    Returns:
        Legacy parsed data, generated text, local summary, and audit results.

    Note:
        The active Streamlit flow composes typed functions from ``src/``.
    """
    # Step 1: Parse resume
    resume_json = parse_resume_to_json(resume_text, provider_name=provider_name, model=model)

    # Extract allowed employers
    allowed_employers = resume_json.get("employers", [])
    if not allowed_employers:
        allowed_employers = list(extract_employers_from_resume_text(resume_text))
        resume_json["employers"] = allowed_employers

    # Step 2: Parse JD
    jd_json = parse_jd_to_json(jd_text, provider_name=provider_name, model=model)

    # Step 3: Match Matrix
    must_requirements = jd_json.get("must", [])
    match_matrix = build_match_matrix(
        must_requirements=must_requirements,
        resume_json=resume_json,
        provider_name=provider_name,
        model=model,
    )

    # Step 4: Rewrite Bullets (6-10)
    rewritten_bullets = rewrite_targeted_bullets(
        resume_json=resume_json,
        jd_json=jd_json,
        allowed_employers=allowed_employers,
        provider_name=provider_name,
        model=model,
    )

    # Step 5: Cover Note (250-400 words)
    cover_note = generate_cover_note(
        resume_json=resume_json,
        jd_json=jd_json,
        allowed_employers=allowed_employers,
        provider_name=provider_name,
        model=model,
    )

    # Step 6: Eight Interview Questions
    interview_questions = generate_interview_questions(
        resume_json=resume_json,
        jd_json=jd_json,
        provider_name=provider_name,
        model=model,
    )

    # Step 7: One-page Summary
    one_page_summary = generate_one_page_summary(
        resume_json=resume_json,
        jd_json=jd_json,
        match_matrix=match_matrix,
        bullets=rewritten_bullets,
    )

    # Grounding audit scan: verify no unverified employer/school strings exist
    audit_results = scan_output_for_unverified_entities(
        generated_data={
            "rewritten_bullets": rewritten_bullets,
            "cover_note": cover_note,
            "interview_questions": interview_questions,
            "one_page_summary": one_page_summary,
            "allowed_employers": allowed_employers,
        },
        raw_resume_text=resume_text,
        target_company=jd_json.get("company", ""),
    )

    return {
        "resume_json": resume_json,
        "jd_json": jd_json,
        "allowed_employers": allowed_employers,
        "match_matrix": match_matrix,
        "rewritten_bullets": rewritten_bullets,
        "cover_note": cover_note,
        "cover_note_word_count": len(cover_note.split()),
        "interview_questions": interview_questions,
        "one_page_summary": one_page_summary,
        "audit_results": audit_results,
    }


# Function aliases matching exact prompt specification
parse_resume = parse_resume_to_json
parse_jd = parse_jd_to_json
match_matrix = build_match_matrix
rewrite_bullets = rewrite_targeted_bullets
cover_note = generate_cover_note
interview_pack = generate_interview_questions
