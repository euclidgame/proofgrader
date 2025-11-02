# Combined Figure Caption and Usage

## Combined Figure (2×3 Layout)

### Panel Descriptions:

**Row 1:**
- **(a) Problem Distribution by Competition**: Shows the distribution of 142 unique problems across 6 mathematical competitions with both counts and percentages
- **(b) Overall Score Distribution**: Histogram of all 426 evaluations showing score frequency with mean (2.41) and median (1.50) 
- **(c) Score Distribution by Model**: Box plots comparing the three models, showing medians (red), means (blue dashed), quartiles, and outliers

**Row 2:**
- **(d) Score Distribution (%) by Model**: Stacked horizontal bars showing percentage breakdown of scores (0-7) for each model with color gradient
- **(e) Average Score by Model and Competition**: Heatmap showing mean scores for each model-competition pair
- **(f) Competition Difficulty Ranking**: Competitions ranked by average score with error bars (SEM), showing TST as hardest and PUTNAM as easiest

---

## Recommended Figure Caption

**Option 1 (Detailed):**
```
Dataset overview and model performance analysis. (a) Distribution of 142 unique problems 
across 6 mathematical competitions, showing problem counts and percentages. (b) Overall 
score distribution across all 426 evaluations, with mean (2.41/7, red) and median 
(1.50/7, green) indicating high task difficulty. (c) Score distribution comparison across 
three state-of-the-art models using box plots, with OpenAI-o3 showing highest median 
performance. (d) Percentage breakdown of scores for each model, colored by score value 
(red=low, green=high), revealing distinct performance patterns. (e) Average scores per 
model-competition pair, highlighting competition-specific strengths and weaknesses. 
(f) Competition difficulty ranking with standard error bars, showing TST (mean: 1.22) 
as most challenging and PUTNAM (mean: 3.11) as least challenging, with overall mean 
(2.41, dashed line) for reference.
```

**Option 2 (Concise):**
```
Dataset composition and model evaluation results. (a) Problem distribution across 6 
competitions. (b) Overall score distribution showing mean (2.41) and median (1.50). 
(c) Model performance comparison via box plots. (d) Score distribution percentages by 
model. (e) Performance heatmap by model and competition. (f) Competition difficulty 
ranking with error bars. TST emerges as the most challenging competition (mean: 1.22), 
while PUTNAM is the least challenging (mean: 3.11). OpenAI-o3 achieves the highest 
overall performance across all metrics.
```

---

## LaTeX Usage

### Full-Width Figure (Two-Column Paper)
```latex
\begin{figure*}[t]
    \centering
    \includegraphics[width=\textwidth]{Combined_Figure.pdf}
    \caption{Dataset overview and model performance analysis. 
    (a) Distribution of 142 unique problems across 6 mathematical competitions. 
    (b) Overall score distribution (mean: 2.41, median: 1.50). 
    (c) Model comparison via box plots. 
    (d) Score distribution percentages by model. 
    (e) Performance heatmap by model and competition. 
    (f) Competition difficulty ranking. 
    OpenAI-o3 achieves highest overall performance; TST is most challenging (mean: 1.22).}
    \label{fig:combined}
\end{figure*}
```

### Single-Column Paper
```latex
\begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{Combined_Figure.pdf}
    \caption{Dataset overview and model performance analysis. See text for details.}
    \label{fig:combined}
\end{figure}
```

---

## Key Statistics to Reference in Text

When discussing this figure in your paper, mention:

1. **Dataset size**: 142 unique problems, 426 total evaluations
2. **Competition coverage**: 6 competitions (PUTNAM: 36, EGMO: 23, USAMO: 24, IMO: 22, APMO: 20, TST: 17)
3. **Overall difficulty**: Mean 2.41/7, Median 1.50/7
4. **Model ranking**: 
   - OpenAI-o3: 2.84 mean (best)
   - Gemini-2.5-pro: 2.55 mean
   - DeepSeek-R1-0528: 1.85 mean
5. **Competition difficulty** (easiest to hardest):
   - PUTNAM: 3.11
   - EGMO: 2.98
   - APMO: 2.83
   - IMO: 1.86
   - USAMO: 1.82
   - TST: 1.22 (most challenging)
6. **Success rates** (score ≥ 6):
   - OpenAI-o3: 26.1%
   - Gemini-2.5-pro: 23.9%
   - DeepSeek-R1-0528: 11.3%

---

## Example Text Integration

"Figure 1 presents a comprehensive overview of our evaluation dataset and model performance. 
The dataset comprises 142 unique mathematical competition problems from 6 competitions 
(Figure 1a), with PUTNAM contributing the most problems (36, 25.4%). The overall score 
distribution (Figure 1b) reveals the challenging nature of these problems, with a mean 
score of 2.41/7 and median of 1.50/7. Among the three evaluated models (Figure 1c), 
OpenAI-o3 achieves the highest performance with a mean score of 2.84, followed by 
Gemini-2.5-pro (2.55) and DeepSeek-R1-0528 (1.85). The score distribution breakdown 
(Figure 1d) shows that DeepSeek-R1-0528 has the highest proportion of zero scores (41%), 
while OpenAI-o3 has the highest perfect score rate (23%). Performance varies significantly 
across competitions (Figure 1e), with all models performing best on PUTNAM problems and 
struggling most with TST problems. Competition difficulty ranking (Figure 1f) confirms 
TST as the most challenging (mean: 1.22, 5.9% success rate) and PUTNAM as the most 
accessible (mean: 3.11, 32.4% success rate)."

---

## Figure Dimensions

- **Size**: 18" × 10" (suitable for two-column papers at full width)
- **Resolution**: 300 DPI
- **Format**: Both PNG and PDF (use PDF for LaTeX)
- **Aspect ratio**: 1.8:1 (wide format)

---

## Notes

- All panels use colorblind-friendly palettes
- Panel labels (a)-(f) are positioned outside the plot area for clarity
- Error bars in panel (f) represent standard error of the mean (SEM)
- Color gradient in panel (d) maps score values (red=0, green=7)
- Heatmap in panel (e) uses diverging colormap centered at 3.5
- Percentages in panel (a) sum to 100%

---

## Customization

To modify the figure, edit `create_combined_figure.py`:
- Figure size: Change `figsize=(18, 10)`
- Spacing: Adjust `hspace` and `wspace` in GridSpec
- Colors: Modify `MODEL_COLORS` and `COMPETITION_COLORS`
- Fonts: Edit `plt.rcParams.update()` section

