# ProofGrader

A comprehensive framework for generating and evaluating mathematical proofs using large language models.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Input Format](#input-format)
- [How to Run](#how-to-run)
- [Output Format](#output-format)
- [Data Validation](#data-validation)
- [Tools & Features](#tools--features)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)
- [FAQ](#faq)

---

## Overview

ProofGrader provides infrastructure for:
- **Generation**: Creating mathematical proofs/solutions with multiple LLMs (OpenAI, Google, Anthropic)
- **Evaluation**: Scoring and assessing proof quality (single-shot or multi-stage workflows)
- **Metrics**: Computing correlation and accuracy metrics against expert gradings
- **Validation**: Automatic data integrity checks at each pipeline stage

**Key Features**:
- ✅ One solution per (problem, generator) pair - simple and clean
- ✅ Automatic validation catches data issues before they cause problems
- ✅ Preserves `reference_solutions` throughout pipeline
- ✅ Supports multiple evaluation workflows (single-shot, decompose-then-judge, etc.)
- ✅ Computes comprehensive metrics (Pearson, Spearman, MAE, RMSE, etc.)

---

## Quick Start

### Which Script to Use?

| Task | Script | Key Flag | Example |
|------|--------|----------|---------|
| **Generate** multiple models | `run_full_workflow.py` | `--generators` + `--skip-evaluation` | `--generators gpt-4 o3 --skip-evaluation` |
| **Evaluate** existing solutions | `evaluate_workflow.py` | `--evaluator-model` | `--evaluator-model gemini-2.5-pro` |
| **Metrics** only | `run_full_workflow.py` | `--skip-generation --skip-evaluation` | `--compute-metrics` |
| Generate **single** model | `generate.py` | `--model` | `--model gpt-4` (1 model only!) |

**⚠️ Common mistakes**:
- ❌ `generate.py --model gpt-4 o3 ...` - Wrong! `generate.py` only accepts 1 model
- ❌ Running full pipeline with 1 evaluator then wanting to try another - Wastes time re-generating!

**✅ Correct approach**:
```bash
# Generate once
python scripts/run_full_workflow.py --generators gpt-4 o3 --skip-evaluation

# Evaluate multiple times (no re-generation!)
python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro --dataset outputs/model_solutions.jsonl ...
python scripts/evaluate_workflow.py --evaluator-model gpt-4 --dataset outputs/model_solutions.jsonl ...
```

---

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd ProofGrader

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API keys
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

### Your First Run

```bash
# Create a problems file
mkdir -p data/test
echo '{"id": "test1", "problem": "What is 2+2?"}' > data/test/problems.jsonl

# ════════════════════════════════════════════════
# STEP 1: GENERATION (Run once)
# ════════════════════════════════════════════════
python scripts/run_full_workflow.py \
  --data-dir data/test \
  --generators gpt-4 gemini-2.5-pro \
  --skip-evaluation  # ← Generation only!

# Solutions saved to: data/test/outputs/model_solutions.jsonl

# ════════════════════════════════════════════════
# STEP 2: EVALUATION (Can run multiple times!)
# ════════════════════════════════════════════════

# Evaluate with gemini
python scripts/evaluate_workflow.py \
  --evaluator-model gemini-2.5-pro \
  --workflow single \
  --dataset data/test/outputs/model_solutions.jsonl \
  --data-version test

# Evaluate with gpt-4 (same solutions, different evaluator!)
python scripts/evaluate_workflow.py \
  --evaluator-model gpt-4 \
  --workflow single \
  --dataset data/test/outputs/model_solutions.jsonl \
  --data-version test
```

**What happens**:

**Generation (Step 1)** - Run once:
1. ✅ Validates `problems.jsonl`
2. 📝 Generates solutions using GPT-4 and Gemini (2 solutions total)
3. 🔍 Validates solutions
4. ✅ Saves to `data/test/outputs/model_solutions.jsonl`

**Evaluation (Step 2)** - Run multiple times with different evaluators:
5. 🎯 Evaluates all solutions using specified evaluator
6. 🔍 Validates evaluations
7. ✅ Saves to `data/test/outputs/evaluations/<evaluator>.eval.jsonl`

**Key benefit**: Generate expensive o3/gpt-4 solutions **once**, then evaluate with 5+ different evaluators without re-generating!

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATION (Run Once)                         │
│                                                                  │
│  problems.jsonl                                                  │
│       ↓                                                          │
│  [Generator 1: gpt-4]  [Generator 2: o3]  [Generator 3: gemini] │
│       ↓                      ↓                    ↓              │
│  model_solutions.jsonl (N_problems × N_generators solutions)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ EVALUATION #1 │    │ EVALUATION #2 │    │ EVALUATION #3 │
│               │    │               │    │               │
│ Evaluator:    │    │ Evaluator:    │    │ Evaluator:    │
│ gemini-2.5    │    │ gpt-4         │    │ o3            │
│               │    │               │    │               │
│ Workflow:     │    │ Workflow:     │    │ Workflow:     │
│ single        │    │ decompose     │    │ reflect       │
│               │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        ↓                     ↓                     ↓
    eval_1/              eval_2/              eval_3/
        ↓                     ↓                     ↓
        └─────────────────────┴─────────────────────┘
                              ↓
                      ┌───────────────┐
                      │    METRICS    │
                      │               │
                      │ Compare all   │
                      │ evaluators    │
                      │ vs experts    │
                      └───────────────┘
```

**Key insight**: One generation → Many evaluations → Comprehensive comparison

---

## Input Format

### Problems File (Required)

**Location**: `data/your_dataset/problems.jsonl`

**Format**: One JSON object per line

**Required fields**:
- `id` (string): Unique problem identifier
- `problem` (string): Problem statement/question

**Optional but recommended**:
- `reference_solutions` (list): Ground truth solutions - **preserved throughout pipeline**
- Any other metadata fields (contest, year, difficulty, source, etc.)

**Complete Example**:
```json
{
  "id": "APMO-2025-1",
  "problem": "Let ABC be an acute triangle inscribed in a circle Γ. Let A₁ be the orthogonal projection of A onto BC so that AA₁ is an altitude...",
  "reference_solutions": [
    "Solution: First notice that, since angles ∠AA₁B₁ and ∠AA₁C₁ are both right...",
    "Alternative approach: Using similar triangles..."
  ],
  "contest": "APMO",
  "year": "2025",
  "problem_number": "1",
  "difficulty": "hard",
  "source_pdf": "apmo_2025.pdf"
}
```

**Minimal Example**:
```json
{"id": "prob1", "problem": "Prove that √2 is irrational."}
```

---

### Expert Gradings (Optional - for metrics)

**Location**: `data/your_dataset/` (same directory as `problems.jsonl`)

**File names** (script auto-detects):
- `expert_gradings.jsonl`
- `evaluation_merged.jsonl`
- `evaluations.jsonl`

**Format**: One JSON object per line

**Required fields**:
- `problem_id` (string): Must match problem ID
- `model_name` (string): Model that generated solution
- `score` (number): Expert score (typically 0-10)

**Optional**:
- `comment` (string): Expert feedback/reasoning

**Example**:
```json
{
  "problem_id": "APMO-2025-1",
  "model_name": "gpt-4",
  "score": 7.5,
  "comment": "Correct approach using similar triangles. Minor gap in final step (parity argument needed)."
}
```

**Why you need this**: If expert gradings exist, the pipeline automatically computes:
- Correlation metrics (how well LLM evaluations match expert scores)
- Error metrics (MAE, RMSE, bias)
- Ranking quality (order preservation)

---

## How to Run

**Philosophy**: Generation and evaluation are **completely independent**. 

**Why separate them?**
- ✅ Generate expensive solutions once (e.g., o3 is costly)
- ✅ Evaluate same solutions with multiple evaluators (compare evaluator quality)
- ✅ Try different evaluation strategies without re-generating
- ✅ Save time and money

### Recommended Workflow: Separate Generation and Evaluation

**TL;DR**:
```bash
# 1️⃣ Generate (once)
python scripts/run_full_workflow.py --data-dir DIR --generators MODEL1 MODEL2 --skip-evaluation

# 2️⃣ Evaluate (multiple times with different evaluators)
python scripts/evaluate_workflow.py --evaluator-model EVAL1 --dataset DIR/outputs/model_solutions.jsonl ...
python scripts/evaluate_workflow.py --evaluator-model EVAL2 --dataset DIR/outputs/model_solutions.jsonl ...

# 3️⃣ Metrics
python scripts/run_full_workflow.py --data-dir DIR --skip-generation --skip-evaluation --compute-metrics
```

#### Step 1: Generate Solutions (Once)

```bash
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 o3 gemini-2.5-pro \
  --skip-evaluation  # Generation only!
```

This creates `data/my_dataset/outputs/model_solutions.jsonl` with solutions from all 3 models.

#### Step 2: Evaluate with Different Evaluators (Multiple Times)

Now evaluate the **same solutions** with different evaluators:

```bash
# Evaluate with gemini-2.5-pro
python scripts/evaluate_workflow.py \
  --evaluator-model gemini-2.5-pro \
  --workflow single \
  --dataset data/my_dataset/outputs/model_solutions.jsonl \
  --data-version my_dataset

# Evaluate with gpt-4 (different evaluator, same solutions!)
python scripts/evaluate_workflow.py \
  --evaluator-model gpt-4 \
  --workflow single \
  --dataset data/my_dataset/outputs/model_solutions.jsonl \
  --data-version my_dataset

# Evaluate with o3 (yet another evaluator!)
python scripts/evaluate_workflow.py \
  --evaluator-model o3 \
  --workflow single \
  --dataset data/my_dataset/outputs/model_solutions.jsonl \
  --data-version my_dataset
```

**Result**: Same solutions evaluated by 3 different evaluators - perfect for comparing evaluator quality!

#### Step 3: Compute Metrics

```bash
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --skip-generation \
  --skip-evaluation \
  --compute-metrics
```

---

### Alternative: All-in-One (Quick but Coupled)

If you want everything in one command (not recommended for research):

```bash
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 gemini-2.5-pro \
  --evaluator gemini-2.5-pro \
  --compute-metrics
```

**Limitation**: Only one evaluator. For multiple evaluators, use the separated workflow above.

**Common Options**:
```bash
# Basic options
--data-dir PATH              # Directory with problems.jsonl (required)
--generators MODEL1 MODEL2   # Models for generation (default: gpt-4)
--evaluator MODEL            # Model for evaluation (default: gemini-2.5-pro)

# Control what runs
--skip-generation           # Use existing solutions
--skip-evaluation           # Skip evaluation step
--compute-metrics           # Compute metrics if expert gradings exist

# Validation
--strict-validation         # Exit immediately on any validation failure
--skip-validation           # Skip all validation (not recommended)

# Performance
--max-concurrent N          # Max concurrent API requests (default: 100)
--max-problems N            # Process only first N problems (for testing)

# Output
--output-dir PATH           # Custom output directory (default: data-dir/outputs)
```

**Full Example**:
```bash
python scripts/run_full_workflow.py \
  --data-dir data/evaluator_data/pilot \
  --generators gpt-4 gemini-2.5-pro deepseek-r1 \
  --evaluator gemini-2.5-pro \
  --workflow single \
  --compute-metrics \
  --strict-validation \
  --max-concurrent 50
```

---

### Option 2: Step-by-Step

For more control, run each stage separately:

#### Step 1: Generate Solutions

**⚠️ Important**: `generate.py` accepts **only ONE model**. For multiple models, use Option 1 (`run_full_workflow.py`).

```bash
# Single model
python scripts/generate.py \
  --model gpt-4 \
  --dataset data/my_dataset/problems.jsonl \
  --template default \
  --output data/my_dataset/solutions_gpt4.jsonl \
  --max-concurrent 100

# For multiple models, you MUST use run_full_workflow.py:
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 gemini-2.5-pro o3
```

**Key Options**:
- `--model`: **Single model name** (gpt-4, gemini-2.5-pro, claude-3-opus, etc.)
- `--dataset`: Path to problems.jsonl
- `--template`: Prompt template (use `--list-templates` to see all)
- `--output`: Where to save results
- `--max-examples`: Limit number of problems (for testing)
- `--no-cache`: Disable caching (re-generate even if already done)

**List available templates**:
```bash
python scripts/generate.py --list-templates
```

**Output**: `solutions_gpt4.jsonl` with fields:
- All original problem fields
- `problem_id`: Problem identifier
- `generator`: Model name
- `solution`: Generated solution text
- `reference_solutions`: Preserved from input
- `generation_metadata`: Model settings used

#### Step 2: Evaluate Solutions

**Simple evaluation**:
```bash
python scripts/evaluate.py \
  --model gemini-2.5-pro \
  --dataset data/my_dataset/solutions_gpt4.jsonl \
  --template evaluation \
  --output data/my_dataset/evaluations.jsonl
```

**Advanced workflows**:
```bash
python scripts/evaluate_workflow.py \
  --evaluator-model gemini-2.5-pro \
  --workflow decompose-then-judge \
  --steps-model gpt-4 \
  --dataset data/my_dataset/solutions_gpt4.jsonl \
  --data-version my_dataset
```

**Available Workflows**:

| Workflow | Description | When to Use |
|----------|-------------|-------------|
| `single` | Basic single-shot evaluation | Default, fast |
| `decompose-then-judge` | Break into steps, then evaluate | Complex proofs |
| `repeat-and-aggregate` | Multiple evaluations, aggregate | Reduce variance |
| `reflect-and-revise` | Self-critique and revision | Improve quality |

**Output**: `*.eval.jsonl` files with fields:
- `id`: Problem ID
- `generator`: Model name
- `score`: Evaluation score
- `assessment`: Detailed evaluation text
- `comments`: Specific feedback

#### Step 3: Compute Metrics (if expert gradings exist)

Metrics are computed automatically with `--compute-metrics`, but can also run manually:

```bash
python proofgrader/metrics/compute_evaluator_distances.py \
  --merged-path data/my_dataset/expert_gradings.jsonl \
  --eval-dir data/my_dataset/outputs/evaluations \
  --out-dir data/my_dataset/outputs/metrics
```

**Metrics computed**:
- **Pearson correlation**: Linear relationship between LLM and expert scores
- **Spearman correlation**: Rank-based correlation
- **Kendall's tau-b**: Pairwise ordering agreement
- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Square Error
- **Bias**: Systematic over/under-prediction
- **Within-tolerance accuracy**: % predictions within ±1 point

---

## Output Format

### Directory Structure

After running the pipeline:
```
data/my_dataset/
├── problems.jsonl              # Your input
├── expert_gradings.jsonl       # Your expert scores (optional)
└── outputs/
    ├── model_solutions.jsonl   # Generated solutions
    ├── evaluations/             # Evaluation results
    │   ├── gpt-4.eval.jsonl
    │   ├── gemini-2.5-pro.eval.jsonl
    │   └── deepseek-r1.eval.jsonl
    └── metrics/                 # Metrics (if expert gradings exist)
        ├── per_evaluator_overall.csv
        ├── per_generator_overall.csv
        ├── disagreement_per_item.csv
        └── order_preservation_overall.csv
```

### Generated Solutions (`model_solutions.jsonl`)

One JSON object per line:
```json
{
  "problem_id": "APMO-2025-1",
  "generator": "gpt-4",
  "solution": "To solve this problem, we start by...",
  "problem": "Let ABC be an acute triangle...",
  "reference_solutions": ["Solution: First notice..."],
  "model": "gpt-4",
  "generation_metadata": {
    "model": "gpt-4",
    "temperature": 0.6,
    "max_tokens": 65536,
    "template": "default"
  },
  "contest": "APMO",
  "year": "2025"
}
```

**Key points**:
- One solution per `(problem_id, generator)` pair
- All original problem fields preserved
- `reference_solutions` preserved for later comparison

### Evaluation Results (`*.eval.jsonl`)

One file per generator:
```json
{
  "id": "APMO-2025-1",
  "unique_id": "APMO-2025-1::gpt-4",
  "generator": "gpt-4",
  "score": 7.5,
  "assessment": "The solution correctly identifies the key geometric relationships...",
  "comments": "Minor gap in the final step regarding parity."
}
```

### Metrics Reports (CSV files)

**per_evaluator_overall.csv**: How well each evaluator correlates with experts
```csv
evaluator,count,mae,rmse,pearson,spearman,kendall_tau_b
gemini-2.5-pro,90,0.8,1.2,0.85,0.82,0.70
```

**per_generator_overall.csv**: Metrics broken down by generator
```csv
evaluator,generator,count,mae,rmse,pearson,spearman
gemini-2.5-pro,gpt-4,30,0.7,1.0,0.88,0.85
gemini-2.5-pro,deepseek-r1,30,0.9,1.3,0.82,0.79
```

---

## Data Validation

ProofGrader automatically validates data at each stage to catch issues early.

### Validation Modes

**1. Default (Recommended)**
```bash
python scripts/run_full_workflow.py --data-dir data/test --generators gpt-4
```
- ✅ Validates at each stage
- ⚠️ Logs warnings but **continues execution**
- Best for: Development, exploration

**2. Strict Mode (Production)**
```bash
python scripts/run_full_workflow.py --data-dir data/test --generators gpt-4 --strict-validation
```
- ✅ Validates at each stage
- ❌ **Exits immediately** on any failure
- Best for: Production pipelines, critical workflows

**3. Skip Mode (Fast but Risky)**
```bash
python scripts/run_full_workflow.py --data-dir data/test --generators gpt-4 --skip-validation
```
- ❌ No validation
- ⚡ Fastest
- Best for: Known-good data, maximum speed

### What Gets Validated

#### ✅ Before Generation (Problems):
- All problems have unique IDs
- No duplicate problem IDs
- All problems have required fields (`id`, `problem`)
- No empty problem statements

#### ✅ After Generation (Solutions):
- All solutions reference valid problems (no orphans)
- Unique `(problem_id, generator)` composite keys
- All solutions have required fields
- `reference_solutions` preserved from problems
- No duplicate solutions

#### ✅ After Evaluation:
- All evaluations match existing solutions
- All evaluations have scores
- No duplicate evaluations
- No missing evaluations for generated solutions

### Example Output

**Success**:
```
================================================================================
PROOFGYM FULL WORKFLOW
================================================================================
Data directory: data/test_data
Generators: ['gpt-4', 'gemini-2.5-pro']
Evaluator: gemini-2.5-pro
Validation: Enabled ✅
================================================================================

🔍 Validating input problems...
INFO -   ✓ All 30 problems have valid unique IDs
✓ Problem validation passed

📝 Generating solutions...
✓ Generated 60 solutions (30 problems × 2 generators)

🔍 Validating generated solutions...
INFO -   ✓ All 60 solutions have valid unique IDs
✓ Solution validation passed

🎯 Running evaluations...
✓ Evaluation completed

🔍 Validating evaluations...
INFO -   ✓ All 60 evaluations have valid IDs
✓ Evaluation validation passed
```

**With Issues (Default mode)**:
```
🔍 Validating generated solutions...
⚠️  Solution validation found issues
  CRITICAL: Duplicate solution IDs detected!
  WARNING: 3 orphan solutions (referencing non-existent problems)
# Continues anyway...
```

**With Issues (Strict mode)**:
```
🔍 Validating generated solutions...
⚠️  Solution validation found issues
  CRITICAL: Duplicate solution IDs detected!
ERROR - Exiting due to --strict-validation
```

### Manual Validation

Validate data without running the full pipeline:

```bash
python proofgrader/data_validation.py --data-dir data/my_dataset

# Output:
# ================================================================================
# DATA VALIDATION
# ================================================================================
# ✓ Problems: 30 (all valid)
# ✓ Solutions: 60 (30 × 2 generators)
# ✓ Evaluations: 60 (complete)
# ✓ Expert Gradings: 30
# ✓ OVERALL: PASSED
# ================================================================================
```

---

## Tools & Features

### 1. Template System

Templates control how prompts are formatted.

**List available templates**:
```bash
python scripts/generate.py --list-templates

# Output:
# ================================================================================
# Available Templates for Generation
# ================================================================================
# default              - Standard problem-solving template
#                        Variables: problem
# math                 - Math-specific with step-by-step format
#                        Variables: problem
# cot                  - Chain-of-thought reasoning
#                        Variables: problem
```

**Get template details**:
```bash
python scripts/generate.py --template-info math

# Output:
# Template: Math Template
# ==================================================
# Description: Math-specific with step-by-step format
# Variables: problem
```

**Template locations**:
- Generation: `templates/generation.yaml`
- Evaluation: `templates/evaluation.yaml`
- Workflows: `templates/workflows.yaml`

**Create custom template**:

Edit `templates/generation.yaml`:
```yaml
my_custom:
  name: "My Custom Template"
  description: "Template for competition math"
  template: |
    Problem: {problem}
    
    Please provide a detailed solution with clear steps.
    Format your answer clearly.
  variables:
    - problem
  system_prompt: "You are an expert mathematician."
```

**Use custom template**:
```bash
python scripts/generate.py --template my_custom --dataset problems.jsonl
```

---

### 2. Result Analysis

**Quick statistics**:
```python
import json

# Load evaluations
with open('outputs/evaluations/gpt-4.eval.jsonl') as f:
    evals = [json.loads(line) for line in f]

scores = [e['score'] for e in evals if 'score' in e]
print(f"Average: {sum(scores)/len(scores):.2f}")
print(f"Min: {min(scores):.2f}, Max: {max(scores):.2f}")
print(f"Median: {sorted(scores)[len(scores)//2]:.2f}")
```

**Find best/worst solutions**:
```python
sorted_evals = sorted(evals, key=lambda x: x.get('score', 0), reverse=True)

print("🏆 Top 5 solutions:")
for e in sorted_evals[:5]:
    print(f"  {e['id']}: {e['score']:.1f} - {e.get('comments', 'No comments')[:50]}...")

print("\n⚠️  Bottom 5 solutions:")
for e in sorted_evals[-5:]:
    print(f"  {e['id']}: {e['score']:.1f} - {e.get('comments', 'No comments')[:50]}...")
```

**Compare models**:
```python
import json
from collections import defaultdict

# Load all evaluations
model_scores = defaultdict(list)

for model in ['gpt-4', 'gemini-2.5-pro']:
    with open(f'outputs/evaluations/{model}.eval.jsonl') as f:
        for line in f:
            e = json.loads(line)
            model_scores[model].append(e['score'])

# Compare
for model, scores in model_scores.items():
    avg = sum(scores) / len(scores)
    print(f"{model}: avg={avg:.2f}, n={len(scores)}")
```

---

### 3. Data Format Checker

**Verify before running**:
```python
import json

# Check problems
with open('data/test/problems.jsonl') as f:
    problems = [json.loads(line) for line in f]

print(f"Total problems: {len(problems)}")

# Verify required fields
for i, p in enumerate(problems):
    assert 'id' in p, f"Problem {i} missing 'id'"
    assert 'problem' in p, f"Problem {i} missing 'problem'"

print("✓ All problems have required fields")

# Check for duplicates
ids = [p['id'] for p in problems]
assert len(ids) == len(set(ids)), "Duplicate IDs found!"
print("✓ All IDs are unique")

# Check optional fields
with_ref = sum(1 for p in problems if 'reference_solutions' in p)
print(f"✓ {with_ref}/{len(problems)} problems have reference_solutions")
```

---

### 4. Evaluating with Multiple Evaluators (Recommended Pattern)

**Core principle**: Generate once, evaluate many times with different evaluators.

**Complete example**:
```bash
#!/bin/bash
DATA_DIR="data/my_dataset"

# ═══════════════════════════════════════════════════════════
# STEP 1: GENERATION (Run once, expensive)
# ═══════════════════════════════════════════════════════════
echo "Generating solutions..."
python scripts/run_full_workflow.py \
  --data-dir $DATA_DIR \
  --generators gpt-4 o3 openrouter/qwen/qwen3-235b-a22b-thinking-2507 gemini-2.5-pro \
  --skip-evaluation  # GENERATION ONLY

# ═══════════════════════════════════════════════════════════
# STEP 2: EVALUATION (Run multiple times, independent)
# ═══════════════════════════════════════════════════════════
SOLUTIONS="$DATA_DIR/outputs/model_solutions.jsonl"

# Evaluate with different evaluators
for evaluator in gemini-2.5-pro gpt-4 o3 claude-3-opus; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Evaluating with: $evaluator"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  python scripts/evaluate_workflow.py \
    --evaluator-model $evaluator \
    --workflow single \
    --dataset $SOLUTIONS \
    --data-version my_dataset
done

# Try different workflows with same evaluator
for workflow in single decompose-then-judge reflect-and-revise; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Workflow: $workflow (evaluator: gemini-2.5-pro)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  python scripts/evaluate_workflow.py \
    --evaluator-model gemini-2.5-pro \
    --workflow $workflow \
    --dataset $SOLUTIONS \
    --data-version my_dataset
done

# ═══════════════════════════════════════════════════════════
# STEP 3: METRICS (Compare all evaluators)
# ═══════════════════════════════════════════════════════════
echo "Computing metrics..."
python scripts/run_full_workflow.py \
  --data-dir $DATA_DIR \
  --skip-generation \
  --skip-evaluation \
  --compute-metrics

echo ""
echo "✅ COMPLETE! Generated once, evaluated multiple times."
```

**Why this is better**:
- 💰 Generate expensive o3 solutions **once** (saves money)
- 🔬 Compare 4+ different evaluators on **identical solutions**
- 🔄 Try different workflows (single, decompose, reflect) on **same data**
- ⚡ Run evaluations in parallel if needed
- 📊 Fair comparison - all evaluators see exact same inputs

**Process multiple datasets**:
```bash
#!/bin/bash
for dataset in pilot trials iclr_submission; do
  echo "========================================="
  echo "Processing $dataset..."
  echo "========================================="
  
  # Generate solutions
  python scripts/run_full_workflow.py \
    --data-dir data/evaluator_data/$dataset \
    --generators gpt-4 gemini-2.5-pro \
    --skip-evaluation
  
  # Evaluate with multiple evaluators
  for evaluator in gemini-2.5-pro gpt-4; do
    python scripts/evaluate_workflow.py \
      --evaluator-model $evaluator \
      --workflow single \
      --dataset data/evaluator_data/$dataset/outputs/model_solutions.jsonl \
      --data-version $dataset
  done
done
```

---

## Troubleshooting

### Issue: "unrecognized arguments" when using multiple models

**Error**:
```
generate.py: error: unrecognized arguments: o3 gemini-2.5-pro
```

**Cause**: `generate.py` only accepts **one model**. You're trying to pass multiple models.

**Fix**: Use `run_full_workflow.py` with `--generators` instead:

```bash
# ❌ Wrong - generate.py doesn't support multiple models
python scripts/generate.py --model gpt-4 o3 gemini-2.5-pro --dataset ...

# ✅ Correct - use run_full_workflow.py with --generators
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 o3 gemini-2.5-pro
```

**Alternative**: Run `generate.py` separately for each model:
```bash
for model in gpt-4 o3 gemini-2.5-pro; do
  python scripts/generate.py \
    --model $model \
    --dataset data/my_dataset/problems.jsonl \
    --output data/my_dataset/solutions_${model}.jsonl
done
```

---

### Issue: "Missing problem IDs"

**Error**:
```
❌ Problem validation failed!
  5 problems without IDs
```

**Cause**: Some problems in `problems.jsonl` don't have `id` field

**Fix**:
```python
import json

# Load problems
with open('problems.jsonl') as f:
    problems = [json.loads(line) for line in f]

# Add IDs
for i, p in enumerate(problems):
    if 'id' not in p:
        p['id'] = f"problem_{i+1}"

# Save
with open('problems.jsonl', 'w') as f:
    for p in problems:
        f.write(json.dumps(p) + '\n')

print(f"✓ Added IDs to {len(problems)} problems")
```

---

### Issue: "Duplicate problem IDs"

**Error**:
```
❌ Problem validation failed!
  Duplicate problem IDs: ['prob1', 'prob2']
```

**Cause**: Same ID used for multiple problems

**Find duplicates**:
```python
import json
from collections import Counter

with open('problems.jsonl') as f:
    problems = [json.loads(line) for line in f]

ids = [p.get('id') for p in problems if p.get('id')]
duplicates = [id for id, count in Counter(ids).items() if count > 1]

print(f"Duplicate IDs: {duplicates}")

# Find which lines
for dup_id in duplicates:
    lines = [i for i, p in enumerate(problems) if p.get('id') == dup_id]
    print(f"  {dup_id}: appears at lines {lines}")
```

**Fix**: Make IDs unique:
```python
# Add suffix to duplicates
seen = {}
for p in problems:
    id = p['id']
    if id in seen:
        seen[id] += 1
        p['id'] = f"{id}_{seen[id]}"
    else:
        seen[id] = 1

# Save
with open('problems.jsonl', 'w') as f:
    for p in problems:
        f.write(json.dumps(p) + '\n')
```

---

### Issue: "Duplicate solution IDs"

**Error**:
```
⚠️  Solution validation found issues
  CRITICAL: Duplicate solution IDs detected!
```

**Cause**: Same `(problem_id, generator)` pair appears multiple times in `model_solutions.jsonl`

**Diagnose**:
```python
import json
from collections import Counter

with open('model_solutions.jsonl') as f:
    solutions = [json.loads(line) for line in f]

keys = [(s['problem_id'], s['generator']) for s in solutions]
duplicates = [k for k, count in Counter(keys).items() if count > 1]

print(f"Duplicates: {duplicates}")
for pid, gen in duplicates:
    indices = [i for i, k in enumerate(keys) if k == (pid, gen)]
    print(f"  ({pid}, {gen}): appears at indices {indices}")
```

**Fix**: Keep only first occurrence:
```python
seen = set()
unique_solutions = []

for sol in solutions:
    key = (sol['problem_id'], sol['generator'])
    if key not in seen:
        unique_solutions.append(sol)
        seen.add(key)

print(f"Removed {len(solutions) - len(unique_solutions)} duplicates")

# Save
with open('model_solutions.jsonl', 'w') as f:
    for sol in unique_solutions:
        f.write(json.dumps(sol) + '\n')
```

---

### Issue: "Orphan solutions"

**Error**:
```
⚠️  Solution validation found issues
  WARNING: 3 orphan solutions (referencing non-existent problems)
```

**Cause**: Solutions reference `problem_id` values that don't exist in `problems.jsonl`

**Find orphans**:
```python
import json

# Load problems
with open('problems.jsonl') as f:
    problems = [json.loads(line) for line in f]
problem_ids = {p['id'] for p in problems}

# Load solutions
with open('model_solutions.jsonl') as f:
    solutions = [json.loads(line) for line in f]

# Find orphans
orphans = [s for s in solutions if s['problem_id'] not in problem_ids]
print(f"Orphan solutions: {len(orphans)}")
for s in orphans[:5]:
    print(f"  {s['problem_id']} (generator: {s['generator']})")
```

**Fix**: Either add missing problems or remove orphans

---

### Issue: "Missing evaluations"

**Error**:
```
⚠️  Evaluation validation found issues
  15 solutions without evaluations
```

**Cause**: Evaluation workflow didn't process all solutions

**Find which are missing**:
```python
import json

# Load solutions
with open('model_solutions.jsonl') as f:
    solutions = [json.loads(line) for line in f]
solution_keys = {(s['problem_id'], s['generator']) for s in solutions}

# Load evaluations
eval_keys = set()
for eval_file in Path('outputs/evaluations').glob('*.eval.jsonl'):
    with open(eval_file) as f:
        for line in f:
            e = json.loads(line)
            eval_keys.add((e['id'], e['generator']))

# Find missing
missing = solution_keys - eval_keys
print(f"Missing evaluations: {len(missing)}")
for pid, gen in list(missing)[:10]:
    print(f"  ({pid}, {gen})")
```

**Fix**: Re-run evaluation:
```bash
python scripts/evaluate_workflow.py \
  --evaluator-model gemini-2.5-pro \
  --workflow single \
  --dataset data/my_dataset/outputs/model_solutions.jsonl
```

---

### Issue: "API rate limits"

**Error**: `RateLimitError` from API

**Fix 1**: Reduce concurrent requests:
```bash
python scripts/run_full_workflow.py \
  --data-dir data/test \
  --generators gpt-4 \
  --max-concurrent 10  # Lower from default 100
```

**Fix 2**: Add delays (edit `proofgrader/api_client.py` rate limiters):
```python
# In api_client.py
RATE_LIMITS = {
    "gemini": 60,   # Lower from 300
    "openai": 50,   # Lower from 500
}
```

---

### Issue: "Out of memory"

**Symptoms**: Process crashes or system becomes unresponsive

**Fix 1**: Process in smaller batches:
```bash
python scripts/run_full_workflow.py \
  --data-dir data/test \
  --generators gpt-4 \
  --max-problems 50  # Process first 50 only
```

**Fix 2**: Run separately for each generator:
```bash
# Generate separately
for model in gpt-4 gemini-2.5-pro; do
  python scripts/generate.py \
    --model $model \
    --dataset problems.jsonl \
    --output solutions_$model.jsonl
done

# Then evaluate
```

---

### Issue: "Empty response from LLM"

**Symptoms**: Solutions or evaluations have empty text

**Check**: Look for empty responses:
```python
import json

with open('model_solutions.jsonl') as f:
    solutions = [json.loads(line) for line in f]

empty = [s for s in solutions if not s.get('solution', '').strip()]
print(f"Empty solutions: {len(empty)}")
for s in empty[:5]:
    print(f"  {s['problem_id']} (generator: {s['generator']})")
```

**Fix**: Re-run for those specific problems or adjust temperature/max_tokens

---

### Issue: "Template not found"

**Error**: `Template 'xyz' not found`

**Fix**: List available templates:
```bash
python scripts/generate.py --list-templates
```

Use one of the listed templates or create a custom one.

---

## Advanced Usage

### Python API

Use ProofGrader as a Python library:

```python
from proofgrader import InferenceEngine, config
from pathlib import Path

# Configure
config.dataset_name = "data/test/problems.jsonl"
config.output_path = "outputs/results.jsonl"
config.max_tokens = 4096
config.temperature = 0.7

# Generate
engine = InferenceEngine(model_name="gpt-4")
success = engine.run_inference(
    template="default",
    max_concurrent=50,
    use_cache=True
)

print(f"Success: {success}")
```

---

### Custom Evaluation Workflow

Create new workflow in `proofgrader/workflows/my_workflow.py`:

```python
from pathlib import Path
from .utils import run_main, write_per_generator_eval

def run_workflow(args):
    """Custom two-stage workflow."""
    
    # Stage 1: First evaluation
    stage1_output = run_main(
        evaluator_model=args.evaluator_model,
        template_name='initial_review',
        dataset_path=Path(args.dataset),
        output_path=args.dump_dir / 'stage1_raw.jsonl'
    )
    
    # Stage 2: Refinement
    stage2_output = run_main(
        evaluator_model=args.evaluator_model,
        template_name='refined_review',
        dataset_path=stage1_output,
        output_path=args.dump_dir / 'stage2_raw.jsonl'
    )
    
    # Parse final results
    write_per_generator_eval(
        evaluator_tag=args.evaluator_tag,
        raw_results_path=stage2_output,
        dataset_path=Path(args.dataset),
        mirror_dir=args.mirror_dir
    )
    
    return stage2_output
```

Register in `proofgrader/workflows/__init__.py`:
```python
from .my_workflow import run_workflow as my_workflow

WORKFLOWS = {
    'my-workflow': my_workflow,
    # ... existing workflows
}
```

Use it:
```bash
python scripts/evaluate_workflow.py --workflow my-workflow ...
```

---

### Environment Variables

**API Keys**:
```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Google Vertex AI** (for Gemini):
```bash
export GEMINI_PROJECT_ID="your-project-id"
export GEMINI_LOCATION="us-central1"
```

**Timeouts and limits**:
Edit `proofgrader/api_client.py`:
```python
DEFAULT_TIMEOUT = 2400  # 40 minutes
RATE_LIMITS = {
    "gemini": 300,
    "openai": 500,
}
```

---

## FAQ

### Q: How many solutions per problem?

**A**: One solution per `(problem, generator)` pair. Simple and clean.

If you have 30 problems and 3 generators, you get exactly 90 solutions.

---

### Q: Can I evaluate the same solutions with multiple evaluators?

**A**: **Yes! This is the recommended approach.** Generate once, evaluate multiple times:

```bash
# 1. Generate once
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 o3 gemini-2.5-pro \
  --skip-evaluation

# 2. Evaluate with different evaluators
for evaluator in gemini-2.5-pro gpt-4 o3 claude-3-opus; do
  python scripts/evaluate_workflow.py \
    --evaluator-model $evaluator \
    --dataset data/my_dataset/outputs/model_solutions.jsonl \
    --data-version my_dataset
done
```

**Why this is better**:
- ✅ Generation and evaluation are independent
- ✅ Don't waste time/money re-generating solutions
- ✅ Compare different evaluators on same solutions
- ✅ Run evaluations in parallel if needed

---

### Q: Why separate generation and evaluation?

**A**: 
- **Research**: Compare evaluator quality on the same solutions (fair comparison)
- **Cost**: Don't re-generate expensive solutions (o3 costs ~$100/1M tokens)
- **Flexibility**: Try different evaluation strategies on same data
- **Reproducibility**: Fixed solutions = consistent comparisons
- **Independence**: Evaluation should not depend on generation process

**Example use case**:
```
Generate 100 solutions with o3 (expensive, run once)
   ↓
Evaluate with 5 different evaluators (cheap, run multiple times)
   ↓
Compare which evaluator best matches expert scores
```

Without separation, you'd waste money re-generating o3 solutions 5 times!

---

### Q: Can I run evaluations in parallel?

**A**: Yes! Since evaluations are independent, you can run them in parallel:

```bash
# Run 4 evaluations simultaneously
python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro ... &
python scripts/evaluate_workflow.py --evaluator-model gpt-4 ... &
python scripts/evaluate_workflow.py --evaluator-model o3 ... &
python scripts/evaluate_workflow.py --evaluator-model claude-3-opus ... &
wait

echo "All evaluations complete!"
```

This dramatically speeds up the evaluation phase.

---

### Q: Can I use multiple attempts per model?

**A**: The system is designed for one solution per generator for simplicity. 

If you need multiple attempts, run generation multiple times with different output files.

---

### Q: What if I don't have expert gradings?

**A**: That's fine! The pipeline works without them. You just won't get metrics computation.

You'll still get:
- ✅ Generated solutions
- ✅ LLM evaluations
- ✅ All validation checks

---

### Q: How do I add a new LLM provider?

**A**: Edit `proofgrader/api_client.py` and add your provider's API calls. Follow the pattern of existing providers (OpenAI, Google, Anthropic).

---

### Q: Can I use local models?

**A**: Yes! Use `vllm_client.py` for local model inference with vLLM. See `proofgrader/vllm_client.py` for details.

---

### Q: How do I customize evaluation prompts?

**A**: Edit templates in `templates/evaluation.yaml`. You can create completely custom evaluation criteria.

---

### Q: What score scale should I use?

**A**: The system is flexible. Common scales:
- 0-10 (recommended for nuance)
- 0-100 (percentage-style)
- Binary (0/1 for correct/incorrect)

Just be consistent across expert gradings and evaluations.

---

### Q: How do I handle very long problems?

**A**: Adjust `max_tokens` in config:
```python
# In proofgrader/config.py
config.max_tokens = 65536  # Increase limit
```

Or use models with larger context windows (Gemini 2.0, GPT-4 Turbo, Claude 3).

---

### Q: Can I resume a failed run?

**A**: Yes! Caching is enabled by default. Just re-run the same command - it will skip already-completed problems.

To force regeneration:
```bash
python scripts/run_full_workflow.py ... --no-cache
```

---

### Q: Generation is taking too long. How can I speed it up?

**A**: Several strategies:

**1. Increase concurrency** (default is 100):
```bash
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 \
  --max-concurrent 200  # Process more in parallel
```

**2. Test with fewer problems first**:
```bash
python scripts/run_full_workflow.py \
  --data-dir data/my_dataset \
  --generators gpt-4 \
  --max-problems 5  # Test with 5 problems first
```

**3. Use faster models for testing**:
```bash
# gpt-4 is slow, gemini-2.5-pro is faster
--generators gemini-2.5-pro  # Faster than gpt-4
```

**4. Check progress**: The pipeline shows real-time progress with ETA:
```
Generating responses: 45/100 (45.0%) | 2.3/s | ETA: 24s
```

**5. Use caching**: If interrupted, just re-run - completed problems are skipped automatically.

**Typical speeds** (varies by model and API limits):
- Gemini: ~5-10 problems/sec
- GPT-4: ~2-5 problems/sec  
- o3: ~0.5-2 problems/sec (slower, more compute)
- OpenRouter: Varies by model

---

### Q: How do I cite this in my research?

**A**: Use this BibTeX:
```bibtex
@software{proofgrader,
  title = {ProofGrader: A Framework for Mathematical Proof Generation and Evaluation},
  author = {ProofGrader Team},
  year = {2024},
  url = {https://github.com/your-repo/proofgrader}
}
```

---

## Additional Documentation

For deeper dives into specific topics:

- **SIMPLIFIED_ID_SYSTEM.md**: Detailed data structure and ID management
- **VALIDATION_STAGES.md**: Complete validation system documentation
- **METRICS_IMPLEMENTATION.md**: How metrics are computed
- **proofgrader/workflows/README.md**: Advanced workflow patterns
- **DOCUMENTATION_INDEX.md**: Guide to all documentation

---

## Quick Reference

### Essential Commands

```bash
# Complete pipeline - MULTIPLE models (recommended)
python scripts/run_full_workflow.py --data-dir DATA_DIR --generators MODEL1 MODEL2 MODEL3

# Generation - SINGLE model only
python scripts/generate.py --dataset problems.jsonl --model MODEL --output out.jsonl
# Note: For multiple models, use run_full_workflow.py with --generators

# Evaluation - single model
python scripts/evaluate.py --dataset solutions.jsonl --model MODEL --output eval.jsonl

# Validation only
python proofgrader/data_validation.py --data-dir DATA_DIR

# List templates
python scripts/generate.py --list-templates
python scripts/evaluate.py --list-templates
```

### Script Selection Guide

```bash
# ✅ Multiple models → Use run_full_workflow.py
python scripts/run_full_workflow.py --data-dir DIR --generators gpt-4 o3 gemini-2.5-pro

# ✅ Single model → Can use generate.py
python scripts/generate.py --model gpt-4 --dataset problems.jsonl

# ❌ WRONG - generate.py doesn't support multiple models
python scripts/generate.py --model gpt-4 o3 gemini-2.5-pro  # ERROR!
```

### Key Files

| File | Purpose | Required? |
|------|---------|-----------|
| `problems.jsonl` | Input problems | ✅ Yes |
| `expert_gradings.jsonl` | Expert scores | ⭕ Optional (for metrics) |
| `model_solutions.jsonl` | Generated solutions | 📝 Output |
| `*.eval.jsonl` | Evaluations | 📝 Output |

### Data Flow

```
problems.jsonl
    ↓ [Generation]
model_solutions.jsonl  (preserves problem fields + reference_solutions)
    ↓ [Evaluation]
*.eval.jsonl  (one file per generator)
    ↓ [Metrics - if expert_gradings.jsonl exists]
metrics/*.csv  (correlation reports)
```

---

## Support

- 📝 **Issues**: Open a GitHub issue
- 📚 **More docs**: See `DOCUMENTATION_INDEX.md` for all guides
- 💬 **Questions**: Check this README first - most answers are here!

---

**That's everything you need to use ProofGrader!** 🎉

Start with the Quick Start, create your `problems.jsonl`, and run the pipeline. The system handles the rest with automatic validation and clear error messages.
