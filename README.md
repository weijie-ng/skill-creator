# skill-creator for Muse

Create new skills, modify and improve existing skills, and measure skill
performance — adapted for Muse and Muse Code.

This is a Muse port of Anthropic's `skill-creator` skill
(https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator/skills/skill-creator,
Apache-2.0, see `LICENSE.txt`). The core workflow is unchanged:
draft → test → review → improve → repeat, with test prompts, baselines,
grading, benchmarking, and description optimisation.

## What changed from the upstream Claude version

- `Claude` / `Claude Code` / `Claude.ai` / `Cowork` references become
  `Muse` / `Muse Code` / `Muse app` / Muse Code CLI sections.
- Headless runs use `muse exec`, not `claude -p`:
  - `scripts/improve_description.py` now calls
    `muse exec --prompt-file <temp-file>` instead of `claude -p` on stdin.
  - `scripts/run_eval.py` now calls `muse exec --prompt-file <query-file>`.
- The Muse-app workflow (no shell CLI) is now explicit: run test prompts as
  subagents (with-skill vs baseline) and present results in chat, instead of
  using the CLI optimisation loop.
- `references/schemas.md` example model is now `muse-spark-1.3` instead of
  `claude-sonnet-4-20250514`.
- The skill name (`skill-creator`) and frontmatter description are preserved,
  with "for Muse and Muse Code" added to the description.

## Honest limitations — read before trusting CLI scores

Muse Code does not expose the Claude-style stream-json Skill tool event that
the original `run_eval.py` relied on (a fake `.claude/commands/` file plus
`claude -p --output-format stream-json` event detection). This port therefore
counts a run as "triggered" when the `muse exec` output names the skill.
That is observed use, not a proven trigger-rate measurement.

Before relying on `run_loop.py` / `run_eval.py` scores, run
`muse exec --help` on your installed Muse Code version and confirm the
`--prompt-file` form and output format. The scripts record `--model` for the
transcript but do not pass a `--model` flag to `muse exec`, because that flag
was not verified for Muse Code here. In the Muse app, use subagent runs
instead of these scripts.

The `muse` CLI is not present in every Muse environment (for example, the
Muse app VM has no `muse` binary). The scripts fail with a clear
"muse CLI not found" message in that case rather than pretending a run
happened.

## Install

### Muse Code

Copy this directory to where Muse Code loads skills for your project, trust
the workspace when asked, and run `muse exec` tests from the project root.

### Muse app (this workspace layout)

Copy the contents of this directory into
`~/workspace/custom-skills/skill-creator/`, then check it is discoverable
via skill search (`skill_creator`).

## Quick checks

```bash
python3 -m py_compile scripts/*.py eval-viewer/*.py
python3 scripts/quick_validate.py .
python3 -m scripts.package_skill .
```
