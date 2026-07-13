# agent-workspace

`agent-workspace` 提供三个可直接安装的 Codex skill，用于先对齐需求，再由多 agent 实施和验证：

- [`grill-with-tree`](.agents/skills/grill-with-tree/SKILL.md)：只读检查代码和文档，用持久化 YAML 决策树解决会影响业务行为或架构边界的问题，最后产出可执行计划。
- [`multi-agents`](.agents/skills/multi-agents/SKILL.md)：在用户明确要求多 agent 协作时，把已批准计划交给独立 workers 实施，再由独立 verifiers 验证。
- [`ponytail`](.agents/skills/ponytail/SKILL.md)：约束 worker 选择真正可用的最小实现，避免无需求支撑的抽象、依赖和脚手架。

推荐组合流程是：需求与架构对齐 → 用户批准计划 → workers 实施 → independent verifiers 验证 → 主 agent 汇总。

## 前置条件

- 支持 Agent Skills 的 Codex。Codex 的仓库级 skill 目录是 `.agents/skills/<skill-name>`，用户级目录是 `$HOME/.agents/skills/<skill-name>`。
- Git，用于克隆和更新本仓库。
- Python 3 和 PyYAML，用于 `grill-with-tree` 的决策树工具：

  ```bash
  python -m pip install pyyaml
  ```

- 使用 `multi-agents` 时，当前 Codex 环境需要提供 subagent 协作能力。

格式和发现规则可参考 [Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills) 与 [Agent Skills Specification](https://agentskills.io/specification)。

## 推荐安装

在 Codex 中调用 `$skill-installer`，直接发送下面这句话：

> 请使用 `$skill-installer` 从 GitHub 仓库 `https://github.com/zhongmaomao/agent-workspace` 安装 `.agents/skills/grill-with-tree`、`.agents/skills/multi-agents` 和 `.agents/skills/ponytail`。

如果只需要其中一个 skill，只保留对应路径。安装后开启一个新任务，再按“首次调用”中的示例使用。

## 手动安装

先克隆仓库：

```bash
git clone https://github.com/zhongmaomao/agent-workspace.git
```

用户级安装会让 skill 可用于本机各项目：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R agent-workspace/.agents/skills/grill-with-tree "$HOME/.agents/skills/"
cp -R agent-workspace/.agents/skills/multi-agents "$HOME/.agents/skills/"
cp -R agent-workspace/.agents/skills/ponytail "$HOME/.agents/skills/"
```

仓库级安装只对指定项目生效。把 `/path/to/project` 换成项目根目录：

```bash
mkdir -p /path/to/project/.agents/skills
cp -R agent-workspace/.agents/skills/grill-with-tree /path/to/project/.agents/skills/
cp -R agent-workspace/.agents/skills/multi-agents /path/to/project/.agents/skills/
cp -R agent-workspace/.agents/skills/ponytail /path/to/project/.agents/skills/
```

## 首次调用

先对齐需求并生成计划：

> 使用 `$grill-with-tree` 检查当前代码和文档，对齐这个需求。保持只读，只产出决策树和执行计划：……

确认计划内容后，再明确批准实施：

> 我批准这个计划。使用 `$multi-agents` 按计划实施和验证，让 workers 使用 `$ponytail full`。

也可以单独使用最小实现约束：

> 使用 `$ponytail full` 实现这个改动：……

## 职责边界

| Skill | 负责 | 不负责 |
| --- | --- | --- |
| `grill-with-tree` | 检查现有代码和文档；对齐业务行为、架构边界和交付范围；维护 YAML 决策树；生成任务化执行计划 | 未获明确授权时修改产品代码；把文件选择、方法结构等普通实现细节交给用户决定 |
| `multi-agents` | 按已批准计划分派独立 workers；分派独立 verifiers；协调明确且可复现的问题修复；由主 agent 汇总结果 | 在没有计划时直接开工；自动改变业务行为；为推测性的边界扩写范围 |
| `ponytail` | 让 worker 优先使用标准库、平台能力和现有依赖；保留最短可验证实现 | 省略安全、数据保护、输入校验、明确需求或必要验证 |

`grill-with-tree` 的状态文件写入目标项目的 `Docs/Plan/grill-with-tree/<requirement-title>-YYYYMMDD.yaml`，最终计划写在同名 `.md` 文件中。它的辅助工具是 [`decision_tree.py`](.agents/skills/grill-with-tree/scripts/decision_tree.py)，运行前需要 PyYAML：

```bash
python .agents/skills/grill-with-tree/scripts/decision_tree.py --help
```

## 完整流程

1. 用户用 `$grill-with-tree` 提出目标。主 agent 读取代码和文档，只询问会改变业务结果或必要架构决策的问题。
2. `grill-with-tree` 串行更新 YAML 决策树，直到所有重要分支关闭，再生成自包含执行计划。
3. 用户检查计划并明确批准。没有批准时，`multi-agents` 不进入实施。
4. 主 agent 用 `$multi-agents` 按独立任务分派 workers。worker 使用 `$ponytail full`，只实现计划要求的最小改动并完成相应检查。
5. workers 完成后，主 agent 分派未参与实现的 verifiers，核对计划、改动和验证结果。
6. 明确且可复现的偏差由 subagent 修复；涉及业务变化或新增范围的问题交回用户决定。
7. 主 agent 汇总实施内容、验证结果、遗留问题和交付位置。

## 更新

通过 `$skill-installer` 安装时，可再次要求它从同一 GitHub 仓库安装最新版本。手动安装时先更新本地克隆：

```bash
git -C agent-workspace pull --ff-only
```

检查变更后，用最新的三个 skill 目录整体替换原安装目录；如果保留了本地修改，先自行合并，不要直接覆盖。

## 目录结构

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
└── README.md
```

## License

本仓库使用 [MIT License](LICENSE)。
