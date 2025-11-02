# Publication-Quality Figures Guide

Generated publication-ready figures for the evaluation dataset paper.

## 📊 Figure Descriptions

### **Figure 1: Dataset Overview** (`Figure1_dataset_overview.png/pdf`)
**Multi-panel figure showing dataset composition and characteristics**

- **(a) Problem Distribution by Competition**: Horizontal bar chart showing the number of unique problems from each competition (APMO, EGMO, IMO, PUTNAM, TST, USAMO)
- **(b) Number of Evaluations per Model**: Heatmap showing how many problems each model was evaluated on for each competition
- **(c) Overall Score Distribution**: Histogram showing the distribution of all scores (0-7) with mean and median indicators

**Recommended caption**: "Dataset overview and composition. (a) Distribution of 142 unique problems across 6 mathematical competitions. (b) Number of evaluations per model-competition pair, showing balanced coverage. (c) Overall score distribution across all 426 evaluations, with mean (2.41) and median (1.50) indicated, demonstrating high task difficulty."

---

### **Figure 2: Model Performance Comparison** (`Figure2_model_performance.png/pdf`)
**Comprehensive comparison of model performance metrics**

- **(a) Score Distribution by Model**: Box plot comparing score distributions across the three models, showing medians, quartiles, and outliers
- **(b) Score Distribution (%) by Model**: Stacked horizontal bar chart showing percentage breakdown of scores (0-7) for each model with color gradient
- **(c) Success and Failure Rates**: Grouped bar chart comparing perfect scores (=7), success rates (≥6), and zero scores (=0) across models

**Recommended caption**: "Comparative analysis of model performance. (a) Box plots showing score distributions with medians (red) and means (blue dashed). (b) Percentage breakdown of scores for each model, colored by score value. (c) Success metrics showing perfect scores, overall success rate (score ≥6), and failure rate (score =0). OpenAI-o3 demonstrates the highest performance across all metrics."

---

### **Figure 3: Performance Across Competitions** (`Figure3_performance_heatmaps.png/pdf`)
**Detailed breakdown of performance by competition type**

- **(a) Average Score by Model and Competition**: Heatmap showing mean scores with color gradient (green=high, red=low)
- **(b) Success Rate by Model and Competition**: Heatmap showing percentage of problems solved with score ≥6
- **(c) Competition Difficulty Ranking**: Horizontal bar chart ranking competitions by average score with error bars (SEM)

**Recommended caption**: "Model performance across different mathematical competitions. (a) Average scores per model-competition pair, revealing competition-specific strengths. (b) Success rates (score ≥6) showing substantial variation across competitions. (c) Competition difficulty ranking with standard error bars, showing TST (mean: 1.22) as the most challenging and PUTNAM (mean: 3.11) as the least challenging competition."

---

### **Figure 4: Temporal and Detailed Analysis** (`Figure4_temporal_analysis.png/pdf`)
**Temporal trends and detailed score distributions**

- **(a) Performance Trends Over Years**: Line plot showing average scores by year for each model and overall trend
- **(b) Score Distribution by Competition**: Violin plot showing full score distributions for each competition, ordered by difficulty

**Recommended caption**: "Temporal and distributional analysis of model performance. (a) Model performance trends across different years, with overall average (gray dashed) for reference. (b) Violin plots showing complete score distributions for each competition, ordered by increasing average score. Mean scores are annotated above each distribution."

---

### **Table 1: Summary Statistics** (`Table1_summary_statistics.png/pdf`)
**Comprehensive statistical summary table**

Complete summary statistics for each model including:
- N (number of evaluations)
- Mean, Median, Standard Deviation
- Min, Max scores
- Zero scores (count and percentage)
- Perfect scores (count and percentage)  
- Success rate ≥6 (count and percentage)
- Overall row for aggregate statistics

**Recommended caption**: "Summary statistics for model performance. Each model was evaluated on 142 problems. OpenAI-o3 achieves the highest mean score (2.84) and success rate (26.1%), while DeepSeek-R1-0528 shows the highest failure rate (40.8% zero scores). Overall statistics demonstrate the challenging nature of the dataset (mean: 2.41/7)."

---

## 📝 Features

All figures include:
- ✅ Colorblind-friendly palettes (verified for deuteranopia, protanopia, tritanopia)
- ✅ High-resolution outputs (300 DPI)
- ✅ Both PNG and PDF formats (PDF recommended for LaTeX)
- ✅ Clear panel labels (a), (b), (c) for multi-panel figures
- ✅ Professional typography and spacing
- ✅ Grid lines and statistical indicators
- ✅ Publication-ready formatting

## 🎨 Color Schemes

**Models:**
- DeepSeek-R1-0528: Orange (#E69F00)
- Gemini-2.5-pro: Sky Blue (#56B4E9)
- OpenAI-o3: Green (#009E73)

**Competitions:**
- APMO: Orange (#E69F00)
- EGMO: Sky Blue (#56B4E9)
- IMO: Green (#009E73)
- PUTNAM: Yellow (#F0E442)
- TST: Dark Blue (#0072B2)
- USAMO: Dark Orange (#D55E00)

## 📄 Recommended Usage in Paper

### Main Paper
- **Figure 1**: Dataset overview (essential)
- **Figure 2**: Model comparison (essential)
- **Figure 3**: Performance across competitions (essential)
- **Table 1**: Summary statistics (can be in main text or appendix)

### Supplementary Material
- **Figure 4**: Temporal analysis (if space limited in main paper)

### Typical Figure Sizes in LaTeX
```latex
% Full width (two-column)
\begin{figure*}[t]
    \centering
    \includegraphics[width=\textwidth]{Figure1_dataset_overview.pdf}
    \caption{Your caption here}
    \label{fig:dataset}
\end{figure*}

% Single column
\begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{Table1_summary_statistics.pdf}
    \caption{Your caption here}
    \label{tab:summary}
\end{figure}
```

## 📊 Key Statistics to Highlight

- **Dataset size**: 142 unique problems, 426 total evaluations
- **Competitions**: 6 major mathematical competitions (APMO, EGMO, IMO, PUTNAM, TST, USAMO)
- **Overall difficulty**: Mean score 2.41/7, median 1.50/7
- **Best model**: OpenAI-o3 (mean: 2.84, success rate: 26.1%)
- **Hardest competition**: TST (mean: 1.22, 5.9% success rate)
- **Easiest competition**: PUTNAM (mean: 3.11, 32.4% success rate)
- **High failure rate**: ~34% of all attempts score 0

## 🔧 Customization

To modify figures, edit `create_paper_figures.py`:
- Colors: Modify `MODEL_COLORS` and `COMPETITION_COLORS` dictionaries
- Font sizes: Adjust `plt.rcParams.update()` at the top
- Figure sizes: Change `figsize` parameters in each function
- Panel layouts: Modify `GridSpec` parameters

## 📝 Citation Recommendation

When describing the dataset, consider including:
1. Total number of problems and evaluations
2. Distribution across competitions  
3. Model performance metrics
4. Competition difficulty rankings
5. Success/failure rates

Example text:
"We evaluate three state-of-the-art models on 142 mathematical competition problems spanning 6 competitions (Figure 1). Performance varies significantly across competitions, with success rates ranging from 5.9% (TST) to 32.4% (PUTNAM) (Figure 3c). OpenAI-o3 achieves the highest overall performance with a mean score of 2.84/7 and a 26.1% success rate (Table 1)."

