# pyvene Workflows

End-to-end recipes for the most common intervention experiments. For shorter,
single-concept walkthroughs see [tutorials.md](tutorials.md); for the class/method
surface see [api.md](api.md).

## Workflow 1: Causal Tracing (ROME-style)

Locate where factual associations are stored by corrupting inputs and restoring
activations.

```python
import pyvene as pv
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained("gpt2-xl")
tokenizer = AutoTokenizer.from_pretrained("gpt2-xl")

# 1. Define clean and corrupted inputs
clean_prompt = "The Space Needle is in downtown"
corrupted_prompt = "The ##### ###### ## ## ########"  # Noise

clean_tokens = tokenizer(clean_prompt, return_tensors="pt")
corrupted_tokens = tokenizer(corrupted_prompt, return_tensors="pt")

# 2. Get clean activations (source)
with torch.no_grad():
    clean_outputs = model(**clean_tokens, output_hidden_states=True)
    clean_states = clean_outputs.hidden_states

# 3. Define restoration intervention
def run_causal_trace(layer, position):
    """Restore clean activation at specific layer and position."""
    config = pv.IntervenableConfig(
        representations=[
            pv.RepresentationConfig(
                layer=layer,
                component="block_output",
                intervention_type=pv.VanillaIntervention,
                unit="pos",
                max_number_of_units=1,
            )
        ]
    )

    intervenable = pv.IntervenableModel(config, model)

    # Run with intervention
    _, patched_outputs = intervenable(
        base=corrupted_tokens,
        sources=[clean_tokens],
        unit_locations={"sources->base": ([[[position]]], [[[position]]])},
        output_original_output=True,
    )

    # Return probability of correct token
    probs = torch.softmax(patched_outputs.logits[0, -1], dim=-1)
    seattle_token = tokenizer.encode(" Seattle")[0]
    return probs[seattle_token].item()

# 4. Sweep over layers and positions
n_layers = model.config.n_layer
seq_len = clean_tokens["input_ids"].shape[1]

results = torch.zeros(n_layers, seq_len)
for layer in range(n_layers):
    for pos in range(seq_len):
        results[layer, pos] = run_causal_trace(layer, pos)

# 5. Visualize (layer x position heatmap)
# High values indicate causal importance
```

### Checklist
- [ ] Prepare clean prompt with target factual association
- [ ] Create corrupted version (noise or counterfactual)
- [ ] Define intervention config for each (layer, position)
- [ ] Run patching sweep
- [ ] Identify causal hotspots in heatmap

## Workflow 2: Activation Patching for Circuit Analysis

Test which components are necessary for a specific behavior.

```python
import pyvene as pv
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# IOI task setup
clean_prompt = "When John and Mary went to the store, Mary gave a bottle to"
corrupted_prompt = "When John and Mary went to the store, John gave a bottle to"

clean_tokens = tokenizer(clean_prompt, return_tensors="pt")
corrupted_tokens = tokenizer(corrupted_prompt, return_tensors="pt")

john_token = tokenizer.encode(" John")[0]
mary_token = tokenizer.encode(" Mary")[0]

def logit_diff(logits):
    """IO - S logit difference."""
    return logits[0, -1, john_token] - logits[0, -1, mary_token]

# Patch attention output at each layer
def patch_attention(layer):
    config = pv.IntervenableConfig(
        representations=[
            pv.RepresentationConfig(
                layer=layer,
                component="attention_output",
                intervention_type=pv.VanillaIntervention,
            )
        ]
    )

    intervenable = pv.IntervenableModel(config, model)

    _, patched_outputs = intervenable(
        base=corrupted_tokens,
        sources=[clean_tokens],
    )

    return logit_diff(patched_outputs.logits).item()

# Find which layers matter
results = []
for layer in range(model.config.n_layer):
    diff = patch_attention(layer)
    results.append(diff)
    print(f"Layer {layer}: logit diff = {diff:.3f}")
```

## Workflow 3: Interchange Intervention Training (IIT) and DAS

Train interventions to discover causal structure.

```python
import pyvene as pv
from transformers import AutoModelForCausalLM
import torch

model = AutoModelForCausalLM.from_pretrained("gpt2")

# 1. Define trainable intervention
config = pv.IntervenableConfig(
    representations=[
        pv.RepresentationConfig(
            layer=6,
            component="block_output",
            intervention_type=pv.RotatedSpaceIntervention,  # Trainable
            low_rank_dimension=64,  # Learn 64-dim subspace
        )
    ]
)

intervenable = pv.IntervenableModel(config, model)

# 2. Set up training
optimizer = torch.optim.Adam(
    intervenable.get_trainable_parameters(),
    lr=1e-4
)

# 3. Training loop (simplified)
for base_input, source_input, target_output in dataloader:
    optimizer.zero_grad()

    _, outputs = intervenable(
        base=base_input,
        sources=[source_input],
    )

    loss = criterion(outputs.logits, target_output)
    loss.backward()
    optimizer.step()

# 4. Analyze learned intervention
# The rotation matrix reveals causal subspace
rotation = intervenable.interventions["layer.6.block_output"][0].rotate_layer
```

### DAS (Distributed Alignment Search)

```python
# Low-rank rotation finds interpretable subspaces
config = pv.IntervenableConfig(
    representations=[
        pv.RepresentationConfig(
            layer=8,
            component="block_output",
            intervention_type=pv.LowRankRotatedSpaceIntervention,
            low_rank_dimension=1,  # Find 1D causal direction
        )
    ]
)
```

## Workflow 4: Model Steering (Honest LLaMA)

Steer model behavior during generation using a pre-trained intervention.

```python
import pyvene as pv
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

# Load pre-trained steering intervention
intervenable = pv.IntervenableModel.load(
    "zhengxuanzenwu/intervenable_honest_llama2_chat_7B",
    model=model,
)

# Generate with steering
prompt = "Is the earth flat?"
inputs = tokenizer(prompt, return_tensors="pt")

# Intervention applied during generation
outputs = intervenable.generate(
    inputs,
    max_new_tokens=100,
    do_sample=False,
)

print(tokenizer.decode(outputs[0]))
```

## Saving and Sharing Interventions

```python
# Save locally
intervenable.save("./my_intervention")

# Load from local
intervenable = pv.IntervenableModel.load(
    "./my_intervention",
    model=model,
)

# Share on HuggingFace
intervenable.save_intervention("username/my-intervention")

# Load from HuggingFace
intervenable = pv.IntervenableModel.load(
    "username/my-intervention",
    model=model,
)
```
