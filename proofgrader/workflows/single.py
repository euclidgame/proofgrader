from pathlib import Path
from typing import Any, Dict

from .utils import (
    EVAL_OUT_DIR,
    EVAL_OUT_DIR_BINARY,
    run_main,
    write_per_generator_eval,
    write_per_generator_eval_binary,
    run_metrics,
    run_binary_metrics,
)


def run_workflow(args: Any) -> None:
    dataset_path = Path(args.dataset)
    template_config = Path(args.template_config)

    if not args.skip_generation:
        run_main(
            evaluator_model=args.evaluator_model,
            template_name=args.template,
            dataset_path=dataset_path,
            template_config=template_config,
            output_path=Path(args.output_raw),
            max_examples=args.max_examples,
            no_cache=args.no_cache,
            processing_mode=args.processing_mode,
            n_sampling=args.n_sampling,
        )
    else:
        if not Path(args.output_raw).exists():
            raise SystemExit(f"--skip-generation specified but raw file not found: {args.output_raw}")

    debug_report_path = Path(args.dump_dir) / "parse_debug_report.json" if args.debug else None
    if getattr(args, "binary", False):
        base_dir = EVAL_OUT_DIR_BINARY
        out_dir = base_dir / str(getattr(args, "data_version", "")) if getattr(args, "data_version", None) else base_dir
        counts = write_per_generator_eval_binary(
            evaluator_tag=args.evaluator_tag,
            raw_results_path=Path(args.output_raw),
            dataset_path=dataset_path,
            mirror_dir=out_dir,
            evaluator_model=args.evaluator_model,
            template_name=args.template,
            debug=args.debug,
            debug_limit=args.debug_limit,
            debug_report_path=debug_report_path,
            use_raw_generator=args.use_raw_generator,
            assume_id_composite=False,
        )
    else:
        base_dir = EVAL_OUT_DIR
        out_dir = base_dir / str(getattr(args, "data_version", "")) if getattr(args, "data_version", None) else base_dir
        counts = write_per_generator_eval(
            evaluator_tag=args.evaluator_tag,
            raw_results_path=Path(args.output_raw),
            dataset_path=dataset_path,
            mirror_dir=out_dir,
            evaluator_model=args.evaluator_model,
            template_name=args.template,
            debug=args.debug,
            debug_limit=args.debug_limit,
            debug_report_path=debug_report_path,
            use_raw_generator=args.use_raw_generator,
            assume_id_composite=False,
        )
    print("Wrote per-generator eval files:")
    for gen, cnt in sorted(counts.items()):
        print(f"  {gen}: {cnt}")
    print(f"Raw dump dir: {args.dump_dir}")
    print(f"Metrics input dir: {out_dir / args.evaluator_tag}")

    if getattr(args, "binary", False):
        run_binary_metrics(getattr(args, "data_version", None))
    else:
        run_metrics(getattr(args, "data_version", None))
    print("Done.")


