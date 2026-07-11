# Loss Functions

Pass the loss name as a string to `forward_backward(data, loss_fn=...)`. All losses are token-level
with shape `(N,)`, use **sum** reduction, and accept numpy or torch inputs.

## cross_entropy (supervised)

Standard next-token prediction, `L(θ) = −E_x[log p_θ(x)]`.

- Inputs: `target_tokens` `(N,) int`, `weights` `(N,) float` (0 = ignore, 1 = train).
- Outputs: `logprobs` `(N,) float`, `loss:sum` scalar.

```python
elementwise_loss = -target_logprobs * weights
loss = elementwise_loss.sum()
```

## Policy-gradient losses

All three take the same inputs: `target_tokens`, `logprobs` (the sampling logprobs from `q`), and
`advantages`.

### importance_sampling
`L = E_{x~q}[ (p_θ(x)/q(x)) · A(x) ]` — policy gradient with off-policy correction.
```python
prob_ratio = torch.exp(target_logprobs - sampling_logprobs)
loss = -(prob_ratio * advantages).sum()
```

### ppo
Clipped surrogate objective. Config: `clip_low_threshold`, `clip_high_threshold`.
```python
fwd_bwd = training_client.forward_backward(
    data, loss_fn="ppo", loss_fn_config={"clip_low_threshold": 0.9, "clip_high_threshold": 1.1})
```
```python
prob_ratio    = torch.exp(target_logprobs - sampling_logprobs)
clipped_ratio = torch.clamp(prob_ratio, 1 - eps, 1 + eps)
loss = -torch.min(prob_ratio * advantages, clipped_ratio * advantages).sum()
```

### cispo
Clipped importance sampling PO — stops gradient through the clipped ratio.
```python
fwd_bwd = training_client.forward_backward(
    data, loss_fn="cispo", loss_fn_config={"clip_low_threshold": 0.8, "clip_high_threshold": 1.2})
```
```python
prob_ratio    = torch.exp(target_logprobs - sampling_logprobs)
clipped_ratio = torch.clamp(prob_ratio, 1 - eps, 1 + eps)
loss = -(clipped_ratio.detach() * target_logprobs * advantages).sum()
```

### dro
Direct reward optimization with a quadratic KL-like penalty. Config: `beta`.
```python
fwd_bwd = training_client.forward_backward(data, loss_fn="dro", loss_fn_config={"beta": 0.05})
```
```python
quadratic = (target_logprobs - sampling_logprobs) ** 2
loss = -(target_logprobs * advantages - 0.5 * beta * quadratic).sum()
```

## Custom losses

For anything not covered, `forward_backward_custom` runs a Python loss over the forward-pass
logprobs. Costs ~1.5× FLOPs and up to 3× wall time (it does a forward, your `loss.backward()`, then a
second forward with a linear surrogate loss).

```python
def custom_loss(data: list[Datum], logprobs: list[torch.Tensor]) -> tuple[torch.Tensor, dict]:
    loss = (torch.cat(logprobs) ** 2).sum()
    return loss, {"custom_loss": loss.item()}

loss, metrics = training_client.forward_backward_custom(data, custom_loss)
```

## Notes

- Token-level losses are summed; to change aggregation, scale the `advantages` yourself.
- Put KL regularization in the **reward**, not the loss.
- PPO reference: Schulman et al., 2017 (https://arxiv.org/abs/1707.06347).
