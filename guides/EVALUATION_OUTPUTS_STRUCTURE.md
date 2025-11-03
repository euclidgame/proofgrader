# Evaluation Outputs Structure

This document describes the new evaluation outputs directory structure.

## Directory Layout

When you run evaluation on a dataset in `data/<your_dataset>/`:

```
data/<your_dataset>/
├── problems.jsonl                  # Input: problems
├── model_solutions.jsonl           # Input: generated solutions
├── expert_gradings.jsonl           # Input: ground truth scores (optional, required for metrics)
└── evaluation_outputs/             # All evaluation outputs go here
    ├── evaluation_runs/            # Raw evaluator outputs
    │   └── single__gpt-4o__basic__<timestamp>/
    │       └── evaluator_raw.jsonl
    ├── evaluator_gradings/         # Parsed per-generator scores
    │   └── single__gpt-4o__basic/
    │       ├── gpt-4o.eval.jsonl
    │       ├── gemini-2.5-pro.eval.jsonl
    │       └── qwen3-235b.eval.jsonl  # Model names sanitized (no slashes)
    └── metrics/                    # Computed metrics and reports
        ├── per_evaluator_summary.json
        ├── per_evaluator_per_generator.csv
        └── ...
```

## Usage

### Basic Evaluation (without metrics)

```bash
python scripts/evaluate.py \
  --data-dir data/test_data \
  --model gpt-4o
```

This will:
1. Generate evaluations using gpt-4o
2. Save raw outputs to `evaluation_runs/`
3. Parse and save per-generator scores to `evaluator_gradings/`
4. Skip metrics (no ground truth required)

### Evaluation with Metrics

```bash
python scripts/evaluate.py \
  --data-dir data/test_data \
  --model gpt-4o \
  --compute-metrics
```

This will:
1. Run evaluation (as above)
2. Check for ground truth file (expert_gradings.jsonl)
3. If found: compute metrics and save to `metrics/`
4. If NOT found: show warning with instructions and exit gracefully (code 0)

### Metrics Only (Use Existing Evaluations)

If you already have evaluations and want to compute metrics:

```bash
python scripts/evaluate.py \
  --data-dir data/test_data \
  --metrics-only
```

This will:
1. Skip evaluation entirely
2. Check for ground truth (required)
3. Check for existing evaluations (required)
4. Compute metrics and save to `metrics/`

Alternatively, call the metrics script directly:

```bash
python proofgrader/metrics/compute_evaluator_distances.py \
  --data-dir data/test_data
```

## Key Changes from Previous Structure

### Before (Old Structure)
- Global `outputs/` directory at project root
- Used `--data-version` parameter
- Model names with slashes created nested directories
- Metrics auto-computed after evaluation

### After (New Structure)
- Per-dataset `evaluation_outputs/` directory
- Uses `--data-dir` parameter  
- Model names sanitized (only part after last slash)
- Metrics computed only when requested
- Ground truth check before metrics

## Model Name Sanitization

Model names with slashes are sanitized for file/directory names:

- `openrouter/qwen/qwen3-235b-a22b` → `qwen3-235b-a22b`
- `gpt-4o` → `gpt-4o` (unchanged)
- `gemini-2.5-pro` → `gemini-2.5-pro` (unchanged)

This prevents creating nested subdirectories and keeps the file structure clean.

## Ground Truth Files

The metrics computation looks for ground truth in this order:

1. `expert_gradings.jsonl` (preferred)
2. `evaluation_merged.jsonl` (fallback)
3. `evaluations.jsonl` (fallback)

All should be in the data directory (e.g., `data/test_data/expert_gradings.jsonl`)

## Error Handling

If `--compute-metrics` is specified but no ground truth file exists:

```
⚠️  Cannot compute metrics: No ground truth file found!

Looked for in data/test_data:
  - expert_gradings.jsonl (preferred)
  - evaluation_merged.jsonl
  - evaluations.jsonl

💡 To compute metrics, add a ground truth file to the data directory, then run:
    python proofgrader/metrics/compute_evaluator_distances.py --data-dir data/test_data

Evaluation completed successfully (without metrics).
```

The script exits cleanly with code 0 (not an error).

