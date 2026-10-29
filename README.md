# skill-creator for the Muse app

Create new skills, modify and improve existing skills, and measure skill
performance — built for the Muse app.

This version is adapted from Anthropic's `skill-creator` skill
(https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator/skills/skill-creator,
Apache-2.0, see `LICENSE.txt`). The core workflow is unchanged:
draft → test → review → improve → repeat, with test prompts, baselines,
grading, benchmarking, and description optimisation.

## How it works in the Muse app

- **Test runs use subagents.** For each test prompt, spawn one subagent
  with the skill and one baseline subagent without it, in the same turn.
  Results are saved under `<skill-name>-workspace/iteration-N/eval-<name>/`.
- **Results are presented in chat.** Test outputs, benchmarks, and the
  review file are delivered as files in chat. The user replies with
  feedback in chat, or sends back the `feedback.json` the viewer
  downloads on submit.
- **Description optimisation uses subagents, not an automated loop.**
  Draft candidate descriptions, test each one with subagent runs on
  train queries, grade them against should-trigger / should-not-trigger,
  score them on a held-out test set, and pick the best test score.
  Scores are grader judgements across subagent runs, reported as such —
  there is no automated trigger-rate tool in this version.
- **Timing is optional.** If a run reports timing, save it to
  `timing.json`. If it does not, leave it out; benchmarks are built
  from grading results.

## What is in this skill, and how each part is used here

| Component | Used in the Muse app as |
| --- | --- |
| `SKILL.md` | The full workflow: capture intent, draft, test, grade, improve, optimise the description, package. |
| `agents/grader.md` | Instructions for a grader subagent that scores assertions against outputs and writes `grading.json`. |
| `agents/comparator.md` | Instructions for a blind-comparison subagent (outputs A/B, winner unknown). |
| `agents/analyzer.md` | Instructions for an analyst subagent that surfaces patterns in benchmark results. |
| `references/schemas.md` | JSON schemas for `evals.json`, `eval_metadata.json`, `grading.json`, `timing.json` (optional), and `benchmark.json`. |
| `scripts/quick_validate.py` | Validates a skill directory: `python3 scripts/quick_validate.py <skill-dir>`. |
| `scripts/package_skill.py` | Packages a skill into a `.skill` file for delivery in chat: `python -m scripts.package_skill <skill-dir>`. |
| `scripts/aggregate_benchmark.py` | Aggregates `grading.json` files into `benchmark.json` / `benchmark.md`: `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>`. |
| `scripts/utils.py` | Shared helper for parsing `SKILL.md` frontmatter, used by the scripts above. |
| `eval-viewer/generate_review.py` | Generates the review as a **static** HTML file for delivery in chat: `python eval-viewer/generate_review.py <workspace> --skill-name <name> --benchmark <workspace>/benchmark.json --static <workspace>/review.html`. No server is started. |
| `eval-viewer/viewer.html` | The review UI template used by the static viewer. |
| `assets/eval_review.html` | Optional interactive table for reviewing a description eval set. The default review is in chat; use this file only if the user prefers the table. |

This version does not include terminal evaluation scripts. Anything that
used to need one is replaced above by a subagent step, a chat step, or a
plain Python script from the table.

## Install in the Muse app

Copy the contents of this directory into
`~/workspace/custom-skills/skill-creator/`, then check it is discoverable
via skill search (`skill_creator`).

## Quick checks

```bash
python3 -m py_compile scripts/*.py eval-viewer/*.py
python3 scripts/quick_validate.py .
python3 -m scripts.package_skill .
```

## Updating an existing skill

Preserve the original skill name (directory name and `name` frontmatter).
Copy to a writeable location before editing, stage packaging in `/tmp/`
first if direct writes fail, and package from the copy.
