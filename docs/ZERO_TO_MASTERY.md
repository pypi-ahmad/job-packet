# Zero to mastery tutorial

Start with the synthetic fixtures, then create and review a packet. This keeps
personal data out of the app while you learn the workflow.

## What you will learn

You will launch the app, parse both source documents, read the match matrix,
generate a packet, and review any leakcheck flags before using the result.

## 1. Prepare Windows

Set the Agnes key as a Windows user environment variable. Replace the example
value with your real key and open a new terminal afterward.

```powershell
setx AGNESAI_API_KEY "your-key"
```

In a Command Prompt at the repository root, run:

```bat
run.cmd
```

If this is the first launch, Notepad opens `.env` and the launcher exits. Close
Notepad, run `run.cmd` again, and wait for Streamlit to open in your browser.
The sidebar should show model `agnes-3.0-flash`, temperature `0`, and
`AGNESAI_API_KEY set: yes`.

## 2. Learn with fixtures

Open the **Resume** tab and select **Load resume fixture**. The text describes
Alex Rivera, including Northwind Analytics and River College. It deliberately
does not mention Google, Stanford, or a PhD.

Open **Job description** and select **Load job fixture**. It targets the
Generative AI data scientist role at Harbor Labs.

Select **Parse resume** and **Parse job description**. Each JSON preview is an
intermediate record, not a polished document. Review these items:

- A role employer and title must be copied verbatim from the resume.
- Schools and skills are source spans, not inferred credentials.
- Job requirements are classified as `must` or `nice`.

If an employer or title is not present in the raw text, parsing should fail
rather than repair it into a familiar organization.

## 3. Read the match matrix

Open **Packet**. After both documents parse, the app shows a row for every
must-have and nice-to-have requirement.

| Status | Meaning | How to use it |
|---|---|---|
| `covered` | The requirement is fully supported by a resume span. | Use the linked evidence when reviewing generated emphasis. |
| `partial` | Some meaningful tokens overlap. | Treat it as a limited connection, not full experience. |
| `missing` | No resume evidence overlaps. | Discuss it only as a stated gap. |

For the fixture, healthcare domain experience is a nice-to-have gap. The app
must not turn that gap into Alex Rivera experience.

## 4. Generate and review a packet

Select **Run all**. The app parses both inputs again, builds the local match
matrix, asks Agnes for the packet, performs the local leakcheck, and saves the
result under `data/packets/<timestamp>/`.

Before using the material:

1. In **Packet**, inspect tailored bullets and each displayed evidence span.
2. Read the cover note for unsupported employers, schools, dates, degrees,
   skills, metrics, or achievements.
3. In **Interview**, confirm every answer uses a resume evidence span or names
   a match-matrix gap as a gap.
4. Read any leakcheck flag. A flag requests review; it is not automatically
   proof of invention.

The fixture run can flag `Augmented Generation`. That documented flag is a
technical phrase, not a candidate-history claim. Do not suppress a new flag
without comparing it to the raw resume and job description.

## 5. Download and locate the result

Use **Download packet ZIP** to obtain all seven artifacts:

- `resume.json`, `jd.json`, and `match.json`;
- `bullets.md`, `cover.md`, `interview.md`, and `packet.md`.

The same files remain on disk in the timestamped packet folder. The latest
paths and leakcheck result are stored in `data/cache/last_packet.json`.

## 6. Use your own documents carefully

Paste a plain-text resume and job description into their tabs. You can also
upload a PDF resume; the app processes it locally through `pdf-inspector` and
puts extracted Markdown in the resume box. If extraction is empty, paste text
instead.

Only resume and job-description content sent for parsing or generation leaves
your machine, and it goes to Agnes. Packets, caches, and ZIP creation stay on
the local disk.

Before submitting anything, compare the final text with your source resume.
The app's grounding checks are safeguards, not a replacement for your review.

## 7. Continue learning

- Read [Grounding and leak checks](GROUNDING.md) to understand the safeguards.
- Read the [Developer guide](DEVELOPER_GUIDE.md) to debug and modify the app.
- Read the [Python reference](PYTHON_REFERENCE.md) before calling modules from
  a script or changing schemas.
