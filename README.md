# ProofGrader

A framework for generating and evaluating mathematical proofs using large language models.

## Overview

ProofGrader provides **three independent scripts**:
- **`generate.py`**: Generate solutions from multiple models (run once)
- **`generate_marking_schemes.py`**: Generate marking schemes for problems (optional, run once)
- **`evaluate.py`**: Evaluate solutions with workflows (run many times with different evaluators)

Generation and evaluation are completely separate. Generate expensive solutions once, optionally add marking schemes, then evaluate with multiple evaluators without re-generating.

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
```

### API Keys

```bash
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

export GOOGLE_APPLICATION_CREDENTIALS="your-credentials_json"

export OPENROUTER_API_KEY="your-api-key"
```
If you encounter problems with api calls, please refer to `proofgrader/api_client.py/_get_model_response_async` and modify it as you need.

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

### Step 1: Prepare Problems with Reference Solutions and Generate Marking Schemes

First, prepare your `problems.jsonl` with reference solutions:

```bash
mkdir -p data/my_dataset
# Add problems.jsonl with id, problem, reference_solutions fields
```

Then generate marking schemes (optional but recommended):

```bash
python scripts/generate_marking_schemes.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro \
  --overwrite
```

**Output**: `data/my_dataset/problems.jsonl` (now includes `marking_scheme` field)

---

### Step 2: Generate Solutions

Generate solutions from multiple models:

```bash
python scripts/generate.py \
  --data-dir data/my_dataset \
  --models gpt-4o o3 gemini-2.5-pro
```

**Output**: `data/my_dataset/model_solutions.jsonl`

---

### Step 3: Evaluate with Multiple Evaluators

```bash
# Basic evaluation
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro

# With marking schemes (if generated in Step 1)
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4o \
  --template with_marking_scheme_and_reference

# Different workflow
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model o3 \
  --workflow decompose-then-judge \
  --steps-model gemini-2.5-pro
```

**Output**: `data/my_dataset/evaluation_outputs/evaluator_gradings/`

---

### Step 4: (Optional) Gather Expert Gradings and Compute Metrics

If you have human expert scores, create `data/my_dataset/expert_gradings.jsonl`:

```json
{"problem_id": "problem-1", "model_name": "gpt-4o", "score": 6.0}
{"problem_id": "problem-1", "model_name": "o3", "score": 7.0}
```

Then compute metrics to compare evaluators against experts:

```bash
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --metrics-only
```

**Output**: `data/my_dataset/evaluation_outputs/metrics/`

See `EXPERT_GRADINGS_FORMAT.md` for details on creating ground truth data

---

## Output Structure

```
data/my_dataset/
├── problems.jsonl                      # Input (with marking_scheme if Step 1 done)
├── model_solutions.jsonl               # Step 2 output: Generated solutions
├── expert_gradings.jsonl              # Step 4 input: Human expert scores (optional)
└── evaluation_outputs/                 # All evaluation outputs
    ├── evaluation_runs/                # Step 3: Raw evaluator outputs
    │   ├── single__gemini-2.5-pro__basic__<timestamp>/
    │   └── single__gpt-4o__with_marking_scheme__<timestamp>/
    ├── evaluator_gradings/             # Step 3: Parsed per-generator scores
    │   ├── single__gemini-2.5-pro__basic/
    │   │   ├── gpt-4o.eval.jsonl
    │   │   ├── o3.eval.jsonl
    │   │   └── gemini-2.5-pro.eval.jsonl
    │   └── single__gpt-4o__with_marking_scheme/
    │       └── ...
    └── metrics/                        # Step 4: Metrics (if expert_gradings exist)
        ├── per_evaluator_overall.csv
        ├── per_evaluator_per_generator.csv
        └── per_evaluator_per_source.csv
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

