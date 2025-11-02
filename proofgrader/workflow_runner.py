#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent  # proofgrader/
PROJECT_ROOT = ROOT.parent  # ProofGym/
# Organized roots
DATA_ROOT = PROJECT_ROOT / "data" / "evaluator_data"
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
DEFAULT_DATASET = DATA_ROOT / "pilot" / "model_output.jsonl"
DEFAULT_TEMPLATE_CONFIG = PROJECT_ROOT / "templates"

# Import workflows from the proofgrader.workflows package
try:
    from proofgrader.workflows import WORKFLOWS  # type: ignore
except Exception:
    WORKFLOWS = None

def show_run_info(args: argparse.Namespace) -> None:
    print("ROOT:", ROOT)
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DATA_ROOT:", DATA_ROOT)
    print("OUTPUTS_ROOT:", OUTPUTS_ROOT)
    print("DEFAULT_DATASET:", DEFAULT_DATASET)
    print("DEFAULT_TEMPLATE_CONFIG:", DEFAULT_TEMPLATE_CONFIG)
    print("WORKFLOWS:", WORKFLOWS)
    print("args:", args)

def main() -> None:
    def _short_model(name: str) -> str:
        try:
            return str(name).strip().split("/")[-1]
        except Exception:
            return str(name)
    p = argparse.ArgumentParser(
        description="Run evaluator workflow: generate evaluations, extract scores, and compute metrics",
    )
    p.add_argument(
        "--evaluator-model",
        required=True,
        help="Remote evaluator model name for single-stage or judge stage (e.g., gemini-2.5-pro)",
    )
    p.add_argument(
        "--template",
        default="basic",
        help="Prompt template name (used in single-stage workflow)",
    )
    p.add_argument(
        "--data-version",
        default="pilot",
        help="Data version key used to derive default dataset and dump dir (e.g., pilot, v1, v2)",
    )
    p.add_argument(
        "--dataset",
        default=None,
        help="Path to merged dataset JSONL. If omitted, defaults to evaluator_design/data/<data-version>/model_output.jsonl",
    )
    p.add_argument(
        "--template-config",
        default=str(DEFAULT_TEMPLATE_CONFIG),
        help="Path to prompt YAML (used in single-stage workflow)",
    )
    p.add_argument(
        "--dump-dir",
        default=None,
        help="Directory to dump this run's raw outputs (evaluator_raw.jsonl only). If not set, defaults to eval_runs/<data-version>/<evaluator>__<template>__<timestamp> under this module.",
    )
    p.add_argument(
        "--evaluator-tag",
        default=None,
        help="Folder name under evaluator_grades for parsed outputs (defaults to <evaluator-model>__<template>).",
    )
    p.add_argument(
        "--output-raw",
        default=None,
        help="Path to save raw evaluator responses from evaluate.py (overrides dump-dir default)",
    )
    p.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip running evaluate.py and reuse the existing raw output (--output-raw or dump-dir default)",
    )
    p.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Optional limit on number of examples (only applies when not skipping generation)",
    )
    p.add_argument("--no-cache", action="store_true", help="Disable caching in evaluate.py run")
    p.add_argument(
        "--processing-mode",
        default="batch",
        choices=["sequential", "batch", "parallel"],
        help="Processing mode (deprecated, batch mode is always used)",
    )
    p.add_argument(
        "--n-sampling",
        type=int,
        default=1,
        help="Number of samples per item in evaluate.py",
    )
    # Workflow selection and options
    p.add_argument(
        "--workflow",
        default="single",
        choices=["single", "decompose-then-judge", "repeat-and-aggregate", "reflect-and-revise"],
        help="Evaluation workflow to run",
    )
    p.add_argument(
        "--num-runs",
        type=int,
        default=3,
        help="Number of repeated runs for repeat-and-aggregate workflow",
    )
    p.add_argument(
        "--steps-model",
        default=None,
        help="Model name for the decomposition stage (required for decompose-then-judge)",
    )
    p.add_argument(
        "--steps-template",
        default="break_into_steps_and_grade",
        help="Template name for decomposition stage (from prompt_templates.yaml)",
    )
    p.add_argument(
        "--judge-template",
        default="with_marking_scheme_and_break_into_steps",
        help="Template name for judge stage (from prompt_templates.yaml)",
    )
    p.add_argument(
        "--templates-config",
        default=str(PROJECT_ROOT / "evaluation_prompt.yaml"),
        help="Path to prompt YAML for multi-stage workflow (defaults to evaluation_prompt.yaml)",
    )
    p.add_argument(
        "--critic-template",
        default="critic_reflection",
        help="Template name for self-critique stage (from prompt_templates.yaml)",
    )
    p.add_argument(
        "--final-template",
        default="final_verdict_from_critique",
        help="Template name for final verdict stage (from prompt_templates.yaml)",
    )
    # Per-stage model overrides for reflect-and-revise
    p.add_argument(
        "--init-model",
        default=None,
        help="Model name for Stage A (initial evaluation) in reflect-and-revise (defaults to --evaluator-model)",
    )
    p.add_argument(
        "--critic-model",
        default=None,
        help="Model name for Stage B (self-critique) in reflect-and-revise (defaults to --evaluator-model)",
    )
    p.add_argument(
        "--final-model",
        default=None,
        help="Model name for Stage C (final verdict) in reflect-and-revise (defaults to --evaluator-model)",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed debug summary and write a debug report JSON",
    )
    p.add_argument(
        "--debug-limit",
        type=int,
        default=5,
        help="Max examples to include per skip reason in the debug report",
    )
    p.add_argument(
        "--use-raw-generator",
        action="store_true",
        help="Use raw 'model' field in evaluator_raw.jsonl to determine generator (instead of mapping by (id,solution))",
    )
    p.add_argument(
        "--binary",
        action="store_true",
        help="Enable binary mode: write to evaluator_grades_binary/ and compute binary metrics",
    )
    args = p.parse_args()

    show_run_info(args)

    # Resolve dataset path using data version if not explicitly provided
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        candidate = DATA_ROOT / str(args.data_version) / "model_output.jsonl"
        dataset_path = candidate
        args.dataset = str(dataset_path)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")
    template_config = Path(args.template_config)
    if not template_config.exists():
        raise SystemExit(f"Template config not found: {template_config}")

    # Derive sensible defaults for run naming and evaluator tag per workflow
    if args.workflow == "decompose-then-judge":
        default_tag = (
            f"decompose-then-judge__"
            f"judge-{_short_model(args.evaluator_model)}__{args.judge_template}__"
            f"steps-{_short_model(args.steps_model)}__{args.steps_template}"
        )
        evaluator_tag_default = (
            f"decompose-then-judge__"
            f"judge-{_short_model(args.evaluator_model)}__{args.judge_template}__"
            f"steps-{_short_model(args.steps_model)}"
        )
    elif args.workflow == "reflect-and-revise":
        # Resolve per-stage models falling back to evaluator_model
        init_model = args.init_model or args.evaluator_model
        critic_model = args.critic_model or args.evaluator_model
        final_model = args.final_model or args.evaluator_model
        # Update args so downstream workflow can use them directly
        args.init_model = init_model
        args.critic_model = critic_model
        args.final_model = final_model
        default_tag = (
            f"reflect-and-revise__A-{_short_model(init_model)}__init-{args.template}__"
            f"B-{_short_model(critic_model)}__critic-{args.critic_template}__"
            f"C-{_short_model(final_model)}__final-{args.final_template}"
        )
        evaluator_tag_default = default_tag
    elif args.workflow == "repeat-and-aggregate":
        default_tag = f"repeat-and-aggregate__{_short_model(args.evaluator_model)}__{args.template}"
        evaluator_tag_default = default_tag
    else:
        # single-stage default
        default_tag = f"single__{_short_model(args.evaluator_model)}__{args.template}"
        evaluator_tag_default = default_tag

    evaluator_tag = args.evaluator_tag or evaluator_tag_default
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.dump_dir:
        dump_dir = Path(args.dump_dir)
    else:
        base = OUTPUTS_ROOT / ("eval_runs_binary" if args.binary else "eval_runs") / str(args.data_version)
        dump_dir = base / f"{default_tag}__{timestamp}"
    dump_dir.mkdir(parents=True, exist_ok=True)

    if args.output_raw:
        output_raw = Path(args.output_raw)
    else:
        output_raw = dump_dir / "evaluator_raw.jsonl"
    output_raw.parent.mkdir(parents=True, exist_ok=True)

    if WORKFLOWS is None:
        raise SystemExit("Workflows package not found. Ensure evaluator_design/workflows exists.")
    if args.workflow not in WORKFLOWS:
        raise SystemExit(f"Unknown workflow: {args.workflow}. Available: {sorted(WORKFLOWS.keys())}")

    # Propagate computed defaults to the workflow
    args.dump_dir = str(dump_dir)
    args.output_raw = str(output_raw)
    args.evaluator_tag = evaluator_tag

    # Dispatch
    WORKFLOWS[args.workflow](args)


if __name__ == "__main__":
    main() 