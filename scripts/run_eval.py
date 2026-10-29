#!/usr/bin/env python3
"""Run trigger evaluation for a skill description (Muse port).

Tests whether a skill's description causes Muse to use the skill for a set
of queries. Outputs results as JSON.

Muse port note — read before trusting scores: the original Claude version
injected a fake command file into .muse/commands/ and detected a Skill tool
event in `claude -p --output-format stream-json`. Muse Code has no equivalent
verified mechanism, so this port instead runs each query with
`muse exec --prompt-file <query-file>` (the skill must already be installed
where Muse Code loads it for the project) and counts a run as triggered
when the run output names the skill. That is observed use, not a proven
trigger-rate measurement. Verify `muse exec --help` / `--json` output on
your installed Muse Code version before treating scores as exact, and in
the Muse app use with-skill vs baseline subagent runs instead of this script.
The --model argument is recorded for compatibility but is not passed as a
`muse exec` flag (not verified for Muse Code here).
"""

import argparse
import json
import os
import select
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Return the current working directory as the project root.

    Muse Code loads project skills from the trusted project directory, so
    run this script from the project root (or set cwd there). Unlike the
    original, this port does not look for a .muse/commands/ directory and
    does not inject a fake skill file.
    """
    return Path.cwd()


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Run a single query via `muse exec`; return whether the skill was used.

    The query is written to a temp prompt file (so long queries do not hit
    argv limits) and run as `muse exec --prompt-file <file>` from
    project_root. Triggered = the skill name appears in the run output.
    Raises FileNotFoundError (caught by run_eval as a failed query, with a
    warning) if the `muse` CLI is not on PATH.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", prefix="muse-eval-", delete=False
    ) as f:
        f.write(query)
        prompt_file = f.name
    try:
        try:
            result = subprocess.run(
                ["muse", "exec", "--prompt-file", prompt_file],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=timeout,
            )
        except FileNotFoundError:
            print(
                "Warning: `muse` CLI not found. Install Muse Code and put "
                "`muse` on PATH, or use subagent runs in the Muse app.",
                file=sys.stderr,
            )
            raise
        output = (result.stdout or "") + " " + (result.stderr or "")
        return skill_name.lower() in output.lower()
    finally:
        try:
            Path(prompt_file).unlink()
        except OSError:
            pass


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to record (default: user's configured model). Not passed as a muse exec flag; see module docstring.")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
