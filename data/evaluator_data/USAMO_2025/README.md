# USAMO 2025 Dataset

This directory contains processed data from the USAMO 2025 competition, sourced from HuggingFace datasets.

## Data Source

- **Model Outputs**: `MathArena/usamo_2025_outputs`
- **Grading Schemes**: `MathArena/usamo_2025`

## Files

### model_output.jsonl

Contains model-generated solutions to USAMO 2025 problems. Each entry includes:

- `id`: Combined identifier in format `{problem_idx}-{idx_answer}` (e.g., "1-0", "1-1", etc.)
- `problem`: The problem statement
- `prompt`: The user message/prompt given to the model
- `model`: The model name (generator)
- `solution`: The model's solution/answer
- `marking_scheme`: The grading scheme for the problem (list of grading criteria)
- `token_usage`: Token usage statistics (prompt_tokens, completion_tokens, total_tokens, cost)
- `human_solution`: The official sample solution from the USAMO 2025 dataset

### evaluation_merged.jsonl

Contains evaluation results for each model output. Each entry includes:

- `problem_id`: Combined identifier matching model_output.jsonl
- `model_name`: The model name
- `score`: Average of points_judge_1 and points_judge_2
- `grading_details_judge_1`: Detailed grading breakdown from judge 1
- `grading_details_judge_2`: Detailed grading breakdown from judge 2
- `max_points_judge_1`: Maximum possible points from judge 1
- `max_points_judge_2`: Maximum possible points from judge 2
- `error_judge_1`: Error information from judge 1 (if any)
- `error_judge_2`: Error information from judge 2 (if any)

## Statistics

- **Total entries**: 264
- **Problems**: 6 (problem_idx: 1-6)
- **Models**: 11 different models
  - Claude-3.7-Sonnet (Think)
  - DeepSeek-R1
  - DeepSeek-R1-0528
  - Grok 3 (Think)
  - QwQ-32B
  - gemini-2.0-flash-thinking
  - gemini-2.5-pro
  - o1-pro (high)
  - o3 (high)
  - o3-mini (high)
  - o4-mini (high)
- **Answers per model**: 4 (idx_answer: 0-3)

## Field Mapping from Original Dataset

The following mappings were applied from the original HuggingFace datasets:

### From usamo_2025_outputs:
- `problem_idx` → used in `id` construction
- `model_name` → `model` in model_output.jsonl, `model_name` in evaluation_merged.jsonl
- `idx_answer` → used in `id` construction
- `problem` → `problem`
- `user_message` → `prompt`
- `answer` → `solution`
- `input_tokens` → `token_usage.prompt_tokens`
- `output_tokens` → `token_usage.completion_tokens`
- `cost` → `token_usage.cost`
- `points_judge_1` and `points_judge_2` → averaged to create `score`
- `grading_details_judge_1` → `grading_details_judge_1`
- `grading_details_judge_2` → `grading_details_judge_2`

### From usamo_2025:
- `grading_scheme` → `marking_scheme`
- `sample_solution` → `human_solution`

## Notes

- The `id` field combines problem_idx and idx_answer to create unique identifiers
- The `score` field is the average of points from both judges
- Unused fields like `generation_info` were excluded as requested
- Token usage information is preserved when available

