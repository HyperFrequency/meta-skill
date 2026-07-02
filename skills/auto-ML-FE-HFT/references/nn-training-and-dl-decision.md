# Sections E & F — NN training techniques + when to apply deep learning

## Section E — NN training techniques per scenario (sharp opinions)

Each scenario is a Recommendation. Baseline = **XGBoost / LightGBM / CatBoost first**; justify the DL step with a quantified gap.

- **E.1 Tabular HFT, ≤1M rows.** Boosting (XGBoost / LightGBM / CatBoost). **Skip DL.** Borisov 2022 + Shwartz-Ziv 2021 find boosting wins on tabular below ~10M rows; tabular NNs (TabNet, SAINT, FT-Transformer) only catch up at scale. Spend time on features.
- **E.2 Tabular HFT, >>1M rows + heavy categoricals.** CatBoost `task_type="GPU"` first. If >50M rows AND boosting plateaus, try a tabular Transformer (SAINT, FT-Transformer). In HFT you can usually downsample / debias before that.
- **E.3 Sequence data, short horizon (≤30 steps).** LSTM + attention head, or small Transformer encoder (2–4 layers). Gap is small; pick what your team maintains.
- **E.4 Sequence data, long context (>1000 steps).** Linear-attention Transformer (Performer / Linformer) or state-space model (S4 / Mamba). Skip vanilla O(n²) attention. Mamba is plausibly the right inductive bias for HFT but evidence is thin. *Unverified for HFT.*
- **E.5 Image-encoded charts.** Small ResNet (ResNet-18, ImageNet pretrain, finetune last block) on 224×224 candle/volume renders. Or a Conv1D-on-features → Conv2D-on-image hybrid. **Cross-link `cnn-pattern-recognition`.**
- **E.6 Multi-modal (price + news + on-chain).** Per-modality encoders (Transformer for price, pretrained LM for news, MLP for on-chain), late-fusion into a shared head. Train with modality-dropout (randomly zero one modality) to prevent collapse.
- **E.7 High noise → low signal.** Denoise with wavelet (cross-link `wavelet-decomposition`) before training. Stronger `weight_decay` (`1e-3` start), higher dropout, label smoothing. If SNR < 1 no architecture saves you — improve features.
- **E.8 Class imbalance (rare events).** Priority order: (1) probability-threshold tuning over a fine grid; (2) `class_weight={0:1, 1:imbalance_ratio}`; (3) focal loss (`α=0.25, γ=2.0`, Lin 2017); (4) SMOTE on train only. Do **not** undersample majority — you discard information.
- **E.9 Regime breaks.** Either per-regime models (cross-link `markov-regime-detection` for the gating model) or a single model with regime appended as a one-hot. Single-model usually wins on data efficiency; per-regime wins when regimes are economically distinct.
- **E.10 RL when action affects market.** Only when your action changes the next state (large orders moving the book, market-making fills). Otherwise supervised alpha + sizing rule dominates with less training instability. **Cross-link `deep-q-learning`, `policy-gradients`.**

## Section F — When to apply deep learning (decision tree)

Walk this in order. Stop at the first **No** that disqualifies deep learning.

```
Q1. Do you have ≥100K labelled rows?
    No  → boosting (XGBoost / LightGBM / CatBoost). Stop.
    Yes → Q2.

Q2. Does sequence / spatial structure matter for the prediction?
    (i.e., would shuffling row order destroy the signal?)
    No  → boosting will dominate. Borisov 2022 / Shwartz-Ziv 2021. Stop.
    Yes → Q3.

Q3. Do you have GPU budget for both initial training AND a retrain cycle?
    (Retraining on stale models is the #1 killer of HFT DL in production.)
    No  → boosting on CPU. Stop.
    Yes → Q4.

Q4. Is interpretability a release requirement?
    (Risk team needs SHAP attributions, counterfactuals, monotonicity constraints.)
    Yes → boosting + SHAP, OR deep model wrapped in SHAP DeepExplainer + counterfactual
          notebooks. Add ~2 weeks of work and a tighter MRM review. Proceed only if
          the deep model has a quantified accuracy gap over boosting that justifies the cost.
    No  → Q5.

Q5. Is your label noisy at the per-sample level?
    (Per-tick noise typically >> than your alpha signal.)
    Yes → use boosting with regularization, or a deep model with heavy weight decay +
          label smoothing + Mixup-style data augmentation. Increased risk of overfitting.
    No  → Q6.

Q6. Do you need to combine modalities (price + book + news + sentiment + macro)?
    Yes → deep multi-modal architecture is the right choice (Section E.6).
    No  → Q7.

Q7. Is your effective context length >1000 steps AND the dependency is non-Markovian?
    (i.e., 30-step LSTM truly cannot capture the signal.)
    Yes → Transformer / linear-attention / SSM. Section E.4.
    No  → small LSTM or just engineered lag features into boosting wins.

Q8. Have you already exhausted feature engineering on a boosting baseline?
    (You can recite the top-10 SHAP features and tell a microstructure story for each.)
    Yes → deep learning is the next legitimate experiment.
    No  → go back to features. Boosting + features is almost always the right answer.
```

**Fact** (cited): Borisov et al. (2022) "Deep Neural Networks and Tabular Data: A Survey" (TNNLS) finds gradient-boosted decision trees outperform deep tabular models on most benchmark datasets. Shwartz-Ziv & Armon (2021) "Tabular Data: Deep Learning Is Not All You Need" (NeurIPS workshop) reaches the same conclusion across 11 datasets.

**Recommendation** (opinionated): in 5+ years of HFT work, the single most common failure mode is "we trained a fancy Transformer because we had GPUs" rather than "we asked whether a boosted tree on better features would have been enough". Default to boosting. Earn the right to use deep learning.
