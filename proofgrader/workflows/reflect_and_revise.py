from pathlib import Path
from typing import Any

from .utils import (
    EVAL_OUT_DIR,
    PROMPT_TEMPLATES_CONFIG,
    run_main,
    write_per_generator_eval,
    run_metrics,
    build_augmented_dataset_from_raw,
)


def run_workflow(args: Any) -> None:
    dataset_path = Path(args.dataset)
    templates_config = Path(args.templates_config or PROMPT_TEMPLATES_CONFIG)

    # Directories
    a_dir = Path(args.dump_dir) / "stage_a_initial_eval"
    b_dir = Path(args.dump_dir) / "stage_b_self_critique"
    c_dir = Path(args.dump_dir) / "stage_c_final_verdict"
    a_dir.mkdir(parents=True, exist_ok=True)
    b_dir.mkdir(parents=True, exist_ok=True)
    c_dir.mkdir(parents=True, exist_ok=True)

    a_raw = a_dir / "initial_raw.jsonl"
    a_dataset_with_report = a_dir / "dataset_with_initial_report.jsonl"
    b_raw = b_dir / "critique_raw.jsonl"
    b_dataset_with_critique = b_dir / "dataset_with_critique.jsonl"
    c_raw = c_dir / "final_raw.jsonl"

    # Resolve per-stage models (fallback to evaluator_model if not provided)
    init_model = getattr(args, "init_model", None) or args.evaluator_model
    critic_model = getattr(args, "critic_model", None) or args.evaluator_model
    final_model = getattr(args, "final_model", None) or args.evaluator_model

    # Step A: Initial Evaluation using baseline template (args.template)
    if not args.skip_generation:
        run_main(
            evaluator_model=init_model,
            template_name=args.template,
            dataset_path=dataset_path,
            template_config=templates_config,
            output_path=a_raw,
            max_examples=args.max_examples,
            no_cache=args.no_cache,
            processing_mode=args.processing_mode,
            n_sampling=args.n_sampling,
        )
    else:
        if not a_raw.exists():
            raise SystemExit(f"--skip-generation specified but initial raw file not found: {a_raw}")

    # Build dataset with the initial report attached
    written_a = build_augmented_dataset_from_raw(
        source_raw_path=a_raw,
        transformed_path=a_dataset_with_report,
        dataset_path=dataset_path,
        field_name="initial_report",
    )
    print(f"Built dataset_with_initial_report with {written_a} items: {a_dataset_with_report}")

    # Write per-generator evaluator grades for Stage A (initial run)
    try:
        # Version-aware mirror directory for outputs
        a_base_dir = EVAL_OUT_DIR
        a_mirror_dir = a_base_dir / str(getattr(args, "data_version", "")) if getattr(args, "data_version", None) else a_base_dir
        # Use a stage-specific tag to avoid clobbering Stage C outputs
        a_tag = (
            f"reflect-and-revise__A-{init_model}__init-{args.template}__stage_a_initial"
            if not getattr(args, "evaluator_tag", None)
            else f"{args.evaluator_tag}__stage_a_initial"
        )
        a_debug_report = a_dir / "parse_debug_report_stage_a.json" if getattr(args, "debug", False) else None
        a_counts = write_per_generator_eval(
            evaluator_tag=a_tag,
            raw_results_path=a_raw,
            dataset_path=dataset_path,
            mirror_dir=a_mirror_dir,
            evaluator_model=init_model,
            template_name=args.template,
            debug=getattr(args, "debug", False),
            debug_limit=getattr(args, "debug_limit", 5),
            debug_report_path=a_debug_report,
            use_raw_generator=getattr(args, "use_raw_generator", False),
            # Stage A IDs are base problem IDs; map generators via metadata/dataset
            assume_id_composite=False,
        )
        print("Wrote Stage A per-generator eval files:")
        for gen, cnt in sorted(a_counts.items()):
            print(f"  {gen}: {cnt}")
        print(f"Stage A metrics input dir: {a_mirror_dir / a_tag}")
    except Exception as e:
        print(f"Warning: failed to write Stage A per-generator eval files: {e}")

    # Step B: Self-Critique using critic template
    critic_template = getattr(args, "critic_template", None) or "critic_reflection"
    run_main(
        evaluator_model=critic_model,
        template_name=critic_template,
        dataset_path=a_dataset_with_report,
        template_config=templates_config,
        output_path=b_raw,
        max_examples=args.max_examples,
        no_cache=args.no_cache,
        processing_mode=args.processing_mode,
        n_sampling=args.n_sampling,
    )

    # Build dataset with the critique attached
    written_b = build_augmented_dataset_from_raw(
        source_raw_path=b_raw,
        transformed_path=b_dataset_with_critique,
        dataset_path=a_dataset_with_report,
        field_name="critique",
    )
    print(f"Built dataset_with_critique with {written_b} items: {b_dataset_with_critique}")

    # Write per-generator evaluator grades for Stage B (self-critique)
    try:
        b_base_dir = EVAL_OUT_DIR
        b_mirror_dir = b_base_dir / str(getattr(args, "data_version", "")) if getattr(args, "data_version", None) else b_base_dir
        b_tag = (
            f"reflect-and-revise__B-{critic_model}__critic-{critic_template}__stage_b_critique"
            if not getattr(args, "evaluator_tag", None)
            else f"{args.evaluator_tag}__stage_b_critique"
        )
        b_debug_report = b_dir / "parse_debug_report_stage_b.json" if getattr(args, "debug", False) else None
        b_counts = write_per_generator_eval(
            evaluator_tag=b_tag,
            raw_results_path=b_raw,
            # Use the dataset fed into Stage B so IDs match; it already carries composite IDs
            dataset_path=a_dataset_with_report,
            mirror_dir=b_mirror_dir,
            evaluator_model=critic_model,
            template_name=critic_template,
            debug=getattr(args, "debug", False),
            debug_limit=getattr(args, "debug_limit", 5),
            debug_report_path=b_debug_report,
            use_raw_generator=getattr(args, "use_raw_generator", False),
            steps_dataset_path=a_dataset_with_report,
            assume_id_composite=True,
        )
        print("Wrote Stage B per-generator eval files:")
        for gen, cnt in sorted(b_counts.items()):
            print(f"  {gen}: {cnt}")
        print(f"Stage B metrics input dir: {b_mirror_dir / b_tag}")
    except Exception as e:
        print(f"Warning: failed to write Stage B per-generator eval files: {e}")

    # Step C: Final Verdict using final template
    final_template = getattr(args, "final_template", None) or "final_verdict_from_critique"
    run_main(
        evaluator_model=final_model,
        template_name=final_template,
        dataset_path=b_dataset_with_critique,
        template_config=templates_config,
        output_path=c_raw,
        max_examples=args.max_examples,
        no_cache=args.no_cache,
        processing_mode=args.processing_mode,
        n_sampling=args.n_sampling,
    )

    # Tag and parse final outputs
    default_tag = (
        f"reflect-and-revise__A-{init_model}__init-{args.template}__"
        f"B-{critic_model}__critic-{critic_template}__"
        f"C-{final_model}__final-{final_template}"
    )
    evaluator_tag = args.evaluator_tag or default_tag

    # Version-aware mirror directory
    base_dir = EVAL_OUT_DIR
    mirror_dir = base_dir / str(getattr(args, "data_version", "")) if getattr(args, "data_version", None) else base_dir

    debug_report_path = c_dir / "parse_debug_report.json" if args.debug else None
    counts = write_per_generator_eval(
        evaluator_tag=evaluator_tag,
        raw_results_path=c_raw,
        dataset_path=dataset_path,
        mirror_dir=mirror_dir,
        evaluator_model=final_model,
        template_name=final_template,
        debug=args.debug,
        debug_limit=args.debug_limit,
        debug_report_path=debug_report_path,
        use_raw_generator=args.use_raw_generator,
        steps_dataset_path=b_dataset_with_critique,
        assume_id_composite=True,
    )
    print("Wrote per-generator eval files:")
    for gen, cnt in sorted(counts.items()):
        print(f"  {gen}: {cnt}")
    print(f"Raw dump dir: {args.dump_dir}")
    print(f"Metrics input dir: {mirror_dir / evaluator_tag}")

    run_metrics(getattr(args, "data_version", None))
    print("Done.")


