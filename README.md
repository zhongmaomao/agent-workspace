# agent-workspace

English | [简体中文](README.zh-CN.md)

**agent-workspace** provides three installable Codex skills for aligning
requirements before coordinating multi-agent implementation and verification:

- [`grill-with-tree`](.agents/skills/grill-with-tree/SKILL.md): inspects code
  and documentation without changing product files, resolves material business
  and architecture decisions through a persistent YAML tree, and produces an
  executable plan.
- [`multi-agents`](.agents/skills/multi-agents/SKILL.md): when the user
  explicitly requests multi-agent collaboration, delegates an approved plan to
  independent workers and then assigns independent verifiers.
- [`ponytail`](.agents/skills/ponytail/SKILL.md): keeps worker implementations
  minimal and avoids abstractions, dependencies, and scaffolding that are not
  justified by the requirement.

The recommended workflow is: requirement and architecture alignment → user
approval → workers implement → independent verifiers check the result → the
main agent reports the result.

## Prerequisites

- A Codex client that supports Agent Skills. Repository-level skills live at
  `.agents/skills/<skill-name>`; user-level skills live at
  `$HOME/.agents/skills/<skill-name>`.
- Git, for cloning and updating this repository.
- Python 3 and PyYAML, required by the `grill-with-tree` decision-tree helper:

  ```bash
  python -m pip install pyyaml
  ```

- A Codex environment with subagent collaboration capabilities when using
  `multi-agents`.

See the [Codex Skills documentation](https://learn.chatgpt.com/docs/build-skills)
and the [Agent Skills Specification](https://agentskills.io/specification) for
the format and discovery rules.

## Recommended installation

Invoke `$skill-installer` in Codex and send this prompt:

> Use `$skill-installer` to install `.agents/skills/grill-with-tree`,
> `.agents/skills/multi-agents`, and `.agents/skills/ponytail` from
> `https://github.com/zhongmaomao/agent-workspace`.

To install only one skill, keep only its path in the prompt. Start a new task
after installation, then use one of the prompts under “First use.”

## Manual installation

Clone the repository:

```bash
git clone https://github.com/zhongmaomao/agent-workspace.git
```

Install at user level to make the skills available across local projects:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R agent-workspace/.agents/skills/grill-with-tree "$HOME/.agents/skills/"
cp -R agent-workspace/.agents/skills/multi-agents "$HOME/.agents/skills/"
cp -R agent-workspace/.agents/skills/ponytail "$HOME/.agents/skills/"
```

For repository-level installation, replace `/path/to/project` with the target
repository root:

```bash
mkdir -p /path/to/project/.agents/skills
cp -R agent-workspace/.agents/skills/grill-with-tree /path/to/project/.agents/skills/
cp -R agent-workspace/.agents/skills/multi-agents /path/to/project/.agents/skills/
cp -R agent-workspace/.agents/skills/ponytail /path/to/project/.agents/skills/
```

## First use

Align a requirement and produce a plan:

> Use `$grill-with-tree` to inspect the current code and documentation and
> align this requirement. Stay read-only and produce only the decision tree and
> execution plan: …

After reviewing the plan, explicitly approve implementation:

> I approve this plan. Use `$multi-agents` to implement and verify it, and have
> workers use `$ponytail full`.

You can also apply the minimal-implementation constraint on its own:

> Use `$ponytail full` to implement this change: …

## Responsibilities

| Skill | Responsible for | Not responsible for |
| --- | --- | --- |
| `grill-with-tree` | Inspecting existing code and documentation; aligning business behavior, architecture boundaries, and delivery scope; maintaining a YAML decision tree; producing a task-oriented execution plan | Changing product code without explicit authorization; asking the user to decide routine implementation details such as file or method structure |
| `multi-agents` | Assigning approved tasks to independent workers; assigning independent verifiers; coordinating fixes for clear and reproducible violations; reporting through the main agent | Starting implementation without a plan; silently changing business behavior; expanding scope for speculative edge cases |
| `ponytail` | Keeping workers on standard-library, native-platform, and existing-dependency solutions; preserving the shortest verifiable implementation | Removing security, data protection, input validation, explicit requirements, or necessary verification |

`grill-with-tree` stores session state at
`Docs/Plan/grill-with-tree/<requirement-title>-YYYYMMDD.yaml` in the target
project and writes the final plan to the matching `.md` file. Its helper is
[`decision_tree.py`](.agents/skills/grill-with-tree/scripts/decision_tree.py)
and requires PyYAML:

```bash
python .agents/skills/grill-with-tree/scripts/decision_tree.py --help
```

## Complete workflow

1. The user invokes `$grill-with-tree` with a goal. The main agent reads the
   code and documentation and asks only about decisions that change the
   business outcome or a necessary architecture boundary.
2. `grill-with-tree` serially updates its YAML decision tree. Once every
   material branch is closed, it produces a self-contained execution plan.
3. The user reviews and explicitly approves the plan. `multi-agents` does not
   start implementation before approval.
4. The main agent uses `$multi-agents` to assign one worker per independent
   task. Workers use `$ponytail full` and implement only the smallest change
   required by the plan, together with its relevant checks.
5. After implementation, the main agent assigns verifiers who did not
   participate in the implementation to check the plan, changes, and evidence.
6. Subagents fix clear, reproducible violations. Business changes and new scope
   return to the user for a decision.
7. The main agent reports the implementation, verification results, remaining
   issues, and delivery locations.

## Updating

For a `$skill-installer` installation, ask it to install the latest version
from the same GitHub repository. For a manual installation, update the clone:

```bash
git -C agent-workspace pull --ff-only
```

Review the changes, then replace the three installed skill directories with
their latest versions. Merge manually first if you keep local modifications.

## Repository layout

```text
.
├── .agents/
│   └── skills/
│       ├── grill-with-tree/
│       │   ├── SKILL.md
│       │   └── scripts/decision_tree.py
│       ├── multi-agents/
│       │   ├── SKILL.md
│       │   └── agents/openai.yaml
│       └── ponytail/
│           └── SKILL.md
├── LICENSE
├── README.md
└── README.zh-CN.md
```

## License

This repository is licensed under the [MIT License](LICENSE).
