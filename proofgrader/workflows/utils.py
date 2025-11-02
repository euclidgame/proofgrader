import json
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


WORKFLOWS_DIR = Path(__file__).resolve().parent  # proofgrader/workflows/
PROOFGRADER_DIR = WORKFLOWS_DIR.parent  # proofgrader/
PROJECT_ROOT = PROOFGRADER_DIR.parent  # project root

# Legacy paths (kept for backward compatibility)
DATA_ROOT = PROJECT_ROOT / "data" / "evaluator_data"
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
DEFAULT_DATASET = DATA_ROOT / "pilot" / "model_outputs_merged.jsonl"
DEFAULT_TEMPLATE_CONFIG = PROJECT_ROOT / "templates"
PROMPT_TEMPLATES_CONFIG = PROJECT_ROOT / "templates"
EVAL_OUT_DIR = OUTPUTS_ROOT / "evaluator_grades"
EVAL_OUT_DIR_BINARY = OUTPUTS_ROOT / "evaluator_grades_binary"

# Scripts
METRICS_SCRIPT = PROOFGRADER_DIR / "metrics" / "compute_evaluator_distances.py"
METRICS_SCRIPT_BINARY = PROOFGRADER_DIR / "metrics" / "compute_evaluator_binary_metrics.py"
DASHBOARD_SCRIPT = PROOFGRADER_DIR / "dashboard" / "build_dashboard.py"
DASHBOARD_SCRIPT_BINARY = PROOFGRADER_DIR / "dashboard" / "build_dashboard_binary.py"
EVALUATE_SCRIPT = PROJECT_ROOT / "main.py"  # Main evaluation script (not the wrapper)


def sanitize_model_name(model_name: str) -> str:
    """
    Sanitize model name for use in file/directory names.
    Uses only the part after the last slash.
    
    Args:
        model_name: Full model name (e.g., "openrouter/qwen/qwen3-235b")
        
    Returns:
        Sanitized name (e.g., "qwen3-235b")
    """
    return str(model_name).split("/")[-1]


def get_evaluation_outputs_dir(data_dir: Path) -> Path:
    """
    Get evaluation outputs directory for a data directory.
    
    Args:
        data_dir: Data directory path (e.g., Path("data/test_data"))
        
    Returns:
        Path to evaluation outputs: <data_dir>/evaluation_outputs/
    """
    return Path(data_dir) / "evaluation_outputs"


def get_evaluator_gradings_dir(data_dir: Path, binary: bool = False) -> Path:
    """
    Get evaluator gradings directory.
    
    Args:
        data_dir: Data directory path
        binary: Whether to use binary gradings directory
        
    Returns:
        Path: <data_dir>/evaluation_outputs/evaluator_gradings[_binary]/
    """
    eval_outputs = get_evaluation_outputs_dir(data_dir)
    subdir = "evaluator_gradings_binary" if binary else "evaluator_gradings"
    return eval_outputs / subdir


def get_metrics_dir(data_dir: Path) -> Path:
    """
    Get metrics output directory.
    
    Args:
        data_dir: Data directory path
        
    Returns:
        Path: <data_dir>/evaluation_outputs/metrics/
    """
    return get_evaluation_outputs_dir(data_dir) / "metrics"


def get_evaluation_runs_dir(data_dir: Path, binary: bool = False) -> Path:
    """
    Get evaluation runs directory.
    
    Args:
        data_dir: Data directory path
        binary: Whether to use binary runs directory
        
    Returns:
        Path: <data_dir>/evaluation_outputs/evaluation_runs[_binary]/
    """
    eval_outputs = get_evaluation_outputs_dir(data_dir)
    subdir = "evaluation_runs_binary" if binary else "evaluation_runs"
    return eval_outputs / subdir


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def build_id_solution_to_model_map(dataset_path: Path) -> Dict[Tuple[str, str], str]:
    mapping: Dict[Tuple[str, str], str] = {}
    for row in read_jsonl(dataset_path):
        rid = row.get("id")
        model = row.get("model")
        sol = row.get("solution")
        if rid is None or not isinstance(model, str):
            continue
        pid = str(rid)
        # Support composite ids of the form "<problem_id>::<model>"
        if "::" in pid:
            try:
                base_id, model_from_id = pid.split("::", 1)
                mapping[(base_id, normalize_text(sol or ""))] = model_from_id
                continue
            except Exception:
                pass
        if isinstance(sol, str):
            key = (pid, normalize_text(sol))
            mapping[key] = model
    return mapping


def extract_json_from_text(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    fence_re = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)
    m = fence_re.search(text)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            return None
    start = text.find("{")
    while start != -1:
        depth = 0
        for end in range(start, len(text)):
            c = text[end]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    cand = text[start:end+1]
                    try:
                        return json.loads(cand)
                    except Exception:
                        break
        start = text.find('{', start + 1)
    return None


def extract_fields_lenient(text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    s = text or ""
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
    blob = fence.group(1) if fence else s
    # Numeric score
    m = re.search(r'"score"\s*:\s*([0-9]+(?:\.[0-9]+)?)', blob)
    if not m:
        m = re.search(r'\bscore\b\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', blob, re.IGNORECASE)
    if m:
        try:
            out['score'] = float(m.group(1))
        except Exception:
            pass
    # Evaluation result as string (correct/incorrect)
    for key in ["evaluation_result", "verdict", "final_verdict", "result"]:
        m2 = re.search(rf'"{key}"\s*:\s*"(correct|incorrect)"', blob, re.IGNORECASE)
        if m2:
            out['evaluation_result'] = m2.group(1).lower()
            break
    # Boolean correctness flags
    if 'evaluation_result' not in out:
        m3 = re.search(r'"(is_correct|correct)"\s*:\s*(true|false)', blob, re.IGNORECASE)
        if m3:
            out['evaluation_result'] = 'correct' if m3.group(2).lower() == 'true' else 'incorrect'
    m = re.search(r'"assessment"\s*:\s*"([\s\S]*?)"\s*(,|\n|\r|\})', blob)
    if m:
        out['assessment'] = m.group(1)
    # Comments (string or array lenient)
    m = re.search(r'"comments"\s*:\s*"([\s\S]*?)"\s*(,|\n|\r|\})', blob)
    if m:
        out['comments'] = m.group(1)
    else:
        cm = re.search(r'"comments"\s*:\s*\[(.*?)\]', blob, re.DOTALL)
        if cm:
            out['comments'] = re.findall(r'"([\s\S]*?)"', cm.group(1))
    # Rationale
    m = re.search(r'"rationale"\s*:\s*"([\s\S]*?)"\s*(,|\n|\r|\})', blob)
    if m:
        out['rationale'] = m.group(1)
    errs = re.search(r'"errors"\s*:\s*\[(.*?)\]', blob, re.DOTALL)
    if errs:
        out['errors'] = re.findall(r'"([\s\S]*?)"', errs.group(1))
    return out


def extract_fields_from_xml(text: str) -> Dict[str, Any]:
    """
    Extract fields from XML-style tags.

    Recognized tags (case-insensitive):
      - <score>number</score>
      - <assessment>...</assessment> or <analysis>...</analysis>
      - <comments>...</comments> or multiple <comment>...</comment>
      - <rationale>...</rationale>
      - <errors>text or <error>...</error> items</errors> or multiple <error> tags

    Returns a dict possibly containing: 'score', 'assessment', 'comments', 'rationale', 'errors'.
    """
    out: Dict[str, Any] = {}
    if not isinstance(text, str) or not text:
        return out
    try:
        # Capture <score>...</score> (numeric content)
        m_score = re.search(r"<\s*score\s*>\s*([-+]?[0-9]+(?:\.[0-9]+)?)\s*<\s*/\s*score\s*>", text, re.IGNORECASE | re.DOTALL)
        if m_score:
            try:
                out["score"] = float(m_score.group(1))
            except Exception:
                pass
        # Capture <analysis>...</analysis> (free text)
        m_analysis = re.search(r"<\s*analysis\s*>\s*([\s\S]*?)\s*<\s*/\s*analysis\s*>", text, re.IGNORECASE)
        if m_analysis:
            out["assessment"] = m_analysis.group(1)
        
        m_assessment = re.search(r"<\s*assessment\s*>\s*([\s\S]*?)\s*<\s*/\s*assessment\s*>", text, re.IGNORECASE)
        if m_assessment:
            out["assessment"] = m_assessment.group(1)

        # Comments: either a single <comments> block or multiple <comment> tags
        m_comments_block = re.search(r"<\s*comments\s*>\s*([\s\S]*?)\s*<\s*/\s*comments\s*>", text, re.IGNORECASE)
        if m_comments_block:
            out["comments"] = m_comments_block.group(1)
        else:
            comments = re.findall(r"<\s*comment\s*>\s*([\s\S]*?)\s*<\s*/\s*comment\s*>", text, re.IGNORECASE)
            if comments:
                out["comments"] = "\n".join([c for c in comments if isinstance(c, str)])

        # Rationale
        m_rat = re.search(r"<\s*rationale\s*>\s*([\s\S]*?)\s*<\s*/\s*rationale\s*>", text, re.IGNORECASE)
        if m_rat:
            out["rationale"] = m_rat.group(1)

        # Errors: prefer list of <error> items; fallback to text content
        error_items = re.findall(r"<\s*error\s*>\s*([\s\S]*?)\s*<\s*/\s*error\s*>", text, re.IGNORECASE)
        if error_items:
            out["errors"] = [e for e in error_items if isinstance(e, str)]
        else:
            m_errors = re.search(r"<\s*errors\s*>\s*([\s\S]*?)\s*<\s*/\s*errors\s*>", text, re.IGNORECASE)
            if m_errors:
                out["errors"] = m_errors.group(1)
    except Exception:
        # Be robust to malformed inputs
        return out
    return out


def extract_solution_from_prompt(prompt: str) -> str:
    if not isinstance(prompt, str):
        return ""
    # Prefer a strict slice between the Original Proof Solution header and ATOMIC STEPS
    start_re = re.compile(r"(?mi)^\s*\*\s*\*\*Original Proof Solution(?:\s*\(verbatim\))?\*\*\s*:?[\t ]*$")
    end_re = re.compile(r"(?mi)^\s*\*\s*\*\*ATOMIC\s*STEPS\b")
    m_start = start_re.search(prompt)
    if m_start:
        start_pos = m_start.end()
        m_end = end_re.search(prompt, pos=start_pos)
        end_pos = m_end.start() if m_end else len(prompt)
        section = prompt[start_pos:end_pos]
        return section.strip()
    # Fallback: locate generic headers
    candidates = [
        "Original Proof Solution (verbatim):",
        "Original Proof Solution:",
        "Proof Solution",
        "Solution",
        "Proof",
    ]
    lower = prompt.lower()
    idx = -1
    for m in candidates:
        j = lower.rfind(m.lower())
        if j > idx:
            idx = j
    if idx == -1:
        return ""
    after = prompt[idx:]
    parts = after.splitlines()
    if parts:
        parts = parts[1:]
    return "\n".join(parts).strip()


def run_main(
    evaluator_model: str,
    template_name: str,
    dataset_path: Path,
    template_config: Path,
    output_path: Path,
    max_examples: int = None,
    no_cache: bool = False,
    processing_mode: str = "batch",
    n_sampling: int = 1,
) -> None:
    """
    Run the evaluation script with the specified parameters.
    
    Note: processing_mode parameter is deprecated and ignored (batch mode is always used).
    """
    cmd = [
        sys.executable,
        str(EVALUATE_SCRIPT),
        "--model",
        evaluator_model,
        "--dataset",
        str(dataset_path),
        "--problem-field",
        "problem",
        "--output",
        str(output_path),
        "--template-config",
        str(template_config),
        "--template",
        template_name,
        "--n-sampling",
        str(n_sampling)
    ]
    if no_cache:
        cmd.append("--no-cache")
    if max_examples is not None:
        cmd.extend(["--max-examples", str(max_examples)])
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        raise SystemExit(f"evaluate.py failed with exit code {res.returncode}")


def write_per_generator_eval(
    evaluator_tag: str,
    raw_results_path: Path,
    dataset_path: Path,
    mirror_dir: Path,
    evaluator_model: str,
    template_name: str,
    debug: bool = False,
    debug_limit: int = 5,
    debug_report_path: Path = None,
    use_raw_generator: bool = False,
    steps_dataset_path: Path = None,
    assume_id_composite: bool = False,
) -> Dict[str, int]:
    idsol_to_model = build_id_solution_to_model_map(dataset_path)
    id_to_model_steps: Dict[str, str] = {}
    if steps_dataset_path and Path(steps_dataset_path).exists():
        try:
            for row in read_jsonl(Path(steps_dataset_path)):
                pid = str(row.get('id')) if row.get('id') is not None else None
                m = row.get('model')
                if pid and isinstance(m, str) and m.strip():
                    id_to_model_steps[pid] = m.strip()
        except Exception:
            pass
    # Build id -> set(models) to allow id-only fallback when unique
    id_to_models: Dict[str, set] = {}
    for (pid, _sol), model in idsol_to_model.items():
        id_to_models.setdefault(pid, set()).add(model)
    rows = read_jsonl(raw_results_path)
    per_gen_latest: Dict[Tuple[str, str], Dict[str, Any]] = {}

    reasons: Dict[str, Dict[str, Any]] = {
        'evaluator_model_mismatch': {'count': 0, 'examples': []},
        'template_mismatch': {'count': 0, 'examples': []},
        'no_response_string': {'count': 0, 'examples': []},
        'no_score_found': {'count': 0, 'examples': []},
        'no_generator_mapping': {'count': 0, 'examples': []},
        'parsed_and_mapped': {'count': 0, 'examples': []},
    }

    # Additional debug tracking for mapping sources and seen generators
    mapping_sources: Dict[str, Dict[str, Any]] = {}
    seen_generators: Dict[str, int] = {}

    def maybe_add(reason: str, obj: Dict[str, Any], extra: Dict[str, Any] = None):
        reasons[reason]['count'] += 1
        if debug and len(reasons[reason]['examples']) < debug_limit:
            rid = obj.get('id')
            gi = obj.get('generation_info', {})
            example = {
                'id': rid,
                'gen_model': gi.get('model'),
                'gen_template': gi.get('template'),
                'raw_model_field': obj.get('model'),
            }
            if isinstance(extra, dict):
                example.update({k: v for k, v in extra.items() if k not in example})
            reasons[reason]['examples'].append(example)

    def track_mapping_source(source: str, base_obj: Dict[str, Any], gen_value: str):
        if not source:
            return
        if source not in mapping_sources:
            mapping_sources[source] = {'count': 0, 'examples': []}
        mapping_sources[source]['count'] += 1
        if debug and len(mapping_sources[source]['examples']) < debug_limit:
            mapping_sources[source]['examples'].append({
                'id': base_obj.get('id'),
                'gen': gen_value,
            })

    for r in rows:
        # Try to get actual problem_id from metadata first, fallback to top-level id
        meta = r.get('metadata') if isinstance(r.get('metadata'), dict) else {}
        pid = meta.get('problem_id') or r.get('problem_id') or r.get("id")
        if not pid:
            continue
        gen_info = r.get("generation_info", {})
        # Be tolerant when generation_info is missing; only enforce checks when present
        if gen_info:
            if gen_info.get("model") != evaluator_model:
                maybe_add('evaluator_model_mismatch', r)
                continue
            if gen_info.get("template") != template_name:
                maybe_add('template_mismatch', r)
                continue
        resp = r.get("response")
        if resp is None and isinstance(r.get("responses"), list) and r.get("responses"):
            resp = r["responses"][0]
        if not isinstance(resp, str):
            maybe_add('no_response_string', r)
            continue
        # XML-first extraction
        xml_fields = extract_fields_from_xml(resp)
        score_f = None
        assessment = None
        comments_val = None
        rationale_val = None
        errors_val = None
        eval_result_str = None
        if 'score' in xml_fields:
            try:
                score_f = float(xml_fields.get('score'))
            except Exception:
                score_f = None
        if 'assessment' in xml_fields:
            assessment = xml_fields.get('assessment')
        if 'comments' in xml_fields:
            comments_val = xml_fields.get('comments')
        if 'rationale' in xml_fields:
            rationale_val = xml_fields.get('rationale')
        # Capture errors from XML if present
        if 'errors' in xml_fields:
            errors_val = xml_fields.get('errors')

        # JSON extraction fallback (only fill missing fields)
        obj = extract_json_from_text(resp)
        if isinstance(obj, dict):
            if score_f is None and 'score' in obj:
                try:
                    score_f = float(obj.get('score'))
                except Exception:
                    score_f = None
            if assessment is None:
                assessment = obj.get('assessment')
            if comments_val is None and obj.get('comments') is not None:
                comments_val = obj.get('comments')
            if rationale_val is None and obj.get('rationale') is not None:
                rationale_val = obj.get('rationale')
            # Only override errors if not already captured from XML
            if errors_val is None:
                errors_val = obj.get('errors')
            # Pull a verdict field if present
            for key in ['evaluation_result', 'verdict', 'final_verdict', 'result']:
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    v = val.strip().lower()
                    if v in {'correct', 'incorrect'}:
                        eval_result_str = v
                        break
            if not eval_result_str:
                # boolean correctness flags
                for key in ['is_correct', 'correct']:
                    val = obj.get(key)
                    if isinstance(val, bool):
                        eval_result_str = 'correct' if val else 'incorrect'
                        break
        if score_f is None:
            fallback = extract_fields_lenient(resp)
            if 'score' in fallback:
                try:
                    score_f = float(fallback['score'])
                except Exception:
                    score_f = None
            if 'assessment' in fallback:
                assessment = fallback.get('assessment')
            if 'comments' in fallback and comments_val is None:
                comments_val = fallback.get('comments')
            if 'rationale' in fallback and rationale_val is None:
                rationale_val = fallback.get('rationale')
            if 'errors' in fallback:
                errors_val = fallback.get('errors')
            if 'evaluation_result' in fallback and isinstance(fallback.get('evaluation_result'), str):
                ev = fallback.get('evaluation_result').strip().lower()
                if ev in {'correct', 'incorrect'}:
                    eval_result_str = ev
        if score_f is None:
            maybe_add('no_score_found', r)
            continue

        # If ids are composite ("<problem_id>::<generator>"), parse directly and do not add unique_id
        if assume_id_composite:
            sid = str(pid)
            if "::" not in sid:
                maybe_add('no_generator_mapping', r)
                continue
            base_id, gen = sid.split("::", 1)
            item: Dict[str, Any] = {"id": base_id, "score": score_f}
            if assessment is not None:
                item['assessment'] = assessment
            if comments_val is not None:
                item['comments'] = comments_val
            if rationale_val is not None:
                item['rationale'] = rationale_val
            if errors_val is not None:
                item['errors'] = errors_val
            if eval_result_str is not None:
                item['evaluation_result'] = eval_result_str
            per_gen_latest[(base_id, gen)] = item
            maybe_add('parsed_and_mapped', r, {'mapping_source': 'composite_id'})
            track_mapping_source('composite_id', r, gen)
            continue
        gen = None
        mapping_source = None
        # meta already extracted above
        # Try metadata.generator first, then metadata.model
        meta_generator = meta.get('generator') if isinstance(meta.get('generator'), str) and meta.get('generator').strip() else None
        meta_model = meta.get('model') if isinstance(meta.get('model'), str) and meta.get('model').strip() else None
        
        if meta_generator:
            gen = meta_generator.strip()
            mapping_source = 'metadata.generator'
        elif meta_model:
            gen = meta_model.strip()
            mapping_source = 'metadata.model'
        elif isinstance(r.get('generator'), str) and r.get('generator').strip():
            gen = r.get('generator').strip()
            mapping_source = 'top_level.generator'
        elif isinstance(r.get('model'), str) and r.get('model').strip():
            gen = r.get('model').strip()
            mapping_source = 'top_level.model'
        elif use_raw_generator and isinstance(r.get('model'), str):
            gen = r.get('model')
            mapping_source = 'raw_model_passthrough'
        if gen is None:
            prompt = r.get("prompt", "")
            sol_from_prompt = extract_solution_from_prompt(prompt)
            key = (str(pid), normalize_text(sol_from_prompt))
            gen = idsol_to_model.get(key)
            mapping_source = 'prompt_solution_map' if gen is not None else mapping_source
            if gen is None:
                # Fallback: id-only mapping if uniquely determined
                models = id_to_models.get(str(pid))
                if models and len(models) == 1:
                    gen = next(iter(models))
                    mapping_source = 'id_unique_model'
            if gen is None and id_to_model_steps.get(str(pid)):
                gen = id_to_model_steps.get(str(pid))
                mapping_source = 'steps_dataset'
        if not gen:
            maybe_add('no_generator_mapping', r, {'mapping_source': mapping_source or ''})
            continue
        item: Dict[str, Any] = {"id": str(pid), "score": score_f, "unique_id": f"{pid}::{gen}"}
        if assessment is not None:
            item['assessment'] = assessment
        if comments_val is not None:
            item['comments'] = comments_val
        if rationale_val is not None:
            item['rationale'] = rationale_val
        if errors_val is not None:
            item['errors'] = errors_val
        if eval_result_str is not None:
            item['evaluation_result'] = eval_result_str
        per_gen_latest[(str(pid), gen)] = item
        maybe_add('parsed_and_mapped', r, {'mapping_source': mapping_source or ''})
        track_mapping_source(mapping_source or 'unknown', r, gen)
        seen_generators[gen] = seen_generators.get(gen, 0) + 1

    mirror_eval_dir = mirror_dir / evaluator_tag
    mirror_eval_dir.mkdir(parents=True, exist_ok=True)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for (pid, gen), item in per_gen_latest.items():
        grouped.setdefault(gen, []).append(item)

    counts: Dict[str, int] = {}
    for gen, items in grouped.items():
        # Sanitize model name for both filename AND data (use only part after last slash)
        sanitized_gen = sanitize_model_name(gen)
        mir_file = mirror_eval_dir / f"{sanitized_gen}.eval.jsonl"
        mir_file.parent.mkdir(parents=True, exist_ok=True)
        with mir_file.open("w", encoding="utf-8") as f:
            for it in items:
                # Use sanitized generator name for matching with expert_gradings
                it_with_gen = dict(it)
                it_with_gen['generator'] = sanitized_gen  # Sanitized name (e.g., "qwen3-235b...")
                f.write(json.dumps(it_with_gen, ensure_ascii=False) + "\n")
        counts[gen] = len(items)

    if debug:
        # Summarize id->models cardinality
        card_stats: Dict[int, int] = {}
        for s in id_to_models.values():
            card_stats[len(s)] = card_stats.get(len(s), 0) + 1
        report = {
            'total_raw': len(rows),
            'written_per_generator': counts,
            'reasons': reasons,
            'mapping_sources': mapping_sources,
            'seen_generators': {k: seen_generators.get(k, 0) for k in sorted(seen_generators)},
            'idsol_to_model_size': len(idsol_to_model),
            'id_to_models_cardinality': {str(k): v for k, v in sorted(card_stats.items())},
        }
        if debug_report_path:
            debug_report_path.parent.mkdir(parents=True, exist_ok=True)
            with debug_report_path.open('w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        print("Debug summary:")
        for k, v in reasons.items():
            print(f"  {k}: {v['count']}")
        print("Written per generator:", counts)
        print("Mapping sources:", {k: v['count'] for k, v in mapping_sources.items()})
        print("Seen generators:", sorted(grouped.keys()))
        print("idsol_to_model entries:", len(idsol_to_model))
        print("id_to_models cardinality:", {k: v for k, v in sorted(card_stats.items())})

    return counts


def run_metrics(data_dir: Path = None) -> None:
    """Run metrics computation for a data directory."""
    cmd = [sys.executable, str(METRICS_SCRIPT)]
    if data_dir:
        cmd.extend(["--data-dir", str(data_dir)])
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        raise SystemExit(f"metrics script failed with exit code {res.returncode}")
    
    cmd = [sys.executable, str(DASHBOARD_SCRIPT)]
    if data_dir:
        cmd.extend(["--data-dir", str(data_dir)])
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        raise SystemExit(f"dashboard script failed with exit code {res.returncode}")


def build_steps_dataset_from_raw(
    steps_raw_path: Path,
    transformed_path: Path,
    dataset_path: Path = None,
    fallback_solution_from_prompt: bool = True,
) -> int:
    """
    Build the judge-stage dataset by copying the original dataset's problem/solution
    and attaching the Stage A response as the `steps` field.

    If `dataset_path` is provided, it is used as the base; otherwise falls back to
    inferring fields from the steps raw file (legacy behavior).
    """
    steps_rows = read_jsonl(steps_raw_path)
    transformed_path.parent.mkdir(parents=True, exist_ok=True)

    # Build a mapping id -> (steps, meta)
    id_to_steps: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for r in steps_rows:
        pid = r.get("id")
        if not pid:
            continue
        resp = r.get("response")
        if resp is None and isinstance(r.get("responses"), list) and r.get("responses"):
            resp = r["responses"][0]
        if not isinstance(resp, str) or not resp.strip():
            continue
        meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        id_to_steps[str(pid)] = (resp, meta)

    written = 0
    with transformed_path.open("w", encoding="utf-8") as out:
        if dataset_path and Path(dataset_path).exists():
            # Preferred path: copy ALL original dataset fields and attach steps
            for base in read_jsonl(Path(dataset_path)):
                pid = base.get("id")
                if pid is None:
                    continue
                key = str(pid)
                if key not in id_to_steps:
                    continue
                steps, meta = id_to_steps[key]
                base_model = base.get("model") if isinstance(base.get("model"), str) and base.get("model").strip() else None
                # If base id is already composite, keep as-is; otherwise append model when available
                if "::" in key:
                    composite_id = key
                else:
                    composite_id = f"{key}::{base_model}" if base_model else key
                # Start from a shallow copy of the base row to preserve all fields
                record: Dict[str, Any] = dict(base)
                # Ensure id reflects the composite id convention
                record["id"] = composite_id
                # Attach/override steps field
                record["steps"] = steps
                # If base lacks marking_scheme but meta provides it, fill it in
                if "marking_scheme" not in record and isinstance(meta.get("marking_scheme"), str):
                    record["marking_scheme"] = meta.get("marking_scheme")
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
        else:
            # Legacy fallback: infer problem/solution from steps raw
            for r in steps_rows:
                pid = r.get("id")
                problem = r.get("problem")
                if not pid or not isinstance(problem, str):
                    continue
                resp = r.get("response")
                if resp is None and isinstance(r.get("responses"), list) and r.get("responses"):
                    resp = r["responses"][0]
                if not isinstance(resp, str):
                    continue
                meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
                solution = meta.get("solution")
                if not isinstance(solution, str) and fallback_solution_from_prompt:
                    sol_from_prompt = extract_solution_from_prompt(r.get("prompt", ""))
                    solution = sol_from_prompt if isinstance(sol_from_prompt, str) and sol_from_prompt.strip() else None
                if not isinstance(solution, str):
                    for alias in ["model_solution", "candidate_solution", "generated_solution"]:
                        if isinstance(meta.get(alias), str):
                            solution = meta.get(alias)
                            break
                marking_scheme = meta.get("marking_scheme") if isinstance(meta.get("marking_scheme"), str) else ""
                record: Dict[str, Any] = {
                    "id": str(pid),
                    "problem": problem,
                    "solution": solution or "",
                    "steps": resp,
                    "marking_scheme": marking_scheme,
                    "metadata": meta,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
    return written


def build_augmented_dataset_from_raw(
    source_raw_path: Path,
    transformed_path: Path,
    dataset_path: Path,
    field_name: str,
) -> int:
    """
    Build a new dataset by copying the original dataset's problem/solution and
    attaching the Stage response as the specified field name (e.g., "initial_report", "critique").

    The resulting IDs follow the same convention as steps builder: if the base id is not
    composite, we append the original generator model ("<id>::<model>") to enable mapping.
    """
    rows = read_jsonl(source_raw_path)
    transformed_path.parent.mkdir(parents=True, exist_ok=True)

    # Map id -> (response, meta)
    id_to_payload: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for r in rows:
        pid = r.get("id")
        if not pid:
            continue
        resp = r.get("response")
        if resp is None and isinstance(r.get("responses"), list) and r.get("responses"):
            resp = r["responses"][0]
        if not isinstance(resp, str) or not resp.strip():
            continue
        meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        id_to_payload[str(pid)] = (resp, meta)

    written = 0
    with transformed_path.open("w", encoding="utf-8") as out:
        for base in read_jsonl(Path(dataset_path)):
            pid = base.get("id")
            if pid is None:
                continue
            key = str(pid)
            if key not in id_to_payload:
                continue
            payload, meta = id_to_payload[key]
            base_model = base.get("model") if isinstance(base.get("model"), str) and base.get("model").strip() else None
            if "::" in key:
                composite_id = key
            else:
                composite_id = f"{key}::{base_model}" if base_model else key
            # Start from a shallow copy of the base row to preserve all fields
            record: Dict[str, Any] = dict(base)
            # Ensure id reflects the composite id convention
            record["id"] = composite_id
            # Attach/override the stage-specific field
            record[field_name] = payload
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    return written


def write_per_generator_eval_binary(
    evaluator_tag: str,
    raw_results_path: Path,
    dataset_path: Path,
    mirror_dir: Path,
    evaluator_model: str,
    template_name: str,
    debug: bool = False,
    debug_limit: int = 5,
    debug_report_path: Path = None,
    use_raw_generator: bool = False,
    steps_dataset_path: Path = None,
    assume_id_composite: bool = False,
) -> Dict[str, int]:
    """
    Same as write_per_generator_eval but writes a `label` (0/1) field
    derived from the parsed numeric `score` using threshold >= 6.
    Outputs are written under `mirror_dir/evaluator_tag/`.
    """
    counts = write_per_generator_eval(
        evaluator_tag=evaluator_tag,
        raw_results_path=raw_results_path,
        dataset_path=dataset_path,
        mirror_dir=mirror_dir,
        evaluator_model=evaluator_model,
        template_name=template_name,
        debug=debug,
        debug_limit=debug_limit,
        debug_report_path=debug_report_path,
        use_raw_generator=use_raw_generator,
        steps_dataset_path=steps_dataset_path,
        assume_id_composite=assume_id_composite,
    )
    # Post-process written files to attach `label`
    out_dir = mirror_dir / evaluator_tag
    for file in out_dir.glob("*.eval.jsonl"):
        try:
            rows = read_jsonl(file)
            with file.open("w", encoding="utf-8") as f:
                for r in rows:
                    # Prefer explicit evaluation_result when present
                    label = None
                    ev = r.get('evaluation_result')
                    if isinstance(ev, str) and ev.strip().lower() in {'correct','incorrect'}:
                        label = 1 if ev.strip().lower() == 'correct' else 0
                    if label is None:
                        sc = r.get("score")
                        try:
                            scf = float(sc)
                            if 0.0 <= scf <= 1.0:
                                label = 1 if scf >= 0.5 else 0
                            else:
                                label = 1 if scf >= 6.0 else 0
                        except Exception:
                            label = 0
                    r["label"] = int(label)
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        except Exception:
            continue
    return counts


def run_binary_metrics(data_dir: Path = None) -> None:
    """Run binary metrics computation for a data directory."""
    cmd = [sys.executable, str(METRICS_SCRIPT_BINARY)]
    if data_dir:
        cmd.extend(["--data-dir", str(data_dir)])
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        raise SystemExit(f"binary metrics script failed with exit code {res.returncode}")


