import json
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st


BASE_DIR = "/home/ubuntu/wenjie-cal/ProofGym/evaluator_design"
JOINED_DEFAULT = f"{BASE_DIR}/outputs/splits/by_year/joined_with_categories.jsonl"
HUMAN_FILE = f"{BASE_DIR}/data/iclr_submission/evaluation_merged.jsonl"
EVAL_GRADES_DIR = f"{BASE_DIR}/outputs/evaluator_grades/iclr_submission/single__o3__with_reference_solution_and_marking_scheme_flexible"

# Optional split files (if present) to annotate records with split membership
SPLIT_OUTPUT_DIR = f"{BASE_DIR}/outputs/splits/by_year"
TRAIN_FILE = f"{SPLIT_OUTPUT_DIR}/train.jsonl"
VAL_FILE = f"{SPLIT_OUTPUT_DIR}/val.jsonl"
TEST_FILE = f"{SPLIT_OUTPUT_DIR}/test.jsonl"


def read_jsonl(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    rows: List[Dict] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def load_joined_or_build(joined_path: str) -> pd.DataFrame:
    """Load precomputed joined records with human/evaluator scores and diffs.

    If not present, build from HUMAN_FILE and evaluator grade files.
    """
    if os.path.exists(joined_path):
        data = read_jsonl(joined_path)
        return pd.DataFrame(data)

    # Build from human + evaluator files
    human_rows = read_jsonl(HUMAN_FILE)
    human_map: Dict[Tuple[str, str], float] = {}
    comment_map: Dict[Tuple[str, str], str] = {}
    for r in human_rows:
        pid = r.get("problem_id") or r.get("id")
        mname = r.get("model_name")
        score = r.get("score")
        if pid is None or mname is None or score is None:
            continue
        human_map[(pid, mname)] = float(score)
        comment_map[(pid, mname)] = r.get("overall_comment", "")

    pred_map: Dict[Tuple[str, str], float] = {}
    # Iterate all evaluator files
    if os.path.isdir(EVAL_GRADES_DIR):
        for fname in os.listdir(EVAL_GRADES_DIR):
            if not fname.endswith(".eval.jsonl"):
                continue
            rows = read_jsonl(os.path.join(EVAL_GRADES_DIR, fname))
            for r in rows:
                pid = r.get("problem_id") or r.get("id")
                mname = r.get("model_name")
                if mname is None:
                    uid = r.get("unique_id")
                    if isinstance(uid, str) and "::" in uid:
                        mname = uid.split("::", 1)[1]
                score = r.get("score")
                if pid is None or mname is None or score is None:
                    continue
                pred_map[(pid, mname)] = float(score)

    records: List[Dict] = []
    for key, h in human_map.items():
        if key not in pred_map:
            continue
        pid, mname = key
        p = pred_map[key]
        diff = p - h
        category = "mid"
        if abs(diff) <= 0.5:
            category = "close"
        elif diff >= 2.0:
            category = "higher_than_human"
        elif diff <= -2.0:
            category = "lower_than_human"
        records.append({
            "problem_id": pid,
            "model_name": mname,
            "human_score": h,
            "evaluator_score": p,
            "diff": diff,
            "category": category,
            "human_analysis": comment_map.get((pid, mname), ""),
        })

    return pd.DataFrame(records)


def annotate_split(
    df: pd.DataFrame,
    train_path: str,
    val_path: str,
    test_path: str,
) -> pd.DataFrame:
    """Add a 'split' column based on provided split files (train/val/test)."""
    split_map: Dict[Tuple[str, str], str] = {}
    for path, split_name in [
        (train_path, "train"),
        (val_path, "val"),
        (test_path, "test"),
    ]:
        if not path:
            continue
        rows = read_jsonl(path)
        for r in rows:
            pid = r.get("problem_id")
            mname = r.get("model_name")
            if pid and mname:
                split_map[(pid, mname)] = split_name
    if not split_map:
        df["split"] = "unspecified"
        return df
    df["split"] = [split_map.get((r.problem_id, r.model_name), "unspecified") for r in df.itertuples()]
    return df


def parse_problem_meta(problem_id: str) -> Tuple[str, str]:
    """Extract (contest, year) from problem_id like 'APMO-2022-1'."""
    if not isinstance(problem_id, str) or "-" not in problem_id:
        return ("UNKNOWN", "UNKNOWN")
    parts = problem_id.split("-")
    if len(parts) < 2:
        return (parts[0], "UNKNOWN")
    contest = parts[0]
    year = parts[1]
    return (contest, year)


def compute_model_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["model_name", "count", "MAE", "RMSE", "mean_diff"]).sort_values("MAE")
    grouped = df.groupby("model_name")
    rows: List[Dict] = []
    for model, g in grouped:
        diffs = g["evaluator_score"].values - g["human_score"].values
        mae = float(np.mean(np.abs(diffs))) if len(diffs) else 0.0
        rmse = float(np.sqrt(np.mean(diffs ** 2))) if len(diffs) else 0.0
        mean_diff = float(np.mean(diffs)) if len(diffs) else 0.0
        rows.append({
            "model_name": model,
            "count": int(len(g)),
            "MAE": mae,
            "RMSE": rmse,
            "mean_diff": mean_diff,
        })
    return pd.DataFrame(rows).sort_values(["MAE", "RMSE", "model_name"])  # primary sort by MAE


def main() -> None:
    st.set_page_config(page_title="ProofGym Evaluator Dashboard", layout="wide")
    st.title("ProofGym Evaluator – Dynamic Dashboard")
    st.caption("Interactively filter problems and recompute metrics / rankings.")

    with st.sidebar:
        st.header("Data Source")
        joined_path = st.text_input("Joined data (JSONL)", value=JOINED_DEFAULT)
        st.write("If not present, it will be built from human + evaluator files.")
        st.subheader("Split files (optional)")
        train_path = st.text_input("Train split JSONL", value=TRAIN_FILE)
        val_path = st.text_input("Val split JSONL", value=VAL_FILE)
        test_path = st.text_input("Test split JSONL", value=TEST_FILE)

    df = load_joined_or_build(joined_path)
    if df.empty:
        st.warning("No data found. Check the paths or run evaluations first.")
        return

    # Enrich with split and basic meta
    df = annotate_split(df, train_path=train_path, val_path=val_path, test_path=test_path)
    meta = df["problem_id"].apply(parse_problem_meta)
    df["contest"] = meta.apply(lambda x: x[0])
    df["year"] = meta.apply(lambda x: x[1])

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        contests = sorted(df["contest"].unique().tolist())
        contest_sel = st.multiselect("Contest", contests, default=contests)
        years = sorted(df[df["contest"].isin(contest_sel)]["year"].unique().tolist())
        year_sel = st.multiselect("Year", years, default=years)
        splits = sorted(df["split"].unique().tolist())
        split_sel = st.multiselect("Split", splits, default=splits)
        categories = ["close", "mid", "higher_than_human", "lower_than_human"]
        cat_sel = st.multiselect("Category", categories, default=categories)
        models = sorted(df["model_name"].unique().tolist())
        model_sel = st.multiselect("Models", models, default=models)

        st.subheader("Score Difference Thresholds")
        close_thr = st.number_input("Close threshold (|diff| <= close)", min_value=0.0, value=0.5, step=0.1)
        dramatic_thr = st.number_input("Dramatic threshold (|diff| >= dramatic)", min_value=0.0, value=2.0, step=0.5)
        if st.button("Recompute categories with thresholds"):
            diffs = df["evaluator_score"] - df["human_score"]
            new_cat = np.where(np.abs(diffs) <= close_thr, "close",
                               np.where(diffs >= dramatic_thr, "higher_than_human",
                                        np.where(diffs <= -dramatic_thr, "lower_than_human", "mid")))
            df["category"] = new_cat

    # Apply filters
    mask = (
        df["contest"].isin(contest_sel) &
        df["year"].isin(year_sel) &
        df["split"].isin(split_sel) &
        df["category"].isin(cat_sel) &
        df["model_name"].isin(model_sel)
    )
    filtered = df[mask].copy()

    # Summary KPIs
    col1, col2, col3, col4 = st.columns(4)
    diffs_all = filtered["evaluator_score"].values - filtered["human_score"].values
    with col1:
        st.metric("Num pairs", value=len(filtered))
    with col2:
        st.metric("MAE", value=f"{float(np.mean(np.abs(diffs_all))) if len(diffs_all) else 0.0:.4f}")
    with col3:
        st.metric("RMSE", value=f"{float(np.sqrt(np.mean(diffs_all**2))) if len(diffs_all) else 0.0:.4f}")
    with col4:
        st.metric("Mean diff", value=f"{float(np.mean(diffs_all)) if len(diffs_all) else 0.0:.4f}")

    st.divider()
    st.subheader("Model Rankings (by MAE)")
    metrics_df = compute_model_metrics(filtered)
    st.dataframe(metrics_df, use_container_width=True)

    # Download metrics
    if not metrics_df.empty:
        csv = metrics_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download metrics CSV", csv, file_name="metrics.csv", mime="text/csv")

    st.divider()
    with st.expander("Show filtered records"):
        # show light view
        view_cols = [
            "problem_id", "model_name", "split", "category",
            "human_score", "evaluator_score", "diff",
        ]
        extra_cols = ["human_analysis"] if "human_analysis" in filtered.columns else []
        show_df = filtered[view_cols + extra_cols].sort_values(["problem_id", "model_name"]).reset_index(drop=True)
        st.dataframe(show_df, use_container_width=True, height=400)


if __name__ == "__main__":
    main()


