---
name: multi-agents
description: Coordinate explicitly requested multi-agent implementation and verification.
license: MIT
---

Keep the main agent focused on coordination: it may explore the relevant context and create or update planning documents, but delegate actual implementation to independent non-forked worker subagents. After workers finish, assign independent non-forked verifier subagents as needed, coordinate any fixes through subagents, and deliver the final verified result.

Notes:
- Instruct worker subagents to use the /ponytail skill.
- By default, use the same model as the main agent for subagents.
- With a user plan: one worker per independent task; parallel is optional.
- Without a user plan: explore the relevant context, align the task, stop and ask for approval.
- Verifier subagents may report no findings.
- Auto-fix only clear, reproducible violations of the approved plan. Findings that change business behavior, or address speculative edge cases require user approval.
