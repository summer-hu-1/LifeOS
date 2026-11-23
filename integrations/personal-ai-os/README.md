# Personal AI OS → LifeOS (private-first integration)

> An optional, human-reviewed bridge for an existing Personal AI OS knowledge base. **This repository is public. Do not commit personal journals, identity details, trading records, tokens, private links or exported user data here.**

## What is connected today?

- The GitHub connector can inspect and propose changes to `summer-hu-1/LifeOS`.
- This fork is the **public LifeOS distribution**, not an installed personal LifeOS instance.
- The eight Personal AI OS files below are a **proposed intake contract**, not a claim that the user's records have already been imported.
- ChatGPT Memory / Projects / Automations, local LifeOS USER files, GitHub Actions and Pulse are **different storage and execution systems**. Connecting GitHub does not synchronize them.

## Architecture and authoritative sources

| Layer | Canonical location | Rule |
|---|---|---|
| Public engine | `summer-hu-1/LifeOS` | Vendor-derived source; review changes by PR |
| Private personal files | Local `~/.config/LIFEOS/USER/` and separately configured **private** backup repository | Primary truth for personal facts after the owner confirms them |
| Personal AI OS source notes | An explicit local export directory | One-way reviewed import; no implicit ChatGPT access |
| LifeOS goals | `USER/TELOS/TELOS.md` | Human-reviewed synthesis, never overwritten by bridge |
| Daily work and follow-ups | Existing personal workflow and task services | Use IDs, provenance and timestamps; don't assume completion |
| Research / code | Their respective GitHub repositories, e.g. `stock_ai` | Reference work rather than copying its private data |
| Runtime and UI | Locally installed LifeOS / Pulse | Verify separately with the official Doctor |

**Intake files (top level of an explicit local export):**

`PROFILE.md`, `GOALS.md`, `PRINCIPLES.md`, `PROJECTS.md`, `KNOWLEDGE.md`, `DECISIONS.md`, `JOURNAL.md`, `SKILLS.md`.

These describe *conceptual* domains; names and contents must be checked against the actual export. If your existing archive uses different filenames, create a local mapping outside this public repository.

## Prerequisites

1. Install LifeOS through its documented consent-based installer **on a machine you control**. Confirm a real `USER` directory exists, and test the install with its official Doctor tool.
2. Keep private notes in a local export folder. Remove API keys, account numbers, credentials and details you do not want copied.
3. Use a private backup repository for personal files only after explicitly verifying its visibility; a public fork is never a destination for private notes.
4. Use Python 3.10+.

## Run — dry-run by default

```bash
python3 integrations/personal-ai-os/bridge.py \
  --from /path/to/private/personal-ai-os-export \
  --user-dir ~/.config/LIFEOS/USER
```

The command returns only filenames, states and aggregate counts. It will **not** write by default. Review statuses and confirm the target is your actual private LifeOS USER tree.

To stage files that do not exist:

```bash
python3 integrations/personal-ai-os/bridge.py \
  --from /path/to/private/personal-ai-os-export \
  --user-dir ~/.config/LIFEOS/USER --apply
```

The target is `USER/IMPORTS/PERSONAL_AI_OS/` — **not** the canonical LifeOS TELOS, memory or config files. Existing files are never replaced. Different existing contents are reported as conflicts; a conflict blocks apply. The bridge creates no remote connection, no Git commit, no agent task, and no background sync.

Run the LifeOS interview with these files as **evidence to review**, then explicitly choose which facts to carry into TELOS / projects / memory. Maintain a source-of-truth ledger: `source → reviewed claim → destination → review date`. Any disagreement stays unresolved until the owner decides.

## Acceptance checks

- [ ] Confirm a private personal-data destination and working backup
- [ ] Dry-run shows expected source files without showing their content
- [ ] Apply stages copies only when requested, without replacing existing files
- [ ] Repeat dry-run reports identical
- [ ] Conflicting content blocks apply, with original data intact
- [ ] LifeOS interview explicitly reviews imported facts and produces user-approved TELOS
- [ ] Official LifeOS Doctor / Pulse checks pass locally (separate from GitHub access)
- [ ] Task loop independently tested: create → schedule → notify → acknowledge → review
- [ ] No personal content or secrets are present in the public GitHub commits or Actions logs

## Boundaries and limitations

This integration is an *offline import aid*, not a ChatGPT connector, not a data sync daemon, not an installer, and not a guarantee that any local device was configured. The public fork tracks an upstream project with its own security policies and moving architecture: audit version changes before upgrading. Do not execute a downloaded install script without reviewing its provenance and consent prompts.

For the official installation and diagnostics, see `LifeOS/SKILL.md`, `LifeOS/INSTALL.md`, and `LifeOS/GETTING-STARTED.md` in this repository.
