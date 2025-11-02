# ProofGrader

A framework for generating and evaluating mathematical proofs using large language models.

## Overview

ProofGrader provides **three independent scripts**:
- **`generate.py`**: Generate solutions from multiple models (run once)
- **`generate_marking_schemes.py`**: Generate marking schemes for problems (optional, run once)
- **`evaluate.py`**: Evaluate solutions with workflows (run many times with different evaluators)

**Key principle**: Generation and evaluation are completely separate. Generate expensive solutions once, optionally add marking schemes, then evaluate with multiple evaluators without re-generating.

---

## Quick Start

### Installation

```bash
# 1. Install Git LFS (required for large data files)
# On Ubuntu/Debian:
sudo apt-get install git-lfs

# On macOS:
brew install git-lfs

# On Windows (use Git Bash or WSL)
# Download from: https://git-lfs.github.com/

# 2. Clone and install
git clone https://github.com/euclidgame/proofgrader.git
cd proofgrader
git lfs install
git lfs pull  # Download large files (problems.jsonl, etc.)
pip install -r requirements.txt

# 3. Set up API keys
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

### Your First Run

```bash
# Create test data
mkdir -p data/test
echo '{"id": "test1", "problem": "What is 2+2?"}' > data/test/problems.jsonl

# Step 1: Generate (once)
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 gemini-2.5-pro

# Step 2: Evaluate (can run multiple times!)
python scripts/evaluate.py \
  --data-dir data/test \
  --model gemini-2.5-pro
```

**That's it!** Solutions saved to `data/test/model_solutions.jsonl`, evaluations to `data/test/outputs/evaluations/`.

---

## The Three Scripts

### 📝 `generate.py` - Solution Generation

**Purpose**: Generate solutions from one or more models

```bash
python scripts/generate.py \
  --data-dir data/my_dataset \
  --models gpt-4 o3 openrouter/qwen/qwen3-235b-a22b-thinking-2507 gemini-2.5-pro
```

**Key Options**:
- `--data-dir`: Directory with `problems.jsonl` (required)
- `--models`: One or more model names (required)
- `--output`: Output file (default: `data-dir/model_solutions.jsonl`)
- `--template`: Generation template (default: `default`)
- `--max-concurrent`: Concurrent requests (default: 100)
- `--max-problems`: Limit problems for testing
- `--strict-validation`: Exit on validation failure
- `--no-cache`: Disable caching

**What it does**:
1. ✅ Validates `problems.jsonl`
2. 📝 Generates solutions from each model (sequentially)
3. 🔍 Validates generated solutions
4. ✅ Saves to `model_solutions.jsonl` (one solution per (problem, model) pair)

**Output**: `model_solutions.jsonl` with fields:
- `problem_id`: Problem identifier
- `generator`: Model name
- `solution`: Generated solution text
- `reference_solutions`: Preserved from problems.jsonl
- All other problem fields preserved

---

### 📋 `generate_marking_schemes.py` - Marking Scheme Generation (Optional)

**Purpose**: Generate detailed grading rubrics for problems

```bash
python scripts/generate_marking_schemes.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro
```

**Key Options**:
- `--data-dir`: Directory with `problems.jsonl` (required)
- `--model`: Model to use for generation (default: gemini-2.5-pro)
- `--template`: Template name (default: `marking_scheme`)
- `--output`: Output file (default: `data-dir/problems_with_marking_schemes.jsonl`)
- `--overwrite`: Overwrite original problems.jsonl
- `--max-problems`: Limit problems for testing

**What it does**:
1. ✅ Reads `problems.jsonl` with reference solutions
2. 📋 Generates marking schemes using LLM
3. 💾 Adds `marking_scheme` field to each problem
4. ✅ Saves to new file (or overwrites if `--overwrite`)

**Output**: Problems with added `marking_scheme` field containing:
- Checkpoints with point values
- Zero-credit items
- Deductions for common errors

**Why use it?**: Marking schemes improve evaluation consistency and enable more accurate grading with templates like `with_marking_scheme_and_reference`.

See `MARKING_SCHEMES_GUIDE.md` for detailed usage.

---

### 🎯 `evaluate.py` - Solution Evaluation

**Purpose**: Evaluate solutions using various workflows (completely independent of generation)

```bash
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro
```

**Key Options**:
- `--data-dir`: Directory with solutions (required)
- `--model`: Evaluator model name (default: `gemini-2.5-pro`)
- `--dataset`: Solutions file (default: `data-dir/model_solutions.jsonl`)
- `--workflow`: Evaluation strategy (default: `single`)
  - `single`: Basic single-shot evaluation
  - `decompose-then-judge`: Break into steps, then evaluate
  - `repeat-and-aggregate`: Multiple evaluations, aggregate
  - `reflect-and-revise`: Self-critique and revision
- `--template`: Evaluation template (default: `basic`)
- `--compute-metrics`: Compute metrics if expert gradings exist
- `--output-dir`: Custom output directory

**Workflow-Specific Options**:
- `--steps-model MODEL`: For decompose-then-judge
- `--num-runs N`: For repeat-and-aggregate
- `--critic-model MODEL`: For reflect-and-revise

**What it does**:
1. 🎯 Reads solutions from `model_solutions.jsonl`
2. 📊 Evaluates using specified workflow
3. ✅ Saves to `data-dir/outputs/evaluations/`
4. 📈 Computes metrics if `--compute-metrics` (optional)

**Output**: `*.eval.jsonl` files with fields:
- `id`: Problem ID
- `generator`: Model that generated solution
- `score`: Evaluation score
- `assessment`: Detailed feedback
- `comments`: Specific notes

---

## Input Format

### Problems File (Required)

**Location**: `data-dir/problems.jsonl`

**Format**: One JSON per line

**Required fields**:
- `id`: Unique identifier
- `problem`: Problem statement

**Optional**:
- `reference_solutions`: Ground truth (preserved throughout)
- Any metadata (contest, year, difficulty, etc.)

**Example**:
```json
{
  "id": "APMO-2025-1",
  "problem": "Let ABC be an acute triangle...",
  "reference_solutions": ["Solution: First notice that..."],
  "contest": "APMO",
  "year": "2025"
}
```

---

### Expert Gradings (Optional)

**Location**: `data-dir/` (one of these names):
- `expert_gradings.jsonl`
- `evaluation_merged.jsonl`
- `evaluations.jsonl`

**Format**:
```json
{
  "problem_id": "APMO-2025-1",
  "model_name": "gpt-4",
  "score": 7.5,
  "comment": "Correct approach but missing final step"
}
```

**Required for**: Metrics computation

---

## Complete Workflow

### Step 1: Generate Solutions (Once)

```bash
python scripts/generate.py \
  --data-dir data/my_dataset \
  --models gpt-4 o3 gemini-2.5-pro
```

**Output**: `data/my_dataset/model_solutions.jsonl`

---

### Step 2: Evaluate with Multiple Evaluators (Many Times)

```bash
# Evaluate with gemini
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro

# Evaluate with gpt-4 (same solutions!)
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4

# Evaluate with o3
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model o3

# Try different workflow
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --workflow decompose-then-judge
```

**Output**: `data/my_dataset/outputs/evaluations/*.eval.jsonl`

---

### Step 3: Compute Metrics (Optional)

```bash
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --compute-metrics
```

**Requirements**: Expert gradings must exist in data-dir

**Output**: `data/my_dataset/metrics/` with correlation reports

---

## Output Structure

```
data/my_dataset/
├── problems.jsonl              # Your input
├── expert_gradings.jsonl       # Your expert scores (optional)
├── model_solutions.jsonl       # Generated solutions
└── outputs/
    └── evaluations/             # Evaluation results
        ├── evaluator_grades/
        │   └── my_dataset/
        │       ├── gpt-4.eval.jsonl
        │       ├── gemini-2.5-pro.eval.jsonl
        │       └── o3.eval.jsonl
        └── metrics/             # Metrics (if --compute-metrics)
            ├── per_evaluator_overall.csv
            └── per_generator_overall.csv
```

---

## Why Two Separate Scripts?

### 💰 Cost Savings
Generate expensive o3 solutions **once** ($100/1M tokens), then evaluate with 5+ different evaluators (cheap) without re-generating.

### 🔬 Fair Comparison
All evaluators see **identical solutions** - true apples-to-apples comparison.

### ⚡ Parallel Evaluations
Run multiple evaluations simultaneously:
```bash
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro &
python scripts/evaluate.py --data-dir data/test --model gpt-4 &
python scripts/evaluate.py --data-dir data/test --model o3 &
wait
```

### 🔄 Flexibility
Try different workflows on same solutions:
```bash
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro --workflow single
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro --workflow decompose-then-judge
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro --workflow reflect-and-revise
```

---

## Common Workflows

### Research: Compare Evaluator Quality

```bash
# 1. Generate once (expensive)
python scripts/generate.py \
  --data-dir data/my_dataset \
  --models gpt-4 o3 gemini-2.5-pro

# 2. Evaluate with multiple evaluators (cheap)
for evaluator in gemini-2.5-pro gpt-4 o3 claude-3-opus; do
  python scripts/evaluate.py \
    --data-dir data/my_dataset \
    --model $evaluator
done

# 3. Compare metrics
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --compute-metrics
```

---

### Production: Batch Processing

```bash
#!/bin/bash
# Generate solutions for multiple datasets
for dataset in pilot trials iclr_submission; do
  python scripts/generate.py \
    --data-dir data/evaluator_data/$dataset \
    --models gpt-4 gemini-2.5-pro
done

# Evaluate all datasets
for dataset in pilot trials iclr_submission; do
  python scripts/evaluate.py \
    --data-dir data/evaluator_data/$dataset \
    --model gemini-2.5-pro \
    --compute-metrics
done
```

---

### Testing: Quick Iteration

```bash
# Test with 5 problems
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 \
  --max-problems 5

python scripts/evaluate.py \
  --data-dir data/test \
  --model gemini-2.5-pro \
  --max-problems 5
```

---

## Data Validation

Both scripts include automatic validation:

**Default mode** (recommended):
```bash
python scripts/generate.py --data-dir data/test --models gpt-4
# Validates but continues on warnings
```

**Strict mode** (production):
```bash
python scripts/generate.py --data-dir data/test --models gpt-4 --strict-validation
# Exits immediately on any validation failure
```

**Skip mode** (fast):
```bash
python scripts/generate.py --data-dir data/test --models gpt-4 --skip-validation
# No validation (not recommended)
```

---

## Troubleshooting

### Issue: "Solutions file not found"

**Error when running evaluate.py**:
```
Solutions file not found: data/my_dataset/model_solutions.jsonl
Run generation first:
  python scripts/generate.py --data-dir data/my_dataset --models gpt-4
```

**Fix**: Run generation first!

---

### Issue: "Problems.jsonl not found"

**Error**:
```
problems.jsonl not found in data/my_dataset
```

**Fix**: Create problems file in the data directory:
```bash
echo '{"id": "prob1", "problem": "Your question here"}' > data/my_dataset/problems.jsonl
```

---

### Issue: "Duplicate solution IDs"

**Error**:
```
⚠️  Solution validation found issues
  CRITICAL: Duplicate solution IDs!
```

**Fix**: Delete `model_solutions.jsonl` and regenerate:
```bash
rm data/my_dataset/model_solutions.jsonl
python scripts/generate.py --data-dir data/my_dataset --models gpt-4
```

---

### Issue: Generation is slow

**Strategies**:

1. **Test with fewer problems first**:
```bash
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 \
  --max-problems 5
```

2. **Increase concurrency**:
```bash
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 \
  --max-concurrent 200
```

3. **Use faster models for testing**:
```bash
--models gemini-2.5-pro  # Faster than o3
```

4. **Monitor progress**: Shows real-time ETA:
```
Generating responses: 45/100 (45.0%) | 2.3/s | ETA: 24s
```

---

## Templates

Both scripts support custom templates:

**List available templates**:
```bash
python scripts/generate.py --list-templates
python scripts/evaluate.py --list-templates
```

**Get template details**:
```bash
python scripts/generate.py --template-info math
```

**Use custom template**:
```bash
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 \
  --template math
```

**Template locations**:
- Generation: `templates/generation.yaml`
- Evaluation: `templates/evaluation.yaml`
- Workflows: `templates/workflows.yaml`

---

## Metrics

Metrics compare evaluator predictions with expert gradings.

**Compute metrics**:
```bash
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --compute-metrics
```

**Requirements**:
- Expert gradings file exists in `data-dir/`
- Evaluations have been run

**Metrics computed**:
- Pearson correlation (linear relationship)
- Spearman correlation (rank-based)
- Kendall's tau-b (pairwise ordering)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Square Error)
- Bias (systematic over/under-prediction)

**Output**: `data-dir/metrics/*.csv`

---

## Advanced Usage

### Python API

```python
from proofgrader import InferenceEngine
from pathlib import Path

# Generate
engine = InferenceEngine(model_name="gpt-4")
# ... configure and run ...
```

### Custom Evaluation Workflow

Create workflow in `proofgrader/workflows/my_workflow.py`, then:

```bash
python scripts/evaluate.py \
  --data-dir data/test \
  --model gemini-2.5-pro \
  --workflow my-workflow
```

See `proofgrader/workflows/README.md` for details.

---

## FAQ

### Q: How do I generate from multiple models?

**A**: Use `--models` (plural) with space-separated model names:

```bash
python scripts/generate.py \
  --data-dir data/test \
  --models gpt-4 o3 gemini-2.5-pro
```

---

### Q: Can I evaluate the same solutions multiple times?

**A**: **Yes! This is the whole point.** Generate once, evaluate many times:

```bash
# Generate once
python scripts/generate.py --data-dir data/test --models gpt-4 o3

# Evaluate with different evaluators
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro
python scripts/evaluate.py --data-dir data/test --model gpt-4
python scripts/evaluate.py --data-dir data/test --model o3
python scripts/evaluate.py --data-dir data/test --model claude-3-opus
```

---

### Q: Where are solutions saved?

**A**: By default: `data-dir/model_solutions.jsonl`

Override with:
```bash
python scripts/generate.py --data-dir data/test --models gpt-4 --output custom.jsonl
```

---

### Q: Where are evaluations saved?

**A**: `data-dir/outputs/evaluations/evaluator_grades/data-version/*.eval.jsonl`

The exact location depends on workflow configuration.

---

### Q: How do I resume if generation fails?

**A**: Just re-run - caching is enabled by default:

```bash
# If interrupted, just run again
python scripts/generate.py --data-dir data/test --models gpt-4
# Skips already-completed problems
```

---

### Q: Can I run evaluations in parallel?

**A**: Yes!

```bash
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro &
python scripts/evaluate.py --data-dir data/test --model gpt-4 &
python scripts/evaluate.py --data-dir data/test --model o3 &
wait
```

---

## Quick Reference

### Essential Commands

```bash
# GENERATION (run once)
python scripts/generate.py --data-dir DATA_DIR --models MODEL1 MODEL2 MODEL3

# EVALUATION (run many times)
python scripts/evaluate.py --data-dir DATA_DIR --model EVALUATOR

# With metrics
python scripts/evaluate.py --data-dir DATA_DIR --model EVALUATOR --compute-metrics

# List templates
python scripts/generate.py --list-templates
python scripts/evaluate.py --list-templates

# Validate data
python proofgrader/data_validation.py --data-dir DATA_DIR
```

### Typical Workflow

```bash
# 1. Generate
python scripts/generate.py --data-dir data/my_dataset --models gpt-4 o3 gemini-2.5-pro

# 2. Evaluate with multiple evaluators
for eval in gemini-2.5-pro gpt-4 o3; do
  python scripts/evaluate.py --data-dir data/my_dataset --model $eval
done

# 3. Metrics
python scripts/evaluate.py --data-dir data/my_dataset --model gemini-2.5-pro --compute-metrics
```

---

## Key Files

| File | Purpose | Created By |
|------|---------|------------|
| `problems.jsonl` | Input problems | You (required) |
| `expert_gradings.jsonl` | Expert scores | You (optional, for metrics) |
| `model_solutions.jsonl` | Generated solutions | `generate.py` |
| `*.eval.jsonl` | Evaluations | `evaluate.py` |
| `metrics/*.csv` | Metrics reports | `evaluate.py --compute-metrics` |

---

## Project Structure

```
ProofGrader/
├── scripts/
│   ├── generate.py          ⭐ Generate solutions (run once)
│   └── evaluate.py          ⭐ Evaluate solutions (run many times)
│
├── proofgrader/             # Core library
│   ├── inference.py
│   ├── api_client.py
│   ├── data_validation.py
│   ├── workflow_runner.py
│   ├── workflows/           # Evaluation workflows
│   └── metrics/             # Metrics computation
│
├── templates/               # Prompt templates
│   ├── generation.yaml
│   ├── evaluation.yaml
│   └── workflows.yaml
│
└── data/                    # Your datasets
    └── my_dataset/
        ├── problems.jsonl            # You create this
        ├── expert_gradings.jsonl     # Optional
        ├── model_solutions.jsonl     # generate.py creates this
        └── outputs/                  # evaluate.py creates this
```

---

## Support

- 📝 GitHub Issues: [your-repo/issues]
- 📚 Additional docs:
  - `proofgrader/workflows/README.md` - Custom workflows
  - `RELEASE_CHECKLIST.md` - Release procedures

---

**That's everything!** Two simple scripts, complete independence, maximum flexibility. 🎉
