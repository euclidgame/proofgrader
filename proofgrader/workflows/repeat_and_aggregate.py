from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import Counter

from .utils import (
    EVAL_OUT_DIR,
    EVAL_OUT_DIR_BINARY,
    get_evaluator_gradings_dir,
    run_main,
    write_per_generator_eval,
    write_per_generator_eval_binary,
    read_jsonl,
)


def _aggregate_scores(values: List[float], mode: str) -> float:
    if not values:
        return None
    if mode == "mean":
        return sum(values) / len(values)
    if mode == "middle":
        # Discrete median: for even counts, take the lower middle element
        # to return an actual observed score (no averaging).
        ordered = sorted(values)
        n = len(ordered)
        mid = n // 2
        if n % 2 == 1:
            return ordered[mid]
        else:
            return ordered[mid - 1]
    if mode == "min":
        return min(values)
    if mode == "max":
        return max(values)
    if mode == "consistency":
        # Majority vote on discrete 0-7 scale: round to nearest int, choose most frequent
        # only if its support exceeds 2; otherwise return the mean of original values.
        ints: List[int] = []
        for v in values:
            try:
                iv = int(round(float(v)))
            except Exception:
                continue
            if 0 <= iv <= 7:
                ints.append(iv)
        if not ints:
            # Fallback to mean of raw values when rounding yields nothing valid
            return sum(values) / len(values)
        counts = Counter(ints)
        max_count = max(counts.values())
        if max_count > 2:
            # Tie-break toward the smaller integer to be conservative
            majority = min(k for k, c in counts.items() if c == max_count)
            return float(majority)
        # If no score occurs more than twice, average the raw values
        return sum(values) / len(values)
    # Fallback to mean
    return sum(values) / len(values)


def run_workflow(args: Any) -> None:
    dataset_path = Path(args.dataset)
    template_config = Path(args.template_config)

    num_runs = int(getattr(args, "num_runs", 1) or 1)
    template_name = getattr(args, "template", None) or getattr(args, "judge_template", None) or "basic"

    def _short_model(name: str) -> str:
        try:
            return str(name).strip().split("/")[-1]
        except Exception:
            return str(name)
    base_tag = f"repeat-and-aggregate__{_short_model(args.evaluator_model)}__{template_name}"

    # Data-dir-aware base dirs
    data_dir_path = getattr(args, "data_dir_path", None)
    is_binary = getattr(args, "binary", False)
    versioned_base_dir = get_evaluator_gradings_dir(data_dir_path, binary=is_binary) if data_dir_path else (EVAL_OUT_DIR_BINARY if is_binary else EVAL_OUT_DIR)

    per_run_tags: List[str] = []
    for i in range(num_runs):
        run_suffix = f"run{i + 1}"
        this_run_tag = f"{base_tag}__{run_suffix}"
        per_run_tags.append(this_run_tag)

        run_dump_dir = Path(args.dump_dir) / run_suffix
        run_dump_dir.mkdir(parents=True, exist_ok=True)
        run_raw_path = run_dump_dir / "evaluator_raw.jsonl"

        print(f"Running the {i+1}th time...")

        print(f"Using template: {template_name}")
        run_main(
            evaluator_model=args.evaluator_model,
            template_name=template_name,
            dataset_path=dataset_path,
            template_config=template_config,
            output_path=run_raw_path,
            max_examples=args.max_examples,
            no_cache=args.no_cache,
            processing_mode=args.processing_mode,
            n_sampling=args.n_sampling,
        )

        debug_report_path = run_dump_dir / "parse_debug_report.json" if args.debug else None
        if getattr(args, "binary", False):
            write_per_generator_eval_binary(
                evaluator_tag=this_run_tag,
                raw_results_path=run_raw_path,
                dataset_path=dataset_path,
                mirror_dir=versioned_base_dir,
                evaluator_model=args.evaluator_model,
                template_name=template_name,
                debug=args.debug,
                debug_limit=args.debug_limit,
                debug_report_path=debug_report_path,
                use_raw_generator=args.use_raw_generator,
                assume_id_composite=False,
            )
        else:
            write_per_generator_eval(
                evaluator_tag=this_run_tag,
                raw_results_path=run_raw_path,
                dataset_path=dataset_path,
                mirror_dir=versioned_base_dir,
                evaluator_model=args.evaluator_model,
                template_name=template_name,
                debug=args.debug,
                debug_limit=args.debug_limit,
                debug_report_path=debug_report_path,
                use_raw_generator=args.use_raw_generator,
                assume_id_composite=False,
            )

    # Aggregate across runs for all modes
    generator_to_files: Dict[str, List[Path]] = {}
    for tag in per_run_tags:
        run_dir = versioned_base_dir / tag
        if not run_dir.exists():
            continue
        for f in run_dir.glob("*.eval.jsonl"):
            gen = f.stem.replace(".eval", "")
            generator_to_files.setdefault(gen, []).append(f)

    # Select aggregation modes depending on binary or numeric
    if getattr(args, "binary", False):
        agg_modes = ["min", "max", "consistency"]
    else:
        # For 0-7 scale (numeric), support mean, min, max, "middle" (discrete median), and majority "consistency"
        agg_modes = ["mean", "middle", "min", "max", "consistency"]

    for aggregate_mode in agg_modes:
        agg_tag = f"{base_tag}__runs{num_runs}__{aggregate_mode}"
        agg_out_dir = versioned_base_dir / agg_tag
        agg_out_dir.mkdir(parents=True, exist_ok=True)

        for gen, files in sorted(generator_to_files.items()):
            # id -> lists across runs
            id_to_scores: Dict[str, List[float]] = {}
            id_to_labels: Dict[str, List[int]] = {}
            for fp in files:
                try:
                    for row in read_jsonl(fp):
                        pid = str(row.get("id")) if row.get("id") is not None else None
                        if not pid:
                            continue
                        if isinstance(row.get("score"), (int, float)):
                            id_to_scores.setdefault(pid, []).append(float(row.get("score")))
                        if row.get("label") is not None:
                            try:
                                id_to_labels.setdefault(pid, []).append(1 if int(row.get("label")) == 1 else 0)
                            except Exception:
                                pass
                except Exception:
                    continue

            out_path = agg_out_dir / f"{gen}.eval.jsonl"
            with out_path.open("w", encoding="utf-8") as out_f:
                for pid in sorted(set(list(id_to_scores.keys()) + list(id_to_labels.keys()))):
                    item: Dict[str, Any] = {"id": pid, "unique_id": f"{pid}::{gen}"}
                    # Binary label aggregation if available
                    if getattr(args, "binary", False) and pid in id_to_labels and id_to_labels[pid]:
                        labels = id_to_labels[pid]
                        if aggregate_mode == "min":
                            agg_label = 1 if all(l == 1 for l in labels) else 0
                        elif aggregate_mode == "max":
                            agg_label = 1 if any(l == 1 for l in labels) else 0
                        elif aggregate_mode == "consistency":
                            agg_label = 1 if sum(labels) >= (len(labels) / 2) else 0
                        else:
                            # For non-binary modes, fallback to score aggregation
                            scores = id_to_scores.get(pid, [])
                            agg_score = _aggregate_scores(scores, aggregate_mode)
                            item["score"] = agg_score
                            if agg_score is not None:
                                try:
                                    scf = float(agg_score)
                                    if 0.0 <= scf <= 1.0:
                                        item["label"] = 1 if scf >= 0.5 else 0
                                    else:
                                        item["label"] = 1 if scf >= 6.0 else 0
                                except Exception:
                                    item["label"] = 0
                            out_f.write(__import__("json").dumps(item, ensure_ascii=False) + "\n")
                            continue
                        item["label"] = int(agg_label)
                        # Also provide a simple score mirror for compatibility
                        item["score"] = float(agg_label)
                    else:
                        # Score aggregation path
                        scores = id_to_scores.get(pid, [])
                        agg_score = _aggregate_scores(scores, aggregate_mode)
                        item["score"] = agg_score
                        if getattr(args, "binary", False) and agg_score is not None:
                            try:
                                scf = float(agg_score)
                                if 0.0 <= scf <= 1.0:
                                    item["label"] = 1 if scf >= 0.5 else 0
                                else:
                                    item["label"] = 1 if scf >= 6.0 else 0
                            except Exception:
                                item["label"] = 0
                    out_f.write(__import__("json").dumps(item, ensure_ascii=False) + "\n")

        print("Aggregated per-generator eval files written to:", agg_out_dir)
        print(f"Raw dump dir (per run): {args.dump_dir}")
        print(f"Evaluator gradings dir: {agg_out_dir}")

    print("Done.")



