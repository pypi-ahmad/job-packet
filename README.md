# Job Packet

Job Packet is a Windows 11 desktop app that creates tailored job application materials and interview practice from a resume and a job description.

## Privacy and data storage

Job Packet runs entirely on your local machine:

- Everything runs directly on Windows 11. It does not use containers, virtual machines, or remote servers.
- The app does not connect to job boards, tracking scripts, or analytics services.
- Resumes, job descriptions, match tables, cover notes, and interview questions stay in `data/packets/<timestamp>/` on your drive.
- The app reads credentials from Windows user or machine environment variables (`AGNESAI_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`) or a local `.env` file ignored by Git. It never logs keys, saves them to disk, or displays them in the interface.
- Output stays tied to facts in the resume. The generator does not invent past employers or jobs.

## Quick start

### Launch with run.cmd

Double-click `run.cmd` in the repository root. The script will:

1. Check for `.env`. If the file is missing, it copies `.env.example` to `.env` and opens Notepad so you can add your keys.
2. Create a virtual environment (`.venv`) with `py -3` if one does not exist.
3. Install dependencies from `requirements.txt`.
4. Open the Streamlit interface in your browser.

### Launch from the terminal

You can also run the app from PowerShell:

```powershell
.\.venv\Scripts\activate.bat
streamlit run app.py
```

## How it works

The interface has four tabs:

- **Resume:** Upload a PDF, text, or Markdown resume, or paste the text directly.
- **Job description:** Upload or paste the job posting.
- **Packet:** Runs the seven-step pipeline:
  1. Extracts bullets, skills, roles, and dates into JSON.
  2. Extracts must-have and nice-to-have requirements, company name, and job title into JSON.
  3. Builds a match table pairing each must-have requirement with resume evidence or marking it missing.
  4. Rewrites 6 to 10 accomplishment bullets using only verified resume details.
  5. Writes a cover note between 250 and 400 words.
  6. Creates 8 interview questions with model answers tied to resume facts.
  7. Builds a one-page summary in Markdown.
  8. Checks all output for unverified employer and school names, displaying live warnings in the interface.
  All files are saved to `data/packets/<timestamp>/` and mirrored to `data/cache/last_packet.json`.
- **Interview:** Displays the 8 interview questions by category, with answers and resume references you can expand during prep.

## Models and providers

- **Agnes AI (default):** Uses `agnes-3.0-flash` at `https://apihub.agnes-ai.com/v1`. Requires the `AGNESAI_API_KEY` environment variable.
- **OpenAI (optional):** Supports `gpt-5.6-luna` and `gpt-5.6-terra`. Requires `OPENAI_API_KEY` and `OPENAI_BASE_URL`.
- **Google Gemini (optional):** Supports `gemini-3.5-flash-lite` and `gemini-3.7-flash` through its OpenAI-compatible endpoint. Requires `GOOGLE_API_KEY`.

If an environment variable is missing, that provider is omitted from the sidebar.

## Project layout

```
job-packet/
├── app.py                     # Streamlit frontend application
├── document_utils.py          # PDF/text extraction & packet storage
├── llm_client.py              # Multi-provider client abstraction via OpenAI SDK
├── pipeline.py                # Grounding & anti-hallucination pipeline
├── run.cmd                    # Root Windows double-clickable launcher
├── requirements.txt           # Core Python dependencies
├── STATUS.md                  # Test execution and verification audit
├── README.md                  # Privacy, documentation, and user guide
├── LICENSE                    # MIT License
├── docs/
│   └── ARCHITECTURE.md        # Technical architecture and data contracts
├── data/
│   ├── cache/                 # Mirrored last packet
│   ├── fixtures/              # Personas and test datasets
│   └── packets/               # Local timestamped packet storage
└── .env.example               # Environment variable templates
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

