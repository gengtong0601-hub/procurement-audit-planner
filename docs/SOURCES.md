# Source provenance and reuse

Downloaded for this assignment on 2026-10-05 (local time):

- Guide: https://procurement-audit-planner.vercel.app/
- Setup: https://procurement-audit-planner.vercel.app/lessons/setup
- Skills: https://procurement-audit-planner.vercel.app/lessons/skills
- Sub-agents: https://procurement-audit-planner.vercel.app/lessons/sub-agents
- Human gate: https://procurement-audit-planner.vercel.app/lessons/human-gate
- Agent teams: https://procurement-audit-planner.vercel.app/lessons/agent-team
- Course data archive: https://procurement-audit-planner.vercel.app/data.zip
- Course repository linked by the guide:
  https://github.com/traversaal-ai/agent-engineering-leidos/tree/main/module_5_Skills_Subagents_MultiAgents/data%206

The archive supplies the original West Berkshire Council PDFs, three Excel
workbooks and raw Contracts Finder export. They are preserved unchanged under
`data/`; their SHA-256 hashes are in `data/manifest.json`. Dataset dates are
described in `docs/DATA_PROFILE.md`, not inferred from download date.

The guide's `CLAUDE.md` is retained verbatim. Several Skill, Agent and verifier
definitions are adapted from its complete copyable examples; specific original
work and hardening are recorded in `IMPLEMENTATION_NOTES.md`. We do not claim
original authorship of supplied course code or assign it a new licence.
Original public-source rights and course redistribution requirements continue
to apply. Source copies in `docs/reference/` support reproducibility.

Additional implementation references:

- Claude Skills: https://code.claude.com/docs/en/skills
- Claude sub-agents: https://code.claude.com/docs/en/sub-agents
- Claude agent teams: https://code.claude.com/docs/en/agent-teams
- Messages API: https://platform.claude.com/docs/en/build-with-claude/working-with-messages

The native Claude team lifecycle is an interactive Claude Code feature. The
web harness uses its own role orchestration and the Messages API; it does not
claim to run native Claude teams through a noninteractive CLI.
