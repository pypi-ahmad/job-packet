# Job Packet Generator

A Windows-native Streamlit app that turns a resume and job description into a
grounded application packet with Agnes `agnes-3.0-flash`.

## Privacy

Resume and job-description content goes only to:

- Agnes at `https://apihub.agnes-ai.com/v1` for parsing and generation.
- The local Windows disk for fixtures, caches, and generated packets.

The app does not use job-board APIs or other model services. Uploaded PDFs are
processed locally with `pdf-inspector`; OCR is not performed. Generated packets
are saved below `data/packets/`, and `data/` is excluded from Git.

## Configure Agnes

Create the Windows user environment variable without putting the key in a
project file:

```powershell
setx AGNESAI_API_KEY "your-key"
```

Open a new terminal after running `setx`. The app reports only whether the
variable is present and never displays its value.

## Run on Windows 11

Double-click `run.cmd`, or run it from Command Prompt:

```bat
run.cmd
```

On first use, `run.cmd` creates `.env` from `.env.example`, opens it in Notepad,
and exits. Run `run.cmd` again to create `.venv`, install `requirements.txt`, and
start Streamlit at `http://localhost:8595`. Before launch, it stops the process
currently listening on port 8595. The Agnes key is still read from the Windows
user environment.

## Reviewer leak test

The synthetic fixtures are:

- `data/fixtures/resume.txt`
- `data/fixtures/jd.txt`

With `AGNESAI_API_KEY` available, run:

```bat
.venv\Scripts\python scripts\smoke_parse.py
.venv\Scripts\python scripts\smoke_packet.py
```

The packet smoke checks that `Google`, `Stanford`, and `PhD` were not introduced
and that the target company, Harbor Labs, was not claimed as Alex Rivera's past
employer. Results are written below `data/cache/` and `data/packets/`.

## Grounding rule

Invented employers, schools, dates, degrees, skills, metrics, or work history are
bugs. Tailoring may change emphasis, but it must not create candidate facts.
See [Grounding](docs/GROUNDING.md) for the deterministic checks and known limits.

## Documentation

- [Zero to mastery tutorial](docs/ZERO_TO_MASTERY.md): first successful packet.
- [Developer guide](docs/DEVELOPER_GUIDE.md): local setup, debugging, and test tiers.
- [Contributor runbook](CONTRIBUTING.md): safe changes and review checklist.
- [Python reference](docs/PYTHON_REFERENCE.md): models and module APIs.
- [Architecture](docs/ARCHITECTURE.md): runtime boundaries and data flow.
- [Grounding and leak checks](docs/GROUNDING.md): evidence contracts and limits.
- [Current verification status](STATUS.md): latest cache and smoke evidence.
