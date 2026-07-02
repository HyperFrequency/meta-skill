# Mamba usage examples

Runnable examples for the `mamba-ssm` package. Assumes Linux + NVIDIA GPU,
PyTorch 1.12+, CUDA 11.6+, and `pip install mamba-ssm[causal-conv1d]`.

## 1. Language model with Mamba-2 (build + generate)

```python
from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel
from mamba_ssm.models.config_mamba import MambaConfig
import torch

config = MambaConfig(
    d_model=1024,           # Hidden dimension
    n_layer=24,             # Number of layers
    vocab_size=50277,       # Vocabulary size
    ssm_cfg=dict(
        layer="Mamba2",     # Use Mamba-2 mixer
        d_state=128,        # Larger state for Mamba-2
        headdim=64,         # Head dimension
        ngroups=1           # Number of groups
    )
)

model = MambaLMHeadModel(config, device="cuda", dtype=torch.float16)

input_ids = torch.randint(0, 1000, (1, 20), device="cuda", dtype=torch.long)
output = model.generate(
    input_ids=input_ids,
    max_length=100,
    temperature=0.7,
    top_p=0.9,
)
```

## 2. Use pretrained Mamba models

Load with `MambaLMHeadModel.from_pretrained` (not HF `AutoModel`):

```python
from transformers import AutoTokenizer
from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel

model_name = "state-spaces/mamba-2.8b"
# state-spaces models use the GPT-NeoX tokenizer
tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-neox-20b")
model = MambaLMHeadModel.from_pretrained(model_name, device="cuda", dtype=torch.float16)

prompt = "The future of AI is"
input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to("cuda")
output_ids = model.generate(
    input_ids=input_ids,
    max_length=200,
    temperature=0.7,
    top_p=0.9,
    repetition_penalty=1.2,
)
print(tokenizer.decode(output_ids[0]))
```

Available pretrained models: `state-spaces/mamba-130m`, `-370m`, `-790m`,
`-1.4b`, `-2.8b`.

## 3. Mamba-1 vs Mamba-2 block

**Mamba-1** (smaller state):
```python
from mamba_ssm import Mamba

model = Mamba(
    d_model=256,
    d_state=16,      # Smaller state dimension
    d_conv=4,
    expand=2,
).to("cuda")
```

**Mamba-2** (multi-head, larger state):
```python
from mamba_ssm import Mamba2

model = Mamba2(
    d_model=256,
    d_state=128,     # Larger state dimension
    d_conv=4,
    expand=2,
    headdim=64,      # Head dimension for multi-head
    ngroups=1,       # Parallel groups
).to("cuda")
```

**Key differences**:
- **State size**: Mamba-1 (d_state=16) vs Mamba-2 (d_state=128)
- **Architecture**: Mamba-2 has a multi-head structure
- **Normalization**: Mamba-2 uses RMSNorm
- **Distributed**: Mamba-2 supports tensor parallelism

See [architecture-details.md](architecture-details.md) for the underlying S6
mechanism and [training-guide.md](training-guide.md) for training loops.
