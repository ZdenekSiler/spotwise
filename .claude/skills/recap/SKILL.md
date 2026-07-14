---
name: recap
description: Print a structured summary of what happened during a deploy or debug session — commands run, outcomes, and what to watch. No files written.
---

# /recap

Print a concise, structured summary of the current session. Write no files.

## Format

- **Goal** — what we set out to do.
- **Changes** — files touched, grouped by area (backend / frontend / docs / deploy).
- **Commands run** — key commands and their outcomes (tests, migrations, deploy, health checks).
- **Result** — what works now, verified how.
- **Watch** — follow-ups, known gaps, sample-data flags, or anything to monitor (e.g. ENTSO-E
  token still needed, supplier price lists still sample data).

Keep it scannable. State failures plainly with the relevant output.
