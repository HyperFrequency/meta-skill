# Training Insights, Monitoring & Troubleshooting

## 1. Loss Behavior (EXPECTED PATTERN)
- **Loss starts near 0 and INCREASES during training.**
- This is CORRECT — loss measures KL divergence from the initial policy.
- The model is learning (diverging from original behavior to optimize rewards).
- Monitor reward metrics instead of loss for progress.

## 2. Reward Tracking
Key metrics to watch:
- `reward`: Average across all completions.
- `reward_std`: Diversity within groups (should remain > 0).
- `kl`: KL divergence from reference (should grow moderately).

**Healthy Training Pattern:**
```
Step   Reward    Reward_Std   KL
100    0.5       0.3          0.02
200    0.8       0.25         0.05
300    1.2       0.2          0.08  ← Good progression
400    1.5       0.15         0.12
```

**Warning Signs:**
- Reward std → 0 (model collapsing to a single response).
- KL exploding (> 0.5) (diverging too much — reduce LR).
- Reward stuck (reward functions too harsh or model-capacity issue).

## 3. Common Pitfalls and Solutions

| Problem | Symptom | Solution |
|---------|---------|----------|
| **Mode collapse** | All completions identical | Increase `num_generations`, add diversity penalty |
| **No learning** | Flat rewards | Check reward function logic, increase LR |
| **OOM errors** | GPU memory exceeded | Reduce `num_generations`, enable gradient checkpointing |
| **Slow training** | < 1 it/s | Enable `use_vllm=True`, use Unsloth, reduce seq length |
| **Format ignored** | Model doesn't follow structure | Increase format reward weight, add incremental rewards |

## Debugging Workflow
1. **Isolate reward functions** — test each independently.
2. **Check data distribution** — ensure diversity in prompts.
3. **Reduce complexity** — start with a single reward, add gradually.
4. **Monitor generations** — print samples every N steps.
5. **Validate extraction logic** — ensure answer parsing works.

### Quick Fixes
```python
# Debug reward function: prints samples, returns dummy rewards
def debug_reward(completions, **kwargs):
    responses = [comp[0]['content'] for comp in completions]
    for i, r in enumerate(responses[:2]):
        print(f"Response {i}: {r[:200]}...")
    return [1.0] * len(responses)

# Test generation without updating the policy
trainer = GRPOTrainer(..., reward_funcs=[debug_reward])
trainer.generate_completions(dataset[:1])
```

## Best Practices Checklist

**Before Training:**
- [ ] Validate dataset format (prompts as `List[Dict]`).
- [ ] Test reward functions on sample data.
- [ ] Calculate expected `max_prompt_length` from data.
- [ ] Choose `num_generations` based on GPU memory.
- [ ] Set up logging (wandb/trackio recommended).

**During Training:**
- [ ] Monitor reward progression (should increase).
- [ ] Check `reward_std` (should stay > 0.1).
- [ ] Watch for OOM errors (reduce batch size if needed).
- [ ] Sample generations every 50-100 steps.
- [ ] Validate format compliance on a holdout set.

**After Training:**
- [ ] Merge LoRA weights if using PEFT.
- [ ] Test on diverse prompts.
- [ ] Compare to baseline model.
- [ ] Document reward weights and hyperparameters.
- [ ] Save reproducibility config.
