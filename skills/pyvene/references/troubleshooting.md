# pyvene Troubleshooting

Common failure modes when configuring and running interventions.

## Issue: Wrong intervention location

```python
# WRONG: Incorrect component name
config = pv.RepresentationConfig(
    component="mlp",  # Not valid!
)

# RIGHT: Use exact component name
config = pv.RepresentationConfig(
    component="mlp_output",  # Valid
)
```

See the component list in `SKILL.md` ("Component Targets") for the full set of
valid names.

## Issue: Dimension mismatch

```python
# Ensure source and base have compatible shapes
# For position-specific interventions:
config = pv.RepresentationConfig(
    unit="pos",
    max_number_of_units=1,  # Intervene on single position
)

# Specify locations explicitly
intervenable(
    base=base_tokens,
    sources=[source_tokens],
    unit_locations={"sources->base": ([[[5]]], [[[5]]])},  # Position 5
)
```

## Issue: Memory with large models

```python
# Use gradient checkpointing
model.gradient_checkpointing_enable()

# Or intervene on fewer components
config = pv.IntervenableConfig(
    representations=[
        pv.RepresentationConfig(
            layer=8,  # Single layer instead of all
            component="block_output",
        )
    ]
)
```

## Issue: LoRA integration

```python
# pyvene v0.1.8+ supports LoRAs as interventions
config = pv.RepresentationConfig(
    intervention_type=pv.LoRAIntervention,
    low_rank_dimension=16,
)
```
