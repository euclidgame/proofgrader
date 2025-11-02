#!/usr/bin/env python3
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any


ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "evaluator_grades_reports_binary"
OUTPUT_HTML = ROOT / "dashboard_binary.html"
DESCRIPTIONS_PATH = ROOT / "evaluator_descriptions.json"
HUMAN_JSONL_PATH = ROOT / "evaluation_merged_binary.jsonl"


def read_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_data() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    overall_path = REPORTS_DIR / "per_evaluator_overall.csv"
    per_gen_path = REPORTS_DIR / "per_evaluator_per_generator.csv"
    per_src_path = REPORTS_DIR / "per_evaluator_per_source.csv"
    # Stratified by true label (optional)
    true_label_overall_path = REPORTS_DIR / "per_evaluator_by_true_label.csv"
    true_label_per_gen_path = REPORTS_DIR / "per_evaluator_per_generator_by_true_label.csv"

    if not overall_path.exists():
        raise SystemExit(f"Missing report: {overall_path}")
    if not per_gen_path.exists():
        raise SystemExit(f"Missing report: {per_gen_path}")
    if not per_src_path.exists():
        raise SystemExit(f"Missing report: {per_src_path}")

    overall = read_csv(overall_path)
    per_gen = read_csv(per_gen_path)
    per_src = read_csv(per_src_path)

    # Optional stratified inputs
    bins_overall: List[Dict[str, Any]] = []
    if true_label_overall_path.exists():
        bins_overall = read_csv(true_label_overall_path)
    bins_per_gen: List[Dict[str, Any]] = []
    if true_label_per_gen_path.exists():
        bins_per_gen = read_csv(true_label_per_gen_path)

    evaluators: List[str] = sorted({row.get("evaluator", "") for row in overall if row.get("evaluator")})

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

    data["overall"] = overall
    data["evaluators"] = evaluators
    data["per_generator_by_evaluator"] = per_gen_by_eval
    data["per_source_by_evaluator"] = per_src_by_eval

    # Group stratified tables by evaluator
    by_eval_bins_overall: Dict[str, List[Dict[str, Any]]] = {}
    for row in (bins_overall or []):
        ev = row.get("evaluator")
        if not ev:
            continue
        by_eval_bins_overall.setdefault(ev, []).append(row)
    for rows in by_eval_bins_overall.values():
        rows.sort(key=lambda r: (int(float(r.get("true_label", 0))),))

    by_eval_bins_per_gen: Dict[str, List[Dict[str, Any]]] = {}
    for row in (bins_per_gen or []):
        ev = row.get("evaluator")
        if not ev:
            continue
        by_eval_bins_per_gen.setdefault(ev, []).append(row)
    for rows in by_eval_bins_per_gen.values():
        rows.sort(key=lambda r: (str(r.get("generator", "")), int(float(r.get("true_label", 0)))))

    data["binary_bins_overall_by_eval"] = by_eval_bins_overall
    data["binary_bins_per_generator_by_eval"] = by_eval_bins_per_gen

    # Optional descriptions
    descriptions: Dict[str, Any] = {}
    template_desc: Dict[str, str] = {}
    if DESCRIPTIONS_PATH.exists():
        try:
            with DESCRIPTIONS_PATH.open("r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    template_desc = obj.get("templates", {}) or {}
                    descriptions = {k: v for k, v in obj.items() if k != "templates"}
        except Exception:
            pass
    data["descriptions"] = descriptions
    data["template_descriptions"] = template_desc

    # Human (binary) scores: aggregate counts per generator/source
    human_records: List[Dict[str, Any]] = []
    if HUMAN_JSONL_PATH.exists():
        with HUMAN_JSONL_PATH.open("r", encoding="utf-8") as f:
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
                try:
                    label = int(obj.get("label", 0))
                except Exception:
                    label = 0
                human_records.append({
                    "problem_id": pid,
                    "generator": obj.get("model_name", ""),
                    "source": src,
                    "label": label,
                })

    # Overall and grouped tallies
    labels = [r["label"] for r in human_records]
    total = len(labels)
    num_correct = sum(1 for v in labels if v == 1)
    num_incorrect = total - num_correct
    human_overall: Dict[str, Any] = {
        "count": total,
        "correct": num_correct,
        "incorrect": num_incorrect,
        "accuracy": (num_correct / total) if total else None,
    }

    by_gen: Dict[str, List[int]] = defaultdict(list)
    by_src: Dict[str, List[int]] = defaultdict(list)
    for r in human_records:
        by_gen[r["generator"]].append(r["label"])
        by_src[r["source"]].append(r["label"])

    def _summarize(group: Dict[str, List[int]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for k, vals in group.items():
            c = sum(1 for v in vals if v == 1)
            n = len(vals)
            rows.append({
                "key": k,
                "count": n,
                "correct": c,
                "incorrect": n - c,
                "accuracy": (c / n) if n else None,
            })
        rows.sort(key=lambda r: (-(r["accuracy"] or 0.0), r["key"]))
        return rows

    human_per_generator = _summarize(by_gen)
    human_per_source = _summarize(by_src)

    # Simple histogram for labels (0/1)
    histogram: Dict[str, int] = {"0": num_incorrect, "1": num_correct}
    per_generator_histograms: Dict[str, Dict[str, int]] = {}
    for g, vals in by_gen.items():
        counts = Counter(vals)
        per_generator_histograms[g] = {"0": counts.get(0, 0), "1": counts.get(1, 0)}
    per_source_histograms: Dict[str, Dict[str, int]] = {}
    for s, vals in by_src.items():
        counts = Counter(vals)
        per_source_histograms[s] = {"0": counts.get(0, 0), "1": counts.get(1, 0)}

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
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Binary Evaluator Results Dashboard</title><style>:root{--bg:#f7f9fc;--panel:#fff;--text:#1f2937;--muted:#6b7280;--accent:#2563eb;--border:#e5e7eb}html,body{margin:0;height:100%;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.layout{display:grid;grid-template-columns:1fr;height:100vh}.sidebar{display:none}.sidebar h2{margin:8px 8px 4px;font-size:14px;color:var(--muted);font-weight:600}.search{margin:8px}.search input{width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border)}.eval-list{margin:8px;display:flex;flex-direction:column;gap:4px}.eval-item{cursor:pointer;border:1px solid var(--border);background:#fff;padding:8px 10px;border-radius:8px;font-size:13px}.eval-item.active{background:#eef2ff;border-color:var(--accent)}.content{overflow:auto}.header{display:flex;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border);background:#fff;position:sticky;top:0}.title{font-size:18px;font-weight:700}.subtitle{font-size:13px;color:var(--muted);margin-top:4px}.container{padding:16px 20px;display:grid;gap:16px}.section{background:#fff;border:1px solid var(--border);border-radius:12px;overflow:hidden}.section h3{margin:0;padding:12px;border-bottom:1px solid var(--border);font-size:14px;background:#f3f4f6}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-bottom:1px solid var(--border);padding:8px 10px;text-align:left;white-space:nowrap}th{position:sticky;top:0;background:#f9fafb}tr:hover td{background:#f9fafb}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:12px}.metric{font-size:12px;color:var(--muted)}.value{font-size:22px;font-weight:700;color:var(--accent)}.toolbar{display:flex;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--border);background:#fff}.pill{padding:6px 10px;background:#f3f4f6;border:1px solid var(--border);border-radius:999px;font-size:12px;color:var(--muted);cursor:pointer}.pill.active{color:var(--text);border-color:var(--accent)}.badge-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}</style></head><body><div class="layout"><aside class="sidebar"><h2>Evaluators</h2><div class="search"><input id="search" placeholder="Search evaluators..."/></div><div id="evalList" class="eval-list"></div></aside><main class="content"><div class="header"><div><div class="title">Binary Evaluator Results Dashboard</div><div class="subtitle">Overview and drill-down for binary metrics</div></div><div class="pill" id="countChip"></div></div><div class="container"><section class="section"><div class="toolbar"><div class="pill active" data-view="overview">Overview</div><div class="pill" data-view="evaluator">Selected Evaluator</div><div class="pill" data-view="human">Human Scores</div></div><div id="overviewView"><div class="table-wrap" id="overallTableWrap"></div></div><div id="evaluatorView" style="display:none"><div class="cards" id="summaryCards"></div><div class="section" style="margin-top:12px"><h3>Per-Generator</h3><div class="table-wrap" id="perGenTableWrap"></div></div><div class="section" style="margin-top:12px"><h3>Per-Source</h3><div class="table-wrap" id="perSrcTableWrap"></div></div></div><div id="humanView" style="display:none"></div></section></div></main></div><script>window.dashboardData=__DATA__;const qs=s=>document.querySelector(s),qsa=s=>Array.from(document.querySelectorAll(s)),fmt=v=>{if(v===null||v===undefined||v==='')return'';const n=Number(v);return Number.isFinite(n)?(Math.abs(n)>=100?n.toFixed(2):n.toFixed(3)):String(v)};const state={selected:null,view:'overview'};function hashCode(str){let h=0;const s=String(str||'');for(let i=0;i<s.length;i++){h=((h<<5)-h)+s.charCodeAt(i);h|=0;}return h;}function colorForKey(key){const h=Math.abs(hashCode(key))%360;return `hsl(${h},70%,45%)`;}function renderSidebar(){const l=qs('#evalList');l.innerHTML='';const q=(qs('#search').value||'').toLowerCase();const evs=(window.dashboardData.evaluators||[]).filter(e=>e.toLowerCase().includes(q));evs.forEach(ev=>{const d=document.createElement('div');d.className='eval-item'+(state.selected===ev?' active':'');d.textContent=ev;d.onclick=()=>{state.selected=ev;state.view='evaluator';sync()};l.appendChild(d)});qs('#countChip').textContent=evs.length+" evaluators"}function renderTable(cols,rows,opts={}){const identityKey=opts.identityKey||null;const highlight=opts.highlight||{};const t=document.createElement('table'),h=document.createElement('thead'),tr=document.createElement('tr');cols.forEach(c=>{const th=document.createElement('th');th.textContent=c.label;tr.appendChild(th)});h.appendChild(tr);t.appendChild(h);const b=document.createElement('tbody');rows.forEach(r=>{const tr=document.createElement('tr');cols.forEach(c=>{const td=document.createElement('td');if(['generator','source','key'].includes(c.key)){const val=r[c.key];const color=colorForKey(val);td.style.borderLeft=`4px solid ${color}`;const span=document.createElement('span');span.innerHTML=`<span class=\\"badge-dot\\" style=\\"background:${color}\\"></span>${val??''}`;td.appendChild(span);}else{const text=fmt(r[c.key]);const idVal=identityKey? r[identityKey]: null;if(idVal && highlight[c.key] && highlight[c.key].has(idVal)){td.innerHTML=`<strong>${text}</strong>`;}else{td.textContent=text;}}tr.appendChild(td);});b.appendChild(tr);});t.appendChild(b);return t}function buildOverview(){const w=qs('#overallTableWrap');w.innerHTML='';const cols=[{key:'evaluator',label:'Evaluator'},{key:'count',label:'Count'},{key:'accuracy',label:'Accuracy'},{key:'precision',label:'Precision'},{key:'recall',label:'Recall'},{key:'f1',label:'F1'},{key:'tnr',label:'TNR'},{key:'npv',label:'NPV'},{key:'tp',label:'TP'},{key:'fp',label:'FP'},{key:'tn',label:'TN'},{key:'fn',label:'FN'}];const rows=(window.dashboardData.overall||[]).slice();rows.sort((a,b)=>Number(b.accuracy)-Number(a.accuracy));const metrics=['accuracy','precision','recall','f1','tnr','npv'];const highlight={};metrics.forEach(m=>{const vals=rows.map(r=>Number(r[m])).filter(v=>Number.isFinite(v));if(vals.length){const best=Math.max(...vals);highlight[m]=new Set(rows.filter(r=>Number(r[m])===best).map(r=>r.evaluator));}});w.appendChild(renderTable(cols,rows,{identityKey:'evaluator',highlight}))}function buildEvaluator(){const ev=state.selected;if(!ev)return;const cards=qs('#summaryCards');cards.innerHTML='';const o=(window.dashboardData.overall||[]).find(r=>r.evaluator===ev)||{};[['accuracy','Accuracy'],['precision','Precision'],['recall','Recall'],['f1','F1'],['tnr','TNR'],['npv','NPV']].forEach(([k,l])=>{const c=document.createElement('div');c.className='card';c.innerHTML='<div class=\\"metric\\">'+l+'</div><div class=\\"value\\">'+fmt(o[k])+'</div>';cards.appendChild(c)});const pg=qs('#perGenTableWrap');pg.innerHTML='';const ps=qs('#perSrcTableWrap');ps.innerHTML='';const perGen=(window.dashboardData.per_generator_by_evaluator?.[ev]||[]).slice();const perSrc=(window.dashboardData.per_source_by_evaluator?.[ev]||[]).slice();perGen.sort((a,b)=>Number(b.accuracy)-Number(a.accuracy));perSrc.sort((a,b)=>Number(b.accuracy)-Number(a.accuracy));const cgen=[{key:'generator',label:'Generator'},{key:'count',label:'Count'},{key:'accuracy',label:'Accuracy'},{key:'precision',label:'Precision'},{key:'recall',label:'Recall'},{key:'f1',label:'F1'},{key:'tnr',label:'TNR'},{key:'npv',label:'NPV'},{key:'tp',label:'TP'},{key:'fp',label:'FP'},{key:'tn',label:'TN'},{key:'fn',label:'FN'}];const csrc=[{key:'source',label:'Source'},{key:'count',label:'Count'},{key:'accuracy',label:'Accuracy'},{key:'precision',label:'Precision'},{key:'recall',label:'Recall'},{key:'f1',label:'F1'},{key:'tnr',label:'TNR'},{key:'npv',label:'NPV'},{key:'tp',label:'TP'},{key:'fp',label:'FP'},{key:'tn',label:'TN'},{key:'fn',label:'FN'}];const highlightGen={};const highlightSrc={};['accuracy','precision','recall','f1','tnr','npv'].forEach(m=>{const vgen=perGen.map(r=>Number(r[m])).filter(v=>Number.isFinite(v));if(vgen.length){const best=Math.max(...vgen);highlightGen[m]=new Set(perGen.filter(r=>Number(r[m])===best).map(r=>r.generator));}const vsrc=perSrc.map(r=>Number(r[m])).filter(v=>Number.isFinite(v));if(vsrc.length){const best2=Math.max(...vsrc);highlightSrc[m]=new Set(perSrc.filter(r=>Number(r[m])===best2).map(r=>r.source));}});pg.appendChild(renderTable(cgen,perGen,{identityKey:'generator',highlight:highlightGen}));ps.appendChild(renderTable(csrc,perSrc,{identityKey:'source',highlight:highlightSrc}))}function buildHuman(){const root=qs('#humanView');root.innerHTML='';const info=window.dashboardData.human_scores||{overall:{},per_generator:[],per_source:[]};const cards=document.createElement('div');cards.className='cards';[['count','Count'],['correct','Correct'],['incorrect','Incorrect'],['accuracy','Accuracy']].forEach(([k,l])=>{const c=document.createElement('div');c.className='card';c.innerHTML='<div class=\\"metric\\">'+l+'</div><div class=\\"value\\">'+fmt(info.overall?.[k])+'</div>';cards.appendChild(c)});root.appendChild(cards);const genSec=document.createElement('div');genSec.className='section';genSec.innerHTML='<h3>Human Scores · Per-Generator</h3>';const genWrap=document.createElement('div');genWrap.className='table-wrap';const genCols=[{key:'key',label:'Generator'},{key:'count',label:'Count'},{key:'correct',label:'Correct'},{key:'incorrect',label:'Incorrect'},{key:'accuracy',label:'Accuracy'}];genWrap.appendChild(renderTable(genCols,info.per_generator||[]));genSec.appendChild(genWrap);root.appendChild(genSec);const srcSec=document.createElement('div');srcSec.className='section';srcSec.innerHTML='<h3>Human Scores · Per-Source</h3>';const srcWrap=document.createElement('div');srcWrap.className='table-wrap';const srcCols=[{key:'key',label:'Source'},{key:'count',label:'Count'},{key:'correct',label:'Correct'},{key:'incorrect',label:'Incorrect'},{key:'accuracy',label:'Accuracy'}];srcWrap.appendChild(renderTable(srcCols,info.per_source||[]));srcSec.appendChild(srcWrap);root.appendChild(srcSec)}function sync(){renderSidebar();qsa('.pill').forEach(el=>el.classList.toggle('active',el.dataset.view===state.view));qs('#overviewView').style.display=state.view==='overview'?'':'none';qs('#evaluatorView').style.display=state.view==='evaluator'?'':'none';qs('#humanView').style.display=state.view==='human'?'':'none';if(state.view==='overview')buildOverview();if(state.view==='evaluator')buildEvaluator();if(state.view==='human')buildHuman()}document.addEventListener('DOMContentLoaded',()=>{qs('#search').addEventListener('input',renderSidebar);qsa('.toolbar .pill').forEach(el=>el.addEventListener('click',()=>{state.view=el.dataset.view;sync()}));sync()});</script></body></html>"""
    html = html.replace("__DATA__", data_json)
    # Make evaluator cells clickable in the overview to jump to Selected Evaluator
    html = html.replace(
        "w.appendChild(renderTable(cols,rows,{identityKey:'evaluator',highlight}))",
        "w.appendChild(renderTable(cols,rows,{identityKey:'evaluator',highlight,clickKey:'evaluator',onRowClick:(r)=>{state.selected=r.evaluator;state.view='evaluator';sync();}}))"
    )
    # Inject Binary Stratification sections into evaluator view
    html = html.replace(
        '</div></div></div><div id="humanView"',
        '<div class="section" style="margin-top:12px"><h3>Binary Label Stratification (0/1)</h3><div class="table-wrap" id="binaryBinsOverallWrap"></div></div><div class="section" style="margin-top:12px"><h3>Binary Label Stratification · Per-Generator</h3><div class="table-wrap" id="binaryBinsPerGenWrap"></div></div></div><div id="humanView"'
    )
    # Inject script to extend buildEvaluator with rendering of stratified tables
    injected = """
<script>
(function(){
  const _origBuildEvaluator = window.buildEvaluator;
  window.buildEvaluator = function(){
    if (typeof _origBuildEvaluator === 'function') { _origBuildEvaluator(); }
    try {
      const ev = (typeof state !== 'undefined') ? state.selected : null;
      const binOverallWrap = document.getElementById('binaryBinsOverallWrap');
      const binPerGenWrap = document.getElementById('binaryBinsPerGenWrap');
      if (binOverallWrap) {
        binOverallWrap.innerHTML = '';
        const rows = ((window.dashboardData && window.dashboardData.binary_bins_overall_by_eval) ? (window.dashboardData.binary_bins_overall_by_eval[ev] || []) : []).slice();
        if (!rows.length) {
          binOverallWrap.textContent = 'No data found.';
        } else {
          const cols = [
            {key:'true_label', label:'True Label'},
            {key:'count', label:'Count'},
            {key:'tp', label:'TP'},
            {key:'fp', label:'FP'},
            {key:'tn', label:'TN'},
            {key:'fn', label:'FN'},
            {key:'accuracy', label:'Accuracy'},
            {key:'precision', label:'Precision'},
            {key:'recall', label:'Recall'},
            {key:'f1', label:'F1'},
            {key:'tnr', label:'TNR'},
            {key:'npv', label:'NPV'}
          ];
          rows.sort((a,b) => Number(a.true_label) - Number(b.true_label));
          binOverallWrap.appendChild(renderTable(cols, rows));
        }
      }
      if (binPerGenWrap) {
        binPerGenWrap.innerHTML = '';
        const rows = ((window.dashboardData && window.dashboardData.binary_bins_per_generator_by_eval) ? (window.dashboardData.binary_bins_per_generator_by_eval[ev] || []) : []).slice();
        if (!rows.length) {
          binPerGenWrap.textContent = 'No data found.';
        } else {
          const cols = [
            {key:'generator', label:'Generator'},
            {key:'true_label', label:'True Label'},
            {key:'count', label:'Count'},
            {key:'tp', label:'TP'},
            {key:'fp', label:'FP'},
            {key:'tn', label:'TN'},
            {key:'fn', label:'FN'},
            {key:'accuracy', label:'Accuracy'},
            {key:'precision', label:'Precision'},
            {key:'recall', label:'Recall'},
            {key:'f1', label:'F1'},
            {key:'tnr', label:'TNR'},
            {key:'npv', label:'NPV'}
          ];
          rows.sort((a,b) => (String(a.generator).localeCompare(String(b.generator))) || (Number(a.true_label) - Number(b.true_label)));
          binPerGenWrap.appendChild(renderTable(cols, rows));
        }
      }
    } catch (e) { /* no-op */ }
  };
})();
</script>
"""
    html = html.replace("</body>", injected + "</body>")
    return html


def main() -> None:
    payload = build_data()
    html = build_html(payload)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote binary dashboard: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()


