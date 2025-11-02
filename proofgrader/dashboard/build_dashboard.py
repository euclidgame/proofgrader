#!/usr/bin/env python3
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any


ROOT = Path(__file__).resolve().parent
OUTPUTS_ROOT = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"  # default legacy path; can be overridden via --data-version or --reports-dir
OUTPUT_HTML = OUTPUTS_ROOT / "dashboard" / "dashboard.html"
DESCRIPTIONS_PATH = OUTPUTS_ROOT / "dashboard" / "evaluator_descriptions.json"


def read_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_data(reports_dir: Path, human_jsonl_path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    overall_path = reports_dir / "per_evaluator_overall.csv"
    overall_norm_path = reports_dir / "per_evaluator_overall_normalized.csv"
    per_gen_path = reports_dir / "per_evaluator_per_generator.csv"
    per_src_path = reports_dir / "per_evaluator_per_source.csv"
    disagreement_path = reports_dir / "disagreement_per_item.csv"
    order_overall_path = reports_dir / "order_preservation_overall.csv"
    verify_vs_solve_path = reports_dir / "verify_vs_solve.csv"
    # Stratified (numeric) optional paths
    true_bin_overall_path = reports_dir / "per_evaluator_by_true_bin.csv"
    true_bin_per_gen_path = reports_dir / "per_evaluator_per_generator_by_true_bin.csv"

    if not overall_path.exists():
        raise SystemExit(f"Missing report: {overall_path}")
    if not per_gen_path.exists():
        raise SystemExit(f"Missing report: {per_gen_path}")
    if not per_src_path.exists():
        raise SystemExit(f"Missing report: {per_src_path}")

    overall = read_csv(overall_path)
    overall_normalized: List[Dict[str, Any]] = []
    if overall_norm_path.exists():
        overall_normalized = read_csv(overall_norm_path)
    disagreement: List[Dict[str, Any]] = []
    if disagreement_path.exists():
        disagreement = read_csv(disagreement_path)
    order_overall: List[Dict[str, Any]] = []
    if order_overall_path.exists():
        order_overall = read_csv(order_overall_path)
    verify_vs_solve: List[Dict[str, Any]] = []
    if verify_vs_solve_path.exists():
        verify_vs_solve = read_csv(verify_vs_solve_path)
    per_gen = read_csv(per_gen_path)
    per_src = read_csv(per_src_path)

    # Optional: numeric stratified by true-score bin
    numeric_bins_overall: List[Dict[str, Any]] = []
    if true_bin_overall_path.exists():
        numeric_bins_overall = read_csv(true_bin_overall_path)
    numeric_bins_per_gen: List[Dict[str, Any]] = []
    if true_bin_per_gen_path.exists():
        numeric_bins_per_gen = read_csv(true_bin_per_gen_path)


    # Build evaluator index (numeric only)
    evaluators: List[str] = sorted({row.get("evaluator", "") for row in overall if row.get("evaluator")})

    # Group detailed tables by evaluator
    per_gen_by_eval: Dict[str, List[Dict[str, Any]]] = {}
    for row in per_gen:
        ev = row.get("evaluator")
        if not ev:
            continue
        per_gen_by_eval.setdefault(ev, []).append(row)

    per_src_by_eval: Dict[str, List[Dict[str, Any]]] = {}
    for row in per_src:
        ev = row.get("evaluator")
        if not ev:
            continue
        per_src_by_eval.setdefault(ev, []).append(row)

    # Merge Kendall tau-b (macro) into overall rows if available
    if order_overall:
        by_eval_k: Dict[str, Dict[str, Any]] = {}
        for row in order_overall:
            ev = str(row.get("evaluator", ""))
            if ev:
                by_eval_k[ev] = row
        for row in overall:
            ev = str(row.get("evaluator", ""))
            krow = by_eval_k.get(ev)
            if krow:
                try:
                    row["kendall_tau_b"] = float(krow.get("macro_kendall_tau_b")) if krow.get("macro_kendall_tau_b") not in (None, "") else ""
                except Exception:
                    row["kendall_tau_b"] = ""
                try:
                    row["weighted_kendall_tau_b"] = float(krow.get("weighted_macro_kendall_tau_b")) if krow.get("weighted_macro_kendall_tau_b") not in (None, "") else ""
                except Exception:
                    row["weighted_kendall_tau_b"] = ""

    data["overall"] = overall
    data["overall_normalized"] = overall_normalized
    data["disagreement_per_item"] = disagreement
    data["order_preservation_overall"] = order_overall
    data["verify_vs_solve"] = verify_vs_solve
    data["evaluators"] = evaluators
    data["per_generator_by_evaluator"] = per_gen_by_eval
    data["per_source_by_evaluator"] = per_src_by_eval

    # Group numeric stratified rows by evaluator
    by_eval_numeric_bins_overall: Dict[str, List[Dict[str, Any]]] = {}
    for row in (numeric_bins_overall or []):
        ev = row.get("evaluator")
        if not ev:
            continue
        by_eval_numeric_bins_overall.setdefault(ev, []).append(row)
    for rows in by_eval_numeric_bins_overall.values():
        rows.sort(key=lambda r: (int(float(r.get("true_bin", 0))),))

    by_eval_numeric_bins_per_gen: Dict[str, List[Dict[str, Any]]] = {}
    for row in (numeric_bins_per_gen or []):
        ev = row.get("evaluator")
        if not ev:
            continue
        by_eval_numeric_bins_per_gen.setdefault(ev, []).append(row)
    for rows in by_eval_numeric_bins_per_gen.values():
        rows.sort(key=lambda r: (str(r.get("generator", "")), int(float(r.get("true_bin", 0)))))

    data["numeric_bins_overall_by_eval"] = by_eval_numeric_bins_overall
    data["numeric_bins_per_generator_by_eval"] = by_eval_numeric_bins_per_gen

    # No binary data in this dashboard

    # Evaluator and template descriptions (optional)
    descriptions: Dict[str, Any] = {}
    template_desc: Dict[str, str] = {}
    if DESCRIPTIONS_PATH.exists():
        try:
            with DESCRIPTIONS_PATH.open("r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    # Split top-level workflow descriptions and template descriptions
                    template_desc = obj.get("templates", {}) or {}
                    descriptions = {k: v for k, v in obj.items() if k != "templates"}
        except Exception:
            # Keep descriptions empty on error
            pass
    data["descriptions"] = descriptions
    data["template_descriptions"] = template_desc

    # Human score aggregates (from evaluation_merged.jsonl)
    def _quantiles(values: List[float]) -> Dict[str, Any]:
        if not values:
            return {"p25": None, "median": None, "p75": None}
        s = sorted(values)
        n = len(s)
        def q(p: float) -> float:
            if n == 1:
                return s[0]
            idx = p * (n - 1)
            lo = math.floor(idx)
            hi = math.ceil(idx)
            if lo == hi:
                return s[lo]
            w = idx - lo
            return s[lo] * (1 - w) + s[hi] * w
        return {"p25": q(0.25), "median": q(0.5), "p75": q(0.75)}

    def _norm_source(src: str) -> str:
        s = str(src).strip()
        return "TST" if s.upper() == "USA" else s

    human_records: List[Dict[str, Any]] = []
    if human_jsonl_path.exists():
        with human_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = obj.get("problem_id", "")
                src = pid.split("-", 1)[0] if "-" in pid else pid
                src = _norm_source(src)
                try:
                    score_val = float(obj.get("score", 0.0))
                except (TypeError, ValueError):
                    score_val = 0.0
                human_records.append({
                    "problem_id": pid,
                    "generator": obj.get("model_name", ""),
                    "source": src,
                    "score": score_val,
                })

    scores = [r["score"] for r in human_records]
    human_overall: Dict[str, Any] = {
        "count": len(scores),
        "mean": (statistics.fmean(scores) if scores else None),
        "stdev": (statistics.pstdev(scores) if len(scores) > 1 else 0.0),
        "min": (min(scores) if scores else None),
        "max": (max(scores) if scores else None),
    }
    human_overall.update(_quantiles(scores))

    by_gen: Dict[str, List[float]] = defaultdict(list)
    by_src: Dict[str, List[float]] = defaultdict(list)
    for r in human_records:
        by_gen[r["generator"]].append(r["score"])
        by_src[r["source"]].append(r["score"])

    def _summarize(group: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for k, vals in group.items():
            row: Dict[str, Any] = {
                "key": k,
                "count": len(vals),
                "mean": (statistics.fmean(vals) if vals else None),
                "stdev": (statistics.pstdev(vals) if len(vals) > 1 else 0.0),
                "min": (min(vals) if vals else None),
                "max": (max(vals) if vals else None),
            }
            row.update(_quantiles(vals))
            rows.append(row)
        rows.sort(key=lambda r: (-(r["mean"] or 0.0), r["key"]))
        return rows

    human_per_generator = _summarize(by_gen)
    human_per_source = _summarize(by_src)

    def _make_hist(vals: List[float]) -> Dict[str, int]:
        hist: Dict[str, int] = {}
        if not vals:
            return hist
        counts = Counter(int(math.floor(s)) for s in vals)
        lo = int(math.floor(min(vals)))
        hi = int(math.ceil(max(vals)))
        for k in range(lo, hi + 1):
            hist[str(k)] = counts.get(k, 0)
        return hist

    histogram: Dict[str, int] = _make_hist(scores)

    per_generator_histograms: Dict[str, Dict[str, int]] = {}
    for g, vals in by_gen.items():
        per_generator_histograms[g] = _make_hist(vals)

    per_source_histograms: Dict[str, Dict[str, int]] = {}
    for s_key, vals in by_src.items():
        per_source_histograms[s_key] = _make_hist(vals)

    data["human_scores"] = {
        "overall": human_overall,
        "per_generator": human_per_generator,
        "per_source": human_per_source,
        "histogram": histogram,
        "per_generator_histograms": per_generator_histograms,
        "per_source_histograms": per_source_histograms,
    }
    return data


def build_html(payload: Dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    # Minimal, self-contained CSS/JS dashboard
    html = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Evaluator Dashboard</title>
  <style>
    :root {
      --bg: #f7f9fc;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #2563eb;
      --good: #16a34a;
      --warn: #d97706;
      --bad: #dc2626;
      --border: #e5e7eb;
    }
    html, body { margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--text); font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
    .layout { display: grid; grid-template-columns: 280px 1fr; height: 100vh; }
    .sidebar { display: block; border-right: 1px solid var(--border); background: var(--panel); }
    .sidebar h2 { margin: 8px 8px 4px; font-size: 14px; color: var(--muted); font-weight: 600; letter-spacing: .02em; }
    .search { margin: 8px; }
    .search input { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border); background: #ffffff; color: var(--text); }
    .eval-list { margin: 8px; display: flex; flex-direction: column; gap: 4px; }
    .eval-item { cursor: pointer; border: 1px solid var(--border); background: #ffffff; padding: 8px 10px; border-radius: 8px; transition: background .15s, border-color .15s; font-size: 13px; }
    .eval-item:hover { background: #f9fafb; border-color: #cbd5e1; }
    .eval-item.active { background: #eef2ff; border-color: var(--accent); box-shadow: 0 0 0 1px inset rgba(37, 99, 235, 0.35); }

    .content { overflow-y: auto; }
    .header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); background: rgba(255,255,255,0.85); position: sticky; top: 0; backdrop-filter: blur(6px); }
    .header .title { font-size: 18px; font-weight: 700; }
    .header .subtitle { font-size: 13px; color: var(--muted); margin-top: 4px; }

    .container { padding: 16px 20px; display: grid; gap: 16px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
    .metric { font-size: 12px; color: var(--muted); }
    .value { font-size: 22px; font-weight: 700; margin-top: 6px; color: var(--accent); }

    .section { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
    .section h3 { margin: 0; padding: 12px 12px; border-bottom: 1px solid var(--border); font-size: 14px; letter-spacing: .02em; background: #f3f4f6; }
    .table-wrap { overflow: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--border); padding: 8px 10px; text-align: left; white-space: nowrap; }
    th { position: sticky; top: 0; background: #f9fafb; }
    tr:hover td { background: #f9fafb; }
    .chip { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid var(--border); background: #f3f4f6; color: var(--text); }
    .badge-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:middle; }

    .toolbar { display: flex; gap: 8px; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border); background: #ffffff; }
    .toolbar .pill { padding: 6px 10px; background: #f3f4f6; border: 1px solid var(--border); border-radius: 999px; font-size: 12px; color: var(--muted); cursor: pointer; }
    .toolbar .pill.active { color: var(--text); border-color: var(--accent); box-shadow: 0 0 0 1px inset rgba(37, 99, 235, 0.35); }
    .toolbar .right { margin-left: auto; display: flex; gap: 8px; align-items: center; }
    .toolbar label { font-size: 12px; color: var(--muted); }
    .toolbar select { padding: 6px 10px; background: #ffffff; border: 1px solid var(--border); border-radius: 8px; font-size: 12px; color: var(--text); }
  </style>
</head>
<body>
  <div class=\"layout\">
    <aside class=\"sidebar\">
      <h2>Evaluators</h2>
      <div class=\"search\"><input id=\"search\" placeholder=\"Search evaluators...\" /></div>
      <div id=\"evalList\" class=\"eval-list\"></div>
    </aside>
    <main class=\"content\">
      <div class=\"header\">
        <div>
          <div class=\"title\">Evaluator Results Dashboard</div>
          <div class=\"subtitle\">Overview and drill-down for all evaluators, per generator and per source</div>
        </div>
        <div class=\"chip\" id=\"countChip\"></div>
      </div>

      <div class=\"container\">
        <section class=\"section\">
          <div class=\"toolbar\">
            <div class=\"pill active\" data-view=\"overview\">Overview</div>
            <div class=\"pill\" data-view=\"evaluator\">Selected Evaluator</div>
            <div class=\"pill\" data-view=\"normalized\">Normalized Overview</div>
            <div class=\"pill\" data-view=\"disagreement\">Disagreement</div>
            <div class=\"pill\" data-view=\"verify\">Verify vs Solve</div>
            <div class=\"right\">
              <label for=\"sortMetric\">Ranked by</label>
              <select id=\"sortMetric\"></select>
            </div>
          </div>
          <div id=\"overviewView\">
            <div class=\"table-wrap\" id=\"overallTableWrap\"></div>
          </div>
          <div id=\"evaluatorView\" style=\"display:none\"> 
            <div class=\"cards\" id=\"summaryCards\"></div>
            <div class=\"section\" style=\"margin-top:12px\"> 
              <h3>About this Evaluator</h3>
              <div class=\"table-wrap\"><div id=\"evaluatorDescription\" style=\"padding:10px\"></div></div>
            </div>
            <div class=\"section\" style=\"margin-top:12px\"> 
              <h3>Per-Generator</h3>
              <div class=\"table-wrap\" id=\"perGenTableWrap\"></div>
            </div>
            <div class=\"section\" style=\"margin-top:12px\"> 
              <h3>Per-Source</h3>
              <div class=\"table-wrap\" id=\"perSrcTableWrap\"></div>
            </div>
            <div class=\"section\" style=\"margin-top:12px\"> 
              <h3>Stratified by True Score (0–7)</h3>
              <div class=\"table-wrap\" id=\"numericBinsOverallWrap\"></div>
            </div>
            <div class=\"section\" style=\"margin-top:12px\"> 
              <h3>Stratified by True Score · Per-Generator</h3>
              <div class=\"table-wrap\" id=\"numericBinsPerGenWrap\"></div>
            </div>
          </div>
          <div id=\"normalizedView\" style=\"display:none\">
            <div class=\"table-wrap\" id=\"overallNormTableWrap\"></div>
          </div>
          <div id=\"disagreementView\" style=\"display:none\"> 
            <div class=\"table-wrap\" id=\"disagreementTableWrap\"></div>
          </div>
          <div id=\"verifyView\" style=\"display:none\"> 
            <div class=\"table-wrap\" id=\"verifyTableWrap\"></div>
          </div>
        </section>
      </div>
    </main>
  </div>

  <script>
    // Dynamic data loading
    window.dashboardData = {};
    window.__dataLoaded = false;
    async function loadData() {
      const chip = document.getElementById('countChip');
      try {
        const resp = await fetch('data.json', { cache: 'no-store' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        window.dashboardData = await resp.json();
        window.__dataLoaded = true;
      } catch (err) {
        console.error('Failed to load data.json. If opening from file://, please serve the folder via a local web server (e.g., `python -m http.server`).', err);
        if (chip) chip.textContent = 'Data load failed';
      }
    }

    const fmt = (v) => {
      if (v === null || v === undefined || v === '') return '';
      const n = Number(v);
      if (!Number.isFinite(n)) return String(v);
      return n.toFixed(3);
    };

    const state = {
      selected: null,
      view: 'overview',
      sortKey: 'rmse',
      sortDir: 'asc', // 'asc' | 'desc'
      selectedSet: new Set()
    };

    const qs = (sel) => document.querySelector(sel);
    const qsa = (sel) => Array.from(document.querySelectorAll(sel));

    function renderSidebar() {
      const list = qs('#evalList');
      list.innerHTML = '';
      const query = qs('#search').value.toLowerCase();
      const all = (window.dashboardData && Array.isArray(window.dashboardData.evaluators)) ? window.dashboardData.evaluators : [];
      const evals = all.filter(e => String(e).toLowerCase().includes(query));
      evals.forEach(ev => {
        const row = document.createElement('div');
        row.className = 'eval-item' + (state.selected === ev ? ' active' : '');
        row.title = ev;
        // checkbox
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.style.marginRight = '8px';
        cb.checked = state.selectedSet.has(ev);
        cb.addEventListener('click', (e) => { e.stopPropagation(); });
        cb.addEventListener('change', () => {
          if (cb.checked) state.selectedSet.add(ev); else state.selectedSet.delete(ev);
          syncView();
        });
        // label
        const label = document.createElement('span');
        label.textContent = ev;
        label.style.userSelect = 'none';
        // clicking the row opens evaluator view
        row.onclick = () => { state.selected = ev; state.view = 'evaluator'; syncView(); };
        row.appendChild(cb);
        row.appendChild(label);
        list.appendChild(row);
      });
      const selectedCount = state.selectedSet.size;
      qs('#countChip').textContent = `${evals.length} evaluators${selectedCount ? ` · ${selectedCount} selected` : ''}`;
    }

    function metricOptionsForView(view) {
      if (view === 'normalized') {
        return [
          {key:'norm_rmse', label:'Norm RMSE', dir:'asc'},
          {key:'norm_mae', label:'Norm MAE', dir:'asc'},
          {key:'norm_bias', label:'Norm Bias |abs|', dir:'asc'},
          {key:'norm_pearson', label:'Norm Pearson', dir:'desc'},
          {key:'norm_wta', label:'Norm WTA', dir:'desc'},
          {key:'count', label:'Count', dir:'desc'}
        ];
      }
      // default overview
      return [
        {key:'rmse', label:'RMSE', dir:'asc'},
        {key:'mae', label:'MAE', dir:'asc'},
        {key:'bias', label:'Bias |abs|', dir:'asc'},
        {key:'pearson', label:'Pearson', dir:'desc'},
        {key:'kendall_tau_b', label:'Kendall tau-b', dir:'desc'},
        {key:'order_preserving_ratio', label:'Order Preserving Ratio', dir:'desc'},
        {key:'wta', label:'WTA', dir:'desc'},
        {key:'count', label:'Count', dir:'desc'}
      ];
    }

    function populateSortSelect() {
      const sel = qs('#sortMetric');
      if (!sel) return;
      const opts = metricOptionsForView(state.view);
      sel.innerHTML = '';
      // Preserve current selection if valid for this view; otherwise, pick view default
      const hasMatch = opts.some(o => o.key === state.sortKey);
      if (!hasMatch) {
        const def = (state.view === 'normalized') ? opts.find(o => o.key === 'norm_rmse') : opts.find(o => o.key === 'rmse');
        if (def) { state.sortKey = def.key; state.sortDir = def.dir; }
      }
      opts.forEach((o) => {
        const opt = document.createElement('option');
        opt.value = o.key + '::' + o.dir;
        opt.textContent = 'Ranked by ' + o.label;
        if (o.key === state.sortKey) { opt.selected = true; }
        sel.appendChild(opt);
      });
    }

    function getSortSpec() {
      // returns {key, dir}
      const sel = qs('#sortMetric');
      if (sel && sel.value) {
        const [k, d] = sel.value.split('::');
        return { key: k, dir: d || 'asc' };
      }
      return { key: state.sortKey, dir: state.sortDir };
    }

    function sortRowsByMetric(rows, key, dir) {
      const isAbs = (key === 'bias' || key === 'norm_bias');
      const val = (r) => {
        const raw = Number(r[key]);
        const n = Number.isFinite(raw) ? raw : (dir === 'asc' ? Infinity : -Infinity);
        return isAbs ? Math.abs(n) : n;
      };
      rows.sort((a,b) => (dir === 'asc' ? (val(a) - val(b)) : (val(b) - val(a))));
    }

    function hashCode(str) {
      let h = 0;
      for (let i = 0; i < str.length; i++) {
        h = ((h << 5) - h) + str.charCodeAt(i);
        h |= 0;
      }
      return h;
    }

    function colorForKey(key) {
      if (!key) return '#9ca3af';
      const h = (Math.abs(hashCode(String(key))) % 360);
      return `hsl(${h}, 70%, 45%)`;
    }

    function renderTable(columns, rows, opts = {}) {
      const identityKey = opts.identityKey || null;
      const highlight = opts.highlight || {}; // { colKey: Set(identity) }
      const clickKey = opts.clickKey || null;
      const onRowClick = (typeof opts.onRowClick === 'function') ? opts.onRowClick : null;
      const table = document.createElement('table');
      const thead = document.createElement('thead');
      const tr = document.createElement('tr');
      columns.forEach(({key, label}) => {
        const th = document.createElement('th');
        th.textContent = label;
        tr.appendChild(th);
      });
      thead.appendChild(tr);
      table.appendChild(thead);

      const tbody = document.createElement('tbody');
      rows.forEach(row => {
        const tr = document.createElement('tr');
        columns.forEach(({key}) => {
          const td = document.createElement('td');
          const val = row[key];
          // Colorize generator/source cells and optionally bold best values
          const isMetric = ['mae','rmse','bias','pearson','order_preserving_ratio','wta','norm_mae','norm_rmse','norm_bias','norm_pearson','norm_wta','count','min_diff','max_diff'].includes(key);
          if (key === 'generator' || key === 'source') {
            const color = colorForKey(val);
            td.style.borderLeft = `4px solid ${color}`;
            const span = document.createElement('span');
            span.innerHTML = `<span class="badge-dot" style="background:${color}"></span>${val ?? ''}`;
            td.appendChild(span);
          } else {
            let text = isMetric ? fmt(val) : (val ?? '');
            const idVal = identityKey ? row[identityKey] : null;
            if (idVal && highlight[key] && highlight[key].has(idVal)) {
              td.innerHTML = `<strong>${text}</strong>`;
            } else {
              td.textContent = text;
            }
            if (clickKey && key === clickKey) {
              td.style.color = 'var(--accent)';
              td.style.textDecoration = 'underline';
              td.style.cursor = 'pointer';
              if (onRowClick) {
                td.addEventListener('click', () => onRowClick(row));
              }
            }
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      return table;
    }

    function buildOverall() {
      const wrap = qs('#overallTableWrap');
      wrap.innerHTML = '';
      const cols = [
        {key:'_rowId', label:'ID'},
        {key:'evaluator', label:'Evaluator'},
        {key:'count', label:'Count'},
        {key:'mae', label:'MAE'},
        {key:'rmse', label:'RMSE'},
        {key:'bias', label:'Bias'},
        {key:'pearson', label:'Pearson'},
        {key:'kendall_tau_b', label:'Kendall tau-b'},
        {key:'order_preserving_ratio', label:'Order Preserving Ratio'},
        {key:'wta', label:'WTA (≤1)'},
        {key:'min_diff', label:'Min Δ'},
        {key:'max_diff', label:'Max Δ'}
      ];
      let rows = [...window.dashboardData.overall];
      if (state.selectedSet && state.selectedSet.size) {
        rows = rows.filter(r => state.selectedSet.has(r.evaluator));
      }
      const spec = getSortSpec();
      sortRowsByMetric(rows, spec.key, spec.dir);
      // Assign sequential row ids after sorting
      rows.forEach((r, i) => { r._rowId = i + 1; });

      // Compute per-column bests to highlight
      const ids = rows.map(r => r.evaluator);
      const num = (v) => Number(v);
      const abs = (v) => Math.abs(Number(v));
      const best = {
        mae: Math.min(...rows.map(r => num(r.mae))),
        rmse: Math.min(...rows.map(r => num(r.rmse))),
        bias_abs: Math.min(...rows.map(r => abs(r.bias))),
        pearson: Math.max(...rows.map(r => num(r.pearson))),
        kendall_tau_b: Math.max(...rows.map(r => num(r.kendall_tau_b))),
        order_preserving_ratio: Math.max(...rows.map(r => num(r.order_preserving_ratio))),
        wta: Math.max(...rows.map(r => num(r.wta))),
      };
      const highlight = {
        mae: new Set(rows.filter(r => num(r.mae) === best.mae).map(r => r.evaluator)),
        rmse: new Set(rows.filter(r => num(r.rmse) === best.rmse).map(r => r.evaluator)),
        bias: new Set(rows.filter(r => abs(r.bias) === best.bias_abs).map(r => r.evaluator)),
        pearson: new Set(rows.filter(r => num(r.pearson) === best.pearson).map(r => r.evaluator)),
        kendall_tau_b: new Set(rows.filter(r => num(r.kendall_tau_b) === best.kendall_tau_b).map(r => r.evaluator)),
        order_preserving_ratio: new Set(rows.filter(r => num(r.order_preserving_ratio) === best.order_preserving_ratio).map(r => r.evaluator)),
        wta: new Set(rows.filter(r => num(r.wta) === best.wta).map(r => r.evaluator)),
      };

      wrap.appendChild(renderTable(cols, rows, { identityKey: 'evaluator', highlight, clickKey: 'evaluator', onRowClick: (r) => { state.selected = r.evaluator; state.view = 'evaluator'; syncView(); } }));
    }

    function buildOverallNormalized() {
      const wrap = qs('#overallNormTableWrap');
      if (!wrap) return;
      wrap.innerHTML = '';
      let rows = [...(window.dashboardData.overall_normalized || [])];
      if (state.selectedSet && state.selectedSet.size) {
        rows = rows.filter(r => state.selectedSet.has(r.evaluator));
      }
      if (!rows.length) { wrap.textContent = 'No normalized metrics found.'; return; }
      const cols = [
        {key:'_rowId', label:'ID'},
        {key:'evaluator', label:'Evaluator'},
        {key:'count', label:'Count'},
        {key:'norm_mae', label:'Norm MAE'},
        {key:'norm_rmse', label:'Norm RMSE'},
        {key:'norm_bias', label:'Norm Bias'},
        {key:'norm_pearson', label:'Norm Pearson'},
        {key:'norm_wta', label:'Norm WTA'}
      ];
      const spec = getSortSpec();
      sortRowsByMetric(rows, spec.key, spec.dir);
      rows.forEach((r, i) => { r._rowId = i + 1; });
      const num = (v) => Number(v);
      const abs = (v) => Math.abs(Number(v));
      const best = {
        norm_mae: Math.min(...rows.map(r => num(r.norm_mae))),
        norm_rmse: Math.min(...rows.map(r => num(r.norm_rmse))),
        norm_bias_abs: Math.min(...rows.map(r => abs(r.norm_bias))),
        norm_pearson: Math.max(...rows.map(r => num(r.norm_pearson))),
      };
      const highlight = {
        norm_mae: new Set(rows.filter(r => num(r.norm_mae) === best.norm_mae).map(r => r.evaluator)),
        norm_rmse: new Set(rows.filter(r => num(r.norm_rmse) === best.norm_rmse).map(r => r.evaluator)),
        norm_bias: new Set(rows.filter(r => abs(r.norm_bias) === best.norm_bias_abs).map(r => r.evaluator)),
        norm_pearson: new Set(rows.filter(r => num(r.norm_pearson) === best.norm_pearson).map(r => r.evaluator)),
      };
      wrap.appendChild(renderTable(cols, rows, { identityKey: 'evaluator', highlight }));
    }

    function buildDisagreement() {
      const wrap = qs('#disagreementTableWrap');
      if (!wrap) return; wrap.innerHTML = '';
      const rows = [...(window.dashboardData.disagreement_per_item || [])];
      if (!rows.length) { wrap.textContent = 'No disagreement data found.'; return; }
      const cols = [
        {key:'_rowId', label:'ID'},
        {key:'problem_id', label:'Problem'},
        {key:'generator', label:'Generator'},
        {key:'true', label:'True'},
        {key:'num_evaluators', label:'#Evaluators'},
        {key:'mean_pred', label:'Mean Pred'},
        {key:'std_pred', label:'Std Pred'},
        {key:'min_pred', label:'Min Pred'},
        {key:'max_pred', label:'Max Pred'},
        {key:'range_pred', label:'Range'},
        {key:'evaluators', label:'Evaluators'},
        {key:'scores', label:'Scores'},
      ];
      rows.sort((a,b) => Number(b.std_pred) - Number(a.std_pred));
      rows.forEach((r, i) => { r._rowId = i + 1; });
      wrap.appendChild(renderTable(cols, rows));
    }

    function buildVerify() {
      const wrap = qs('#verifyTableWrap');
      if (!wrap) return; wrap.innerHTML = '';
      const rows = [...(window.dashboardData.verify_vs_solve || [])];
      if (!rows.length) { wrap.textContent = 'No verify vs solve data found.'; return; }
      const cols = [
        {key:'_rowId', label:'ID'},
        {key:'evaluator', label:'Evaluator'},
        {key:'mapped_generator', label:'Mapped Generator'},
        {key:'problem_id', label:'Problem'},
        {key:'eval_count', label:'Eval Count'},
        {key:'eval_mae', label:'Eval MAE'},
        {key:'eval_rmse', label:'Eval RMSE'},
        {key:'eval_bias', label:'Eval Bias'},
        {key:'eval_wta', label:'Eval WTA (≤1)'},
        {key:'model_own_score', label:'Model Own Score'},
      ];
      // Sort by eval_rmse ascending then by model_own_score descending
      rows.sort((a,b) => (Number(a.eval_rmse) - Number(b.eval_rmse)) || (Number(b.model_own_score) - Number(a.model_own_score)));
      rows.forEach((r, i) => { r._rowId = i + 1; });
      wrap.appendChild(renderTable(cols, rows));
    }

    function buildEvaluator() {
      const ev = state.selected;
      const cards = qs('#summaryCards');
      cards.innerHTML = '';
      // Description block
      const descEl = qs('#evaluatorDescription');
      if (descEl) {
        const descMap = (window.dashboardData && window.dashboardData.descriptions) || {};
        const desc = descMap[ev] || '';
        descEl.textContent = desc;
      }
      const o = window.dashboardData.overall.find(r => r.evaluator === ev);
      if (o) {
        const metrics = [
          {k:'mae', label:'MAE'},
          {k:'rmse', label:'RMSE'},
          {k:'bias', label:'Bias'},
          {k:'pearson', label:'Pearson r'},
          {k:'kendall_tau_b', label:'Kendall tau-b'},
          {k:'order_preserving_ratio', label:'Order Preserving Ratio'},
          {k:'wta', label:'WTA (≤1)'},
        ];
        metrics.forEach(m => {
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `<div class="metric">${m.label}</div><div class="value">${fmt(o[m.k])}</div>`;
          cards.appendChild(card);
        });
      }

      const perGenWrap = qs('#perGenTableWrap');
      perGenWrap.innerHTML = '';
      const perSrcWrap = qs('#perSrcTableWrap');
      perSrcWrap.innerHTML = '';

      const perGen = (window.dashboardData.per_generator_by_evaluator[ev] || []).slice();
      const perSrc = (window.dashboardData.per_source_by_evaluator[ev] || []).slice();

      const perGenCols = [
        {key:'generator', label:'Generator'},
        {key:'count', label:'Count'},
        {key:'mae', label:'MAE'},
        {key:'rmse', label:'RMSE'},
        {key:'bias', label:'Bias'},
        {key:'pearson', label:'Pearson'},
        {key:'wta', label:'WTA (≤1)'},
        {key:'norm_mae', label:'Norm MAE'},
        {key:'norm_rmse', label:'Norm RMSE'},
        {key:'norm_bias', label:'Norm Bias'},
        {key:'norm_wta', label:'Norm WTA (≤1)'},
      ];
      const perSrcCols = [
        {key:'source', label:'Source'},
        {key:'count', label:'Count'},
        {key:'mae', label:'MAE'},
        {key:'rmse', label:'RMSE'},
        {key:'bias', label:'Bias'},
        {key:'pearson', label:'Pearson'},
        {key:'wta', label:'WTA (≤1)'},
        {key:'norm_mae', label:'Norm MAE'},
        {key:'norm_rmse', label:'Norm RMSE'},
        {key:'norm_bias', label:'Norm Bias'},
        {key:'norm_wta', label:'Norm WTA (≤1)'},
      ];

      perGen.sort((a,b) => Number(a.rmse) - Number(b.rmse));
      perSrc.sort((a,b) => Number(a.rmse) - Number(b.rmse));

      perGenWrap.appendChild(renderTable(perGenCols, perGen));
      perSrcWrap.appendChild(renderTable(perSrcCols, perSrc));
      // Stratified tables
      const numOverallWrap = qs('#numericBinsOverallWrap');
      const numPerGenWrap = qs('#numericBinsPerGenWrap');
      if (numOverallWrap) {
        numOverallWrap.innerHTML = '';
        const rows = ((window.dashboardData.numeric_bins_overall_by_eval||{})[ev] || []).slice();
        if (!rows.length) {
          numOverallWrap.textContent = 'No data found.';
        } else {
          const cols = [
            {key:'true_bin', label:'True Bin'},
            {key:'count', label:'Count'},
            {key:'mae', label:'MAE'},
            {key:'rmse', label:'RMSE'},
            {key:'bias', label:'Bias'},
            {key:'pearson', label:'Pearson'},
            {key:'wta', label:'WTA (≤1)'},
            {key:'min_diff', label:'Min Δ'},
            {key:'max_diff', label:'Max Δ'},
          ];
          rows.sort((a,b) => Number(a.true_bin) - Number(b.true_bin));
          numOverallWrap.appendChild(renderTable(cols, rows));
        }
      }
      if (numPerGenWrap) {
        numPerGenWrap.innerHTML = '';
        const rows = ((window.dashboardData.numeric_bins_per_generator_by_eval||{})[ev] || []).slice();
        if (!rows.length) {
          numPerGenWrap.textContent = 'No data found.';
        } else {
          const cols = [
            {key:'generator', label:'Generator'},
            {key:'true_bin', label:'True Bin'},
            {key:'count', label:'Count'},
            {key:'mae', label:'MAE'},
            {key:'rmse', label:'RMSE'},
            {key:'bias', label:'Bias'},
            {key:'pearson', label:'Pearson'},
            {key:'wta', label:'WTA (≤1)'},
            {key:'min_diff', label:'Min Δ'},
            {key:'max_diff', label:'Max Δ'},
          ];
          rows.sort((a,b) => (String(a.generator).localeCompare(String(b.generator))) || (Number(a.true_bin) - Number(b.true_bin)));
          numPerGenWrap.appendChild(renderTable(cols, rows));
        }
      }
    }

    function syncToolbar() {
      qsa('.toolbar .pill').forEach(el => {
        el.classList.toggle('active', el.dataset.view === state.view);
      });
      populateSortSelect();
    }

    function syncView() {
      // Defer rendering of heavy views until data is loaded
      if (!window.__dataLoaded) {
        renderSidebar();
        syncToolbar();
        const chip = qs('#countChip');
        if (chip) chip.textContent = 'Loading...';
        return;
      }
      renderSidebar();
      syncToolbar();
      const showOverview = state.view === 'overview';
      const showEvaluator = state.view === 'evaluator';
      const showNorm = state.view === 'normalized';
      const showDis = state.view === 'disagreement';
      const showVer = state.view === 'verify';
      qs('#overviewView').style.display = showOverview ? '' : 'none';
      qs('#evaluatorView').style.display = showEvaluator ? '' : 'none';
      qs('#normalizedView').style.display = showNorm ? '' : 'none';
      qs('#disagreementView').style.display = showDis ? '' : 'none';
      qs('#verifyView').style.display = showVer ? '' : 'none';
      if (showOverview) buildOverall();
      if (showNorm) buildOverallNormalized();
      if (showEvaluator) buildEvaluator();
      if (showDis) buildDisagreement();
      if (showVer) buildVerify();
    }

    // Wire up events
    document.addEventListener('DOMContentLoaded', () => {
      const searchEl = qs('#search');
      if (searchEl) searchEl.addEventListener('input', renderSidebar);
      const sortSel = qs('#sortMetric');
      if (sortSel) {
        sortSel.addEventListener('change', () => { const [k, d] = sortSel.value.split('::'); state.sortKey = k; state.sortDir = d; syncView(); });
      }
      qsa('.toolbar .pill').forEach(el => {
        el.addEventListener('click', () => { state.view = el.dataset.view; syncView(); });
      });
      // Initial render (empty) then load data and render again
      renderSidebar();
      loadData().then(() => { syncView(); });
    });
  </script>
</body>
</html>
"""
    html = html.replace("__DATA__", data_json)
    # Inject Human Scores tab and view container (ensure both new pills exist)
    if 'data-view="human"' not in html:
        html = html.replace(
            '<div class="pill" data-view="evaluator">Selected Evaluator</div>',
            '<div class="pill" data-view="evaluator">Selected Evaluator</div>\n            <div class="pill" data-view="human">Human Scores</div>'
        )
    html = html.replace(
        '          </div>\n        </section>',
        '          </div>\n          <div id="humanView" style="display:none"></div>\n        </section>'
    )
    # Append script to support Human Scores rendering and view switching
    injected = """
<script>
(function(){
  function renderHistogram(hist) {
    const wrap = document.createElement('div');
    const table = document.createElement('table');
    const thead = document.createElement('thead'); const trh = document.createElement('tr');
    ['Bin (floor)','Count'].forEach(label => { const th = document.createElement('th'); th.textContent = label; trh.appendChild(th); });
    thead.appendChild(trh); table.appendChild(thead);
    const tbody = document.createElement('tbody');
    const keys = Object.keys(hist || {}).map(k => Number(k)).sort((a,b) => a - b);
    keys.forEach(k => { const tr = document.createElement('tr'); const tdK = document.createElement('td'); tdK.textContent = String(k); const tdV = document.createElement('td'); tdV.textContent = String(hist[String(k)] || 0); tr.appendChild(tdK); tr.appendChild(tdV); tbody.appendChild(tr); });
    table.appendChild(tbody); wrap.appendChild(table); return wrap;
  }
  function buildHuman() {
    const root = document.getElementById('humanView'); if (!root) return; root.innerHTML = '';
    const info = (window.dashboardData && window.dashboardData.human_scores) || { overall:{}, per_generator:[], per_source:[], histogram:{}, per_generator_histograms:{}, per_source_histograms:{} };
    const cards = document.createElement('div'); cards.className = 'cards';
    [['count','Count'],['mean','Mean'],['stdev','Std Dev'],['min','Min'],['median','Median'],['p75','P75'],['max','Max']].forEach(([k,label]) => {
      const card = document.createElement('div'); card.className = 'card'; card.innerHTML = '<div class=\"metric\">'+label+'</div><div class=\"value\">'+(typeof fmt==='function'?fmt(info.overall?.[k]):String(info.overall?.[k]??''))+'</div>'; cards.appendChild(card);
    });
    root.appendChild(cards);
    const genSection = document.createElement('div'); genSection.className = 'section'; genSection.innerHTML = '<h3>Human Scores · Per-Generator</h3>'; const genWrap = document.createElement('div'); genWrap.className = 'table-wrap';
    const genCols = [{key:'generator',label:'Generator'},{key:'count',label:'Count'},{key:'mean',label:'Mean'},{key:'stdev',label:'Std Dev'},{key:'min',label:'Min'},{key:'p25',label:'P25'},{key:'median',label:'Median'},{key:'p75',label:'P75'},{key:'max',label:'Max'}];
    const genRows = (info.per_generator||[]).map(r => Object.assign({}, r, { generator: r.key }));
    genWrap.appendChild(typeof renderTable==='function'?renderTable(genCols, genRows):document.createTextNode('')); genSection.appendChild(genWrap); root.appendChild(genSection);
    const srcSection = document.createElement('div'); srcSection.className = 'section'; srcSection.innerHTML = '<h3>Human Scores · Per-Source</h3>'; const srcWrap = document.createElement('div'); srcWrap.className = 'table-wrap';
    const srcCols = [{key:'source',label:'Source'},{key:'count',label:'Count'},{key:'mean',label:'Mean'},{key:'stdev',label:'Std Dev'},{key:'min',label:'Min'},{key:'p25',label:'P25'},{key:'median',label:'Median'},{key:'p75',label:'P75'},{key:'max',label:'Max'}];
    const srcRows = (info.per_source||[]).map(r => Object.assign({}, r, { source: r.key }));
    srcWrap.appendChild(typeof renderTable==='function'?renderTable(srcCols, srcRows):document.createTextNode('')); srcSection.appendChild(srcWrap); root.appendChild(srcSection);
    const histSection = document.createElement('div'); histSection.className = 'section'; histSection.innerHTML = '<h3>Human Scores · Histogram (Overall)</h3>'; const histWrap = document.createElement('div'); histWrap.className = 'table-wrap'; histWrap.appendChild(renderHistogram(info.histogram || {})); histSection.appendChild(histWrap); root.appendChild(histSection);
    const genHistSection = document.createElement('div'); genHistSection.className = 'section'; genHistSection.innerHTML = '<h3>Human Scores · Histograms by Generator</h3>'; const genHistWrap = document.createElement('div'); genHistWrap.className = 'table-wrap';
    const genKeys = Object.keys(info.per_generator_histograms || {}).sort();
    genKeys.forEach(k => { const sub = document.createElement('div'); sub.style.padding = '8px 10px'; const color = (typeof colorForKey==='function')?colorForKey(k):'#9ca3af'; sub.innerHTML = '<div style="font-weight:600;margin-bottom:6px;border-left:4px solid '+color+';padding-left:8px;"><span class="badge-dot" style="background:'+color+'"></span>'+k+'</div>'; sub.appendChild(renderHistogram((info.per_generator_histograms||{})[k]||{})); genHistWrap.appendChild(sub); });
    genHistSection.appendChild(genHistWrap); root.appendChild(genHistSection);
    const srcHistSection = document.createElement('div'); srcHistSection.className = 'section'; srcHistSection.innerHTML = '<h3>Human Scores · Histograms by Source</h3>'; const srcHistWrap = document.createElement('div'); srcHistWrap.className = 'table-wrap';
    const srcKeys = Object.keys(info.per_source_histograms || {}).sort();
    srcKeys.forEach(k => { const sub = document.createElement('div'); sub.style.padding = '8px 10px'; const color = (typeof colorForKey==='function')?colorForKey(k):'#9ca3af'; sub.innerHTML = '<div style="font-weight:600;margin-bottom:6px;border-left:4px solid '+color+';padding-left:8px;"><span class="badge-dot" style="background:'+color+'"></span>'+k+'</div>'; sub.appendChild(renderHistogram((info.per_source_histograms||{})[k]||{})); srcHistWrap.appendChild(sub); });
    srcHistSection.appendChild(srcHistWrap); root.appendChild(srcHistSection);
  }
  const _origSync = window.syncView;
  window.syncView = function() {
    if (typeof renderSidebar==='function') renderSidebar();
    if (typeof syncToolbar==='function') syncToolbar();
    else if (typeof qsa==='function'){ qsa('.toolbar .pill').forEach(el => { el.classList.toggle('active', el.dataset.view === state.view); }); }
    const showOverview = state.view === 'overview'; const showEvaluator = state.view === 'evaluator'; const showHuman = state.view === 'human'; const showNorm = state.view === 'normalized';
    const ov = document.querySelector('#overviewView'); if (ov) ov.style.display = showOverview ? '' : 'none';
    const ev = document.querySelector('#evaluatorView'); if (ev) ev.style.display = showEvaluator ? '' : 'none';
    const nv = document.querySelector('#normalizedView'); if (nv) nv.style.display = showNorm ? '' : 'none';
    const hv = document.querySelector('#humanView'); if (hv) hv.style.display = showHuman ? '' : 'none';
    if (showOverview && typeof buildOverall==='function') buildOverall();
    if (showNorm && typeof buildOverallNormalized==='function') buildOverallNormalized();
    if (showEvaluator && typeof buildEvaluator==='function') buildEvaluator();
    if (showHuman) buildHuman();
  };
})();
</script>
"""
    html = html.replace("</body>", injected + "</body>")
    return html


def main() -> None:
    p = argparse.ArgumentParser(description="Build evaluator dashboard HTML")
    p.add_argument("--data-version", default=None, help="Data version; reads reports from outputs/reports/<version> and human JSONL from data/<version>/evaluation_merged.jsonl by default")
    p.add_argument("--reports-dir", default=None, help="Path to reports directory (overrides --data-version)")
    p.add_argument("--human-jsonl", default=None, help="Path to evaluation_merged.jsonl (overrides --data-version default)")
    p.add_argument("--out", default=None, help="Output HTML path (defaults to evaluator_design/dashboard.html)")
    args = p.parse_args()

    # Resolve reports directory
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
    elif args.data_version:
        reports_dir = OUTPUTS_ROOT / "reports" / str(args.data_version)
    else:
        reports_dir = REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Resolve human JSONL path (prefer evaluation_test.jsonl, fallback to evaluation_merged.jsonl)
    if args.human_jsonl:
        human_path = Path(args.human_jsonl)
    elif args.data_version:
        candidate_test = ROOT / "data" / str(args.data_version) / "evaluation_test.jsonl"
        candidate_merged = ROOT / "data" / str(args.data_version) / "evaluation_merged.jsonl"
        human_path = candidate_merged
    else:
        # Legacy default at repo root; keep fallback behavior
        candidate_test = ROOT / "evaluation_test.jsonl"
        candidate_merged = ROOT / "evaluation_merged.jsonl"
        human_path = candidate_merged

    payload = build_data(reports_dir, human_path)
    html = build_html(payload)
    # Version-aware default output location when --out not provided
    out_html = Path(args.out) if args.out else (OUTPUTS_ROOT / "dashboard" / (str(args.data_version) if args.data_version else "") / "dashboard.html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    # Write JSON payload for dynamic loading
    out_json = out_html.parent / "data.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote dashboard: {out_html}\nWrote data: {out_json}")


if __name__ == "__main__":
    main()


