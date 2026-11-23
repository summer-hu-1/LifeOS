# Personal AI OS — Six-layer architecture contract

Status: proposed integration architecture, not a claim that each service is running.

| Layer | Owner / component | Input → output | Acceptance evidence |
|---|---|---|---|
| Decision center | ChatGPT conversation, user approvals | intent → task/plan/research request | request and review reference |
| Knowledge and memory | Private LifeOS USER + reviewed Markdown archive | confirmed records → contextual facts | provenance, review date, no secret leakage |
| Agent execution | LifeOS Skills + Codex + bounded workers | approved plan → explicit action record | invocation, action outcome, trace |
| Daily automation | task_loop local SQLite outbox, later trusted scheduler/provider | due task → queued → delivered → acknowledged → completed | provider receipt and separate acknowledgement |
| Personal workspace | Pulse, quant research links, project overview | authoritative read-only status → dashboard | UI screenshot and live Doctor verification |
| Private storage + versioning | local USER and separately verified private GitHub repo | personal data → owner-approved backup | private repo visibility + redacted backup test |

## Important facts

- `summer-hu-1/LifeOS` is a PUBLIC fork of `danielmiessler/LifeOS`, not the user's personal data home.
- This branch contains implementation and tests only. No personal diary, positions, messages, or identity data is committed.
- Existing scheduled ChatGPT reports and notifications are separate from the local task outbox and must not be claimed as integrated.
- The user has previously discussed `stock_ai`; link that project by a repository URL, don't inline portfolio or trading records.
- UI and remote notifications should be built after private storage, authentication, consent, and an auditable transport are established.
- The local CLI is the smallest deterministic demonstration. It does not grant itself authority to trade, publish, send messages, delete files, or modify confidential documents.

## Stage gates

1. **Bridge:** unit tests + gitleaks + sensitive scan green on PR.
2. **Private store:** verify a *separate* private destination exists and backup recovery works.
3. **Local execution:** owner-run LifeOS Doctor, dry-run import and local state-machine test.
4. **Notification provider:** prove actual receipt, acknowledgement and retry/idempotency with permitted destination.
5. **Dashboard:** bind read-only status through an authenticated local API, demonstrate without sensitive data in logs.
6. **Production readiness:** access control, encrypted backup, recovery simulation, dependency pinning and rollback.

Do not merge upstream LifeOS upgrades and custom functionality without reviewing the diff and running checks.
