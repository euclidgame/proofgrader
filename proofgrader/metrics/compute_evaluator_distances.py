#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import csv
import random

# Input locations (can be overridden via CLI)
SCRIPT_DIR = Path(__file__).resolve().parent  # proofgrader/metrics/
PROOFGRADER_DIR = SCRIPT_DIR.parent  # proofgrader/
PROJECT_ROOT = PROOFGRADER_DIR.parent  # project root

# Add project root to Python path for imports
sys.path.insert(0, str(PROJECT_ROOT))
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
MERGED_PATH = DATA_ROOT / "expert_gradings.jsonl"  # Default ground truth file
EVAL_DIR = OUTPUTS_ROOT / "evaluator_grades"
OUT_DIR = OUTPUTS_ROOT / "reports"

# Helper functions for data-dir-specific paths
def get_evaluator_gradings_dir(data_dir: Path, binary: bool = False) -> Path:
    """Get evaluator gradings directory for a data directory."""
    eval_outputs = data_dir / "evaluation_outputs"
    subdir = "evaluator_gradings_binary" if binary else "evaluator_gradings"
    return eval_outputs / subdir

def get_metrics_dir(data_dir: Path) -> Path:
    """Get metrics output directory for a data directory."""
    return data_dir / "evaluation_outputs" / "metrics"

# Utilities

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def safe_rmse(values: List[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def pearsonr(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n == 0 or n != len(ys):
        return float("nan")
    mx = safe_mean(xs)
    my = safe_mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return float("nan")
    return num / (denx * deny)


def rank(values: List[float]) -> List[float]:
    # Average ranks for ties
    pairs = sorted((v, i) for i, v in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + j + 2) / 2.0  # 1-based ranks
        for k in range(i, j + 1):
            ranks[pairs[k][1]] = avg_rank
        i = j + 1
    return ranks


def spearmanr(xs: List[float], ys: List[float]) -> float:
    if len(xs) == 0 or len(xs) != len(ys):
        return float("nan")
    rx = rank(xs)
    ry = rank(ys)
    return pearsonr(rx, ry)


def kendall_tau_b(xs: List[float], ys: List[float]) -> float:
    """
    Compute Kendall's tau-b correlation coefficient between two sequences with tie handling.

    - Returns nan if lengths mismatch or < 2 or if denominator is zero due to all ties.
    - Treats equal values in xs or ys as ties.
    """
    n = len(xs)
    if n != len(ys) or n < 2:
        return float("nan")

    # Count concordant, discordant, ties in x, ties in y
    concordant = 0
    discordant = 0
    ties_x = 0
    ties_y = 0

    for i in range(n - 1):
        xi = xs[i]
        yi = ys[i]
        for j in range(i + 1, n):
            xj = xs[j]
            yj = ys[j]
            dx = xi - xj
            dy = yi - yj
            if dx == 0 and dy == 0:
                # tied in both, does not affect C/D, but contributes to ties in both implicitly
                ties_x += 1
                ties_y += 1
            elif dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            else:
                prod = dx * dy
                if prod > 0:
                    concordant += 1
                elif prod < 0:
                    discordant += 1

    # Tau-b denominator accounts for ties
    c = float(concordant)
    d = float(discordant)
    tx = float(ties_x)
    ty = float(ties_y)
    denom = math.sqrt((c + d + tx) * (c + d + ty))
    if denom == 0.0:
        return float("nan")
    return (c - d) / denom


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def ensure_eval_dir() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# Core logic

# Default tolerance for within-tolerance accuracy (|pred - true| <= TOLERANCE)
DEFAULT_TOLERANCE = 1.0

def extract_year_from_problem_id(problem_id: str) -> str:
    """Extract year from problem_id like 'APMO-2022-1' -> '2022'"""
    parts = str(problem_id).split("-")
    for part in parts:
        if len(part) == 4 and part.isdigit():
            return part
    return "unknown"

def load_merged_scores() -> Dict[Tuple[str, str], float]:
    # key: (problem_id, model_name)
    merged_rows = read_jsonl(MERGED_PATH)
    merged_scores: Dict[Tuple[str, str], float] = {}
    for r in merged_rows:
        problem_id = r.get("problem_id")
        model_name = r.get("model_name")
        score = r.get("score")
        if problem_id is None or model_name is None or score is None:
            continue
        merged_scores[(str(problem_id), str(model_name))] = float(score)
    return merged_scores


def parse_evaluator_file(path: Path) -> Tuple[str, Dict[str, float]]:
    # returns (generator_name, mapping of problem_id -> score)
    rows = read_jsonl(path)
    
    # Try to get generator name from the data first (full model name)
    # Fallback to filename (sanitized name)
    generator_name = None
    if rows:
        # Check first record for generator field
        first_record = rows[0]
        generator_name = first_record.get('generator') or first_record.get('model')
    
    # Fallback to filename if not found in data
    if not generator_name:
        generator_name = path.stem.replace(".eval", "")
    
    mapping: Dict[str, float] = {}
    for r in rows:
        problem_id = r.get("id") or r.get("problem_id")
        score = r.get("score")
        if problem_id is None or score is None:
            continue
        mapping[str(problem_id)] = float(score)
    return generator_name, mapping


def compute_metrics(y_true: List[float], y_pred: List[float], tolerance: float = DEFAULT_TOLERANCE) -> Dict[str, float]:
    diffs = [p - t for t, p in zip(y_true, y_pred)]
    abs_diffs = [abs(d) for d in diffs]
    # within-tolerance accuracy: fraction of examples with |error| <= tolerance
    wta = (sum(1 for a in abs_diffs if a <= tolerance) / len(abs_diffs)) if abs_diffs else float("nan")
    return {
        "count": float(len(diffs)),
        "mae": safe_mean(abs_diffs),
        "rmse": safe_rmse(diffs),
        "bias": safe_mean(diffs),  # mean(pred - true)
        "pearson": pearsonr(y_true, y_pred),
        "spearman": spearmanr(y_true, y_pred),
        "wta": wta,
        "min_diff": min(diffs) if diffs else float("nan"),
        "max_diff": max(diffs) if diffs else float("nan"),
    }


def compute_problem_std_map() -> Dict[str, float]:
    # Compute per-problem std dev of merged scores across models
    merged_rows = read_jsonl(MERGED_PATH)
    by_problem: Dict[str, List[float]] = {}
    for r in merged_rows:
        pid = str(r.get("problem_id"))
        sc = r.get("score")
        if pid is None or sc is None:
            continue
        by_problem.setdefault(pid, []).append(float(sc))
    stds: Dict[str, float] = {}
    for pid, scores in by_problem.items():
        if len(scores) <= 1:
            stds[pid] = 1.0
            continue
        m = safe_mean(scores)
        var = safe_mean([(s - m) ** 2 for s in scores])
        std = math.sqrt(var)
        stds[pid] = std if std > 0 else 1.0
    return stds


def compute_pairwise_order_stats(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    """
    Compute how well the predicted scores preserve the pairwise order induced by true scores.

    For n items, consider all pairs (i, j), i < j. We count a pair as comparable if the
    true scores are not tied: y_true[i] != y_true[j]. A pair is correct if the predicted
    order matches the true order, i.e., (y_true[i] - y_true[j]) * (y_pred[i] - y_pred[j]) > 0.
    Predicted ties (y_pred[i] == y_pred[j]) on comparable pairs are treated as incorrect.
    Returns counts and accuracy over comparable pairs.
    """
    n = len(y_true)
    if n != len(y_pred) or n < 2:
        return {
            "num_items": float(n),
            "num_pairs": 0.0,
            "comparable_pairs": 0.0,
            "correct_pairs": 0.0,
            "order_acc": float("nan"),
        }
    total_pairs = n * (n - 1) // 2
    comparable = 0
    correct = 0
    for i in range(n):
        ti = y_true[i]
        pi = y_pred[i]
        for j in range(i + 1, n):
            tj = y_true[j]
            pj = y_pred[j]
            t_diff = ti - tj
            if t_diff == 0:
                continue  # skip true ties
            p_diff = pi - pj
            comparable += 1
            if p_diff == 0:
                # treat predicted tie as incorrect on a comparable pair
                continue
            if t_diff * p_diff > 0:
                correct += 1
    acc = (correct / comparable) if comparable > 0 else float("nan")
    return {
        "num_items": float(n),
        "num_pairs": float(total_pairs),
        "comparable_pairs": float(comparable),
        "correct_pairs": float(correct),
        "order_acc": acc,
    }


def _group_by_problem(items: List[Tuple[str, float, float]]) -> Dict[str, List[Tuple[float, float]]]:
    by_problem: Dict[str, List[Tuple[float, float]]] = {}
    for pid, t, p in items:
        by_problem.setdefault(str(pid), []).append((float(t), float(p)))
    return by_problem


def _macro_from_problem_metrics(problem_to_pairs: Dict[str, List[Tuple[float, float]]]) -> Dict[str, float]:
    # Compute metrics per problem then macro-average over problems (unweighted mean over problems)
    per_problem_metrics: List[Dict[str, float]] = []
    for pairs in problem_to_pairs.values():
        y_t = [t for (t, _) in pairs]
        y_p = [p for (_, p) in pairs]
        per_problem_metrics.append(compute_metrics(y_t, y_p))
    def avg_field(field: str) -> float:
        vals = [m.get(field) for m in per_problem_metrics if isinstance(m.get(field), (int, float)) and not math.isnan(float(m.get(field)))]
        return safe_mean([float(v) for v in vals]) if vals else float("nan")
    return {
        "macro_problem_mae": avg_field("mae"),
        "macro_problem_rmse": avg_field("rmse"),
        "macro_problem_bias": avg_field("bias"),
        "macro_problem_pearson": avg_field("pearson"),
        "macro_problem_spearman": avg_field("spearman"),
        "macro_problem_wta": avg_field("wta"),
        "macro_problem_count": float(len(per_problem_metrics)),
    }


def _macro_from_problem_metrics_normalized(problem_to_pairs: Dict[str, List[Tuple[float, float]]], problem_std: Dict[str, float]) -> Dict[str, float]:
    # Normalize per problem then compute per-problem metrics and macro-average them
    per_problem_metrics: List[Dict[str, float]] = []
    for pid, pairs in problem_to_pairs.items():
        std = float(problem_std.get(str(pid), 1.0) or 1.0)
        y_t = [t / std for (t, _) in pairs]
        y_p = [p / std for (_, p) in pairs]
        per_problem_metrics.append(compute_metrics(y_t, y_p))
    def avg_field(field: str) -> float:
        vals = [m.get(field) for m in per_problem_metrics if isinstance(m.get(field), (int, float)) and not math.isnan(float(m.get(field)))]
        return safe_mean([float(v) for v in vals]) if vals else float("nan")
    return {
        "macro_norm_mae": avg_field("mae"),
        "macro_norm_rmse": avg_field("rmse"),
        "macro_norm_bias": avg_field("bias"),
        "macro_norm_pearson": avg_field("pearson"),
        "macro_norm_spearman": avg_field("spearman"),
        "macro_norm_wta": avg_field("wta"),
        "macro_norm_count": float(len(per_problem_metrics)),
    }


def _percentile(sorted_values: List[float], q: float) -> float:
    # q in [0,1]
    if not sorted_values:
        return float("nan")
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_values[lo])
    frac = pos - lo
    return float(sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac)


def _bootstrap_macro_ci_from_problem_metrics(
    problem_to_pairs: Dict[str, List[Tuple[float, float]]],
    *,
    problem_std: Dict[str, float] = None,
    normalized: bool = False,
    rng: random.Random,
    num_bootstrap: int,
    ci_level: float = 0.95,
    fields: List[str] = None,
) -> Dict[str, float]:
    # Build per-problem metrics
    per_problem_metrics: List[Dict[str, float]] = []
    for pid, pairs in problem_to_pairs.items():
        if normalized:
            std = float((problem_std or {}).get(str(pid), 1.0) or 1.0)
            y_t = [t / std for (t, _) in pairs]
            y_p = [p / std for (_, p) in pairs]
        else:
            y_t = [t for (t, _) in pairs]
            y_p = [p for (_, p) in pairs]
        per_problem_metrics.append(compute_metrics(y_t, y_p))

    fields = fields or ["mae", "rmse", "bias", "pearson", "spearman", "wta"]
    # Initialize containers
    field_to_samples: Dict[str, List[float]] = {f: [] for f in fields}

    if num_bootstrap <= 0 or len(per_problem_metrics) == 0:
        return {}

    q_lo = (1.0 - ci_level) / 2.0
    q_hi = 1.0 - q_lo

    # Pre-extract values per field for speed
    per_field_values: Dict[str, List[float]] = {}
    for f in fields:
        vals = [m.get(f) for m in per_problem_metrics if isinstance(m.get(f), (int, float)) and not math.isnan(float(m.get(f)))]
        per_field_values[f] = [float(v) for v in vals]

    # If a field has no values at all across problems, skip bootstrapping it
    active_fields = [f for f in fields if per_field_values.get(f)]
    if not active_fields:
        return {}

    # Bootstrap by resampling valid values per field with replacement (complete-case bootstrap)
    for _ in range(int(num_bootstrap)):
        for f in active_fields:
            vals_f = per_field_values[f]
            m = len(vals_f)
            if m == 0:
                field_to_samples[f].append(float("nan"))
                continue
            # sample m values with replacement
            total = 0.0
            for _ in range(m):
                total += vals_f[rng.randrange(0, m)]
            field_to_samples[f].append(total / m)

    # Compute percentiles
    out: Dict[str, float] = {}
    for f in active_fields:
        vals = [v for v in field_to_samples[f] if isinstance(v, (int, float)) and not math.isnan(float(v))]
        if not vals:
            continue
        vals.sort()
        lo = _percentile(vals, q_lo)
        hi = _percentile(vals, q_hi)
        prefix = "macro_norm_" if normalized else "macro_problem_"
        out[f"{prefix}{f}_lo"] = lo
        out[f"{prefix}{f}_hi"] = hi
    return out


def main() -> None:
    # Parse optional CLI overrides for versioning/paths
    parser = argparse.ArgumentParser(description="Compute evaluator distance metrics")
    parser.add_argument("--eval-dir", default=None, help="Directory containing per-evaluator folders with *.eval.jsonl files")
    parser.add_argument("--out-dir", default=None, help="Directory to write reports to")
    parser.add_argument("--merged-path", default=None, help="Path to expert_gradings.jsonl with true scores per (problem_id, model)")
    parser.add_argument("--data-dir", default=None, help="Data directory path (e.g., data/test_data). If set, defaults adjust to <data-dir>/evaluation_outputs/{evaluator_gradings,metrics}")
    parser.add_argument("--bootstrap-iters", type=int, default=0, help="If >0, add percentile CIs via problem-level bootstrap with this many resamples")
    parser.add_argument("--bootstrap-ci", type=float, default=0.95, help="CI level for bootstrap, e.g., 0.95 for 95%")
    parser.add_argument("--bootstrap-seed", type=int, default=13, help="Random seed for bootstrap resampling")
    parser.add_argument("--bootstrap-metrics", default="mae,rmse,bias,pearson,spearman,wta", help="Comma-separated macro metrics to bootstrap (subset of mae,rmse,bias,pearson,spearman,wta)")
    parser.add_argument("--bootstrap-scope", default="all", help="Bootstrap scope: one of all,overall,generator,source")
    parser.add_argument("--skip-disagreement", action="store_true", help="Skip computing disagreement_per_item.csv (speeds up run)")
    parser.add_argument("--skip-order", action="store_true", help="Skip computing order-preservation analyses (speeds up run)")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verify-vs-solve analysis (speeds up run)")
    args = parser.parse_args()

    global MERGED_PATH, EVAL_DIR, OUT_DIR
    
    # When data-dir is specified, adjust all paths to be relative to data-dir/evaluation_outputs/
    if args.data_dir:
        data_dir_path = Path(args.data_dir)
        
        # Set paths relative to data directory using local helper functions
        EVAL_DIR = Path(args.eval_dir) if args.eval_dir else get_evaluator_gradings_dir(data_dir_path)
        OUT_DIR = Path(args.out_dir) if args.out_dir else get_metrics_dir(data_dir_path)
        
        # Ground truth: look in data directory
        if args.merged_path:
            MERGED_PATH = Path(args.merged_path)
        else:
            # Try expert_gradings.jsonl first, then evaluation_merged.jsonl
            candidate_expert = data_dir_path / "expert_gradings.jsonl"
            candidate_merged = data_dir_path / "evaluation_merged.jsonl"
            
            if candidate_expert.exists():
                MERGED_PATH = candidate_expert
            elif candidate_merged.exists():
                MERGED_PATH = candidate_merged
            else:
                # Default to expert_gradings.jsonl (will error if not found)
                MERGED_PATH = candidate_expert
    else:
        # No data-dir: use explicit paths or defaults
        EVAL_DIR = Path(args.eval_dir) if args.eval_dir else EVAL_DIR
        OUT_DIR = Path(args.out_dir) if args.out_dir else OUT_DIR
        MERGED_PATH = Path(args.merged_path) if args.merged_path else MERGED_PATH

    ensure_out_dir()
    ensure_eval_dir()
    
    print(f"Ground truth file: {MERGED_PATH}")
    print(f"Evaluation directory: {EVAL_DIR}")
    print(f"Output directory: {OUT_DIR}")
    
    merged = load_merged_scores()
    problem_std = compute_problem_std_map()

    # Bootstrap config
    bootstrap_iters = int(args.bootstrap_iters) if hasattr(args, "bootstrap_iters") and args.bootstrap_iters is not None else 0
    bootstrap_ci = float(args.bootstrap_ci) if hasattr(args, "bootstrap_ci") and args.bootstrap_ci is not None else 0.95
    bootstrap_rng = random.Random(int(args.bootstrap_seed) if hasattr(args, "bootstrap_seed") and args.bootstrap_seed is not None else 13)
    bootstrap_metrics = [s.strip() for s in str(getattr(args, "bootstrap_metrics", "")).split(",") if s.strip()]
    bootstrap_scope = str(getattr(args, "bootstrap_scope", "all") or "all").lower()

    per_evaluator_summary: Dict[str, Any] = {}
    per_evaluator_generator_rows: List[Dict[str, Any]] = []
    per_evaluator_source_rows: List[Dict[str, Any]] = []
    per_evaluator_overall_rows: List[Dict[str, Any]] = []
    per_evaluator_overall_norm_rows: List[Dict[str, Any]] = []
    per_evaluator_overall_macro_rows: List[Dict[str, Any]] = []
    # Stratified by true-score bin (0-7)
    per_evaluator_true_bin_rows: List[Dict[str, Any]] = []
    per_evaluator_per_gen_true_bin_rows: List[Dict[str, Any]] = []

    # Cross-evaluator accumulation for disagreement per item (problem_id, generator)
    # key: (problem_id, generator) -> List[(evaluator_name, true, pred)]
    cross_eval_items: Dict[Tuple[str, str], List[Tuple[str, float, float]]] = {}

    # Per-evaluator, per-problem accumulation across generators to assess verification ability
    # evaluator_name -> problem_id -> List[(true, pred)]
    per_evaluator_problem: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}

    # Iterate evaluator folders
    for evaluator_folder in sorted(p for p in EVAL_DIR.iterdir() if p.is_dir()):
        evaluator_name = evaluator_folder.name

        # For per-generator storage, include problem_id to allow normalization
        generator_to_items: Dict[str, List[Tuple[str, float, float]]] = {}
        # Aggregate per-source across all generators
        source_to_items: Dict[str, List[Tuple[str, float, float]]] = {}

        # Iterate generator files (*.eval.jsonl)
        for file in sorted(evaluator_folder.glob("*.eval.jsonl")):
            if file.name.lower() == "prompt.txt" or file.name.lower().endswith("prompt.tex"):
                continue
            generator_name, eval_map = parse_evaluator_file(file)

            items: List[Tuple[str, float, float]] = []  # (problem_id, true, pred)
            for problem_id, eval_score in eval_map.items():
                key = (problem_id, generator_name)
                if key in merged:
                    items.append((problem_id, merged[key], eval_score))
                    # also aggregate per-source
                    src = str(problem_id).split("-")[0]
                    source_to_items.setdefault(src, []).append((problem_id, merged[key], eval_score))
            if items:
                generator_to_items[generator_name] = items
                # Cross-evaluator per-item accumulation
                for pid, t, p in items:
                    cross_eval_items.setdefault((str(pid), generator_name), []).append((evaluator_name, t, p))
                    # Per-evaluator per-problem accumulation for verification analysis
                    per_evaluator_problem.setdefault(evaluator_name, {}).setdefault(str(pid), []).append((t, p))

        # Compute per-generator and overall metrics (both raw and problem-normalized)
        evaluator_report: Dict[str, Any] = {
            "evaluator": evaluator_name,
            "generators": {},
            "sources": {},
            "overall": {},
            "overall_normalized": {},
            "overall_macro": {},
        }

        overall_true: List[float] = []
        overall_pred: List[float] = []
        overall_true_norm: List[float] = []  # values after scaling by problem std (y_true/std)
        overall_pred_norm: List[float] = []

        # For macro-averaging across generators (unweighted)
        macro_components: List[Dict[str, float]] = []

        # Prepare stratification holders
        def _true_bin(v: float) -> int:
            try:
                b = int(math.floor(float(v)))
            except Exception:
                b = 0
            return max(0, min(7, b))

        # overall: bin -> list[(t,p)]
        overall_bins: Dict[int, List[Tuple[float, float]]] = {}
        # per generator: generator -> bin -> list[(t,p)]
        per_gen_bins: Dict[str, Dict[int, List[Tuple[float, float]]]] = {}

        for generator_name, items in sorted(generator_to_items.items()):
            y_true = [t for _, t, _ in items]
            y_pred = [p for _, _, p in items]
            metrics = compute_metrics(y_true, y_pred)

            # Normalized by problem std
            y_true_n: List[float] = []
            y_pred_n: List[float] = []
            for pid, t, p in items:
                std = problem_std.get(str(pid), 1.0)
                y_true_n.append(t / std)
                y_pred_n.append(p / std)
            norm_metrics = compute_metrics(y_true_n, y_pred_n)

            # Macro over problems for this generator
            by_problem = _group_by_problem(items)
            macro_problem = _macro_from_problem_metrics(by_problem)
            macro_problem_norm = _macro_from_problem_metrics_normalized(by_problem, problem_std)

            # Bootstrap CIs for macro-by-problem metrics (raw and normalized)
            gen_macro_ci = _bootstrap_macro_ci_from_problem_metrics(
                by_problem, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
            ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "generator")) else {}
            gen_macro_norm_ci = _bootstrap_macro_ci_from_problem_metrics(
                by_problem, problem_std=problem_std, normalized=True, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
            ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "generator")) else {}

            # Enrich per-generator row
            per_evaluator_generator_rows.append({
                "evaluator": evaluator_name,
                "generator": generator_name,
                **metrics,
                "norm_wta": norm_metrics.get("wta"),
                "norm_mae": norm_metrics.get("mae"),
                "norm_rmse": norm_metrics.get("rmse"),
                "norm_bias": norm_metrics.get("bias"),
                "macro_problem_mae": macro_problem.get("macro_problem_mae"),
                "macro_problem_rmse": macro_problem.get("macro_problem_rmse"),
                "macro_problem_bias": macro_problem.get("macro_problem_bias"),
                "macro_problem_pearson": macro_problem.get("macro_problem_pearson"),
                "macro_problem_spearman": macro_problem.get("macro_problem_spearman"),
                "macro_problem_wta": macro_problem.get("macro_problem_wta"),
                "macro_norm_mae": macro_problem_norm.get("macro_norm_mae"),
                "macro_norm_rmse": macro_problem_norm.get("macro_norm_rmse"),
                "macro_norm_bias": macro_problem_norm.get("macro_norm_bias"),
                "macro_norm_pearson": macro_problem_norm.get("macro_norm_pearson"),
                "macro_norm_spearman": macro_problem_norm.get("macro_norm_spearman"),
                "macro_norm_wta": macro_problem_norm.get("macro_norm_wta"),
                **gen_macro_ci,
                **gen_macro_norm_ci,
            })

            evaluator_report["generators"][generator_name] = {
                **metrics,
                "normalized": {
                    "wta": norm_metrics.get("wta"),
                    "mae": norm_metrics.get("mae"),
                    "rmse": norm_metrics.get("rmse"),
                    "bias": norm_metrics.get("bias"),
                    "pearson": norm_metrics.get("pearson"),
                    "spearman": norm_metrics.get("spearman"),
                },
                "macro_by_problem": {
                    "wta": macro_problem.get("macro_problem_wta"),
                    "mae": macro_problem.get("macro_problem_mae"),
                    "rmse": macro_problem.get("macro_problem_rmse"),
                    "bias": macro_problem.get("macro_problem_bias"),
                    "pearson": macro_problem.get("macro_problem_pearson"),
                    "spearman": macro_problem.get("macro_problem_spearman"),
                },
                "macro_normalized_by_problem": {
                    "wta": macro_problem_norm.get("macro_norm_wta"),
                    "mae": macro_problem_norm.get("macro_norm_mae"),
                    "rmse": macro_problem_norm.get("macro_norm_rmse"),
                    "bias": macro_problem_norm.get("macro_norm_bias"),
                    "pearson": macro_problem_norm.get("macro_norm_pearson"),
                    "spearman": macro_problem_norm.get("macro_norm_spearman"),
                },
                "macro_by_problem_ci": gen_macro_ci,
                "macro_normalized_by_problem_ci": gen_macro_norm_ci,
            }

            overall_true.extend(y_true)
            overall_pred.extend(y_pred)
            overall_true_norm.extend(y_true_n)
            overall_pred_norm.extend(y_pred_n)
            macro_components.append(metrics)

            # Stratify for this generator
            for (_, t, p) in items:
                b = _true_bin(t)
                overall_bins.setdefault(b, []).append((t, p))
                per_gen_bins.setdefault(generator_name, {}).setdefault(b, []).append((t, p))

        # Per-source metrics (across all generators)
        for source_name, items in sorted(source_to_items.items()):
            y_true = [t for _, t, _ in items]
            y_pred = [p for _, _, p in items]
            metrics = compute_metrics(y_true, y_pred)

            # Normalized by problem std
            y_true_n: List[float] = []
            y_pred_n: List[float] = []
            for pid, t, p in items:
                std = problem_std.get(str(pid), 1.0)
                y_true_n.append(t / std)
                y_pred_n.append(p / std)
            norm_metrics = compute_metrics(y_true_n, y_pred_n)

            # Macro over problems for this source
            by_problem_src = _group_by_problem(items)
            macro_problem_src = _macro_from_problem_metrics(by_problem_src)
            macro_problem_src_norm = _macro_from_problem_metrics_normalized(by_problem_src, problem_std)
            src_macro_ci = _bootstrap_macro_ci_from_problem_metrics(
                by_problem_src, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
            ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "source")) else {}
            src_macro_norm_ci = _bootstrap_macro_ci_from_problem_metrics(
                by_problem_src, problem_std=problem_std, normalized=True, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
            ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "source")) else {}

            per_evaluator_source_rows.append({
                "evaluator": evaluator_name,
                "source": source_name,
                **metrics,
                "norm_wta": norm_metrics.get("wta"),
                "norm_mae": norm_metrics.get("mae"),
                "norm_rmse": norm_metrics.get("rmse"),
                "norm_bias": norm_metrics.get("bias"),
                "macro_problem_mae": macro_problem_src.get("macro_problem_mae"),
                "macro_problem_rmse": macro_problem_src.get("macro_problem_rmse"),
                "macro_problem_bias": macro_problem_src.get("macro_problem_bias"),
                "macro_problem_pearson": macro_problem_src.get("macro_problem_pearson"),
                "macro_problem_spearman": macro_problem_src.get("macro_problem_spearman"),
                "macro_problem_wta": macro_problem_src.get("macro_problem_wta"),
                "macro_norm_mae": macro_problem_src_norm.get("macro_norm_mae"),
                "macro_norm_rmse": macro_problem_src_norm.get("macro_norm_rmse"),
                "macro_norm_bias": macro_problem_src_norm.get("macro_norm_bias"),
                "macro_norm_pearson": macro_problem_src_norm.get("macro_norm_pearson"),
                "macro_norm_spearman": macro_problem_src_norm.get("macro_norm_spearman"),
                "macro_norm_wta": macro_problem_src_norm.get("macro_norm_wta"),
                **src_macro_ci,
                **src_macro_norm_ci,
            })

            evaluator_report["sources"][source_name] = {
                **metrics,
                "normalized": {
                    "wta": norm_metrics.get("wta"),
                    "mae": norm_metrics.get("mae"),
                    "rmse": norm_metrics.get("rmse"),
                    "bias": norm_metrics.get("bias"),
                    "pearson": norm_metrics.get("pearson"),
                    "spearman": norm_metrics.get("spearman"),
                },
                "macro_by_problem": {
                    "wta": macro_problem_src.get("macro_problem_wta"),
                    "mae": macro_problem_src.get("macro_problem_mae"),
                    "rmse": macro_problem_src.get("macro_problem_rmse"),
                    "bias": macro_problem_src.get("macro_problem_bias"),
                    "pearson": macro_problem_src.get("macro_problem_pearson"),
                    "spearman": macro_problem_src.get("macro_problem_spearman"),
                },
                "macro_normalized_by_problem": {
                    "wta": macro_problem_src_norm.get("macro_norm_wta"),
                    "mae": macro_problem_src_norm.get("macro_norm_mae"),
                    "rmse": macro_problem_src_norm.get("macro_norm_rmse"),
                    "bias": macro_problem_src_norm.get("macro_norm_bias"),
                    "pearson": macro_problem_src_norm.get("macro_norm_pearson"),
                    "spearman": macro_problem_src_norm.get("macro_norm_spearman"),
                },
                "macro_by_problem_ci": src_macro_ci,
                "macro_normalized_by_problem_ci": src_macro_norm_ci,
            }

        # Overall pooled metrics
        overall_metrics = compute_metrics(overall_true, overall_pred)

        # Compute order preserving ratio (micro over comparable pairs across problems for this evaluator)
        problem_map = per_evaluator_problem.get(evaluator_name, {})
        total_comparable_pairs_overall = 0.0
        total_correct_pairs_overall = 0.0
        for pairs in problem_map.values():
            if len(pairs) < 2:
                continue
            y_true_op = [t for (t, _) in pairs]
            y_pred_op = [p for (_, p) in pairs]
            stats_op = compute_pairwise_order_stats(y_true_op, y_pred_op)
            cp_op = float(stats_op.get("comparable_pairs") or 0.0)
            cc_op = float(stats_op.get("correct_pairs") or 0.0)
            total_comparable_pairs_overall += cp_op
            total_correct_pairs_overall += cc_op
        order_preserving_ratio = (total_correct_pairs_overall / total_comparable_pairs_overall) if total_comparable_pairs_overall > 0 else float("nan")

        # Macro by problem across all generators for this evaluator
        problem_map = per_evaluator_problem.get(evaluator_name, {})
        macro_overall = _macro_from_problem_metrics(problem_map)
        overall_macro_ci = _bootstrap_macro_ci_from_problem_metrics(
            problem_map, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
        ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "overall")) else {}

        # Expose macro metrics as the main metrics in overall outputs
        # Keep pooled metrics as separate fields for reference
        evaluator_report["overall"] = {
            # Main metrics = macro by problem
            "count": overall_metrics.get("count"),
            "mae": macro_overall.get("macro_problem_mae"),
            "rmse": macro_overall.get("macro_problem_rmse"),
            "bias": macro_overall.get("macro_problem_bias"),
            "pearson": macro_overall.get("macro_problem_pearson"),
            "spearman": macro_overall.get("macro_problem_spearman"),
            "wta": macro_overall.get("macro_problem_wta"),
            "min_diff": overall_metrics.get("min_diff"),
            "max_diff": overall_metrics.get("max_diff"),
            "order_preserving_ratio": order_preserving_ratio,
            "macro_by_problem": {
                "wta": macro_overall.get("macro_problem_wta"),
                "mae": macro_overall.get("macro_problem_mae"),
                "rmse": macro_overall.get("macro_problem_rmse"),
                "bias": macro_overall.get("macro_problem_bias"),
                "pearson": macro_overall.get("macro_problem_pearson"),
                "spearman": macro_overall.get("macro_problem_spearman"),
            },
            "macro_by_problem_ci": overall_macro_ci,
            "pooled": {
                "mae": overall_metrics.get("mae"),
                "rmse": overall_metrics.get("rmse"),
                "bias": overall_metrics.get("bias"),
                "pearson": overall_metrics.get("pearson"),
                "spearman": overall_metrics.get("spearman"),
                "wta": overall_metrics.get("wta"),
            },
        }
        per_evaluator_overall_rows.append({
            "evaluator": evaluator_name,
            # Main metrics = macro
            "count": overall_metrics.get("count"),
            "mae": macro_overall.get("macro_problem_mae"),
            "rmse": macro_overall.get("macro_problem_rmse"),
            "bias": macro_overall.get("macro_problem_bias"),
            "pearson": macro_overall.get("macro_problem_pearson"),
            "spearman": macro_overall.get("macro_problem_spearman"),
            "wta": macro_overall.get("macro_problem_wta"),
            "min_diff": overall_metrics.get("min_diff"),
            "max_diff": overall_metrics.get("max_diff"),
            "order_preserving_ratio": order_preserving_ratio,
            # Also include pooled metrics for reference
            "pooled_mae": overall_metrics.get("mae"),
            "pooled_rmse": overall_metrics.get("rmse"),
            "pooled_bias": overall_metrics.get("bias"),
            "pooled_pearson": overall_metrics.get("pearson"),
            "pooled_spearman": overall_metrics.get("spearman"),
            "pooled_wta": overall_metrics.get("wta"),
            # Keep explicit macro columns for clarity if needed downstream
            "macro_problem_mae": macro_overall.get("macro_problem_mae"),
            "macro_problem_rmse": macro_overall.get("macro_problem_rmse"),
            "macro_problem_bias": macro_overall.get("macro_problem_bias"),
            "macro_problem_pearson": macro_overall.get("macro_problem_pearson"),
            "macro_problem_spearman": macro_overall.get("macro_problem_spearman"),
            "macro_problem_wta": macro_overall.get("macro_problem_wta"),
            **overall_macro_ci,
        })

        # Overall problem-normalized metrics (pooled)
        overall_norm_metrics = compute_metrics(overall_true_norm, overall_pred_norm)
        # Macro normalized by problem
        macro_overall_norm = _macro_from_problem_metrics_normalized(problem_map, problem_std)
        overall_macro_norm_ci = _bootstrap_macro_ci_from_problem_metrics(
            problem_map, problem_std=problem_std, normalized=True, rng=bootstrap_rng, num_bootstrap=bootstrap_iters, ci_level=bootstrap_ci, fields=bootstrap_metrics
        ) if (bootstrap_iters > 0 and bootstrap_scope in ("all", "overall")) else {}
        evaluator_report["overall_normalized"] = {
            **overall_norm_metrics,
            "macro_normalized_by_problem": {
                "wta": macro_overall_norm.get("macro_norm_wta"),
                "mae": macro_overall_norm.get("macro_norm_mae"),
                "rmse": macro_overall_norm.get("macro_norm_rmse"),
                "bias": macro_overall_norm.get("macro_norm_bias"),
                "pearson": macro_overall_norm.get("macro_norm_pearson"),
                "spearman": macro_overall_norm.get("macro_norm_spearman"),
            },
            "macro_normalized_by_problem_ci": overall_macro_norm_ci,
        }
        per_evaluator_overall_norm_rows.append({
            "evaluator": evaluator_name,
            "count": overall_norm_metrics.get("count"),
            "norm_wta": overall_norm_metrics.get("wta"),
            "norm_mae": overall_norm_metrics.get("mae"),
            "norm_rmse": overall_norm_metrics.get("rmse"),
            "norm_bias": overall_norm_metrics.get("bias"),
            "norm_pearson": overall_norm_metrics.get("pearson"),
            "norm_spearman": overall_norm_metrics.get("spearman"),
            "macro_norm_mae": macro_overall_norm.get("macro_norm_mae"),
            "macro_norm_rmse": macro_overall_norm.get("macro_norm_rmse"),
            "macro_norm_bias": macro_overall_norm.get("macro_norm_bias"),
            "macro_norm_pearson": macro_overall_norm.get("macro_norm_pearson"),
            "macro_norm_spearman": macro_overall_norm.get("macro_norm_spearman"),
            "macro_norm_wta": macro_overall_norm.get("macro_norm_wta"),
            **overall_macro_norm_ci,
        })

        # Macro-average across generators (equal weight per generator)
        def avg(field: str) -> float:
            vals = [d[field] for d in macro_components if field in d and isinstance(d[field], (float, int))]
            return safe_mean([float(v) for v in vals]) if vals else float("nan")

        evaluator_report["overall_macro"] = {
            "num_generators": float(len(macro_components)),
            "mae": avg("mae"),
            "rmse": avg("rmse"),
            "bias": avg("bias"),
            "wta": avg("wta"),
            "pearson": avg("pearson"),
            "spearman": avg("spearman"),
        }
        per_evaluator_overall_macro_rows.append({
            "evaluator": evaluator_name,
            "num_generators": float(len(macro_components)),
            "macro_mae": avg("mae"),
            "macro_rmse": avg("rmse"),
            "macro_bias": avg("bias"),
            "macro_wta": avg("wta"),
            "macro_pearson": avg("pearson"),
            "macro_spearman": avg("spearman"),
        })

        per_evaluator_summary[evaluator_name] = evaluator_report

        # Append stratified rows (overall by true-score bin)
        for b in sorted(overall_bins.keys()):
            pairs = overall_bins[b]
            if not pairs:
                continue
            y_t = [t for (t, _) in pairs]
            y_p = [p for (_, p) in pairs]
            m = compute_metrics(y_t, y_p)
            per_evaluator_true_bin_rows.append({
                "evaluator": evaluator_name,
                "true_bin": int(b),
                **m,
            })

        # Append stratified rows (per generator by true-score bin)
        for gen_name in sorted(per_gen_bins.keys()):
            bin_map = per_gen_bins[gen_name]
            for b in sorted(bin_map.keys()):
                pairs = bin_map[b]
                if not pairs:
                    continue
                y_t = [t for (t, _) in pairs]
                y_p = [p for (_, p) in pairs]
                m = compute_metrics(y_t, y_p)
                per_evaluator_per_gen_true_bin_rows.append({
                    "evaluator": evaluator_name,
                    "generator": gen_name,
                    "true_bin": int(b),
                    **m,
                })

    # Write outputs
    write_json(OUT_DIR / "per_evaluator_summary.json", per_evaluator_summary)

    # CSVs
    # Simplified per-generator metrics - only macro metrics
    gen_fields = [
        "evaluator",
        "generator",
        "count",
        "mae",
        "rmse",
        "bias",
        "pearson",
        "spearman",
        "wta",
    ]
    # Filter rows to only include specified fields
    gen_rows_filtered = [{k: row.get(k) for k in gen_fields} for row in per_evaluator_generator_rows]
    write_csv(OUT_DIR / "per_evaluator_per_generator.csv", gen_rows_filtered, gen_fields)

    # Simplified per-source metrics - only macro metrics
    src_fields = [
        "evaluator",
        "source",
        "count",
        "mae",
        "rmse",
        "bias",
        "pearson",
        "spearman",
        "wta",
    ]
    # Filter rows to only include specified fields
    src_rows_filtered = [{k: row.get(k) for k in src_fields} for row in per_evaluator_source_rows]
    write_csv(OUT_DIR / "per_evaluator_per_source.csv", src_rows_filtered, src_fields)

    # Simplified overall metrics - only macro metrics (averaged per-problem)
    overall_fields = [
        "evaluator",
        "count",
        "mae",
        "rmse",
        "bias",
        "pearson",
        "spearman",
        "wta",
    ]
    # Filter rows to only include specified fields
    overall_rows_filtered = [{k: row.get(k) for k in overall_fields} for row in per_evaluator_overall_rows]
    write_csv(OUT_DIR / "per_evaluator_overall.csv", overall_rows_filtered, overall_fields)

    # Write stratified outputs by true-score bins (0-7)
    strat_fields = [
        "evaluator",
        "true_bin",
        "count",
        "mae",
        "rmse",
        "bias",
        "pearson",
        "spearman",
        "wta",
        "min_diff",
        "max_diff",
    ]
    if per_evaluator_true_bin_rows:
        write_csv(OUT_DIR / "per_evaluator_by_true_bin.csv", per_evaluator_true_bin_rows, strat_fields)

    strat_gen_fields = [
        "evaluator",
        "generator",
        "true_bin",
        "count",
        "mae",
        "rmse",
        "bias",
        "pearson",
        "spearman",
        "wta",
        "min_diff",
        "max_diff",
    ]
    if per_evaluator_per_gen_true_bin_rows:
        write_csv(OUT_DIR / "per_evaluator_per_generator_by_true_bin.csv", per_evaluator_per_gen_true_bin_rows, strat_gen_fields)

    print(f"Wrote reports to: {OUT_DIR}")

    # Additional analyses
    # 1) Disagreement across evaluators per (problem_id, generator)
    if not getattr(args, "skip_disagreement", False):
        disagreement_rows: List[Dict[str, Any]] = []
        for (pid, gen), triples in cross_eval_items.items():
            if len(triples) < 2:
                continue
            eval_names = [e for (e, _, _) in triples]
            truths = [t for (_, t, _) in triples]
            preds = [p for (_, _, p) in triples]
            # all truths should match per (pid, gen) key; use first
            true_val = truths[0] if truths else float("nan")
            m = safe_mean(preds)
            var = safe_mean([(p - m) ** 2 for p in preds]) if preds else float("nan")
            std = math.sqrt(var) if preds else float("nan")
            row = {
                "problem_id": pid,
                "generator": gen,
                "true": true_val,
                "num_evaluators": float(len(triples)),
                "mean_pred": m,
                "std_pred": std,
                "min_pred": min(preds) if preds else float("nan"),
                "max_pred": max(preds) if preds else float("nan"),
                "range_pred": (max(preds) - min(preds)) if preds else float("nan"),
                "evaluators": ";".join(eval_names),
                "scores": ";".join(f"{e}:{p:.6g}" for e, p in zip(eval_names, preds)),
            }
            disagreement_rows.append(row)

        if disagreement_rows:
            # Sort by std descending, then range descending
            disagreement_rows.sort(key=lambda r: (-(r.get("std_pred") or 0.0), -(r.get("range_pred") or 0.0)))
            disagreement_fields = [
                "problem_id", "generator", "true", "num_evaluators",
                "mean_pred", "std_pred", "min_pred", "max_pred", "range_pred",
                "evaluators", "scores",
            ]
            write_csv(OUT_DIR / "disagreement_per_item.csv", disagreement_rows, disagreement_fields)

    # 2) Pairwise order preservation across generators for each problem (per evaluator)
    order_problem_rows: List[Dict[str, Any]] = []
    order_overall_rows: List[Dict[str, Any]] = []
    if not getattr(args, "skip_order", False):
      for evaluator_name, problem_map in per_evaluator_problem.items():
        total_items = 0.0
        total_comparable_pairs = 0.0
        total_correct_pairs = 0.0
        num_problems = float(len(problem_map))
        problems_with_pairs = 0.0
        macro_accs: List[float] = []
        macro_spearmans: List[float] = []
        macro_kendalls: List[float] = []
        weighted_spearman_num = 0.0
        weighted_spearman_den = 0.0
        weighted_kendall_num = 0.0
        weighted_kendall_den = 0.0
        for pid, pairs in problem_map.items():
            if len(pairs) < 2:
                continue
            y_true = [t for (t, _) in pairs]
            y_pred = [p for (_, p) in pairs]
            stats = compute_pairwise_order_stats(y_true, y_pred)
            sr = spearmanr(y_true, y_pred)
            kt = kendall_tau_b(y_true, y_pred)
            kt = kendall_tau_b(y_true, y_pred)
            order_problem_rows.append({
                "evaluator": evaluator_name,
                "problem_id": pid,
                "num_items": stats.get("num_items"),
                "num_pairs": stats.get("num_pairs"),
                "comparable_pairs": stats.get("comparable_pairs"),
                "correct_pairs": stats.get("correct_pairs"),
                "order_acc": stats.get("order_acc"),
                "spearman": sr,
                "kendall_tau_b": kt,
            })
            total_items += float(len(pairs))
            cp = float(stats.get("comparable_pairs") or 0.0)
            cc = float(stats.get("correct_pairs") or 0.0)
            total_comparable_pairs += cp
            total_correct_pairs += cc
            if cp > 0:
                problems_with_pairs += 1.0
                oa = stats.get("order_acc")
                if isinstance(oa, (int, float)) and not math.isnan(float(oa)):
                    macro_accs.append(float(oa))
                if isinstance(sr, (int, float)) and not math.isnan(float(sr)):
                    macro_spearmans.append(float(sr))
                    n_items = float(len(pairs))
                    if n_items >= 2.0:
                        weighted_spearman_num += float(sr) * n_items
                        weighted_spearman_den += n_items
                if isinstance(kt, (int, float)) and not math.isnan(float(kt)):
                    macro_kendalls.append(float(kt))
                    n_items = float(len(pairs))
                    if n_items >= 2.0:
                        weighted_kendall_num += float(kt) * n_items
                        weighted_kendall_den += n_items
        micro_acc = (total_correct_pairs / total_comparable_pairs) if total_comparable_pairs > 0 else float("nan")
        macro_acc = safe_mean(macro_accs) if macro_accs else float("nan")
        macro_spearman = safe_mean(macro_spearmans) if macro_spearmans else float("nan")
        weighted_macro_spearman = (weighted_spearman_num / weighted_spearman_den) if weighted_spearman_den > 0 else float("nan")
        macro_kendall = safe_mean(macro_kendalls) if macro_kendalls else float("nan")
        weighted_macro_kendall = (weighted_kendall_num / weighted_kendall_den) if weighted_kendall_den > 0 else float("nan")
        order_overall_rows.append({
            "evaluator": evaluator_name,
            "problems": num_problems,
            "problems_with_pairs": problems_with_pairs,
            "total_items": total_items,
            "total_comparable_pairs": total_comparable_pairs,
            "total_correct_pairs": total_correct_pairs,
            "micro_order_acc": micro_acc,
            "macro_order_acc": macro_acc,
            "macro_spearman": macro_spearman,
            "weighted_macro_spearman": weighted_macro_spearman,
            "macro_kendall_tau_b": macro_kendall,
            "weighted_macro_kendall_tau_b": weighted_macro_kendall,
        })

    if not getattr(args, "skip_order", False) and order_problem_rows:
        order_problem_fields = [
            "evaluator", "problem_id", "num_items", "num_pairs",
            "comparable_pairs", "correct_pairs", "order_acc", "spearman", "kendall_tau_b",
        ]
        write_csv(OUT_DIR / "order_preservation_per_problem.csv", order_problem_rows, order_problem_fields)

    if not getattr(args, "skip_order", False) and order_overall_rows:
        order_overall_fields = [
            "evaluator", "problems", "problems_with_pairs", "total_items",
            "total_comparable_pairs", "total_correct_pairs", "micro_order_acc", "macro_order_acc", "macro_spearman", "weighted_macro_spearman", "macro_kendall_tau_b", "weighted_macro_kendall_tau_b",
        ]
        write_csv(OUT_DIR / "order_preservation_overall.csv", order_overall_rows, order_overall_fields)

    # 3) Verify-vs-solve analysis: for each evaluator, estimate verification quality per problem
    #    and compare to the mapped generator model's own ability to solve the problem.
    # Build list of generator model names from merged
    generator_names = sorted({model for (_, model) in merged.keys()})

    def map_evaluator_to_generator_name(evaluator_name: str) -> str:
        en = evaluator_name.lower()
        matches = [g for g in generator_names if g and g.lower() in en]
        if not matches:
            return ""
        # choose longest match
        return max(matches, key=len)

    if not getattr(args, "skip_verify", False):
        verify_rows: List[Dict[str, Any]] = []
        for evaluator_name, problem_map in per_evaluator_problem.items():
            mapped_gen = map_evaluator_to_generator_name(evaluator_name)
            for pid, pairs in problem_map.items():
                y_true = [t for (t, _) in pairs]
                y_pred = [p for (_, p) in pairs]
                m = compute_metrics(y_true, y_pred)
                own_score = merged.get((str(pid), mapped_gen)) if mapped_gen else None
                verify_rows.append({
                    "evaluator": evaluator_name,
                    "mapped_generator": mapped_gen,
                    "problem_id": pid,
                    "eval_count": float(len(pairs)),
                    "eval_mae": m.get("mae"),
                    "eval_rmse": m.get("rmse"),
                    "eval_bias": m.get("bias"),
                    "eval_wta": m.get("wta"),
                    "model_own_score": (float(own_score) if own_score is not None else float("nan")),
                })

        if verify_rows:
            verify_fields = [
                "evaluator", "mapped_generator", "problem_id", "eval_count",
                "eval_mae", "eval_rmse", "eval_bias", "eval_wta", "model_own_score",
            ]
            write_csv(OUT_DIR / "verify_vs_solve.csv", verify_rows, verify_fields)


if __name__ == "__main__":
    main() 