from pathlib import Path
from typing import Any

from .utils import (
    EVAL_OUT_DIR,
    EVAL_OUT_DIR_BINARY,
    PROMPT_TEMPLATES_CONFIG,
    get_evaluator_gradings_dir,
    run_main,
    write_per_generator_eval,
    write_per_generator_eval_binary,
    build_steps_dataset_from_raw,
)


def run_workflow(args: Any) -> None:
    dataset_path = Path(args.dataset)
    multi_templates_config = Path(args.templates_config or PROMPT_TEMPLATES_CONFIG)
    if not args.steps_model:
        raise SystemExit("--steps-model is required for decompose-then-judge workflow")

    steps_dump_dir = Path(args.dump_dir) / "steps_stage"
    judge_dump_dir = Path(args.dump_dir) / "judge_stage"
    steps_dump_dir.mkdir(parents=True, exist_ok=True)
    judge_dump_dir.mkdir(parents=True, exist_ok=True)

    steps_raw_path = steps_dump_dir / "steps_raw.jsonl"
    steps_dataset_path = steps_dump_dir / "steps_dataset.jsonl"
    judge_raw_path = judge_dump_dir / "judge_raw.jsonl"

    # Stage 1: decomposition
    if not args.skip_generation:
        run_main(
            evaluator_model=args.steps_model,
            template_name=args.steps_template,
            dataset_path=dataset_path,
            template_config=multi_templates_config,
            output_path=steps_raw_path,
            max_examples=args.max_examples,
            no_cache=args.no_cache,
            processing_mode=args.processing_mode,
            n_sampling=args.n_sampling,
        )
    else:
        if not steps_raw_path.exists():
            raise SystemExit(f"--skip-generation specified but steps raw file not found: {steps_raw_path}")

    # Build the judge dataset by copying original records and attaching steps
    written = build_steps_dataset_from_raw(
        steps_raw_path=steps_raw_path,
        transformed_path=steps_dataset_path,
        dataset_path=dataset_path,
    )
    print(f"Built steps dataset with {written} items: {steps_dataset_path}")

    # Stage 2: judge
    run_main(
        evaluator_model=args.evaluator_model,
        template_name=args.judge_template,
        dataset_path=steps_dataset_path,
        template_config=multi_templates_config,
        output_path=judge_raw_path,
        max_examples=args.max_examples,
        no_cache=args.no_cache,
        processing_mode=args.processing_mode,
        n_sampling=args.n_sampling,
    )

    # Tag
    decomp_tag_suffix = f"via_steps_{args.steps_model}"
    judge_default_tag = f"{args.evaluator_model}__{args.judge_template}__{decomp_tag_suffix}"
    judge_evaluator_tag = args.evaluator_tag or judge_default_tag

    debug_report_path = judge_dump_dir / "parse_debug_report.json" if args.debug else None
    
    # Compute data-dir-specific output directory
    data_dir_path = getattr(args, "data_dir_path", None)
    is_binary = getattr(args, "binary", False)
    out_dir = get_evaluator_gradings_dir(data_dir_path, binary=is_binary) if data_dir_path else (EVAL_OUT_DIR_BINARY if is_binary else EVAL_OUT_DIR)
    
    if getattr(args, "binary", False):
        counts = write_per_generator_eval_binary(
            evaluator_tag=judge_evaluator_tag,
            raw_results_path=judge_raw_path,
            dataset_path=dataset_path,
            mirror_dir=out_dir,
            evaluator_model=args.evaluator_model,
            template_name=args.judge_template,
            debug=args.debug,
            debug_limit=args.debug_limit,
            debug_report_path=debug_report_path,
            use_raw_generator=args.use_raw_generator,
            steps_dataset_path=steps_dataset_path,
            assume_id_composite=True,
        )
    else:
        counts = write_per_generator_eval(
            evaluator_tag=judge_evaluator_tag,
            raw_results_path=judge_raw_path,
            dataset_path=dataset_path,
            mirror_dir=out_dir,
            evaluator_model=args.evaluator_model,
            template_name=args.judge_template,
            debug=args.debug,
            debug_limit=args.debug_limit,
            debug_report_path=debug_report_path,
            use_raw_generator=args.use_raw_generator,
            steps_dataset_path=steps_dataset_path,
            assume_id_composite=True,
        )
    print("Wrote per-generator eval files:")
    for gen, cnt in sorted(counts.items()):
        print(f"  {gen}: {cnt}")
    print(f"Raw dump dir: {args.dump_dir}")
    print(f"Evaluator gradings dir: {out_dir / judge_evaluator_tag}")
    print("Done.")


