# 发给 teammate：Claude Code 验证与人工审批清单

这份文件记录**仍需真人在 Claude Code 中执行、观察和保存证据的部分**。
仓库里的文件和本地脚本测试不等于已经执行过 Claude 原生 Skills、Sub-agents
或 Agent teams。本项目没有冒充 Claude 运行记录，没有替真实审计人批准风险或签核。

教程：[Procurement Audit Planner](https://procurement-audit-planner.vercel.app/)。
网站的 **27 项**包含两个前置准备（VS Code、Claude Code）和 **25 个编号步骤**：
1.1–1.5、2.1–2.2、3.1–3.7、4.1–4.3、5.1–5.8。课程网站截图中的数量、日期、风险编号只是示例，不能当成
当前数据的验收数值。可离线查阅 `docs/reference/` 内的页面文本和完整 prompts。

## 交接状态

已经准备：教程项目说明、公开数据、三个 Skills、六个 Agents、Python 分析及
验证脚本、输出证据草稿、风险登记表构建器、规划包构建器和 QA 检查器。
具体已跑过的脚本结果以 README、当前 outputs 及测试日志为准。

尚未宣称完成：Claude 安装/登录及项目识别、Claude 原生技能调用、子代理委派、
项目 memory 实际持久化、三名 teammate 的消息协作、真实风险逐项决策、最终
签核。网页 harness 的测试与部署属于 Part B；即使网页可跑通，也不能替代这里
的 Claude 原生架构证据。GitHub 上传、线上部署后的 URL 需要另外确认并填写。

## 一、启动与环境检查

1. 在自己的机器安装 VS Code 和 Claude Code，使用本人/课程允许的账号登录。
   安装和登录操作遵循 [Claude Code 官方文档](https://code.claude.com/docs/en/setup)。
   不把登录信息、API key 或会话令牌提交到 GitHub。
2. 用 VS Code 打开这个项目文件夹。克隆到别的机器后**重新创建** Python 环境，
   不复制本机 `.venv`。
3. 在项目终端执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
claude --version
claude
```

`pdftotext` / `pdfinfo` 是教程使用的 Poppler 工具。为保证本地与云端一致，
本项目来源验证器固定使用锁定版本的 pypdf。安装 Poppler 不会改变验证器的抽取方式。
若需要查看教程中的 Poppler 命令输出，可另行安装，但不要混用两种抽取文本来修改来源引文。
Python 版本要求以 README/requirements 为准。

启动后先发这个 prompt：

```text
What do you know about this project?
Read CLAUDE.md and summarize the three skills, six agents, evidence rules,
and two human gates. Inspect the existing files; do not recreate or overwrite
working implementations. Tell me which parts still require a native Claude run.
```

验收：Claude 正确读取当前项目的 `CLAUDE.md`，识别 `.claude/skills` 和
`.claude/agents`；不能声称已有真实审批或签核。保存版本、日期、启动位置以及
这段回复的截图或导出记录到 `docs/claude-evidence/`（该目录由验证人创建）。

## 二、按 guide 逐步核验

表中“文件已准备”只表示可供 Claude 检查和运行，**不是勾选完成的依据**。

| Guide 步骤 | 已准备的文件/脚本 | teammate 在 Claude 中要做的验证 | 建议留下的证据 |
|---|---|---|---|
| 1.1 项目与 Claude | 当前项目目录 | 安装、登录、在正确目录启动 Claude | 版本与启动截图 |
| 1.2 项目 brief | CLAUDE.md | 发送上面的项目理解 prompt | 正确描述架构的回复 |
| 1.3 下载数据 | data/、来源清单 | 核对规则 PDF、支出文件、合同 CSV、四份委员会 PDF | 文件清单/来源核对 |
| 1.4 工具 | requirements.txt、.venv 创建方法 | 验证 Python 库，检查 PDF 提取工具/后备实现 | 版本/依赖结果 |
| 1.5 目录 | .claude/skills、.claude/agents、scripts、outputs | 确認 Claude 可发现目录 | 目录清单 |
| 2.1 extract-rules | SKILL.md、verify_quotes.py | 让 Claude 读原文/布局文本、理解规则 schema，并跑故意错误 fixture | 错误被拒绝的输出 |
| 2.2 运行 Skill | rules.json 草稿 | 原生 `/extract-rules`；逐页覆盖、quote 与 clause 抽查 | 调用日志、验证结果 |
| 3.1 spend-analyst | agent 定义、clean.py、analyse.py | 确认 Claude 使用专门子代理，理解实际表头、可选合同、标签 | 子代理启动/返回记录 |
| 3.2 运行 spend | analytics 输出 | `Run the spend-analyst.`；只读摘要，不把全量数据放入上下文 | 子代理日志、数字自检 |
| 3.3 findings-analyst | agent 定义、verify_history.py | 核对 PDF 架构、assurance/actions/scales 的来源和缺口 | 文件加载/验证记录 |
| 3.4 运行 findings | history.json 草稿、PDF 图片 | `Run the findings-analyst.`；渲染并核对 opinion、impact scale、risk band 三处 | 三张截图和逐项核对 |
| 3.5 risk-assessment | Skill、build_register.py | 理解 citation/placeholder/schema；好坏风险 fixture；实际评分判断 | fixture 结果/判断说明 |
| 3.6 risk-assessor | agent 定义 | 确认该子代理读取对应 Skill、而非主会话直接假装完成 | 子代理记录 |
| 3.7 风险登记表 | ratings/register 草稿（以当前输出为准） | `Run the risk-assessor.`；自行重跑 builder；检查无 supplier name、无未经计算数字 | summary table/输出日志 |
| 4.1 展示人工关卡 | auditor-comments.md 空模板 | 显示 comments 与 register，逐项匹配、数空白项 | 尚未决策的表格截图 |
| 4.2 人工逐项决定 | 保留空白，不自动 approve | 真人给 approve/amend/reject、理由、姓名和日期 | 决策文件 diff |
| 4.3 应用决定 | revision 校验与 baseline | 再跑 risk-assessor；amend/reject 生效、未授权内容不变 | revision header 与 gate 日志 |
| 5.1 完成剩余决策 | 完整性关卡 | 只有真人审阅后填写剩余行，仍有空白必须阻塞 | 全行已决策/有效理由 |
| 5.2 启用 Teams | .claude/settings.json | 新会话确认实验开关生效；失败时按实际版本排查 | 设置与运行能力截图 |
| 5.3 audit-program | Skill、build_pack.py | gate → plan judgments → deterministic pack；测试缺失/无效输入阻塞 | builder 输出 |
| 5.4 planner | planner.md | 作为 team member 启动；只写自己的 plan/pack | PACK READY 消息 |
| 5.5 challenger | challenger.md | 与 planner 直接通信；有来源的 challenge；最多两轮 | 双方消息/challenges.md |
| 5.6 qa-reviewer | qa-reviewer.md、scripts/checks | 与 planner 直接通信；运行四项检查；缺文件/未审风险不能通过 | QA 日志/review.md |
| 5.7 运行团队 | 三份 agent 定义 | 启动真正 team，等待三种 DONE，再关闭 teammates | team 生命周期和直接消息 |
| 5.8 最后签核 | review.md 的签核块由 QA 产生 | 真人查看 READY 与 for-auditor 项，明确签核或退回 | 真实姓名/日期/决定 |

## 三、可以直接复制的操作 prompts

### A. 原生 Skills 与 Sub-agents

先做备份或 Git commit，避免与本地参考输出比较时失去原版本。不要把数据或
outputs 整体塞进聊天上下文；让 agent 使用文件和摘要。

```text
/extract-rules
```

```text
Run the spend-analyst and findings-analyst as their named sub-agents.
Follow their files in .claude/agents/. Keep their tool results and outputs
separate. Python must compute every number. Inspect the existing scripts
before changing them. Report all missing inputs and caveats.
```

```text
Run the risk-assessor. Follow .claude/skills/risk-assessment/SKILL.md.
Treat current outputs as draft evidence to review, not as prior approval.
Run the builder until it has no failures or warnings. Preserve blank human
decisions. Show the register summary and report whether any supplier name
appears in a risk statement or justification.
```

核心脚本检查（项目根目录）：

```bash
.venv/bin/python .claude/skills/extract-rules/verify_quotes.py outputs/rules.json data/contract-rules.pdf
.venv/bin/python scripts/verify_history.py outputs/history.json data/committee
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python .claude/skills/risk-assessment/build_register.py outputs/risk-ratings.json
.venv/bin/python .claude/skills/audit-program/build_pack.py --gate
```

人工尚未完成时，最后一条 **退出非零并说明未决策/未应用 revision 是正确结果**。
不能为了拿到 PASS 删除检查、手工填 revision 标题，或把测试夹具中的审批复制到
真实输出。当前 builder 会把有效 revision 与原始 judgments、comments、register
的摘要绑定；改动后需要重跑。

### B. 两个人工关卡

先让 Claude 展示现状：

```text
Show outputs/auditor-comments.md next to the Summary of outputs/risk-register.md.
Count undecided rows with Python. Do not fill any decision. Show the evidence
and scope caveats I need to consider before deciding.
```

随后**由真人替换**下面内容后发送；这里没有预设任何实际风险的决定：

```text
Record only my following decisions in outputs/auditor-comments.md.
Reviewer: [真实姓名]. Date: [YYYY-MM-DD].
[逐条填写实际存在的风险 ID、approve/amend/reject 与理由；不要保留占位符。]
Leave every unmentioned row unchanged. Then run the risk-assessor to apply
these decisions and validate the revision. Do not plan while any row is blank.
```

`amend` 请明确字段，例如 “Raise likelihood to 3”；自由文字的语义仍需要人核对，
脚本只能自动验证其能解析的明确分数与结构约束。Rejected risk 必须移出 register，
保留 `excluded` 理由与原决策行。教程的 R-01/R-09/R-10 是演示，不能机械复制。

### C. 真正的 Agent team（全部风险已决策后）

```text
Run the agent team for the audit planning pack, following CLAUDE.md.
First run build_pack.py --gate and stop if it fails. Spawn planner, challenger,
and qa-reviewer as named teammates from .claude/agents/. Tell each the other
two names. The challenger and qa-reviewer wait for PACK READY v1; they message
the planner directly. The lead does not relay routine messages. Follow the
maximum two challenge rounds. Wait for PLANNER DONE, CHALLENGER DONE and QA DONE,
then shut down the teammates. Do not fill the auditor sign-off block.
```

验收重点：这不是主会话依次扮演三个角色。要看到实际 teammates/任务、直接消息、
pack 版本、QA 失败修复（若有）、三种 DONE、关闭生命周期。若安装版本不支持
该实验能力，记录版本与原始错误，先与老师确认兼容实现，不能把顺序调用冒称为
原生 Agent teams。

```bash
.venv/bin/python .claude/skills/audit-program/build_pack.py --gate
.venv/bin/python .claude/skills/audit-program/build_pack.py
.venv/bin/python scripts/checks/run_checks.py
```

四项检查（quotes / numbers / trace / samples）都通过才允许输出
`READY FOR SIGN-OFF`；`BLOCKED` 回到团队修正。检测脚本不是审计意见，
human 必须查看 source、抽样设计、未解决的 for-auditor 项。

最后由真人确认后发送：

```text
Show outputs/review.md and the points marked for the auditor in challenges.md.
[查看后再明确提供：name、date、decision 为 sign off 或 return to the team、comment。]
```

## 四、Memory 专项检查

- spend-analyst、findings-analyst、risk-assessor 及团队成员的 `memory: project`
  由 Claude 运行时管理，文件已声明不等于已经持久化。
- 允许保留短的 procedural lesson，例如错误表头处理、quote normalization、
  citation syntax。不能保存当前 supplier、金额、分数、risk finding 或具体审批。
- 重新开启会话时，验证 memory 被读取但 agent 仍重新读取当前输入。
- 若无值得记忆的新经验，**没有新 memory 条目是合理的**，不要编造经验来完成勾选。
- 保存脱敏后的 memory 清单与 agent 的说明，不必提交个人/账号环境信息。

## 五、建议的验收证据包与提交前检查

在 `docs/claude-evidence/` 按步骤保存日志/截图，并记录操作者、日期、Claude
版本、输入版本（commit/hash）、实际退出码。最终 README 只把有证据的步骤
标记为完成；保留暂缺项。重点文件：

- skill 调用、两名分析子代理、risk-assessor 的实际运行记录；
- rules/history quote 验证、故意错误 fixture 和完整测试结果；
- 人工 decisions、validated revision、闭合 gate；
- 真正 team 的启动、直接消息、关闭记录；
- planning memo、risk-control matrix、audit program、sample CSV、challenges、
  review，及真实最终签核。

Part A 提交 GitHub repository URL；Part B 提交独立部署 URL。部署后从另一台
机器/无本地服务的浏览器走完整流程，验证数据分析、风险人工决策、规划、QA、
最终签核与导出。不要仅用本机 localhost 截图代替部署验收。
