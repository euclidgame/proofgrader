# Expert Gradings Format

This document explains the format for `expert_gradings.jsonl` (ground truth scores).

## Purpose

`expert_gradings.jsonl` contains human expert scores for solutions. It's used by the metrics computation to evaluate how well automated evaluators match human judgment.

## File Location

Place in your data directory:
```
data/test_data/expert_gradings.jsonl
```

## Format

Each line is a JSON object with these **required** fields:

```json
{
  "problem_id": "APMO-2025-1",
  "model_name": "gpt-5",
  "score": 6.0
}
```

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `problem_id` | string | Must match problem IDs in `problems.jsonl` | `"APMO-2025-1"` |
| `model_name` | string | Must match generator names in `model_solutions.jsonl` | `"gpt-5"`, `"gemini-2.5-pro"` |
| `score` | float | Expert score, typically 0-7 scale | `6.0`, `7.0`, `4.5` |

### Important Notes

1. **Use Sanitized Model Names:** The `model_name` should use the simple name (without provider prefixes):
   - ✅ Correct: `"qwen3-235b-a22b-thinking-2507"` (just the model name)
   - ❌ Wrong: `"openrouter/qwen/qwen3-235b-a22b-thinking-2507"` (includes provider)
   - ✅ Correct: `"gpt-5"`, `"o3"`, `"gemini-2.5-pro"`
   
   **Rule:** Use only the part after the last slash (`/`) in the full model identifier.

2. **One Record Per (Problem, Model) Pair:** Each combination should appear exactly once

3. **Score Scale:** Typically 0-7:
   - 0-2: Incorrect/poor
   - 3-4: Partially correct
   - 5-6: Mostly correct with minor issues
   - 7: Fully correct

## Example File

Here's a complete example for 2 problems and 2 models:

```jsonl
{"problem_id": "APMO-2025-1", "model_name": "gpt-5", "score": 6.0}
{"problem_id": "APMO-2025-1", "model_name": "gemini-2.5-pro", "score": 7.0}
{"problem_id": "APMO-2025-2", "model_name": "gpt-5", "score": 5.0}
{"problem_id": "APMO-2025-2", "model_name": "gemini-2.5-pro", "score": 6.0}
```

## Test File Created

I've created a fake `expert_gradings.jsonl` for your test data:

**Location:** `data/test_data/expert_gradings.jsonl`

**Contents:**
- 116 records (29 problems × 4 models)
- Random but realistic scores (weighted toward 5-7)
- Matches all your problem IDs and model names

**Models included (sanitized names):**
- `gpt-5`
- `o3`
- `qwen3-235b-a22b-thinking-2507` (not `openrouter/qwen/qwen3-235b-a22b-thinking-2507`)
- `gemini-2.5-pro`

## Verify It Works

Check the file:
```bash
# View sample records
head -5 data/test_data/expert_gradings.jsonl

# Count records
wc -l data/test_data/expert_gradings.jsonl

# Validate JSON format
python3 -c "import json; print('Valid!' if all(json.loads(l) for l in open('data/test_data/expert_gradings.jsonl')) else 'Invalid')"
```

## Test Metrics Computation

Now you can test the full pipeline:

```bash
# Run evaluation with metrics
python scripts/evaluate.py \
  --data-dir data/test_data \
  --model gpt-4o \
  --compute-metrics
```

Or just compute metrics on existing evaluations:

```bash
python scripts/evaluate.py \
  --data-dir data/test_data \
  --metrics-only
```

## Creating Real Expert Gradings

For production use, replace the fake scores with actual human expert evaluations:

1. Export solutions for human review
2. Have experts grade each solution on the 0-7 scale
3. Create `expert_gradings.jsonl` with the format above
4. Ensure `problem_id` and `model_name` match exactly

## Alternative File Names

The system also accepts these filenames (in priority order):
1. `expert_gradings.jsonl` (preferred)
2. `evaluation_merged.jsonl` (alternative)
3. `evaluations.jsonl` (legacy)

All should use the same format shown above.

