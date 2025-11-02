#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import csv


# Locations (version-aware)
ROOT = Path(__file__).resolve().parent
OUTPUTS_ROOT = ROOT / "outputs"
DATA_ROOT = ROOT / "data"
GT_PATH = ROOT / "evaluation_merged_binary.jsonl"
EVAL_DIR = OUTPUTS_ROOT / "evaluator_grades_binary"
OUT_DIR = OUTPUTS_ROOT / "reports_binary"

# Threshold used to derive labels from evaluator numeric scores
PRED_SCORE_THRESHOLD = 6.0


# IO helpers
def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def ensure_eval_dir() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)


# Core parsing
def load_binary_ground_truth() -> Dict[Tuple[str, str], int]:
    """Return mapping (problem_id, model_name) -> label (0/1)."""
    gt: Dict[Tuple[str, str], int] = {}
    rows = read_jsonl(GT_PATH)
    for r in rows:
        pid = r.get("problem_id")
        model = r.get("model_name")
        label = r.get("label")
        if pid is None or model is None or label is None:
            continue
        try:
            gt[(str(pid), str(model))] = int(label)
        except Exception:
            continue
    return gt


def parse_evaluator_file_binary(path: Path) -> Tuple[str, Dict[str, int]]:
    """Parse an evaluator per-generator file and return binary labels.

    Returns: (generator_name, mapping of problem_id -> predicted_label)
    """
    generator_name = path.stem.replace(".eval", "")
    rows = read_jsonl(path)
    mapping: Dict[str, int] = {}
    for r in rows:
        pid = r.get("id") or r.get("problem_id")
        if pid is None:
            continue
        # Prefer explicit label if present; else threshold score
        if r.get("label") is not None:
            try:
                label = 1 if int(r.get("label")) == 1 else 0
            except Exception:
                label = 0
        else:
            score = r.get("score")
            if score is None:
                continue
            try:
                label = 1 if float(score) >= PRED_SCORE_THRESHOLD else 0
            except Exception:
                label = 0
        mapping[str(pid)] = label
    return generator_name, mapping


# Metrics
def safe_div(num: float, den: float) -> float:
    return (num / den) if den else float("nan")


def compute_confusion(y_true: List[int], y_pred: List[int]) -> Tuple[int, int, int, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    return tp, fp, tn, fn


def compute_prf(tp: int, fp: int, tn: int, fn: int) -> Dict[str, float]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall) if precision == precision and recall == recall else float("nan")
    acc = safe_div(tp + tn, tp + fp + tn + fn)
    # Additional metrics
    tnr = safe_div(tn, tn + fp)  # specificity / true negative rate
    npv = safe_div(tn, tn + fn)  # negative predictive value
    return {
        "count": float(tp + fp + tn + fn),
        "tp": float(tp),
        "fp": float(fp),
        "tn": float(tn),
        "fn": float(fn),
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tnr": tnr,
        "npv": npv,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute binary evaluator metrics")
    parser.add_argument("--eval-dir", default=None, help="Directory containing per-evaluator folders with *.eval.jsonl files")
    parser.add_argument("--out-dir", default=None, help="Directory to write binary reports to")
    parser.add_argument("--gt-path", default=None, help="Path to evaluation_merged_binary.jsonl")
    parser.add_argument("--data-version", default=None, help="Data version to look under outputs/evaluator_grades_binary/<version> and outputs/reports_binary/<version>")
    args = parser.parse_args()

    global EVAL_DIR, OUT_DIR, GT_PATH
    if args.eval_dir:
        EVAL_DIR = Path(args.eval_dir)
    elif args.data_version:
        EVAL_DIR = OUTPUTS_ROOT / "evaluator_grades_binary" / str(args.data_version)

    if args.out_dir:
        OUT_DIR = Path(args.out_dir)
    elif args.data_version:
        OUT_DIR = OUTPUTS_ROOT / "reports_binary" / str(args.data_version)

    if args.gt_path:
        GT_PATH = Path(args.gt_path)
    elif args.data_version:
        # Prefer versioned ground-truth inside data/<version>/ if present
        candidate1 = DATA_ROOT / str(args.data_version) / "evaluation_merged_binary.jsonl"
        candidate2 = ROOT / f"evaluation_merged_binary_{args.data_version}.jsonl"
        if candidate1.exists():
            GT_PATH = candidate1
        elif candidate2.exists():
            GT_PATH = candidate2

    ensure_out_dir()
    ensure_eval_dir()
    gt = load_binary_ground_truth()

    per_evaluator_summary: Dict[str, Any] = {}
    per_evaluator_generator_rows: List[Dict[str, Any]] = []
    per_evaluator_source_rows: List[Dict[str, Any]] = []
    per_evaluator_overall_rows: List[Dict[str, Any]] = []
    per_evaluator_overall_macro_rows: List[Dict[str, Any]] = []
    # Stratified by true label (0/1)
    per_evaluator_true_label_rows: List[Dict[str, Any]] = []
    per_evaluator_per_gen_true_label_rows: List[Dict[str, Any]] = []

    for evaluator_folder in sorted(p for p in EVAL_DIR.iterdir() if p.is_dir()):
        evaluator_name = evaluator_folder.name

        generator_to_items: Dict[str, List[Tuple[str, int, int]]] = {}
        source_to_items: Dict[str, List[Tuple[str, int, int]]] = {}

        for file in sorted(evaluator_folder.glob("*.eval.jsonl")):
            if file.name.lower() == "prompt.txt" or file.name.lower().endswith("prompt.tex"):
                continue
            generator_name, pred_map = parse_evaluator_file_binary(file)

            items: List[Tuple[str, int, int]] = []  # (problem_id, true, pred)
            for problem_id, pred_label in pred_map.items():
                key = (problem_id, generator_name)
                if key in gt:
                    items.append((problem_id, gt[key], pred_label))
                    src = str(problem_id).split("-")[0]
                    source_to_items.setdefault(src, []).append((problem_id, gt[key], pred_label))
            if items:
                generator_to_items[generator_name] = items

        evaluator_report: Dict[str, Any] = {
            "evaluator": evaluator_name,
            "generators": {},
            "sources": {},
            "overall": {},
            "overall_macro": {},
        }

        # Macro components across generators
        macro_components: List[Dict[str, float]] = []

        overall_true: List[int] = []
        overall_pred: List[int] = []
        # Stratification holders
        # overall: label -> list[(t,p)]
        overall_bins: Dict[int, List[Tuple[int, int]]] = {}
        # per generator: generator -> label -> list[(t,p)]
        per_gen_bins: Dict[str, Dict[int, List[Tuple[int, int]]]] = {}

        for generator_name, items in sorted(generator_to_items.items()):
            y_true = [t for _, t, _ in items]
            y_pred = [p for _, _, p in items]
            tp, fp, tn, fn = compute_confusion(y_true, y_pred)
            metrics = compute_prf(tp, fp, tn, fn)

            per_evaluator_generator_rows.append({
                "evaluator": evaluator_name,
                "generator": generator_name,
                **metrics,
            })
            evaluator_report["generators"][generator_name] = metrics

            overall_true.extend(y_true)
            overall_pred.extend(y_pred)
            macro_components.append(metrics)

            # Stratify for this generator by true label (0/1)
            for (_, t, p) in items:
                lbl = int(1 if t == 1 else 0)
                overall_bins.setdefault(lbl, []).append((t, p))
                per_gen_bins.setdefault(generator_name, {}).setdefault(lbl, []).append((t, p))

        for source_name, items in sorted(source_to_items.items()):
            y_true = [t for _, t, _ in items]
            y_pred = [p for _, _, p in items]
            tp, fp, tn, fn = compute_confusion(y_true, y_pred)
            metrics = compute_prf(tp, fp, tn, fn)
            per_evaluator_source_rows.append({
                "evaluator": evaluator_name,
                "source": source_name,
                **metrics,
            })
            evaluator_report["sources"][source_name] = metrics

        # Overall pooled
        tp, fp, tn, fn = compute_confusion(overall_true, overall_pred)
        overall_metrics = compute_prf(tp, fp, tn, fn)
        evaluator_report["overall"] = overall_metrics
        per_evaluator_overall_rows.append({
            "evaluator": evaluator_name,
            **overall_metrics,
        })

        # Macro average across generators (equal weight per generator)
        def avg(field: str) -> float:
            values = [d[field] for d in macro_components if field in d]
            if not values:
                return float("nan")
            # Some may be NaN; include them in mean the same way as float math
            finite = [v for v in values if v == v]
            return (sum(finite) / len(finite)) if finite else float("nan")

        evaluator_report["overall_macro"] = {
            "num_generators": float(len(macro_components)),
            "macro_accuracy": avg("accuracy"),
            "macro_precision": avg("precision"),
            "macro_recall": avg("recall"),
            "macro_f1": avg("f1"),
        }
        per_evaluator_overall_macro_rows.append({
            "evaluator": evaluator_name,
            "num_generators": float(len(macro_components)),
            "macro_accuracy": evaluator_report["overall_macro"]["macro_accuracy"],
            "macro_precision": evaluator_report["overall_macro"]["macro_precision"],
            "macro_recall": evaluator_report["overall_macro"]["macro_recall"],
            "macro_f1": evaluator_report["overall_macro"]["macro_f1"],
        })

        per_evaluator_summary[evaluator_name] = evaluator_report

        # Append stratified rows (overall by true label)
        for lbl in sorted(overall_bins.keys()):
            pairs = overall_bins[lbl]
            if not pairs:
                continue
            y_t = [t for (t, _) in pairs]
            y_p = [p for (_, p) in pairs]
            tp, fp, tn, fn = compute_confusion(y_t, y_p)
            m = compute_prf(tp, fp, tn, fn)
            per_evaluator_true_label_rows.append({
                "evaluator": evaluator_name,
                "true_label": int(lbl),
                **m,
            })

        # Append stratified rows (per generator by true label)
        for gen_name in sorted(per_gen_bins.keys()):
            bin_map = per_gen_bins[gen_name]
            for lbl in sorted(bin_map.keys()):
                pairs = bin_map[lbl]
                if not pairs:
                    continue
                y_t = [t for (t, _) in pairs]
                y_p = [p for (_, p) in pairs]
                tp, fp, tn, fn = compute_confusion(y_t, y_p)
                m = compute_prf(tp, fp, tn, fn)
                per_evaluator_per_gen_true_label_rows.append({
                    "evaluator": evaluator_name,
                    "generator": gen_name,
                    "true_label": int(lbl),
                    **m,
                })

    # Write outputs
    write_json(OUT_DIR / "per_evaluator_summary_binary.json", per_evaluator_summary)

    gen_fields = [
        "evaluator", "generator", "count", "tp", "fp", "tn", "fn",
        "accuracy", "precision", "recall", "f1", "tnr", "npv",
    ]
    write_csv(OUT_DIR / "per_evaluator_per_generator.csv", per_evaluator_generator_rows, gen_fields)

    src_fields = [
        "evaluator", "source", "count", "tp", "fp", "tn", "fn",
        "accuracy", "precision", "recall", "f1", "tnr", "npv",
    ]
    write_csv(OUT_DIR / "per_evaluator_per_source.csv", per_evaluator_source_rows, src_fields)

    overall_fields = [
        "evaluator", "count", "tp", "fp", "tn", "fn",
        "accuracy", "precision", "recall", "f1", "tnr", "npv",
    ]
    write_csv(OUT_DIR / "per_evaluator_overall.csv", per_evaluator_overall_rows, overall_fields)

    overall_macro_fields = [
        "evaluator", "num_generators",
        "macro_accuracy", "macro_precision", "macro_recall", "macro_f1",
    ]
    write_csv(OUT_DIR / "per_evaluator_overall_macro.csv", per_evaluator_overall_macro_rows, overall_macro_fields)

    # Write stratified outputs by true label (0/1)
    strat_fields = [
        "evaluator", "true_label", "count", "tp", "fp", "tn", "fn",
        "accuracy", "precision", "recall", "f1", "tnr", "npv",
    ]
    if per_evaluator_true_label_rows:
        write_csv(OUT_DIR / "per_evaluator_by_true_label.csv", per_evaluator_true_label_rows, strat_fields)

    strat_gen_fields = [
        "evaluator", "generator", "true_label", "count", "tp", "fp", "tn", "fn",
        "accuracy", "precision", "recall", "f1", "tnr", "npv",
    ]
    if per_evaluator_per_gen_true_label_rows:
        write_csv(OUT_DIR / "per_evaluator_per_generator_by_true_label.csv", per_evaluator_per_gen_true_label_rows, strat_gen_fields)

    print(f"Wrote binary reports to: {OUT_DIR}")


if __name__ == "__main__":
    main()


