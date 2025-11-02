#!/usr/bin/env python3
"""
Build an interactive dashboard with dynamic filtering capabilities.
Users can filter by year, generator, source, and see metrics update in real-time.
"""
import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent
OUTPUTS_ROOT = ROOT / "outputs"
OUTPUT_HTML = OUTPUTS_ROOT / "dashboard" / "dynamic_dashboard.html"


def load_detailed_data(reports_dir: Path) -> Dict[str, Any]:
    """Load detailed evaluation data with metadata"""
    detailed_path = reports_dir / "detailed_evaluation_data.json"
    summary_path = reports_dir / "detailed_data_summary.json"
    kendall_path = reports_dir / "order_preservation_overall.csv"
    
    if not detailed_path.exists():
        raise FileNotFoundError(
            f"Detailed data not found at {detailed_path}. "
            "Please run collect_detailed_data.py first."
        )
    
    with detailed_path.open("r", encoding="utf-8") as f:
        detailed_data = json.load(f)
    
    summary = {}
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as f:
            summary = json.load(f)
    
    # Load Kendall-tau data
    kendall_data = {}
    if kendall_path.exists():
        with kendall_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                evaluator = row.get("evaluator", "")
                kendall_tau = row.get("macro_kendall_tau_b", "")
                if evaluator and kendall_tau:
                    try:
                        kendall_data[evaluator] = float(kendall_tau)
                    except (ValueError, TypeError):
                        pass
    
    return {
        "detailed_data": detailed_data,
        "summary": summary,
        "kendall_tau": kendall_data,
    }


def build_html(data: Dict[str, Any]) -> str:
    """Build interactive HTML dashboard with filtering"""
    data_json = json.dumps(data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dynamic Evaluator Dashboard</title>
  <style>
    :root {{
      --bg: #f7f9fc;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #2563eb;
      --good: #16a34a;
      --warn: #d97706;
      --bad: #dc2626;
      --border: #e5e7eb;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; min-height: 100vh; background: var(--bg); color: var(--text); 
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }}
    
    .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
    
    .header {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0 0 8px 0; font-size: 28px; font-weight: 700; }}
    .header p {{ margin: 0; color: var(--muted); font-size: 14px; }}
    
    .filters {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
    .filters h2 {{ margin: 0 0 16px 0; font-size: 18px; font-weight: 600; }}
    .filter-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
    .filter-section {{ }}
    .filter-section label {{ display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 8px; }}
    .filter-options {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .filter-chip {{ padding: 6px 12px; background: #f3f4f6; border: 2px solid var(--border); border-radius: 6px; 
      font-size: 13px; cursor: pointer; transition: all 0.15s; user-select: none; }}
    .filter-chip:hover {{ background: #e5e7eb; }}
    .filter-chip.active {{ background: #eef2ff; border-color: var(--accent); color: var(--accent); font-weight: 600; }}
    .filter-chip.all {{ font-weight: 600; }}
    
    .stats {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 20px; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
    .stat-card {{ text-align: center; padding: 12px; background: #f9fafb; border-radius: 8px; }}
    .stat-value {{ font-size: 24px; font-weight: 700; color: var(--accent); }}
    .stat-label {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
    
    .results {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
    .results h2 {{ margin: 0; padding: 16px; border-bottom: 1px solid var(--border); font-size: 18px; background: #f9fafb; }}
    .table-wrap {{ overflow: auto; max-height: 600px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px 12px; text-align: left; white-space: nowrap; }}
    th {{ position: sticky; top: 0; background: #f9fafb; font-weight: 600; z-index: 1; cursor: pointer; user-select: none; }}
    th:hover {{ background: #f3f4f6; }}
    th.sorted-asc::after {{ content: ' ↑'; color: var(--accent); }}
    th.sorted-desc::after {{ content: ' ↓'; color: var(--accent); }}
    tr:hover td {{ background: #f9fafb; }}
    td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .best {{ font-weight: 700; color: var(--good); }}
    
    .loading {{ text-align: center; padding: 40px; color: var(--muted); }}
    .empty {{ text-align: center; padding: 40px; color: var(--muted); }}
    
    .button {{ padding: 8px 16px; background: var(--accent); color: white; border: none; border-radius: 6px; 
      font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s; }}
    .button:hover {{ background: #1d4ed8; }}
    .button-secondary {{ background: #f3f4f6; color: var(--text); }}
    .button-secondary:hover {{ background: #e5e7eb; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🔬 Dynamic Evaluator Dashboard</h1>
      <p>Filter by year, generator, and source to see metrics for different subsets of your evaluation data</p>
    </div>
    
    <div class="filters">
      <h2>Filters</h2>
      <div class="filter-grid">
        <div class="filter-section">
          <label>Year</label>
          <div class="filter-options" id="yearFilters"></div>
        </div>
        <div class="filter-section">
          <label>Generator</label>
          <div class="filter-options" id="generatorFilters"></div>
        </div>
        <div class="filter-section">
          <label>Source</label>
          <div class="filter-options" id="sourceFilters"></div>
        </div>
      </div>
    </div>
    
    <div class="stats">
      <div class="stats-grid" id="statsGrid"></div>
    </div>
    
    <div class="results">
      <h2>Evaluator Performance <span id="resultCount"></span></h2>
      <div class="table-wrap">
        <table id="resultsTable">
          <thead id="tableHead"></thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    // Load data
    const DATA = {data_json};
    
    // State
    const state = {{
      filters: {{
        years: new Set(),
        generators: new Set(),
        sources: new Set(),
      }},
      sortColumn: 'rmse',
      sortDirection: 'asc',
    }};
    
    // Utility functions
    const fmt = (v, decimals = 3) => {{
      if (v === null || v === undefined || v === '' || !Number.isFinite(v)) return '—';
      return Number(v).toFixed(decimals);
    }};
    
    const mean = arr => arr.length ? arr.reduce((a,b) => a+b, 0) / arr.length : NaN;
    const stdev = arr => {{
      if (arr.length < 2) return NaN;
      const m = mean(arr);
      const variance = arr.reduce((sum, x) => sum + Math.pow(x - m, 2), 0) / arr.length;
      return Math.sqrt(variance);
    }};
    const rmse = arr => arr.length ? Math.sqrt(arr.reduce((sum, x) => sum + x*x, 0) / arr.length) : NaN;
    const pearson = (xs, ys) => {{
      if (xs.length !== ys.length || xs.length === 0) return NaN;
      const mx = mean(xs), my = mean(ys);
      const num = xs.reduce((sum, x, i) => sum + (x - mx) * (ys[i] - my), 0);
      const denx = Math.sqrt(xs.reduce((sum, x) => sum + Math.pow(x - mx, 2), 0));
      const deny = Math.sqrt(ys.reduce((sum, y) => sum + Math.pow(y - my, 2), 0));
      return (denx === 0 || deny === 0) ? NaN : num / (denx * deny);
    }};
    
    // Filter data based on current selections
    function getFilteredData() {{
      return DATA.detailed_data.filter(row => {{
        if (state.filters.years.size > 0 && !state.filters.years.has(row.year)) return false;
        if (state.filters.generators.size > 0 && !state.filters.generators.has(row.generator)) return false;
        if (state.filters.sources.size > 0 && !state.filters.sources.has(row.source)) return false;
        return true;
      }});
    }}
    
    // Compute metrics for each evaluator on filtered data
    function computeMetrics(data) {{
      const byEvaluator = {{}};
      const TOLERANCE = 1.0;  // Within-tolerance threshold
      
      data.forEach(row => {{
        if (!byEvaluator[row.evaluator]) {{
          byEvaluator[row.evaluator] = {{
            trueScores: [],
            predScores: [],
          }};
        }}
        byEvaluator[row.evaluator].trueScores.push(row.true_score);
        byEvaluator[row.evaluator].predScores.push(row.pred_score);
      }});
      
      const results = [];
      const kendallTauData = DATA.kendall_tau || {{}};
      
      for (const [evaluator, scores] of Object.entries(byEvaluator)) {{
        const diffs = scores.trueScores.map((t, i) => scores.predScores[i] - t);
        const absDiffs = diffs.map(d => Math.abs(d));
        
        // WTA: fraction of predictions within tolerance
        const withinTolerance = absDiffs.filter(d => d <= TOLERANCE).length;
        const wta = absDiffs.length > 0 ? withinTolerance / absDiffs.length : NaN;
        
        // Kendall-tau from pre-computed data (doesn't change with filtering, but include for reference)
        const kendallTau = kendallTauData[evaluator];
        
        results.push({{
          evaluator,
          count: scores.trueScores.length,
          mae: mean(absDiffs),
          rmse: rmse(diffs),
          bias: mean(diffs),
          pearson: pearson(scores.trueScores, scores.predScores),
          wta: wta,
          kendall_tau: kendallTau,
        }});
      }}
      
      return results;
    }}
    
    // Render filters
    function renderFilters() {{
      const summary = DATA.summary || {{}};
      
      // Year filters
      const years = summary.years || [];
      const yearEl = document.getElementById('yearFilters');
      yearEl.innerHTML = '';
      
      const allYearChip = createFilterChip('All', state.filters.years.size === 0, () => {{
        state.filters.years.clear();
        update();
      }});
      allYearChip.classList.add('all');
      yearEl.appendChild(allYearChip);
      
      years.forEach(year => {{
        const chip = createFilterChip(year, state.filters.years.has(year), () => {{
          if (state.filters.years.has(year)) {{
            state.filters.years.delete(year);
          }} else {{
            state.filters.years.add(year);
          }}
          update();
        }});
        yearEl.appendChild(chip);
      }});
      
      // Generator filters
      const generators = summary.generators || [];
      const genEl = document.getElementById('generatorFilters');
      genEl.innerHTML = '';
      
      const allGenChip = createFilterChip('All', state.filters.generators.size === 0, () => {{
        state.filters.generators.clear();
        update();
      }});
      allGenChip.classList.add('all');
      genEl.appendChild(allGenChip);
      
      generators.forEach(gen => {{
        const chip = createFilterChip(gen, state.filters.generators.has(gen), () => {{
          if (state.filters.generators.has(gen)) {{
            state.filters.generators.delete(gen);
          }} else {{
            state.filters.generators.add(gen);
          }}
          update();
        }});
        genEl.appendChild(chip);
      }});
      
      // Source filters
      const sources = summary.sources || [];
      const srcEl = document.getElementById('sourceFilters');
      srcEl.innerHTML = '';
      
      const allSrcChip = createFilterChip('All', state.filters.sources.size === 0, () => {{
        state.filters.sources.clear();
        update();
      }});
      allSrcChip.classList.add('all');
      srcEl.appendChild(allSrcChip);
      
      sources.forEach(src => {{
        const chip = createFilterChip(src, state.filters.sources.has(src), () => {{
          if (state.filters.sources.has(src)) {{
            state.filters.sources.delete(src);
          }} else {{
            state.filters.sources.add(src);
          }}
          update();
        }});
        srcEl.appendChild(chip);
      }});
    }}
    
    function createFilterChip(label, active, onClick) {{
      const chip = document.createElement('div');
      chip.className = 'filter-chip' + (active ? ' active' : '');
      chip.textContent = label;
      chip.addEventListener('click', onClick);
      return chip;
    }}
    
    // Render stats
    function renderStats(filteredData) {{
      const grid = document.getElementById('statsGrid');
      grid.innerHTML = '';
      
      const stats = [
        {{ label: 'Total Records', value: filteredData.length }},
        {{ label: 'Evaluators', value: new Set(filteredData.map(r => r.evaluator)).size }},
        {{ label: 'Problems', value: new Set(filteredData.map(r => r.problem_id)).size }},
        {{ label: 'Years', value: new Set(filteredData.map(r => r.year)).size }},
        {{ label: 'Generators', value: new Set(filteredData.map(r => r.generator)).size }},
        {{ label: 'Sources', value: new Set(filteredData.map(r => r.source)).size }},
      ];
      
      stats.forEach(stat => {{
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
          <div class="stat-value">${{stat.value.toLocaleString()}}</div>
          <div class="stat-label">${{stat.label}}</div>
        `;
        grid.appendChild(card);
      }});
    }}
    
    // Render results table
    function renderTable(metrics) {{
      const head = document.getElementById('tableHead');
      const body = document.getElementById('tableBody');
      const countEl = document.getElementById('resultCount');
      
      countEl.textContent = `(${{metrics.length}} evaluators)`;
      
      if (metrics.length === 0) {{
        body.innerHTML = '<tr><td colspan="8" class="empty">No data matches the current filters</td></tr>';
        return;
      }}
      
      // Sort metrics
      metrics.sort((a, b) => {{
        let aVal = a[state.sortColumn];
        let bVal = b[state.sortColumn];
        
        // Handle bias sorting by absolute value
        if (state.sortColumn === 'bias') {{
          aVal = Math.abs(aVal);
          bVal = Math.abs(bVal);
        }}
        
        // Handle NaN - for metrics where higher is better, NaN should be at the bottom
        const higherIsBetter = ['pearson', 'wta', 'kendall_tau'].includes(state.sortColumn);
        if (!Number.isFinite(aVal)) {{
          aVal = (state.sortDirection === 'asc') ? Infinity : -Infinity;
          if (higherIsBetter) aVal = -aVal;  // Flip for "higher is better" metrics
        }}
        if (!Number.isFinite(bVal)) {{
          bVal = (state.sortDirection === 'asc') ? Infinity : -Infinity;
          if (higherIsBetter) bVal = -bVal;  // Flip for "higher is better" metrics
        }}
        
        return state.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }});
      
      // Find best values for highlighting
      const validMetrics = metrics.filter(m => Number.isFinite(m.mae) && Number.isFinite(m.rmse));
      const best = {{
        mae: Math.min(...validMetrics.map(m => m.mae)),
        rmse: Math.min(...validMetrics.map(m => m.rmse)),
        bias: Math.min(...validMetrics.map(m => Math.abs(m.bias))),
        pearson: Math.max(...validMetrics.map(m => m.pearson)),
        wta: Math.max(...validMetrics.filter(m => Number.isFinite(m.wta)).map(m => m.wta)),
        kendall_tau: Math.max(...validMetrics.filter(m => Number.isFinite(m.kendall_tau)).map(m => m.kendall_tau)),
      }};
      
      // Render header
      const columns = [
        {{ key: 'evaluator', label: 'Evaluator', sortable: false }},
        {{ key: 'count', label: 'Count', sortable: true }},
        {{ key: 'mae', label: 'MAE', sortable: true }},
        {{ key: 'rmse', label: 'RMSE', sortable: true }},
        {{ key: 'bias', label: 'Bias', sortable: true }},
        {{ key: 'pearson', label: 'Pearson', sortable: true }},
        {{ key: 'wta', label: 'WTA', sortable: true }},
        {{ key: 'kendall_tau', label: 'Kendall-τ', sortable: true }},
      ];
      
      head.innerHTML = '';
      const tr = document.createElement('tr');
      columns.forEach(col => {{
        const th = document.createElement('th');
        th.textContent = col.label;
        if (col.sortable) {{
          th.style.cursor = 'pointer';
          if (state.sortColumn === col.key) {{
            th.classList.add(state.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
          }}
          th.addEventListener('click', () => {{
            if (state.sortColumn === col.key) {{
              state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
            }} else {{
              state.sortColumn = col.key;
              // Higher is better for pearson, wta, and kendall_tau
              const higherIsBetter = ['pearson', 'wta', 'kendall_tau'].includes(col.key);
              state.sortDirection = higherIsBetter ? 'desc' : 'asc';
            }}
            update();
          }});
        }}
        tr.appendChild(th);
      }});
      head.appendChild(tr);
      
      // Render body
      body.innerHTML = '';
      metrics.forEach((metric, idx) => {{
        const tr = document.createElement('tr');
        
        // Evaluator name
        const tdEval = document.createElement('td');
        tdEval.textContent = metric.evaluator;
        tdEval.title = metric.evaluator;
        tr.appendChild(tdEval);
        
        // Count
        const tdCount = document.createElement('td');
        tdCount.className = 'number';
        tdCount.textContent = metric.count;
        tr.appendChild(tdCount);
        
        // MAE
        const tdMae = document.createElement('td');
        tdMae.className = 'number';
        if (Number.isFinite(metric.mae) && Math.abs(metric.mae - best.mae) < 0.001) {{
          tdMae.classList.add('best');
        }}
        tdMae.textContent = fmt(metric.mae);
        tr.appendChild(tdMae);
        
        // RMSE
        const tdRmse = document.createElement('td');
        tdRmse.className = 'number';
        if (Number.isFinite(metric.rmse) && Math.abs(metric.rmse - best.rmse) < 0.001) {{
          tdRmse.classList.add('best');
        }}
        tdRmse.textContent = fmt(metric.rmse);
        tr.appendChild(tdRmse);
        
        // Bias
        const tdBias = document.createElement('td');
        tdBias.className = 'number';
        if (Number.isFinite(metric.bias) && Math.abs(Math.abs(metric.bias) - best.bias) < 0.001) {{
          tdBias.classList.add('best');
        }}
        tdBias.textContent = fmt(metric.bias);
        tr.appendChild(tdBias);
        
        // Pearson
        const tdPearson = document.createElement('td');
        tdPearson.className = 'number';
        if (Number.isFinite(metric.pearson) && Math.abs(metric.pearson - best.pearson) < 0.001) {{
          tdPearson.classList.add('best');
        }}
        tdPearson.textContent = fmt(metric.pearson);
        tr.appendChild(tdPearson);
        
        // WTA
        const tdWta = document.createElement('td');
        tdWta.className = 'number';
        if (Number.isFinite(metric.wta) && Math.abs(metric.wta - best.wta) < 0.001) {{
          tdWta.classList.add('best');
        }}
        tdWta.textContent = fmt(metric.wta);
        tr.appendChild(tdWta);
        
        // Kendall-tau
        const tdKendall = document.createElement('td');
        tdKendall.className = 'number';
        if (Number.isFinite(metric.kendall_tau) && Math.abs(metric.kendall_tau - best.kendall_tau) < 0.001) {{
          tdKendall.classList.add('best');
        }}
        tdKendall.textContent = fmt(metric.kendall_tau);
        tr.appendChild(tdKendall);
        
        body.appendChild(tr);
      }});
    }}
    
    // Main update function
    function update() {{
      renderFilters();
      const filtered = getFilteredData();
      renderStats(filtered);
      const metrics = computeMetrics(filtered);
      renderTable(metrics);
    }}
    
    // Initialize
    document.addEventListener('DOMContentLoaded', () => {{
      update();
    }});
  </script>
</body>
</html>'''
    
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Build dynamic evaluator dashboard")
    parser.add_argument("--data-version", default=None, help="Data version (e.g., 'iclr_submission')")
    parser.add_argument("--reports-dir", default=None, help="Path to reports directory")
    parser.add_argument("--out", default=None, help="Output HTML path")
    args = parser.parse_args()

    # Resolve reports directory
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
    elif args.data_version:
        reports_dir = OUTPUTS_ROOT / "reports" / str(args.data_version)
    else:
        reports_dir = OUTPUTS_ROOT / "reports"

    # Load data
    print(f"Loading data from: {reports_dir}")
    data = load_detailed_data(reports_dir)
    print(f"Loaded {len(data['detailed_data'])} evaluation records")

    # Build HTML
    html = build_html(data)

    # Write output
    if args.out:
        out_path = Path(args.out)
    elif args.data_version:
        out_path = OUTPUTS_ROOT / "dashboard" / str(args.data_version) / "dynamic_dashboard.html"
    else:
        out_path = OUTPUT_HTML

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    
    print(f"\n✓ Dynamic dashboard created: {out_path}")
    print(f"\nTo view the dashboard:")
    print(f"  1. Open the file in a web browser: file://{out_path.absolute()}")
    print(f"  2. Or serve it locally: cd {out_path.parent} && python -m http.server 8000")


if __name__ == "__main__":
    main()

