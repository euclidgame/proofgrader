#!/usr/bin/env python3
"""
Create publication-quality multi-panel figures for paper
Combines related visualizations into coherent figures with subplots
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches

# Set publication-quality style
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'axes.linewidth': 1.2,
    'grid.linewidth': 0.8,
    'lines.linewidth': 2,
    'patch.linewidth': 1,
    'xtick.major.width': 1.2,
    'ytick.major.width': 1.2,
})

# Colorblind-friendly palette
MODEL_COLORS = {
    'DeepSeek-R1-0528': '#E69F00',    # Orange
    'Gemini-2.5-pro': '#56B4E9',      # Sky Blue
    'OpenAI-o3': '#009E73'             # Green
}

COMPETITION_COLORS = {
    'APMO': '#E69F00',
    'EGMO': '#56B4E9', 
    'IMO': '#009E73',
    'PUTNAM': '#F0E442',
    'TST': '#0072B2',
    'USAMO': '#D55E00'
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

def add_panel_label(ax, label, x=-0.1, y=1.05):
    """Add panel label (a), (b), etc."""
    ax.text(x, y, f'({label})', transform=ax.transAxes,
            fontsize=14, fontweight='bold', va='top', ha='right')

def figure1_dataset_overview(df, output_dir):
    """
    Figure 1: Dataset Overview
    (a) Problem distribution by competition
    (b) Problem count per model-competition
    (c) Score distribution histogram
    """
    fig = plt.figure(figsize=(16, 5))
    gs = GridSpec(1, 3, figure=fig, wspace=0.3)
    
    # Panel (a): Source distribution
    ax1 = fig.add_subplot(gs[0, 0])
    source_counts = df.groupby('source')['problem_id'].nunique().sort_values(ascending=True)
    colors = [COMPETITION_COLORS[s] for s in source_counts.index]
    bars = ax1.barh(source_counts.index, source_counts.values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
    ax1.set_xlabel('Number of Unique Problems', fontweight='bold')
    ax1.set_ylabel('Competition', fontweight='bold')
    ax1.set_title('Problem Distribution by Competition', fontweight='bold')
    ax1.grid(axis='x', alpha=0.3, linestyle='--')
    # Add counts on bars
    for i, (bar, val) in enumerate(zip(bars, source_counts.values)):
        ax1.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val}',
                va='center', ha='left', fontsize=10, fontweight='bold')
    add_panel_label(ax1, 'a')
    
    # Panel (b): Problem count heatmap
    ax2 = fig.add_subplot(gs[0, 1])
    pivot_count = df.pivot_table(values='score', index='model_name', columns='source', aggfunc='count', fill_value=0)
    # Reorder columns by total
    col_order = df.groupby('source')['problem_id'].nunique().sort_values(ascending=False).index
    pivot_count = pivot_count[col_order]
    
    sns.heatmap(pivot_count, annot=True, fmt='g', cmap='YlOrRd', 
                cbar_kws={'label': 'Evaluations'}, ax=ax2, 
                linewidths=1, linecolor='white',
                vmin=0, vmax=pivot_count.max().max())
    ax2.set_xlabel('Competition', fontweight='bold')
    ax2.set_ylabel('Model', fontweight='bold')
    ax2.set_title('Number of Evaluations per Model', fontweight='bold')
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0)
    add_panel_label(ax2, 'b')
    
    # Panel (c): Overall score distribution
    ax3 = fig.add_subplot(gs[0, 2])
    bins = np.arange(-0.5, 8.5, 1)
    counts, edges, patches = ax3.hist(df['score'], bins=bins, color='steelblue', 
                                       edgecolor='black', alpha=0.7, linewidth=1.5)
    ax3.set_xlabel('Score', fontweight='bold')
    ax3.set_ylabel('Frequency', fontweight='bold')
    ax3.set_title('Overall Score Distribution', fontweight='bold')
    ax3.set_xticks(range(0, 8))
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    # Add statistics
    mean_score = df['score'].mean()
    median_score = df['score'].median()
    ax3.axvline(mean_score, color='red', linestyle='--', linewidth=2.5, 
                label=f'Mean: {mean_score:.2f}', zorder=10)
    ax3.axvline(median_score, color='darkgreen', linestyle='--', linewidth=2.5,
                label=f'Median: {median_score:.2f}', zorder=10)
    ax3.legend(frameon=True, fancybox=True, shadow=True)
    # Add count labels on bars
    for i, (count, edge) in enumerate(zip(counts, edges[:-1])):
        if count > 0:
            ax3.text(edge + 0.5, count + 5, f'{int(count)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    add_panel_label(ax3, 'c')
    
    plt.savefig(output_dir / 'Figure1_dataset_overview.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'Figure1_dataset_overview.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 1: Dataset Overview")

def figure2_model_performance(df, output_dir):
    """
    Figure 2: Model Performance Comparison
    (a) Box plot comparison
    (b) Score distribution per model  
    (c) Success and failure rates
    """
    fig = plt.figure(figsize=(16, 5))
    gs = GridSpec(1, 3, figure=fig, wspace=0.3)
    
    models = sorted(df['model_name'].unique())
    
    # Panel (a): Box plot
    ax1 = fig.add_subplot(gs[0, 0])
    positions = range(len(models))
    box_data = [df[df['model_name'] == m]['score'].values for m in models]
    colors = [MODEL_COLORS[m] for m in models]
    
    bp = ax1.boxplot(box_data, positions=positions, widths=0.6, patch_artist=True,
                     showmeans=True, meanline=True,
                     boxprops=dict(linewidth=1.5, edgecolor='black'),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5),
                     medianprops=dict(linewidth=2, color='red'),
                     meanprops=dict(linewidth=2, color='blue', linestyle='--'))
    
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Score', fontweight='bold')
    ax1.set_title('Score Distribution by Model', fontweight='bold')
    ax1.set_xticks(positions)
    ax1.set_xticklabels([m.replace('-', '-\n') for m in models], fontsize=9)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_ylim(-0.5, 7.5)
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='red', lw=2, label='Median'),
                      Line2D([0], [0], color='blue', lw=2, linestyle='--', label='Mean')]
    ax1.legend(handles=legend_elements, loc='upper left', frameon=True)
    add_panel_label(ax1, 'a')
    
    # Panel (b): Score distribution per model (stacked)
    ax2 = fig.add_subplot(gs[0, 1])
    width = 0.7
    score_bins = range(8)
    
    for i, model in enumerate(models):
        model_scores = df[df['model_name'] == model]['score']
        hist, _ = np.histogram(model_scores, bins=np.arange(-0.5, 8.5, 1))
        percentages = hist / len(model_scores) * 100
        
        bars = ax2.barh(i, 100, height=width, color='lightgray', alpha=0.3, edgecolor='black')
        
        left = 0
        for score, pct in enumerate(percentages):
            if pct > 0:
                color = plt.cm.RdYlGn(score / 7)  # Color gradient based on score
                ax2.barh(i, pct, height=width, left=left, 
                        color=color, edgecolor='white', linewidth=0.5)
                if pct > 5:  # Only label if segment is large enough
                    ax2.text(left + pct/2, i, f'{pct:.0f}%',
                            ha='center', va='center', fontsize=8, fontweight='bold')
                left += pct
    
    ax2.set_yticks(range(len(models)))
    ax2.set_yticklabels([m.replace('-', '-\n') for m in models], fontsize=9)
    ax2.set_xlabel('Percentage of Problems', fontweight='bold')
    ax2.set_title('Score Distribution (%) by Model', fontweight='bold')
    ax2.set_xlim(0, 100)
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=plt.cm.RdYlGn, 
                               norm=plt.Normalize(vmin=0, vmax=7))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax2, orientation='horizontal', pad=0.15, aspect=30)
    cbar.set_label('Score', fontweight='bold')
    cbar.set_ticks(range(8))
    add_panel_label(ax2, 'b')
    
    # Panel (c): Success and failure rates
    ax3 = fig.add_subplot(gs[0, 2])
    x = np.arange(len(models))
    width = 0.25
    
    perfect_rates = [df[df['model_name'] == m]['score'].apply(lambda s: s == 7).mean() * 100 for m in models]
    success_rates = [df[df['model_name'] == m]['score'].apply(lambda s: s >= 6).mean() * 100 for m in models]
    zero_rates = [df[df['model_name'] == m]['score'].apply(lambda s: s == 0).mean() * 100 for m in models]
    
    bars1 = ax3.bar(x - width, perfect_rates, width, label='Perfect (7)', 
                    color='#2ECC71', alpha=0.8, edgecolor='black', linewidth=1)
    bars2 = ax3.bar(x, success_rates, width, label='Success (≥6)',
                    color='#3498DB', alpha=0.8, edgecolor='black', linewidth=1)
    bars3 = ax3.bar(x + width, zero_rates, width, label='Zero (0)',
                    color='#E74C3C', alpha=0.8, edgecolor='black', linewidth=1)
    
    ax3.set_ylabel('Percentage (%)', fontweight='bold')
    ax3.set_title('Success and Failure Rates', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([m.replace('-', '-\n') for m in models], fontsize=9)
    ax3.legend(loc='upper right', frameon=True, fancybox=True)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.set_ylim(0, max(max(zero_rates), max(success_rates)) * 1.15)
    
    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    add_panel_label(ax3, 'c')
    
    plt.savefig(output_dir / 'Figure2_model_performance.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'Figure2_model_performance.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 2: Model Performance Comparison")

def figure3_performance_heatmaps(df, output_dir):
    """
    Figure 3: Performance Across Competitions
    (a) Average score heatmap
    (b) Success rate heatmap
    (c) Competition difficulty ranking
    """
    fig = plt.figure(figsize=(16, 5.5))
    gs = GridSpec(1, 3, figure=fig, wspace=0.4)
    
    # Prepare data
    col_order = df.groupby('source')['score'].mean().sort_values(ascending=False).index
    models = sorted(df['model_name'].unique())
    
    # Panel (a): Average score heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    pivot_mean = df.pivot_table(values='score', index='model_name', columns='source', aggfunc='mean')
    pivot_mean = pivot_mean[col_order]
    
    sns.heatmap(pivot_mean, annot=True, fmt='.2f', cmap='RdYlGn', center=3.5,
                vmin=0, vmax=7, cbar_kws={'label': 'Average Score'}, ax=ax1,
                linewidths=1.5, linecolor='white', annot_kws={'fontsize': 10, 'fontweight': 'bold'})
    ax1.set_xlabel('Competition', fontweight='bold')
    ax1.set_ylabel('Model', fontweight='bold')
    ax1.set_title('Average Score by Model and Competition', fontweight='bold')
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    ax1.set_yticklabels(ax1.get_yticklabels(), rotation=0)
    add_panel_label(ax1, 'a')
    
    # Panel (b): Success rate heatmap
    ax2 = fig.add_subplot(gs[0, 1])
    df['success'] = (df['score'] >= 6).astype(int)
    pivot_success = df.pivot_table(values='success', index='model_name', columns='source', aggfunc='mean') * 100
    pivot_success = pivot_success[col_order]
    
    sns.heatmap(pivot_success, annot=True, fmt='.1f', cmap='YlGnBu',
                vmin=0, vmax=50, cbar_kws={'label': 'Success Rate (%)'}, ax=ax2,
                linewidths=1.5, linecolor='white', annot_kws={'fontsize': 10, 'fontweight': 'bold'})
    ax2.set_xlabel('Competition', fontweight='bold')
    ax2.set_ylabel('Model', fontweight='bold')
    ax2.set_title('Success Rate (Score ≥ 6) by Model and Competition', fontweight='bold')
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0)
    add_panel_label(ax2, 'b')
    
    # Panel (c): Competition difficulty with error bars
    ax3 = fig.add_subplot(gs[0, 2])
    
    difficulty_stats = df.groupby('source')['score'].agg(['mean', 'std', 'sem']).sort_values('mean')
    colors = [COMPETITION_COLORS[s] for s in difficulty_stats.index]
    
    bars = ax3.barh(range(len(difficulty_stats)), difficulty_stats['mean'], 
                    xerr=difficulty_stats['sem'], capsize=5,
                    color=colors, alpha=0.8, edgecolor='black', linewidth=1.5,
                    error_kw={'linewidth': 2, 'ecolor': 'black'})
    
    ax3.set_yticks(range(len(difficulty_stats)))
    ax3.set_yticklabels(difficulty_stats.index)
    ax3.set_xlabel('Average Score (± SEM)', fontweight='bold')
    ax3.set_ylabel('Competition', fontweight='bold')
    ax3.set_title('Competition Difficulty Ranking', fontweight='bold')
    ax3.axvline(df['score'].mean(), color='red', linestyle='--', linewidth=2,
                label=f'Overall Mean: {df["score"].mean():.2f}', zorder=0)
    ax3.grid(axis='x', alpha=0.3, linestyle='--')
    ax3.legend(loc='lower right', frameon=True)
    ax3.set_xlim(0, 7)
    
    # Add value labels
    for i, (idx, row) in enumerate(difficulty_stats.iterrows()):
        ax3.text(row['mean'] + 0.15, i, f'{row["mean"]:.2f}',
                va='center', ha='left', fontsize=10, fontweight='bold')
    add_panel_label(ax3, 'c')
    
    plt.savefig(output_dir / 'Figure3_performance_heatmaps.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'Figure3_performance_heatmaps.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 3: Performance Across Competitions")

def figure4_temporal_analysis(df, output_dir):
    """
    Figure 4: Temporal and Detailed Analysis
    (a) Performance trends by year
    (b) Score distribution by competition (violin)
    """
    fig = plt.figure(figsize=(16, 5.5))
    gs = GridSpec(1, 2, figure=fig, wspace=0.3)
    
    # Panel (a): Performance trends by year
    ax1 = fig.add_subplot(gs[0, 0])
    
    df_with_year = df.dropna(subset=['year'])
    if len(df_with_year) > 0:
        year_model_perf = df_with_year.pivot_table(
            values='score', index='year', columns='model_name', aggfunc='mean'
        )
        
        models = sorted(df['model_name'].unique())
        for model in models:
            if model in year_model_perf.columns:
                ax1.plot(year_model_perf.index, year_model_perf[model], 
                        marker='o', linewidth=2.5, markersize=8, 
                        label=model, color=MODEL_COLORS[model], alpha=0.8)
        
        ax1.set_xlabel('Year', fontweight='bold')
        ax1.set_ylabel('Average Score', fontweight='bold')
        ax1.set_title('Model Performance Trends Over Years', fontweight='bold')
        ax1.legend(loc='best', frameon=True, fancybox=True, shadow=True)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_ylim(0, 7)
        
        # Add overall trend line
        overall_trend = df_with_year.groupby('year')['score'].mean()
        ax1.plot(overall_trend.index, overall_trend.values, 
                linestyle='--', linewidth=2, color='gray', alpha=0.6,
                label='Overall Average', zorder=0)
        ax1.legend(loc='best', frameon=True, fancybox=True, shadow=True)
    else:
        ax1.text(0.5, 0.5, 'No year data available', 
                ha='center', va='center', transform=ax1.transAxes, fontsize=14)
    
    add_panel_label(ax1, 'a')
    
    # Panel (b): Score distribution by competition (violin)
    ax2 = fig.add_subplot(gs[0, 1])
    
    sources_ordered = df.groupby('source')['score'].mean().sort_values().index
    df['source_ordered'] = pd.Categorical(df['source'], categories=sources_ordered, ordered=True)
    
    parts = ax2.violinplot([df[df['source'] == s]['score'].values for s in sources_ordered],
                          positions=range(len(sources_ordered)),
                          widths=0.7, showmeans=True, showmedians=True)
    
    # Color the violins
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(COMPETITION_COLORS[sources_ordered[i]])
        pc.set_alpha(0.7)
        pc.set_edgecolor('black')
        pc.set_linewidth(1.5)
    
    # Style the other components
    for partname in ('cbars', 'cmins', 'cmaxes', 'cmedians', 'cmeans'):
        if partname in parts:
            parts[partname].set_edgecolor('black')
            parts[partname].set_linewidth(1.5)
    
    ax2.set_xticks(range(len(sources_ordered)))
    ax2.set_xticklabels(sources_ordered, rotation=45, ha='right')
    ax2.set_ylabel('Score', fontweight='bold')
    ax2.set_xlabel('Competition', fontweight='bold')
    ax2.set_title('Score Distribution by Competition', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_ylim(-0.5, 7.5)
    
    # Add mean scores as text
    for i, source in enumerate(sources_ordered):
        mean_score = df[df['source'] == source]['score'].mean()
        ax2.text(i, 7.3, f'{mean_score:.1f}', ha='center', va='bottom',
                fontsize=9, fontweight='bold', 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    add_panel_label(ax2, 'b')
    
    plt.savefig(output_dir / 'Figure4_temporal_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'Figure4_temporal_analysis.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 4: Temporal and Detailed Analysis")

def create_summary_table_figure(df, output_dir):
    """
    Create a publication-quality summary statistics table as a figure
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')
    
    models = sorted(df['model_name'].unique())
    
    # Prepare table data
    table_data = []
    for model in models:
        model_data = df[df['model_name'] == model]['score']
        table_data.append([
            model,
            len(model_data),
            f"{model_data.mean():.2f}",
            f"{model_data.median():.2f}",
            f"{model_data.std():.2f}",
            f"{model_data.min():.1f}",
            f"{model_data.max():.1f}",
            f"{(model_data == 0).sum()}\n({(model_data == 0).mean()*100:.1f}%)",
            f"{(model_data == 7).sum()}\n({(model_data == 7).mean()*100:.1f}%)",
            f"{(model_data >= 6).sum()}\n({(model_data >= 6).mean()*100:.1f}%)"
        ])
    
    # Add overall row
    all_scores = df['score']
    table_data.append([
        'Overall',
        len(all_scores),
        f"{all_scores.mean():.2f}",
        f"{all_scores.median():.2f}",
        f"{all_scores.std():.2f}",
        f"{all_scores.min():.1f}",
        f"{all_scores.max():.1f}",
        f"{(all_scores == 0).sum()}\n({(all_scores == 0).mean()*100:.1f}%)",
        f"{(all_scores == 7).sum()}\n({(all_scores == 7).mean()*100:.1f}%)",
        f"{(all_scores >= 6).sum()}\n({(all_scores >= 6).mean()*100:.1f}%)"
    ])
    
    col_labels = ['Model', 'N', 'Mean', 'Median', 'Std', 'Min', 'Max', 
                  'Zero\nScores', 'Perfect\nScores (7)', 'Success\nRate (≥6)']
    
    # Create color array for rows
    row_colors = []
    for model in models:
        row_colors.append('white')
    row_colors.append('lightgray')  # Overall row
    
    table = ax.table(cellText=table_data,
                    colLabels=col_labels,
                    cellLoc='center',
                    loc='center',
                    colColours=['lightblue']*len(col_labels),
                    cellColours=[[c]*len(col_labels) for c in row_colors])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)
    
    # Bold the header and overall row
    for i in range(len(col_labels)):
        table[(0, i)].set_text_props(weight='bold', fontsize=12)
        table[(len(table_data), i)].set_text_props(weight='bold')
    
    # Bold the first column
    for i in range(len(table_data) + 1):
        table[(i, 0)].set_text_props(weight='bold')
    
    plt.title('Summary Statistics by Model', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'Table1_summary_statistics.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'Table1_summary_statistics.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Table 1: Summary Statistics")

def main():
    # File paths
    data_file = Path(__file__).parent / 'evaluation_merged.jsonl'
    output_dir = Path(__file__).parent / 'paper_figures'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("Loading data...")
    df = load_data(data_file)
    print(f"Loaded {len(df)} evaluations from {df['problem_id'].nunique()} unique problems")
    print(f"Models: {', '.join(sorted(df['model_name'].unique()))}")
    print(f"Competitions: {', '.join(sorted(df['source'].unique()))}")
    print()
    
    # Create figures
    print("Creating publication-quality figures...")
    print()
    figure1_dataset_overview(df, output_dir)
    figure2_model_performance(df, output_dir)
    figure3_performance_heatmaps(df, output_dir)
    figure4_temporal_analysis(df, output_dir)
    create_summary_table_figure(df, output_dir)
    
    print()
    print("="*60)
    print(f"✓ All figures saved to: {output_dir}")
    print(f"  - Generated {len(list(output_dir.glob('*.png')))} PNG files")
    print(f"  - Generated {len(list(output_dir.glob('*.pdf')))} PDF files")
    print("="*60)

if __name__ == '__main__':
    main()

