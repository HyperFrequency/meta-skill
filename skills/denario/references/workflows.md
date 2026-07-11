# Denario Workflows & Examples

All examples assume `from denario import Denario, Journal` and that provider credentials are
configured (see [llm-configuration.md](llm-configuration.md)).

## Pattern 1 — Fully automated

Let Denario drive every stage. Best when you want breadth of exploration from a dataset.

```python
den = Denario(project_dir="./climate_research")
den.set_data_description("""
Dataset: global temperature anomalies (1880-2023), monthly, CSV [year, month, anomaly]
Source: NASA GISTEMP; strong autocorrelation, seasonality, sparse pre-1900
Tools: pandas, scipy, sklearn, matplotlib, seaborn
Domain: climate science
Goal: quantify and characterize the long-term warming trend
""")
den.get_idea()
den.get_method()
den.get_results()
den.get_paper(journal=Journal.APS)
```

## Pattern 2 — Custom idea, automated execution

You know the question; let Denario design and run the study.

```python
den = Denario(project_dir="./custom_idea")
den.set_data_description("Financial time-series: daily S&P 500 close, 2010-2023; tools: pandas, statsmodels, sklearn")
den.set_idea("Predict short-horizon volatility with an LSTM and compare to a GARCH baseline")
den.get_method()
den.get_results()
den.get_paper(journal=Journal.APS)
```

## Pattern 3 — Format-only (paper from existing results)

Use Denario purely as a manuscript formatter when the science is already done.

```python
den = Denario(project_dir="./paper_generation")
den.set_data_description("Traffic flow from 100 intersections, Jan-Jun 2023, 1-min intervals")
den.set_idea("Optimize traffic-light timing with reinforcement learning to cut congestion")
den.set_method("methodology.md")   # your written methodology
den.set_results("results.md")      # your computed findings + figure captions
den.get_paper(journal=Journal.APS)
```

## Pattern 4 — Iterative refinement

Revise an upstream stage, then re-run only what depends on it — no need to redo the whole
pipeline.

```python
den = Denario(project_dir="./iterative")
den.set_data_description("...")
den.get_idea(); den.get_method(); den.get_results()

# after reviewing results.md, tighten the method:
den.set_method("""
Revised: swap t-test for Mann-Kendall; add sensitivity analysis; add 5-fold CV
""")
den.get_results()                  # re-execute with the new method
den.get_paper(journal=Journal.APS)
```

## Rich data descriptions matter

The quality of generated ideas tracks the quality of the description. Compare:

```python
# weak
den.set_data_description("Gene expression data from cancer patients")

# strong
den.set_data_description("""
Dataset: breast-cancer microarray, 500 patients (250 responders / 250 non-responders)
Features: log2 expression of 20,000 genes; CSV matrix (samples × genes)
Clinical metadata: age, tumor stage, response, survival time
Tools: pandas, sklearn (PCA/RF/SVM), lifelines, matplotlib/seaborn
Objectives: gene signatures predictive of response; candidate targets; CV-validated
Caveats: <5% missing values; batch effects already corrected
""")
```

Always name: data format & size, available tools/libraries, domain, objectives, and known
data-quality issues.

## Cross-domain sketches

The five-stage API is domain-agnostic; only the data description changes.

**Time-series forecasting**
```python
den.set_data_description("""
US monthly unemployment (1950-2023) + GDP growth, inflation, rates; multivariate TS
Tools: statsmodels, pmdarima, prophet, sklearn
Goals: model the trend, forecast 12 months, find leading indicators, quantify uncertainty
Caveats: seasonality, recession structural breaks, non-stationary (unit root)
""")
den.get_idea(); den.get_method(); den.get_results(); den.get_paper(journal=Journal.APS)
```

**Imbalanced ML classification**
```python
den.set_data_description("""
Customer churn: 50k rows, 30 mixed num/cat features, 20% positive class
Tools: pandas, sklearn (RF/XGBoost/logreg), imblearn, SHAP
Goals: predictive churn model, key drivers, actionable insight, target AUC-ROC > 0.85
""")
den.get_idea(); den.get_method(); den.get_results(); den.get_paper(journal=Journal.APS)
```

**Medical imaging (hybrid)**
```python
den.set_data_description("10k chest X-rays, labels {normal, pneumonia, COVID-19}, 224x224 PNG; tools: TF/Keras, sklearn, OpenCV")
den.set_idea("Transfer-learn ResNet50 for 3-class X-ray classification; add Grad-CAM interpretability")
den.get_method(); den.get_results(); den.get_paper(journal=Journal.APS)
```

## Save and version the workflow

Keep the driver script and commit `project_dir` after each stage so the research is
reproducible and auditable:

```bash
cd project_dir && git init
git add . && git commit -m "data description"
# ...commit again after idea / method / results / paper
```

## Notes on capabilities to confirm upstream

- **Literature search**: Denario incorporates prior-work retrieval within the idea/method
  stages; a stable, separately documented public method for standalone literature search is
  not something to assume — verify against upstream docs (and for a dedicated prior-work
  pass, the `literature-review` skill is the focused alternative).
- **Fast mode**: "fast" runs are just a matter of choosing a lighter model backend (see
  [llm-configuration.md](llm-configuration.md)), not a distinct API.
