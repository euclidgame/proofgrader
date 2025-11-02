# Figure Caption and Paper Text

## 📊 FIGURE CAPTION (Brief Version)

**Figure 1: Dataset composition and model performance evaluation.**
**(a)** Distribution of 142 unique problems across 6 mathematical competitions. **(b)** Overall score distribution showing mean score of 2.41/7 (red dashed) and median of 1.50/7 (green dashed), indicating high task difficulty. **(c)** Box plots comparing score distributions across three models, with OpenAI-o3 achieving highest median performance. **(d)** Percentage breakdown of scores by model, revealing OpenAI-o3 has the most balanced distribution while DeepSeek-R1-0528 shows highest failure rate. **(e)** Performance heatmap showing average scores per model-competition pair, highlighting substantial variation across problem sources. **(f)** Competition difficulty ranking with error bars (±SEM), showing TST as most challenging (mean: 1.22) and PUTNAM as most accessible (mean: 3.11).

---

## 📝 PAPER TEXT: Model Performance Analysis

### Section: Results and Analysis

We evaluate three state-of-the-art large language models on our benchmark: DeepSeek-R1-0528, Gemini-2.5-pro, and OpenAI-o3. Figure 1 presents a comprehensive overview of our evaluation results across 142 unique problems from six major mathematical competitions: APMO, EGMO, IMO, PUTNAM, TST, and USAMO.

**Overall Performance.** The overall score distribution (Figure 1b) reveals that mathematical competition problems pose significant challenges to current models, with a mean score of 2.41 out of 7 (median: 1.50). Notably, 34.5% of all attempts result in zero scores, while only 17.6% achieve near-perfect or perfect scores (≥6). This distribution is heavily right-skewed, with the majority of scores concentrated in the lower range (0-3), indicating that most problems remain largely unsolved by current models.

**Model Comparison.** Among the three models, OpenAI-o3 demonstrates the strongest performance with a mean score of 2.84 and a success rate (score ≥6) of 26.1% (Figure 1c). Gemini-2.5-pro achieves moderate performance (mean: 2.55, success rate: 23.9%), while DeepSeek-R1-0528 lags notably behind (mean: 1.85, success rate: 11.3%). The score distribution analysis (Figure 1d) reveals distinct behavioral patterns: DeepSeek-R1-0528 exhibits a bimodal distribution with high concentrations at both extremes (40.8% zeros, 10.6% perfect scores), suggesting an "all-or-nothing" solving pattern. In contrast, OpenAI-o3 shows a more uniform distribution across score ranges, indicating more consistent partial credit achievement and robust problem-solving strategies.

**Competition-Specific Analysis.** Performance varies dramatically across competition sources (Figure 1e,f). All models perform best on PUTNAM problems (overall mean: 3.11, 32.4% success rate), followed by EGMO (mean: 2.98) and APMO (mean: 2.83). Conversely, TST problems prove exceptionally challenging, with an overall mean score of only 1.22 and a mere 5.9% success rate. IMO and USAMO problems fall in the middle range (means: 1.86 and 1.82, respectively). This variation suggests that certain problem types or mathematical domains present particular difficulties for current models. Notably, OpenAI-o3 maintains a consistent advantage across all competitions, though even this top-performing model struggles significantly with TST problems (mean: 1.22).

**Key Findings.** Our analysis reveals three critical insights: (1) Current models remain far from human expert-level performance on mathematical competition problems, with success rates below 30% even for the best model; (2) There exists substantial room for improvement in handling complex, multi-step mathematical reasoning; and (3) Competition source significantly impacts difficulty, with olympiad-style problems (TST, IMO, USAMO) proving more challenging than exam-style problems (PUTNAM), suggesting that different mathematical reasoning skills are required across problem types.

---

## 🎯 ALTERNATIVE SHORTER VERSION (2-3 paragraphs)

We evaluate three state-of-the-art models—DeepSeek-R1-0528, Gemini-2.5-pro, and OpenAI-o3—on 142 mathematical competition problems spanning six competitions (Figure 1a). The overall performance reveals significant challenges, with a mean score of 2.41/7 and median of 1.50/7 (Figure 1b). OpenAI-o3 achieves the highest performance (mean: 2.84, 26.1% success rate), followed by Gemini-2.5-pro (mean: 2.55, 23.9% success rate) and DeepSeek-R1-0528 (mean: 1.85, 11.3% success rate) (Figure 1c). Notably, 34.5% of all attempts result in zero scores, while only 17.6% achieve scores ≥6, highlighting the substantial difficulty gap.

The score distribution analysis (Figure 1d) reveals distinct model behaviors: DeepSeek-R1-0528 exhibits a bimodal pattern with high concentrations at extremes (40.8% zeros, 10.6% perfect scores), suggesting an "all-or-nothing" approach, while OpenAI-o3 shows more uniform distribution across score ranges, indicating robust partial credit achievement. Performance varies dramatically by competition (Figure 1e,f), with PUTNAM problems being most accessible (mean: 3.11, 32.4% success rate) and TST problems most challenging (mean: 1.22, 5.9% success rate). Even the top-performing model struggles with olympiad-style problems, suggesting fundamental limitations in complex mathematical reasoning that warrant future investigation.

---

## 📊 KEY STATISTICS TABLE (for paper body)

| Metric | DeepSeek-R1 | Gemini-2.5 | OpenAI-o3 | Overall |
|--------|-------------|------------|-----------|---------|
| Mean Score (±SD) | 1.85±2.27 | 2.55±2.64 | 2.84±2.81 | 2.41±2.61 |
| Median Score | 1.00 | 2.00 | 2.00 | 1.50 |
| Success Rate (≥6) | 11.3% | 23.9% | 26.1% | 20.4% |
| Perfect Scores (=7) | 10.6% | 19.7% | 22.5% | 17.6% |
| Zero Scores (=0) | 40.8% | 28.2% | 34.5% | 34.5% |

**Table 1: Summary statistics for model performance across all 142 problems.**

---

## 🎨 OPTIONAL: In-Text Reference Examples

"As shown in Figure 1a, our dataset comprises..."

"The score distribution (Figure 1b) reveals that..."

"Model comparison (Figure 1c) demonstrates that OpenAI-o3 outperforms..."

"Score breakdown analysis (Figure 1d) shows distinct patterns..."

"The performance heatmap (Figure 1e) highlights competition-specific variations..."

"Competition difficulty ranking (Figure 1f) confirms that TST problems..."

---

## 💡 DISCUSSION POINTS

Consider addressing these points in your Discussion section:

1. **Performance Gap**: Why do all models struggle? (complex multi-step reasoning, symbolic manipulation, proof verification)

2. **Competition Variance**: Why is PUTNAM easier than TST? (problem structure, domain coverage, proof complexity)

3. **Model Behavior Differences**: 
   - DeepSeek's bimodal pattern → overfitting or brittleness?
   - OpenAI-o3's uniformity → better generalization?

4. **Zero-Score Problem**: 34.5% complete failures indicate:
   - Problem comprehension issues
   - Inability to start/formulate approach
   - Hallucination or invalid reasoning

5. **Future Directions**:
   - Need for better mathematical reasoning architectures
   - Importance of formal verification
   - Value of partial credit in evaluation

---

## ✅ READY TO COPY-PASTE

Both the brief caption and the analysis text above are publication-ready. Simply copy and paste into your paper draft, adjusting formatting as needed for your specific journal/conference style.

