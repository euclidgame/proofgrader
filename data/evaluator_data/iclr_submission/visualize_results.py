#!/usr/bin/env python3
"""
Visualize evaluation results from evaluation_merged.jsonl
Creates various plots showing model performance across different competitions
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def load_data(filepath):
    """Load JSONL data into pandas DataFrame"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)

def extract_source(problem_id):
    """Extract source/competition from problem_id (part before first '-')"""
    return problem_id.split('-')[0]

def create_visualizations(df, output_dir):
    """Create all visualizations"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Add source column
    df['source'] = df['problem_id'].apply(extract_source)
    
    # 1. Source Distribution
    plt.figure(figsize=(10, 6))
    source_counts = df['source'].value_counts()
    plt.bar(source_counts.index, source_counts.values, color='steelblue', alpha=0.8)
    plt.title('Distribution of Problems by Source/Competition', fontsize=16, fontweight='bold')
    plt.xlabel('Competition', fontsize=12)
    plt.ylabel('Number of Problems', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'source_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Overall Score Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(df['score'], bins=np.arange(-0.5, 8.5, 1), color='skyblue', edgecolor='black', alpha=0.7)
    plt.title('Overall Score Distribution (All Models)', fontsize=16, fontweight='bold')
    plt.xlabel('Score', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.xticks(range(0, 8))
    plt.axvline(df['score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {df["score"].mean():.2f}')
    plt.axvline(df['score'].median(), color='green', linestyle='--', linewidth=2, label=f'Median: {df["score"].median():.2f}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'overall_score_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Score Distribution per Model
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    models = df['model_name'].unique()
    colors = ['skyblue', 'lightcoral', 'lightgreen']
    
    for i, model in enumerate(sorted(models)):
        model_data = df[df['model_name'] == model]['score']
        axes[i].hist(model_data, bins=np.arange(-0.5, 8.5, 1), color=colors[i], edgecolor='black', alpha=0.7)
        axes[i].set_title(f'{model}\n(Mean: {model_data.mean():.2f}, Median: {model_data.median():.2f})', 
                         fontsize=12, fontweight='bold')
        axes[i].set_xlabel('Score', fontsize=10)
        axes[i].set_ylabel('Frequency', fontsize=10)
        axes[i].set_xticks(range(0, 8))
    
    plt.suptitle('Score Distribution by Model', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'score_distribution_by_model.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Model Performance Comparison (Box Plot)
    plt.figure(figsize=(10, 6))
    df_sorted = df.sort_values('model_name')
    sns.boxplot(data=df_sorted, x='model_name', y='score', palette='Set2')
    plt.title('Score Distribution Comparison Across Models', fontsize=16, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'model_comparison_boxplot.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 5. Per-Model Performance on Different Competitions (Heatmap)
    pivot_mean = df.pivot_table(values='score', index='model_name', columns='source', aggfunc='mean')
    plt.figure(figsize=(14, 6))
    sns.heatmap(pivot_mean, annot=True, fmt='.2f', cmap='RdYlGn', center=3.5, 
                vmin=0, vmax=7, cbar_kws={'label': 'Average Score'})
    plt.title('Average Score per Model by Competition', fontsize=16, fontweight='bold')
    plt.xlabel('Competition', fontsize=12)
    plt.ylabel('Model', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_heatmap_mean.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 6. Problem Count per Model-Source combination
    pivot_count = df.pivot_table(values='score', index='model_name', columns='source', aggfunc='count')
    plt.figure(figsize=(14, 6))
    sns.heatmap(pivot_count, annot=True, fmt='g', cmap='Blues', cbar_kws={'label': 'Number of Problems'})
    plt.title('Number of Problems Evaluated per Model by Competition', fontsize=16, fontweight='bold')
    plt.xlabel('Competition', fontsize=12)
    plt.ylabel('Model', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_dir / 'problem_count_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 7. Success Rate (Score >= 6) by Model and Source
    df['success'] = (df['score'] >= 6).astype(int)
    pivot_success = df.pivot_table(values='success', index='model_name', columns='source', aggfunc='mean') * 100
    plt.figure(figsize=(14, 6))
    sns.heatmap(pivot_success, annot=True, fmt='.1f', cmap='YlGnBu', 
                cbar_kws={'label': 'Success Rate (%)'}, vmin=0, vmax=100)
    plt.title('Success Rate (Score ≥ 6) per Model by Competition (%)', fontsize=16, fontweight='bold')
    plt.xlabel('Competition', fontsize=12)
    plt.ylabel('Model', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_dir / 'success_rate_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 8. Perfect Score Rate (Score = 7) by Model
    df['perfect'] = (df['score'] == 7).astype(int)
    perfect_by_model = df.groupby('model_name')['perfect'].mean() * 100
    plt.figure(figsize=(10, 6))
    bars = plt.bar(perfect_by_model.index, perfect_by_model.values, color=['#FF6B6B', '#4ECDC4', '#95E1D3'], alpha=0.8)
    plt.title('Perfect Score Rate (Score = 7) by Model', fontsize=16, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Perfect Score Rate (%)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.savefig(output_dir / 'perfect_score_rate.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 9. Zero Score Rate by Model
    df['zero_score'] = (df['score'] == 0).astype(int)
    zero_by_model = df.groupby('model_name')['zero_score'].mean() * 100
    plt.figure(figsize=(10, 6))
    bars = plt.bar(zero_by_model.index, zero_by_model.values, color=['#E74C3C', '#3498DB', '#2ECC71'], alpha=0.8)
    plt.title('Zero Score Rate (Score = 0) by Model', fontsize=16, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Zero Score Rate (%)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.savefig(output_dir / 'zero_score_rate.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 10. Difficulty by Source (Average Score)
    difficulty_by_source = df.groupby('source')['score'].mean().sort_values()
    plt.figure(figsize=(12, 6))
    bars = plt.barh(difficulty_by_source.index, difficulty_by_source.values, color='coral', alpha=0.8)
    plt.title('Average Score by Competition (Lower = Harder)', fontsize=16, fontweight='bold')
    plt.xlabel('Average Score', fontsize=12)
    plt.ylabel('Competition', fontsize=12)
    plt.axvline(df['score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Overall Mean: {df["score"].mean():.2f}')
    for i, bar in enumerate(bars):
        width = bar.get_width()
        plt.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:.2f}', ha='left', va='center', fontsize=10, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'difficulty_by_source.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 11. Score distribution across sources (violin plot)
    plt.figure(figsize=(14, 8))
    sources_ordered = df.groupby('source')['score'].mean().sort_values().index
    df['source_ordered'] = pd.Categorical(df['source'], categories=sources_ordered, ordered=True)
    sns.violinplot(data=df, x='source_ordered', y='score', palette='muted')
    plt.title('Score Distribution by Competition', fontsize=16, fontweight='bold')
    plt.xlabel('Competition', fontsize=12)
    plt.ylabel('Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'score_violin_by_source.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 12. Model comparison across years (if year info available)
    df['year'] = df['problem_id'].str.extract(r'-(\d{4})-')[0]
    if df['year'].notna().sum() > 0:
        plt.figure(figsize=(14, 8))
        year_model_perf = df.dropna(subset=['year']).pivot_table(
            values='score', index='year', columns='model_name', aggfunc='mean'
        )
        year_model_perf.plot(marker='o', linewidth=2, markersize=8)
        plt.title('Model Performance Trends Over Years', fontsize=16, fontweight='bold')
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Average Score', fontsize=12)
        plt.legend(title='Model', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'performance_trends_by_year.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    # 13. Summary Statistics Table (as image)
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')
    
    summary_stats = []
    for model in sorted(df['model_name'].unique()):
        model_data = df[df['model_name'] == model]['score']
        summary_stats.append([
            model,
            len(model_data),
            f"{model_data.mean():.2f}",
            f"{model_data.median():.2f}",
            f"{model_data.std():.2f}",
            f"{(model_data == 0).sum()} ({(model_data == 0).mean()*100:.1f}%)",
            f"{(model_data == 7).sum()} ({(model_data == 7).mean()*100:.1f}%)",
            f"{(model_data >= 6).sum()} ({(model_data >= 6).mean()*100:.1f}%)"
        ])
    
    table = ax.table(cellText=summary_stats,
                    colLabels=['Model', 'N', 'Mean', 'Median', 'Std Dev', 'Zero Scores', 'Perfect (7)', 'Success (≥6)'],
                    cellLoc='center',
                    loc='center',
                    colColours=['lightblue']*8)
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    plt.title('Summary Statistics by Model', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'summary_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 14. Generate text summary report
    with open(output_dir / 'summary_report.txt', 'w') as f:
        f.write("="*80 + "\n")
        f.write("EVALUATION RESULTS SUMMARY REPORT\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total evaluations: {len(df)}\n")
        f.write(f"Total unique problems: {df['problem_id'].nunique()}\n")
        f.write(f"Total models: {df['model_name'].nunique()}\n")
        f.write(f"Total competitions: {df['source'].nunique()}\n\n")
        
        f.write("-"*80 + "\n")
        f.write("OVERALL STATISTICS\n")
        f.write("-"*80 + "\n")
        f.write(f"Mean score: {df['score'].mean():.2f}\n")
        f.write(f"Median score: {df['score'].median():.2f}\n")
        f.write(f"Std deviation: {df['score'].std():.2f}\n")
        f.write(f"Min score: {df['score'].min():.2f}\n")
        f.write(f"Max score: {df['score'].max():.2f}\n\n")
        
        f.write("-"*80 + "\n")
        f.write("STATISTICS BY MODEL\n")
        f.write("-"*80 + "\n")
        for model in sorted(df['model_name'].unique()):
            model_data = df[df['model_name'] == model]['score']
            f.write(f"\n{model}:\n")
            f.write(f"  Problems evaluated: {len(model_data)}\n")
            f.write(f"  Mean score: {model_data.mean():.2f}\n")
            f.write(f"  Median score: {model_data.median():.2f}\n")
            f.write(f"  Std deviation: {model_data.std():.2f}\n")
            f.write(f"  Zero scores: {(model_data == 0).sum()} ({(model_data == 0).mean()*100:.1f}%)\n")
            f.write(f"  Perfect scores (7): {(model_data == 7).sum()} ({(model_data == 7).mean()*100:.1f}%)\n")
            f.write(f"  Success rate (≥6): {(model_data >= 6).sum()} ({(model_data >= 6).mean()*100:.1f}%)\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("STATISTICS BY COMPETITION\n")
        f.write("-"*80 + "\n")
        for source in sorted(df['source'].unique()):
            source_data = df[df['source'] == source]['score']
            f.write(f"\n{source}:\n")
            f.write(f"  Problems: {len(source_data)}\n")
            f.write(f"  Mean score: {source_data.mean():.2f}\n")
            f.write(f"  Median score: {source_data.median():.2f}\n")
            f.write(f"  Success rate (≥6): {(source_data >= 6).mean()*100:.1f}%\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("TOP 10 EASIEST PROBLEMS (by average score)\n")
        f.write("-"*80 + "\n")
        easiest = df.groupby('problem_id')['score'].mean().sort_values(ascending=False).head(10)
        for i, (problem, score) in enumerate(easiest.items(), 1):
            f.write(f"{i:2d}. {problem:30s} - Average: {score:.2f}\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("TOP 10 HARDEST PROBLEMS (by average score)\n")
        f.write("-"*80 + "\n")
        hardest = df.groupby('problem_id')['score'].mean().sort_values().head(10)
        for i, (problem, score) in enumerate(hardest.items(), 1):
            f.write(f"{i:2d}. {problem:30s} - Average: {score:.2f}\n")
    
    print(f"\nAll visualizations saved to: {output_dir}")
    print(f"Generated {len(list(output_dir.glob('*.png')))} plots")
    print(f"Summary report: {output_dir / 'summary_report.txt'}")

if __name__ == '__main__':
    # File paths
    data_file = Path(__file__).parent / 'evaluation_merged.jsonl'
    output_dir = Path(__file__).parent / 'visualizations'
    
    # Load data
    print(f"Loading data from {data_file}...")
    df = load_data(data_file)
    print(f"Loaded {len(df)} evaluations")
    
    # Create visualizations
    print("Creating visualizations...")
    create_visualizations(df, output_dir)
    
    print("\nDone!")

