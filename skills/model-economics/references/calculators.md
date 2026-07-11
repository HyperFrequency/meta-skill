# Calculators

Plain-Python cost math — no dependencies. Copy, plug in *your* measured numbers (see
`references/pricing-tables.md` for anchors), and read the result critically against the
failure modes in `references/decision-framework.md`.

---

## 1. Self-hosted inference cost per million tokens

```python
def inference_cost_per_million_tokens(gpu_cost_per_hour: float, tokens_per_second: float) -> float:
    """Cost to serve 1M tokens on a self-hosted GPU.

    Args:
        gpu_cost_per_hour: Rental/reservation cost of the GPU(s), e.g. 3.25 for one H100.
                           For multi-GPU serving, pass the summed hourly cost.
        tokens_per_second: MEASURED aggregate throughput for your model at your batch
                           profile. Use a real benchmark, not a vendor headline number.

    Returns:
        Dollars per 1,000,000 tokens, assuming the GPU is ~100% utilized.
        Divide realism in: at 50% utilization the true cost is ~2x this.
    """
    tokens_per_hour = tokens_per_second * 3600
    cost_per_token = gpu_cost_per_hour / tokens_per_hour
    return cost_per_token * 1_000_000
```

The `~100% utilized` assumption is the biggest lie in most build-vs-buy decks. A dedicated
GPU billed 24/7 but only busy 30% of the time costs ~3x the number this returns. Serverless
(scale-to-zero) billing sidesteps this at the price of cold-start latency.

---

## 2. Break-even analysis (the core deliverable)

```python
def break_even_analysis(
    monthly_api_spend: float,      # current frontier bill for the task you'd replace
    training_cost: float,          # one-time: GPU/managed training + data prep
    monthly_inference_cost: float, # ongoing cost to serve the specialist (incl. idle time)
    setup_hours: float = 40,       # engineering time to stand up the pipeline
    hourly_rate: float = 100,      # fully-loaded engineering cost per hour
    monthly_maintenance_hours: float = 0,  # ongoing eng time (retrain, monitoring, drift)
) -> dict:
    """Months until a specialized model pays back its upfront cost.

    All 'monthly' figures should describe the SAME traffic volume so the comparison is
    apples-to-apples. If traffic grows, re-run with the projected volume.
    """
    engineering_cost = setup_hours * hourly_rate
    total_upfront = training_cost + engineering_cost
    monthly_maintenance_cost = monthly_maintenance_hours * hourly_rate
    monthly_savings = monthly_api_spend - monthly_inference_cost - monthly_maintenance_cost

    if monthly_savings <= 0:
        return {
            "viable": False,
            "reason": "Specialist costs more per month than the API it replaces",
            "monthly_savings": monthly_savings,
        }

    months_to_break_even = total_upfront / monthly_savings
    return {
        "viable": True,
        "total_upfront_cost": total_upfront,
        "training_cost": training_cost,
        "engineering_cost": engineering_cost,
        "monthly_api_spend": monthly_api_spend,
        "monthly_inference_cost": monthly_inference_cost,
        "monthly_maintenance_cost": monthly_maintenance_cost,
        "monthly_savings": monthly_savings,
        "months_to_break_even": round(months_to_break_even, 1),
        "year_1_net_savings": monthly_savings * 12 - total_upfront,
        "year_2_savings": monthly_savings * 12,  # upfront already amortized
    }
```

> Note: `monthly_maintenance_hours` is the one line most cost models omit and most projects
> pay for. Specialists drift; budget for periodic retrains and monitoring from day one.

### Worked example — replacing a standard-tier API for one narrow task

```python
result = break_even_analysis(
    monthly_api_spend=5000,        # $5K/month on a standard-tier model for this task
    training_cost=500,             # $500: 8B LoRA fine-tune + data prep
    monthly_inference_cost=200,    # $200/month serving an 8B on serverless GPU
    setup_hours=40,                # ~1 week of engineering
    hourly_rate=100,
    monthly_maintenance_hours=4,   # ~half a day/month of upkeep
)
# monthly_savings = 5000 - 200 - 400 = 4400
# total_upfront   = 500 + 4000 = 4500
# months_to_break_even ≈ 1.0
# year_1_net_savings ≈ 48,300
```

Without the maintenance line the same case shows ~$52K year-1 savings; the $400/month of
upkeep is exactly the kind of cost that quietly erases a thin margin at low volume.

---

## 3. ROI timeline template

Once `break_even_analysis` returns `viable: True`, lay the cash flow out month by month so
stakeholders see the crossover. Fill from your own numbers:

| Month | Frontier cost | Specialist cost | Cumulative savings | Notes |
|-------|---------------|-----------------|--------------------|-------|
| 0  | —      | 4,500 upfront | −4,500 | Training + engineering |
| 1  | 5,000  | 600           | −100   | First month live (incl. upkeep) |
| 2  | 5,000  | 600           | +4,300 | Break-even crossed |
| 3  | 5,000  | 600           | +8,700 | |
| 6  | 5,000  | 600           | +21,900 | |
| 12 | 5,000  | 900           | +47,700 | Includes a retrain |

Always show at least one retrain in the 12-month row so the timeline is not artificially
rosy.

---

## 4. Sensitivity check (do this before presenting)

A single break-even number hides risk. Re-run the analysis at:
- **0.5x and 2x traffic** — does break-even survive if volume is half your guess?
- **Frontier price −30%** — the frontier is a moving target and trends cheaper; if a price
  cut kills your ROI, the case is fragile.
- **Setup hours ×2** — engineering estimates are optimistic; double them and re-check.
- **Utilization 100% → 40%** on `monthly_inference_cost` for dedicated GPUs.

If break-even holds (say, under ~6–9 months) across all four, the case is robust. If it only
works at your rosiest assumptions, treat it as "not yet."
