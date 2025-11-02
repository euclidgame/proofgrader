# Complete ProofGrader Workflow

This guide shows the complete workflow from start to finish.

## Overview

ProofGrader has **three independent scripts** that run sequentially:

```
1. generate.py              → Generate solutions
2. generate_marking_schemes.py  → Generate rubrics (optional)
3. evaluate.py              → Evaluate solutions
```

## Full Workflow

### Step 0: Prepare Your Data

Create a data directory with `problems.jsonl`:

```bash
mkdir -p data/my_dataset
```

Your `problems.jsonl` should have:
```json
{"id": "problem-1", "problem": "Prove that...", "reference_solutions": "Solution..."}
{"id": "problem-2", "problem": "Show that...", "reference_solutions": "Proof..."}
```

### Step 1: Generate Solutions

Generate solutions from multiple models:

```bash
python scripts/generate.py \
  --data-dir data/my_dataset \
  --models gpt-4o o3 gemini-2.5-pro
```

**Output:** `data/my_dataset/model_solutions.jsonl`

**Time:** ~1-5 minutes per problem per model
**Cost:** ~$0.10-1.00 per problem per model

### Step 2: Generate Marking Schemes (Optional but Recommended)

Generate grading rubrics for better evaluation:

```bash
python scripts/generate_marking_schemes.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --overwrite
```

**Output:** `data/my_dataset/problems.jsonl` (with `marking_scheme` field added)

**Time:** ~30 seconds per problem
**Cost:** ~$0.01-0.10 per problem

**Why do this?**
- ✅ More consistent evaluation across problems
- ✅ Better detection of partial correctness
- ✅ Higher correlation with human grading
- ✅ Reusable across all future evaluations

### Step 3: Evaluate Solutions

Evaluate with one or more evaluator models:

```bash
# Without marking schemes
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4o

# With marking schemes (if generated in Step 2)
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4o \
  --template with_marking_scheme_and_reference
```

**Output:** 
- `data/my_dataset/evaluation_outputs/evaluation_runs/` (raw outputs)
- `data/my_dataset/evaluation_outputs/evaluator_gradings/` (per-generator scores)

**Time:** ~5-30 seconds per solution
**Cost:** ~$0.01-0.05 per solution

### Step 4: Compute Metrics (If You Have Expert Gradings)

If you have human expert scores:

```bash
# Option 1: During evaluation
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4o \
  --compute-metrics

# Option 2: After evaluation
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --metrics-only
```

**Requires:** `data/my_dataset/expert_gradings.jsonl` with format:
```json
{"problem_id": "problem-1", "model_name": "gpt-4o", "score": 6.0}
{"problem_id": "problem-1", "model_name": "o3", "score": 7.0}
```

**Output:** `data/my_dataset/evaluation_outputs/metrics/`
- `per_evaluator_overall.csv` - Overall performance
- `per_evaluator_per_generator.csv` - Breakdown by model
- `per_evaluator_per_source.csv` - Breakdown by contest

## Example: Complete Pipeline

```bash
# Prepare data
mkdir -p data/math_olympiad
# ... add problems.jsonl with 50 problems ...

# Step 1: Generate solutions (3 models)
python scripts/generate.py \
  --data-dir data/math_olympiad \
  --models gpt-4o o3 gemini-2.5-pro
# Output: 150 solutions (50 problems × 3 models)

# Step 2: Generate marking schemes (optional)
python scripts/generate_marking_schemes.py \
  --data-dir data/math_olympiad \
  --model gemini-2.5-pro \
  --overwrite
# Output: problems.jsonl now has marking_scheme field

# Step 3a: Evaluate with basic template
python scripts/evaluate.py \
  --data-dir data/math_olympiad \
  --model gpt-4o
# Output: 150 evaluations

# Step 3b: Evaluate with marking schemes
python scripts/evaluate.py \
  --data-dir data/math_olympiad \
  --model gemini-2.5-pro \
  --template with_marking_scheme_and_reference
# Output: Another 150 evaluations

# Step 4: Compute metrics (if you have expert_gradings.jsonl)
python scripts/evaluate.py \
  --data-dir data/math_olympiad \
  --metrics-only
# Output: Metrics comparing evaluators to experts
```

## Directory Structure After Complete Workflow

```
data/math_olympiad/
├── problems.jsonl                      # Input (with marking_scheme if generated)
├── model_solutions.jsonl               # Step 1 output
├── expert_gradings.jsonl              # Optional (for metrics)
└── evaluation_outputs/
    ├── evaluation_runs/                # Step 3 raw outputs
    │   ├── single__gpt-4o__basic__20251102-123456/
    │   └── single__gemini-2.5-pro__with_marking_scheme__20251102-123457/
    ├── evaluator_gradings/             # Step 3 parsed scores
    │   ├── single__gpt-4o__basic/
    │   │   ├── gpt-4o.eval.jsonl
    │   │   ├── o3.eval.jsonl
    │   │   └── gemini-2.5-pro.eval.jsonl
    │   └── single__gemini-2.5-pro__with_marking_scheme/
    │       ├── gpt-4o.eval.jsonl
    │       ├── o3.eval.jsonl
    │       └── gemini-2.5-pro.eval.jsonl
    └── metrics/                        # Step 4 metrics (if computed)
        ├── per_evaluator_overall.csv
        ├── per_evaluator_per_generator.csv
        └── per_evaluator_per_source.csv
```

## Cost Estimation

For 100 problems with 3 solution models and 2 evaluator models:

| Step | API Calls | Estimated Cost |
|------|-----------|----------------|
| Generate solutions | 300 (100 × 3) | $30-300 |
| Generate marking schemes | 100 | $1-10 |
| Evaluate solutions | 600 (300 × 2) | $3-30 |
| **Total** | **1000** | **$34-340** |

Costs vary by:
- Model (o3 > gpt-4o > gemini-2.5-pro)
- Problem complexity (longer = more expensive)
- Template verbosity

## Tips

1. **Start small:** Test with `--max-problems 5` first
2. **Generate once:** Solutions are cached, don't regenerate
3. **Evaluate multiple times:** Try different evaluators and templates
4. **Use marking schemes:** Improves evaluation quality significantly
5. **Compare evaluators:** Run metrics to see which evaluator matches experts best

## See Also

- `MARKING_SCHEMES_GUIDE.md` - Detailed marking scheme generation guide
- `EXPERT_GRADINGS_FORMAT.md` - How to create ground truth data
- `EVALUATION_OUTPUTS_STRUCTURE.md` - Output directory structure
- `ID_SCHEMA.md` - How IDs work throughout the pipeline

