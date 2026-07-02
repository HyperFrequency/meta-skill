# Pitfalls, production, and diagnostics

## Common pitfalls

1. **Training on contaminated data.** AEs are unsupervised but assume the train set is *mostly* normal. If 30% of your "training" rows are anomalies, the AE learns to reconstruct them too. Either (a) pre-filter with a cheap detector first, or (b) set `contamination` honestly so PyOD's loss / threshold handle it.
2. **Latent dim too large.** A latent of 16 on a 20-dim feature matrix is basically an identity function. Reconstruction error becomes constant → no signal. Rule of thumb: `latent ≤ d_in / 4`.
3. **Scale mismatch.** Mixing raw price ($100) with log-return (1e-3) in the same feature row — the AE will only "see" the big-magnitude features. Always standardise; PyOD's `preprocessing=True` does this internally, hand-rolled code does not.
4. **Threshold drift.** A fixed threshold from training data goes stale as volatility changes. Recompute the threshold on a rolling window of recent scores (e.g. `np.quantile(recent_scores, 0.95)`).
5. **Non-stationarity = constant false positives.** A regime change isn't an anomaly per row — but per row, every row in the new regime looks anomalous. Use a rolling retrain or an explicit regime model (HMM, change-point detector) on top.
6. **Evaluating on synthetic anomalies you injected.** AE trivially detects "add a huge spike to one row". Evaluate on real labeled events (flash crashes, halts) or by precision-at-k.

## Scaling to production

- **Streaming scoring.** Once a PyOD AE is fit, calling `decision_function` per new row is fine for low-frequency signals (every minute). For high-frequency, pre-load the underlying `clf.model_` and call it directly with a torch tensor — avoids PyOD's scaler refit overhead.
- **Rolling retrain cadence.** Anomaly definitions drift. Retrain on the last 30-60 days of "normal" data daily or weekly. Keep a small held-out clean window as a regression check.
- **Score calibration.** Raw recon errors are not comparable across retrains because the AE re-initialises. Always re-derive the threshold from the new train set's score distribution; do not carry a hard-coded threshold across retrains.
- **Two-stage filters.** Use the AE as a *recall-heavy* first stage (low threshold, many flags), then run a slower expensive model (LLM, human, hand-crafted rule) on the flags. AEs are great gates, mediocre final classifiers.
- **Persistence.** PyOD models pickle cleanly: `joblib.dump(clf, "ae.pkl")`. For the underlying torch model, save `state_dict` separately if you want to deploy without the PyOD wrapper.

## Diagnostics — AE flags everything (or nothing)

Order of investigation:

1. Plot per-row recon error on the train set: it should be a tight distribution with a thin right tail. If it's bimodal, the train set is contaminated.
2. Confirm preprocessing actually ran (`preprocessing=True`): print `clf.scaler_.mean_` and check it isn't all zeros.
3. Reduce `latent_dim` aggressively (set to 2). If the AE still reconstructs perfectly, your features carry no information; if it now flags everything sensibly, latent was too large.
4. Compare against `IsolationForest` as a baseline. If IF beats the AE by a wide margin, the AE is mis-specified — usually wrong loss or wrong scale.
