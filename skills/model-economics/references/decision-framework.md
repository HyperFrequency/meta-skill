# Decision Framework, Failure Modes & Intake Questions

Use this after the calculators return a number. A viable break-even is necessary but not
sufficient — the qualitative fit and the failure modes below decide whether the number is
trustworthy.

---

## Intake questions (ask before estimating)

1. **Monthly frontier spend on the task you'd replace?**
   - `< $500/mo` → probably not worth it; the upfront cost dominates.
   - `$500–2K/mo` → worth investigating.
   - `$2K+/mo` → strong candidate.
   - `$10K+/mo` → almost certainly worth it.
2. **How constrained is the task?**
   - Single narrow task (classification, extraction, formatting, canned domain Q&A) → great fit.
   - A few related tasks → good fit.
   - Many diverse, open-ended tasks (general assistant) → hard to specialize; stay on the API.
3. **What production data do you have?**
   - Logs *with* user feedback / accept-reject signals → excellent (train directly).
   - Logs *without* feedback → good; distill the frontier model's outputs.
   - No production data → you need a synthetic bootstrap first; add that cost and risk.
4. **What is the quality bar?**
   - Must match the frontier exactly → harder; may need a larger student or hybrid routing.
   - ~90% of frontier quality is acceptable → an 8B LoRA is often enough.
   - Task-specific metric (accuracy, valid-format rate) → easiest to hit and to prove.

---

## Strong case for specialization
- Monthly API spend > $1,000 on the target task.
- Constrained, stable task that does not change every week.
- Production data available to train or distill from.
- Quality requirements are well-defined and measurable.

## Weak case (stay on the API)
- Monthly spend < $500, or highly bursty/uncertain volume.
- Diverse, open-ended, or frontier-reasoning-dependent tasks.
- No production data and no cheap way to generate it.
- Rapid task churn, or you expect an imminent frontier release to reset the baseline.
- No ML-engineering capacity to own retrains and monitoring.

## Hybrid routing (often the best answer)
Route by difficulty instead of choosing one model for everything:
- ~90% of requests → cheap specialist (fast, ~$0.05–0.15/M).
- ~10% of requests → frontier fallback (novel, complex, high-stakes).
- Result: **80–90% cost reduction** while preserving frontier quality on the hard tail.

Cost it as a blend: `blended_cost = 0.9 * specialist_cost + 0.1 * frontier_cost`, plus a
router (a cheap classifier or a confidence threshold on the specialist). The router itself
has a cost and an error rate — mis-routed hard cases hit the specialist and degrade quality,
so measure router accuracy, not just the blend price.

---

## Failure modes that erase the savings

- **Utilization gap.** Self-hosted $/M assumes a full GPU. Bursty traffic on a *dedicated*
  GPU can run 20–40% utilized → real cost 2.5–5x the headline. Fix: use serverless
  (scale-to-zero) billing, or size the reservation to sustained (not peak) load, or batch.
- **Throughput never materializes.** The tokens/sec anchors are *batched* aggregates. At low
  concurrency you get a fraction of them, so $/M rises. Measure at *your* real concurrency.
- **Retrain / drift treadmill.** Data and task distributions shift; a specialist decays.
  Budget periodic retrains + eval as recurring cost (the `monthly_maintenance_hours` input).
- **Frontier price cuts.** The frontier trends cheaper and better over time. A case that only
  breaks even against today's price is fragile — stress-test at frontier −30% (see the
  sensitivity check in `references/calculators.md`).
- **Engineering underestimate.** "One week to set up" is almost always 2–3x. Serving infra,
  eval harness, data pipeline, and on-call all count. Double the estimate and re-check.
- **Quality regression cost.** A cheaper model that is subtly worse can cost more than it
  saves (support load, churn, bad outputs). Gate the switch on an eval (see the
  `lm-evaluation-harness` sibling) and keep the frontier fallback wired in.
- **Latency SLA.** Cold starts on serverless and queueing under load can miss a latency SLO
  the API met effortlessly. If latency is contractual, price the always-warm capacity.
- **Fixed minimums.** Reserved GPUs, managed endpoints, and some serverless plans bill a
  floor regardless of traffic — at low volume the floor, not the per-token rate, dominates.

---

## Boundaries — where this framework stops
This is the *economics* layer only. It does not:
- Train the model — hand off to `peft`, `unsloth`, `trl-fine-tuning`, `axolotl`,
  `llama-factory`, or `ml-training-recipes`; distillation to `knowledge-distillation`.
- Serve the model — hand off to `vllm`, `sglang`, `tensorrt-llm`, or `llama-cpp`.
- Provision GPUs — hand off to `modal`, `lambda-labs`, or `skypilot`.
- Measure quality — hand off to `lm-evaluation-harness` or `judge-panel`.

Produce the cost/ROI verdict here; delegate execution to those siblings.
