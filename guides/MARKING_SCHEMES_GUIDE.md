# Marking Schemes Generation Guide

This guide explains how to generate marking schemes for your problems.

## What are Marking Schemes?

Marking schemes are detailed grading rubrics that:
- Break down the solution into checkpoints (worth points)
- List common deductions for errors
- Provide zero-credit items (things that don't deserve points)
- Help evaluators grade consistently on a 0-7 scale

## Why Use Them?

Using marking schemes in evaluation:
- ✅ More consistent grading across problems
- ✅ Better detection of partial correctness
- ✅ Clearer breakdown of where solutions succeed/fail
- ✅ Higher correlation with human expert scores

## Usage

### Basic Command

```bash
python scripts/generate_marking_schemes.py \
  --data-dir data/test_data \
  --model gemini-2.5-pro
```

This will:
1. Read `data/test_data/problems.jsonl`
2. Generate marking schemes using gemini-2.5-pro
3. Save to `data/test_data/problems_with_marking_schemes.jsonl`

### Options

```bash
# Use a different model
python scripts/generate_marking_schemes.py \
  --data-dir data/test_data \
  --model gpt-4o

# Use different template (problem-only, no reference solution)
python scripts/generate_marking_schemes.py \
  --data-dir data/test_data \
  --model gemini-2.5-pro \
  --template marking_scheme_from_problem

# Overwrite original problems.jsonl (careful!)
python scripts/generate_marking_schemes.py \
  --data-dir data/test_data \
  --model gemini-2.5-pro \
  --overwrite

# Test on first 5 problems
python scripts/generate_marking_schemes.py \
  --data-dir data/test_data \
  --model gemini-2.5-pro \
  --max-problems 5
```

## Available Templates

### 1. `marking_scheme` (Default, Recommended)
- **Requires:** Problem + Reference Solution
- **Generates:** 3-section rubric (Checkpoints, Zero-Credit, Deductions)
- **Most comprehensive and structured**

### 2. `marking_scheme_from_problem`
- **Requires:** Problem only (no reference solution)
- **Generates:** Similar 3-section rubric
- **Use when:** You don't have reference solutions

## Output Format

The script adds a `marking_scheme` field to each problem:

### Before
```json
{
  "id": "APMO-2025-1",
  "problem": "Let ABC be an acute triangle...",
  "reference_solutions": "Solution text..."
}
```

### After
```json
{
  "id": "APMO-2025-1",
  "problem": "Let ABC be an acute triangle...",
  "reference_solutions": "Solution text...",
  "marking_scheme": "### Checkpoints\n1. [2 pts] Establish that B₁C₁ is a circle with diameter AA₁...\n2. [3 pts] Show similarity between triangles...\n..."
}
```

## Using Marking Schemes in Evaluation

Once you have marking schemes, use them with evaluation templates that support them:

```bash
python scripts/evaluate.py \
  --data-dir data/test_data \
  --model gpt-4o \
  --template with_marking_scheme_and_reference
```

Available evaluation templates with marking scheme support:
- `with_marking_scheme_and_reference`
- `with_marking_scheme_ref_free`
- `with_reference_solution_and_marking_scheme_basic`

## Best Practices

1. **Use a strong model for generation:**
   - Recommended: `gemini-2.5-pro`, `gpt-4o`, `o3`
   - These produce more detailed and accurate rubrics

2. **Review generated schemes:**
   - Check that checkpoints add up to 7 points max
   - Verify deductions are reasonable
   - Ensure consistency across similar problems

3. **Iterative refinement:**
   - Generate schemes
   - Test with evaluations
   - Manually refine problematic schemes
   - Re-save to problems.jsonl

4. **Keep reference solutions:**
   - The `marking_scheme` template works best with reference solutions
   - Produces more accurate checkpoints aligned with the solution structure

## Example Workflow

```bash
# 1. Generate marking schemes
python scripts/generate_marking_schemes.py \
  --data-dir data/my_dataset \
  --model gemini-2.5-pro

# 2. Review the output (optional)
# Check: data/my_dataset/problems_with_marking_schemes.jsonl

# 3. Replace original if satisfied
mv data/my_dataset/problems_with_marking_schemes.jsonl \
   data/my_dataset/problems.jsonl

# 4. Use in evaluation
python scripts/evaluate.py \
  --data-dir data/my_dataset \
  --model gpt-4o \
  --template with_marking_scheme_and_reference
```

## Cost Considerations

Generating marking schemes requires API calls:
- **Cost:** 1 API call per problem
- **Typical cost:** $0.01-0.10 per problem (depending on model and problem complexity)
- **For 100 problems:** ~$1-10

Since marking schemes are reusable, generate once and use for all future evaluations!

