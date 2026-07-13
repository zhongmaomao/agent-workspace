---
name: grill-with-tree
description: "Read-only business and architecture alignment workflow: inspect code/docs, resolve material decisions through a persistent YAML tree, then emit a concise task-organized execution plan with stable core tests where applicable. Use when a user wants to stress-test or align a plan before another agent or multi-agent workflow implements it."
license: MIT
---

Align the requirement until its observable business behavior and necessary architecture decisions are shared. Continue across rounds only while a material decision remains open.

Default to read-only alignment. Unless the user explicitly asks to implement, change only the decision-tree YAML and final consensus document, never product code, configuration, scenes, assets, or tests.

## Core Rule

Organize user alignment by business behavior and only the technical decisions that materially affect architecture boundaries, data flow, state ownership, contracts, compatibility, or long-term cost. Never organize the conversation by implementation tasks.

Walk material decisions depth-first and recommend an answer for every question. Inspect code/docs instead of asking what is locally discoverable. Treat file choices, method structure, task decomposition, implementation sequence, and test matrices as agent-owned unless they change the user's outcome or delivery scope.

The deliverable is a self-contained execution plan organized as independently assignable tasks. Each task includes its own goal, implementation plan, verification, and core test cases when applicable.

## State File

Keep the tree in YAML, not only in chat. Run `python "<skill-dir>/scripts/decision_tree.py" --help`; the helper requires PyYAML. Store sessions as `Docs/Plan/grill-with-tree/<requirement-title>-YYYYMMDD.yaml` and the final document beside them as `.md`. Use `--file` to continue a session and `--force` only after the user rejects the top-level alignment.

## YAML Write Discipline

Serialize every YAML mutation. Run exactly one writing command at a time and base the next write on the latest file. Never mutate the same session through parallel tools, jobs, pipelines, or agents; parallelize read-only exploration only.

## First Round

First, explore the codebase and docs enough to understand the plan's target, architecture, affected files, and constraints. Do not ask what is locally discoverable.

Create the session with `init`, recording the requirement overview, change surface, and inspected sources. Add one first-level branch per material decision with `add-question`, including a recommendation and grounding.

The first-round message has exactly three parts, no headings: (1) a short paragraph restating the business goal, (2) a short paragraph on the architecture and change surface, (3) a compact list of material questions with recommended answers. Keep task decomposition out of the user-facing alignment unless it changes scope, staged delivery, or another user-visible outcome.

## Handling User Replies

If the user rejects or materially corrects the overview or change surface: re-explore, regenerate the same file with `init --file ... --force`, add a fresh set of first-level branches, and repeat the three-part display.

Record each reply with `update-question`, including the feedback, status, and resolved conclusion.

- Accepts the recommendation with no remaining business or architecture ambiguity → `closed` with a clear `--resolution`.
- Disagrees, adds a material constraint, or leaves a material dependency open → `answered`/`branching`, then add only the necessary follow-up.

Find the next open node with `decision_tree.py next --file ...`.

## Traversal Discipline

Use first-level questions to map the material decision space, then pursue one branch at a time, depth-first. Treat agreement as a leaf even when implementation, task, or test choices remain; branch only when the answer exposes another unresolved business behavior or necessary architecture decision.

Do not start implementation until material business and architecture assumptions are resolved, unless the user explicitly says to proceed with current assumptions. Record that override in the YAML first.

## Question Gate

Before every `add-question`, require both materiality and grounding:

- Ask only when different answers materially change observable business behavior or a necessary architecture decision. Evidence alone does not make an implementation detail user-facing.
- If code/docs determine the answer, inspect and record the fact instead of asking. Use `code: <files/symbols> - <fact>` or `docs: <source> - <fact>`.
- For a genuine product or strategy choice, use `product: needs user decision`.
- Keep `assumption: ...` only when the answer is genuinely unverifiable and requires confirmation.

Explore only deeply enough to support a recommendation. Do not create a node when both answers lead to the same user-visible result and architecture contract.

## Task Decomposition

Derive tasks after the user-facing decisions are aligned. Split work only when doing so brings a clear implementation benefit, such as:

- one task would otherwise be too large to implement coherently;
- independent work can proceed in parallel with limited ownership conflict;
- the requirement contains unrelated change surfaces that should not share one implementation task.

Do not set or target a task count. Do not split tests, documentation, or final validation into separate tasks unless they are independently deliverable. Keep coupled changes together when they share core files, control flow, or verification. Record dependencies and overlapping ownership in the final plan rather than asking the user how many tasks to create.

## Test Discipline

Use tests to protect stable business design. Treat long-term stability as equally important as present accuracy, and never distort the business behavior or architecture merely to make it easier to test.

Choose the smallest set of tests that clearly bounds the task's core business outcome. Add a boundary only when it is reachable, materially important, and plausibly affected by the change. Reuse existing coverage and avoid duplicating unchanged behavior.

Never make business configuration content itself the subject of a unit test. Do not assert current configuration rows, values, mappings, ordering, flags, tuning parameters, spreadsheet contents, or a specific cfgId unless the implementation itself hardcodes that cfgId as part of its stable contract.

A configuration-content-only task needs no unit tests; state that none apply and put its concrete content checks under Verification as configuration inspection, export, runtime, or delivery acceptance. Tests may still protect stable configuration schemas, configuration-processing logic, or business behavior driven by minimal synthetic configuration, but must assert the stable contract rather than the chosen configuration content.

Do not pursue completeness for its own sake. Avoid tests tied to transient UI tuning values, incidental implementation structure, upstream-invalid states outside the changed contract, or every theoretically possible edge. Prefer observable outcomes and stable relationships over exact internal values. Verify visual or intentionally tunable presentation through the project's runtime/visual workflow instead of brittle unit assertions.

Do not create dedicated user-facing test-alignment branches by default. Ask the user only when writing the test exposes a real ambiguity in the expected business behavior; ask about that behavior, not about the test case.

## Closing the Tree

When `next` reports none, set the top-level status to `closed`, run `validate`, write the same-basename `.md` plan, and report both paths.

Write a self-contained execution plan that another agent can implement without the chat. State settled conclusions, not discussion history, question logs, or alternatives considered. Keep unresolved items in the YAML instead of guessing in the document.

Lead with the shared goal, scope boundaries, stable contracts, cross-cutting decisions, and task dependencies. Include a glossary only when the plan introduces genuinely ambiguous terms.

Then organize the body as a **task list** derived by the agent under the decomposition rules above. Each task states, in this order:

- **Goal** — the business outcome the task delivers and why it is in scope.
- **Test cases** — the minimal stable contracts selected under Test Discipline, or an explicit statement that none apply.
- **Implementation plan** — affected modules/files, data and control flow, and the settled approach.
- **Verification** — the focused automated, runtime, integration, visual, or configuration acceptance checks that prove the goal without duplicating the test list.

## Decision Node Status

Use decision IDs such as `Q1`, `Q1.1`, `Q1.1.1`. Use `open` for unanswered nodes, `answered` while deciding whether to close or branch, `branching` while material children remain, `closed` for resolved leaves, and `revisit` when prior alignment changes. Run command `--help` for all fields.
