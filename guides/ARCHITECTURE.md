# ProofGrader Architecture

## Simple Two-Script Design

ProofGrader uses **two completely independent scripts**:

```
┌─────────────────────┐
│   generate.py       │  ← Generate solutions (run once)
│                     │
│ Input:  problems    │
│ Output: solutions   │
└─────────────────────┘
           ↓
    model_solutions.jsonl
           ↓
┌─────────────────────┐
│   evaluate.py       │  ← Evaluate solutions (run many times)
│                     │
│ Input:  solutions   │
│ Output: evaluations │
└─────────────────────┘
```

## Scripts

### `generate.py` - Solution Generation

- **Input**: `data-dir/problems.jsonl`
- **Output**: `data-dir/model_solutions.jsonl`
- **Supports**: Multiple models (sequential execution)
- **Run**: Once per dataset

**Command**:
```bash
python scripts/generate.py --data-dir DIR --models MODEL1 MODEL2 ...
```

---

### `evaluate.py` - Solution Evaluation

- **Input**: `data-dir/model_solutions.jsonl` (default)
- **Output**: `data-dir/outputs/evaluations/*.eval.jsonl`
- **Supports**: Workflows (single, decompose-then-judge, etc.)
- **Run**: Multiple times with different evaluators

**Command**:
```bash
python scripts/evaluate.py --data-dir DIR --model EVALUATOR
```

---

## Independence

### Why Separate?

1. **Cost**: Generate expensive solutions once
2. **Comparison**: Evaluate with multiple evaluators on identical data
3. **Flexibility**: Try different workflows without re-generating
4. **Research**: Fair evaluator comparison

### Example

```bash
# Generate once (expensive - o3 costs $100/1M tokens)
python scripts/generate.py --data-dir data/test --models gpt-4 o3 gemini-2.5-pro

# Evaluate 5 times (cheap - evaluation is fast)
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro
python scripts/evaluate.py --data-dir data/test --model gpt-4
python scripts/evaluate.py --data-dir data/test --model o3
python scripts/evaluate.py --data-dir data/test --model claude-3-opus
python scripts/evaluate.py --data-dir data/test --model deepseek-r1

# Compare: Which evaluator best matches expert scores?
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro --compute-metrics
```

**Result**: 5 evaluator comparisons without wasting money on re-generation!

---

## Data Flow

```
problems.jsonl (your input)
    ↓ [generate.py]
model_solutions.jsonl
    ↓ [evaluate.py with evaluator 1]
    ├─→ evaluations/gemini-2.5-pro.eval.jsonl
    ↓ [evaluate.py with evaluator 2]
    ├─→ evaluations/gpt-4.eval.jsonl
    ↓ [evaluate.py with evaluator 3]
    └─→ evaluations/o3.eval.jsonl
```

Each evaluation is **completely independent** - can run in parallel!

---

## File Locations

### Input (You Create)
- `data-dir/problems.jsonl` - Required
- `data-dir/expert_gradings.jsonl` - Optional (for metrics)

### Intermediate (generate.py Creates)
- `data-dir/model_solutions.jsonl` - Generated solutions

### Output (evaluate.py Creates)
- `data-dir/outputs/evaluations/.../*.eval.jsonl` - Evaluations
- `data-dir/metrics/*.csv` - Metrics (if --compute-metrics)

---

## Key Design Decisions

### One Solution Per (Problem, Model)

Simplified from multi-attempt system:
- Clean 1:1 mapping
- No `response_idx` complexity
- Easier debugging

### Sequential Generation

Models run one at a time:
- Simpler code
- Easier to monitor
- More reliable

If you need parallel generation, run multiple instances of `generate.py` with different `--models`.

### Default Paths

- `generate.py` defaults output to `data-dir/model_solutions.jsonl`
- `evaluate.py` defaults input to `data-dir/model_solutions.jsonl`

**Result**: Commands are shorter!

```bash
# Short and simple
python scripts/generate.py --data-dir data/test --models gpt-4
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro
```

---

## Migration from Old Structure

**Old scripts** (removed):
- ❌ `run_full_workflow.py` - Did generation + evaluation (coupled)
- ❌ `evaluate_workflow.py` - Renamed to `evaluate.py`

**New scripts**:
- ✅ `generate.py` - Generation only (supports multiple models)
- ✅ `evaluate.py` - Evaluation only (supports workflows)

**Old command**:
```bash
python scripts/run_full_workflow.py \
  --data-dir data/test \
  --generators gpt-4 \
  --evaluator gemini-2.5-pro
```

**New command**:
```bash
# Separate generation and evaluation
python scripts/generate.py --data-dir data/test --models gpt-4
python scripts/evaluate.py --data-dir data/test --model gemini-2.5-pro
```

**Benefits**:
- ✅ Simpler mental model (two scripts, two purposes)
- ✅ True independence
- ✅ More flexible
- ✅ Easier to understand

---

## Summary

**Simple**: Two scripts, clear purposes  
**Independent**: Generation and evaluation completely separate  
**Flexible**: Evaluate same solutions with multiple evaluators  
**Efficient**: Generate expensive solutions once  

**Commands**:
```bash
generate.py --data-dir DIR --models MODEL1 MODEL2 ...  # Once
evaluate.py --data-dir DIR --model EVALUATOR           # Many times
```

**That's it!** 🎉

