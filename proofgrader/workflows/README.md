## Workflow module (evaluator_design/workflows)

This module organizes evaluator workflows into small, focused files. The top-level runner `evaluator_design/run_evaluator_workflow.py` parses CLI args and dispatches into a chosen workflow here.

### Why this structure?
- **Separation of concerns**: CLI parsing and run orchestration live in `run_evaluator_workflow.py`; per-workflow logic lives here.
- **Extensibility**: Add new workflows by dropping in a file and registering it.
- **Reusability**: Shared utilities (calling `main.py`, parsing, metrics) live in `utils.py`.

### Directory layout
- `__init__.py`: Exposes `WORKFLOWS` dispatch map.
- `utils.py`: Shared helpers:
  - Running `main.py` with model/template (`run_main`)
  - Parsing raw evaluator JSONL into `evaluator_grades/*` (`write_per_generator_eval`)
  - Building steps dataset for judge stage (`build_steps_dataset_from_raw`)
  - Running metrics report (`run_metrics`)
- `single.py`: One-stage, prompt-only evaluator.
- `decompose_then_judge.py`: Two-stage pipeline (decompose steps → judge with marking scheme + steps).

### Running workflows
All workflows are invoked via the runner:

```bash
python evaluator_design/run_evaluator_workflow.py \
  --workflow <single|decompose-then-judge> \
  --evaluator-model <judge_model> \
  --dataset evaluator_design/data/pilot/model_outputs_merged.jsonl
```

Common flags:
- `--dataset`: JSONL with fields at least `id`, `problem`, `solution`, `model`.
- `--template-config`: Defaults to `evaluation_prompt.yaml` (used for single-stage only).
- `--templates-config`: Defaults to `prompt_templates.yaml` (used for multi-stage workflows).
- `--processing-mode`: `sequential|batch|parallel` (passed through to `main.py`).
- `--n-sampling`: Number of samples per example.
- `--dump-dir`: Base directory for this run’s artifacts; defaults to a timestamped folder under `eval_runs/`.
- `--evaluator-tag`: Name for parsed outputs under `evaluator_grades/` (optional; auto-derived if not provided).

#### Example: Single-stage (prompt-only evaluator)
```bash
python evaluator_design/run_evaluator_workflow.py \
  --workflow single \
  --evaluator-model gemini-2.5-pro \
  --template basic \
  --dataset evaluator_design/data/pilot/model_outputs_merged.jsonl \
  --template-config evaluation_prompt.yaml
```

#### Example: Decompose-then-judge
Stage A uses Model A to extract steps. Stage B uses Model B to judge using a marking scheme + the extracted steps.

```bash
python evaluator_design/run_evaluator_workflow.py \
  --workflow decompose-then-judge \
  --steps-model gemini-2.5-pro \
  --steps-template break_into_steps_and_grade \
  --evaluator-model o3 \
  --judge-template with_marking_scheme_and_break_into_steps \
  --dataset evaluator_design/data/pilot/model_outputs_merged.jsonl \
  --templates-config prompt_templates.yaml
```

### Outputs
For each run you’ll see a timestamped folder under `evaluator_design/outputs/eval_runs/<version>/<tag>__<timestamp>/`:
- Single-stage:
  - `evaluator_raw.jsonl`: Raw LLM outputs from `main.py`.
- Decompose-then-judge:
  - `steps_stage/steps_raw.jsonl`: Raw step tables from Stage A.
  - `steps_stage/steps_dataset.jsonl`: Transformed dataset (adds `steps`, `solution`, `marking_scheme`).
  - `judge_stage/judge_raw.jsonl`: Raw JSON responses from Stage B.

Parsed, per-generator evaluator results go to:
- `evaluator_design/outputs/evaluator_grades/<version>/<evaluator_tag>/*.eval.jsonl`

Metrics and reports go to:
- `evaluator_design/outputs/reports/<version>/`
  - Includes per-generator and overall summaries, plus normalized/macros.

### Adding a new workflow
1) Create a file implementing a `run_workflow(args)` function.

```python
from pathlib import Path

from .utils import run_main, write_per_generator_eval, run_metrics, EVAL_OUT_DIR

def run_workflow(args):
    dataset_path = Path(args.dataset)
    # 1) Generate raw outputs with run_main(...)
    # 2) Parse to evaluator_grades with write_per_generator_eval(...)
    # 3) Run metrics with run_metrics()
```

2) Register it in `__init__.py`:

```python
from .my_new_workflow import run_workflow as my_new

WORKFLOWS = {
    # existing entries...
    "my-new-workflow": my_new,
}
```

3) Call it from the runner:

```bash
python evaluator_design/run_evaluator_workflow.py --workflow my-new-workflow ...
```

### Notes on data fields
- Stage B (judge) expects a dataset with: `problem`, `solution`, `steps`, and (optionally) `marking_scheme`.
- `build_steps_dataset_from_raw` extracts `steps` from Stage A response; it also copies `marking_scheme` and tries to set `solution` from metadata, with prompt fallback.
- Generator mapping uses `metadata.model` where available; otherwise `(id, solution)` mapping from the original dataset.

### Where templates live
- Single-stage templates: `evaluation_prompt.yaml`.
- Multi-stage templates: use `evaluation_prompt.yaml` by default (both `break_into_steps_and_grade` and `with_marking_scheme_and_break_into_steps` are defined there). You can override with `--templates-config`.


