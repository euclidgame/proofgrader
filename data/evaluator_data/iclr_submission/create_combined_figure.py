#!/usr/bin/env python3
"""
Create a combined 2x3 publication figure with selected panels
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from matplotlib.gridspec import GridSpec

# Set publication-quality style with modern aesthetics
sns.set_style("whitegrid", {
    'grid.linestyle': '--',
    'grid.alpha': 0.3,
    'axes.edgecolor': '.15',
    'axes.linewidth': 1.5,
})

plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.titlesize': 16,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'Palatino'],
    'text.usetex': False,
    'axes.linewidth': 1.5,
    'grid.linewidth': 0.8,
    'lines.linewidth': 2.5,
    'patch.linewidth': 1.2,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.major.size': 5,
    'ytick.major.size': 5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.facecolor': '#FAFAFA',
    'figure.facecolor': 'white',
})

# Elegant colorblind-friendly palette with distinct colors
MODEL_COLORS = {
    'DeepSeek-R1-0528': '#2E86AB',    # Ocean Blue
    'Gemini-2.5-pro': '#A23B72',      # Plum Purple
    'OpenAI-o3': '#F18F01'            # Warm Orange
}

COMPETITION_COLORS = {
    'APMO': '#E63946',     # Red
    'EGMO': '#F77F00',     # Orange
    'IMO': '#06A77D',      # Teal
    'PUTNAM': '#4361EE',   # Blue
    'TST': '#7209B7',      # Purple
    'USAMO': '#F72585'     # Pink
}

def load_data(filepath):
    """Load JSONL data into pandas DataFrame"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    df = pd.DataFrame(data)
    df['source'] = df['problem_id'].apply(lambda x: x.split('-')[0])
    df['year'] = df['problem_id'].str.extract(r'-(\d{4})-')[0]
    return df

def add_panel_label(ax, label, x=-0.12, y=1.08):
    """Add panel label (a), (b), etc."""
    ax.text(x, y, f'({label})', transform=ax.transAxes,
            fontsize=18, fontweight='bold', va='top', ha='right',
            family='serif', color='#222222')

def create_combined_figure(df, output_dir):
    """
    Create 2x3 combined figure with:
    Row 1: Fig1(a), Fig1(c), Fig2(a)
    Row 2: Fig2(b), Fig3(a), Fig3(c)
    """
    fig = plt.figure(figsize=(19, 11), facecolor='white')
    gs = GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.45,
                  left=0.07, right=0.98, top=0.95, bottom=0.07)
    
    models = sorted(df['model_name'].unique())
    
    # ===== ROW 1, COL 1: Figure 1(a) - Source distribution with percentages =====
    ax1 = fig.add_subplot(gs[0, 0])
    source_counts = df.groupby('source')['problem_id'].nunique().sort_values(ascending=True)
    total_problems = source_counts.sum()
    bars = ax1.barh(source_counts.index, source_counts.values, color='#3B7EA1', 
                    alpha=0.8, edgecolor='white', linewidth=2)
    ax1.set_xlabel('Number of Unique Problems', fontweight='bold')
    ax1.set_ylabel('Competition', fontweight='bold')
    ax1.set_title('Problem Distribution by Competition', fontweight='bold', pad=15)
    ax1.grid(axis='x', alpha=0.25, linestyle='--', zorder=0)
    
    # Add counts and percentages on bars
    for i, (bar, val) in enumerate(zip(bars, source_counts.values)):
        percentage = val / total_problems * 100
        ax1.text(val + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{val} ({percentage:.1f}%)',
                va='center', ha='left', fontsize=10.5, fontweight='normal', color='#333333')
    add_panel_label(ax1, 'a')
    
    # ===== ROW 1, COL 2: Figure 1(c) - Overall score distribution =====
    ax2 = fig.add_subplot(gs[0, 1])
    bins = np.arange(-0.5, 8.5, 1)
    counts, edges, patches = ax2.hist(df['score'], bins=bins, color='#3B7EA1', 
                                       edgecolor='white', alpha=0.85, linewidth=2)
    ax2.set_xlabel('Score', fontweight='bold')
    ax2.set_ylabel('Frequency', fontweight='bold')
    ax2.set_title('Overall Score Distribution', fontweight='bold', pad=15)
    ax2.set_xticks(range(0, 8))
    ax2.grid(axis='y', alpha=0.25, linestyle='--', zorder=0)
    
    # Add statistics
    mean_score = df['score'].mean()
    median_score = df['score'].median()
    ax2.axvline(mean_score, color='#E63946', linestyle='--', linewidth=3, 
                label=f'Mean: {mean_score:.2f}', zorder=10, alpha=0.9)
    ax2.axvline(median_score, color='#06A77D', linestyle='--', linewidth=3,
                label=f'Median: {median_score:.2f}', zorder=10, alpha=0.9)
    ax2.legend(frameon=True, fancybox=False, shadow=False, loc='upper right', 
               framealpha=0.95, edgecolor='gray')
    
    # Add count labels on bars
    for i, (count, edge) in enumerate(zip(counts, edges[:-1])):
        if count > 0:
            ax2.text(edge + 0.5, count + 5, f'{int(count)}',
                    ha='center', va='bottom', fontsize=10, fontweight='normal', color='#333333')
    add_panel_label(ax2, 'b')
    
    # ===== ROW 1, COL 3: Figure 2(a) - Box plot comparison =====
    ax3 = fig.add_subplot(gs[0, 2])
    positions = range(len(models))
    box_data = [df[df['model_name'] == m]['score'].values for m in models]
    
    bp = ax3.boxplot(box_data, positions=positions, widths=0.6, patch_artist=True,
                     showmeans=True, meanline=True,
                     boxprops=dict(linewidth=2, edgecolor='#333333'),
                     whiskerprops=dict(linewidth=2, color='#666666'),
                     capprops=dict(linewidth=2, color='#666666'),
                     medianprops=dict(linewidth=3, color='#E63946'),
                     meanprops=dict(linewidth=3, color='#4361EE', linestyle='--'))
    
    # Use single color for all boxes
    for patch in bp['boxes']:
        patch.set_facecolor('#3B7EA1')
        patch.set_alpha(0.7)
    
    ax3.set_ylabel('Score', fontweight='bold')
    ax3.set_title('Score Distribution by Model', fontweight='bold', pad=15)
    ax3.set_xticks(positions)
    ax3.set_xticklabels([m.replace('-', '-\n') for m in models], fontsize=10)
    ax3.grid(axis='y', alpha=0.25, linestyle='--', zorder=0)
    ax3.set_ylim(-0.5, 7.5)
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='#E63946', lw=3, label='Median'),
                      Line2D([0], [0], color='#4361EE', lw=3, linestyle='--', label='Mean')]
    ax3.legend(handles=legend_elements, loc='upper left', frameon=True, 
               framealpha=0.95, edgecolor='gray')
    add_panel_label(ax3, 'c')
    
    # ===== ROW 2, COL 1: Figure 2(b) - Score distribution per model (stacked) =====
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.grid(False)  # Disable grid before plotting
    width = 0.7
    
    # Reverse models so they match the heatmap order (top to bottom)
    models_reversed = list(reversed(models))
    
    for i, model in enumerate(models_reversed):
        model_scores = df[df['model_name'] == model]['score']
        hist, _ = np.histogram(model_scores, bins=np.arange(-0.5, 8.5, 1))
        percentages = hist / len(model_scores) * 100
        
        left = 0
        for score, pct in enumerate(percentages):
            if pct > 0:
                color = plt.cm.RdYlGn(score / 7)  # Color gradient based on score
                ax4.barh(i, pct, height=width, left=left, 
                        color=color, edgecolor='white', linewidth=1.5)
                if pct > 5:  # Only label if segment is large enough
                    ax4.text(left + pct/2, i, f'{pct:.0f}%',
                            ha='center', va='center', fontsize=10, fontweight='normal', color='#222222')
                left += pct
    
    ax4.set_yticks(range(len(models_reversed)))
    ax4.set_yticklabels([m.replace('-', '-\n') for m in models_reversed], fontsize=10)
    ax4.set_xlabel('Percentage of Problems', fontweight='bold')
    ax4.set_title('Score Distribution (%) by Model', fontweight='bold', pad=15)
    ax4.set_xlim(0, 100)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=plt.cm.RdYlGn, 
                               norm=plt.Normalize(vmin=0, vmax=7))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax4, orientation='horizontal', pad=0.15, aspect=30)
    cbar.set_label('Score', fontweight='bold')
    cbar.set_ticks(range(8))
    cbar.outline.set_linewidth(1.5)
    add_panel_label(ax4, 'd')
    
    # ===== ROW 2, COL 2: Figure 3(a) - Average score heatmap =====
    ax5 = fig.add_subplot(gs[1, 1])
    col_order = df.groupby('source')['score'].mean().sort_values(ascending=False).index
    pivot_mean = df.pivot_table(values='score', index='model_name', columns='source', aggfunc='mean')
    pivot_mean = pivot_mean[col_order]
    # Reindex to ensure same model order as panels c and d
    pivot_mean = pivot_mean.reindex(models)
    
    sns.heatmap(pivot_mean, annot=True, fmt='.2f', cmap='RdYlGn', center=3.5,
                vmin=0, vmax=7, cbar_kws={'label': 'Average Score'}, ax=ax5,
                linewidths=2.5, linecolor='white', annot_kws={'fontsize': 11, 'fontweight': 'normal'})
    ax5.set_xlabel('Competition', fontweight='bold')
    ax5.set_ylabel('Model', fontweight='bold')
    ax5.set_title('Average Score by Model and Competition', fontweight='bold', pad=15)
    ax5.set_xticklabels(ax5.get_xticklabels(), rotation=45, ha='right', fontsize=11)
    ax5.set_yticklabels(ax5.get_yticklabels(), rotation=0, fontsize=11)
    
    # Improve colorbar
    cbar = ax5.collections[0].colorbar
    cbar.outline.set_linewidth(1.5)
    cbar.ax.tick_params(labelsize=10)
    add_panel_label(ax5, 'e')
    
    # ===== ROW 2, COL 3: Figure 3(c) - Competition difficulty ranking =====
    ax6 = fig.add_subplot(gs[1, 2])
    
    difficulty_stats = df.groupby('source')['score'].agg(['mean', 'std', 'sem']).sort_values('mean')
    
    bars = ax6.barh(range(len(difficulty_stats)), difficulty_stats['mean'], 
                    xerr=difficulty_stats['sem'], capsize=6,
                    color='#3B7EA1', alpha=0.8, edgecolor='white', linewidth=2,
                    error_kw={'linewidth': 2.5, 'ecolor': '#333333', 'alpha': 0.7})
    
    ax6.set_yticks(range(len(difficulty_stats)))
    ax6.set_yticklabels(difficulty_stats.index, fontsize=11)
    ax6.set_xlabel('Average Score (± SEM)', fontweight='bold')
    ax6.set_ylabel('Competition', fontweight='bold')
    ax6.set_title('Competition Difficulty Ranking', fontweight='bold', pad=15)
    ax6.axvline(df['score'].mean(), color='#E63946', linestyle='--', linewidth=3,
                label=f'Overall Mean: {df["score"].mean():.2f}', zorder=0, alpha=0.9)
    ax6.grid(axis='x', alpha=0.25, linestyle='--', zorder=0)
    ax6.legend(loc='lower right', frameon=True, framealpha=0.95, edgecolor='gray')
    ax6.set_xlim(0, 7)
    
    # Add value labels
    for i, (idx, row) in enumerate(difficulty_stats.iterrows()):
        ax6.text(row['mean'] + 0.15, i, f'{row["mean"]:.2f}',
                va='center', ha='left', fontsize=10.5, fontweight='normal', color='#333333')
    add_panel_label(ax6, 'f')
    
    # Save figure
    plt.savefig(output_dir / 'Combined_Figure.png', dpi=400, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.savefig(output_dir / 'Combined_Figure.pdf', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    
    print("✓ Combined Figure (2×3 grid) created successfully!")

def main():
    # File paths
    data_file = Path(__file__).parent / 'evaluation_merged.jsonl'
    output_dir = Path(__file__).parent / 'paper_figures'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("Loading data...")
    df = load_data(data_file)
    print(f"Loaded {len(df)} evaluations from {df['problem_id'].nunique()} unique problems")
    print()
    
    # Create combined figure
    print("Creating combined 2×3 figure...")
    create_combined_figure(df, output_dir)
    
    print()
    print("="*60)
    print("✓ Combined figure saved:")
    print(f"  - {output_dir / 'Combined_Figure.png'}")
    print(f"  - {output_dir / 'Combined_Figure.pdf'}")
    print("="*60)
    print()
    print("Panel layout:")
    print("  Row 1: (a) Problem Distribution  (b) Score Distribution  (c) Model Comparison")
    print("  Row 2: (d) Score % by Model      (e) Performance Heatmap  (f) Difficulty Ranking")

if __name__ == '__main__':
    main()

