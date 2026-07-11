# Hypogenic Usage Reference

Source: https://github.com/ChicagoHAI/hypothesis-generation (PyPI: `hypogenic`, MIT).

## Installation

The upstream README recommends a conda env on Python 3.10:

```bash
conda create --name hypogenic python=3.10
conda activate hypogenic
pip install hypogenic          # API-based models only
```

For local models / development, install from source instead:

```bash
git clone https://github.com/ChicagoHAI/hypothesis-generation.git
cd hypothesis-generation
pip install -e ".[dev]"        # local models + dev features
# Literature processing (HypoRefine/Union) also needs s2orc-doc2json:
pip install git+https://github.com/allenai/s2orc-doc2json@71c022ed4bed3ffc71d22c2ac5cdbc133ad04e3c
```

**Optional Redis cache:** caches prompt/response pairs to cut API cost. Default port is **6832** (override with `--port`). Build Redis from source per the upstream README.

**Example datasets:**
```bash
git clone https://github.com/ChicagoHAI/HypoGeniC-datasets.git ./data           # data-driven
git clone https://github.com/ChicagoHAI/Hypothesis-agent-datasets.git ./data    # literature + data
# Full benchmark datasets: https://github.com/ChicagoHAI/HypoBench-datasets
```

## CLI

```bash
hypogenic_generation --help     # generate a hypothesis bank
hypogenic_inference --help      # run inference on a hypothesis bank
```
Note: upstream states CLI support for *new* tasks/datasets will arrive in a later release; for custom tasks, adapt the example scripts below.

## Python API (real API as of the example scripts)

> IMPORTANT: there is no `hypogenic.BaseTask(...).generate_hypotheses(...)` / `.inference(...)`
> convenience API. The actual workflow wires together explicit algorithm classes.

Key imports:
```python
from hypogenic.tasks import BaseTask
from hypogenic.prompt import BasePrompt
from hypogenic.utils import set_seed
from hypogenic.extract_label import extract_label_register
from hypogenic.LLM_wrapper import llm_wrapper_register
from hypogenic.algorithm.summary_information import SummaryInformation
from hypogenic.algorithm.generation import DefaultGeneration
from hypogenic.algorithm.inference import (
    DefaultInference, OneStepAdaptiveInference,
    FilterAndWeightInference, TwoStepAdaptiveInference, UpperboundInference,
)
from hypogenic.algorithm.replace import DefaultReplace
from hypogenic.algorithm.update import DefaultUpdate, SamplingUpdate
```

### Generation (adapted from `examples/generation.py`)
```python
api = llm_wrapper_register.build(model_type)(model=model_name, path_name=model_path)
# For existing tasks (shoe, hotel_reviews, retweet, headline_binary) use the register;
# for a new task pass your own extract_label= function instead.
task = BaseTask(task_config_path, extract_label=None, from_register=extract_label_register)

set_seed(seed)
train_data, _, _ = task.get_data(num_train, num_test, num_val, seed)
prompt_class = BasePrompt(task)
inference_class = DefaultInference(api, prompt_class, train_data, task)
generation_class = DefaultGeneration(api, prompt_class, inference_class, task)

update_class = DefaultUpdate(
    generation_class=generation_class,
    inference_class=inference_class,
    replace_class=DefaultReplace(max_num_hypotheses),
    save_path=output_folder,
    num_init=num_init, k=k, alpha=alpha,
    update_batch_size=update_batch_size,
    num_hypotheses_to_update=num_hypotheses_to_update,
    save_every_n_examples=save_every_10_examples,
)

hypotheses_bank = update_class.batched_initialize_hypotheses(
    num_init, init_batch_size=init_batch_size,
    init_hypotheses_per_batch=init_hypotheses_per_batch,
    cache_seed=cache_seed, temperature=temperature, max_tokens=max_tokens,
)
hypotheses_bank = update_class.update(
    current_epoch=0, hypotheses_bank=hypotheses_bank,
    current_seed=seed, cache_seed=cache_seed,
)
update_class.save_to_json(hypotheses_bank, sample="final", seed=seed, epoch=0)
```

### Inference (adapted from `examples/inference.py`)
```python
# inference_type options: default, filter_and_weight, one_step_adaptive, two_step_adaptive
hyp_bank = {h: SummaryInformation.from_dict(d) for h, d in load_dict(hypothesis_file).items()}
api = llm_wrapper_register.build(model_type)(model=model_name, path_name=model_path)

set_seed(seed)
train_data, test_data, val_data = task.get_data(num_train, num_test, num_val, seed)
prompt_class = BasePrompt(task)
inference_class = inference_register.build(inference_type)(api, prompt_class, train_data, task)

pred_list, label_list = inference_class.run_inference_final(
    test_data, hyp_bank,
    adaptive_num_hypotheses=adaptive_num_hypotheses,
    cache_seed=cache_seed, max_concurrent=max_concurrent,
    generate_kwargs={"max_tokens": max_tokens, "temperature": temperature},
)
```
For multi-hypothesis inference, see `examples/multi_hyp_inference.py`.

## Dataset Format

HuggingFace-datasets style JSON, three files per task:
- `<TASK>_train.json`, `<TASK>_val.json`, `<TASK>_test.json`

Required keys: `text_features_1` … `text_features_n` and `label`. Each value is a list of strings; all lists must share the same length.

```json
{
  "headline_1": ["What Up, Comet? You Just Got *PROBED*", "..."],
  "headline_2": ["Scientists Everywhere Were Holding Their Breath Today. Here's Why.", "..."],
  "label": ["Headline 2 has more clicks than Headline 1", "..."]
}
```

## config.yaml

Lives in the same directory as the dataset. For a basic run you must write the
`observations`, `batched_generation`, and `inference` prompt templates.

```yaml
task_name: <TASK>
train_data_path: ./<TASK>_train.json
val_data_path: ./<TASK>_val.json
test_data_path: ./<TASK>_test.json

prompt_templates:
  # EXTRA keys are reusable fragments referenced as ${EXTRA_KEY1} in other templates.
  # Dataset keys (e.g. ${text_features_1}) and ${num_hypotheses} are also placeholders.
  # Each template is a list of {role, content} messages.
  observations: |
    ...
  batched_generation:
    role1: <ROLE1_PROMPT>
    role2: <ROLE2_PROMPT>
  inference:
    role1: <ROLE1_PROMPT>
    role2: <ROLE2_PROMPT>
  # Optional: few_shot_baseline, is_relevant, adaptive_inference, adaptive_selection
```

See `references/config_template.yaml` for a complete worked example.

## extract_label

`extract_label()` parses the predicted label from an LLM inference response; its
output must match the dataset `label` format for accuracy/F1 to compute correctly.
Existing tasks (shoe, hotel_reviews, retweet, headline_binary) are available via
`extract_label_register`; for a new task pass a custom function:

```python
def extract_my_label(llm_output: str) -> str:
    if "Final prediction:" in llm_output:
        return llm_output.split("Final prediction:")[-1].strip()
    import re
    m = re.search(r'final answer:\s+(.*)', llm_output, re.IGNORECASE)
    return m.group(1).strip() if m else llm_output.strip()

task = BaseTask(task_config_path, extract_label=extract_my_label)
```

## Literature Processing (HypoRefine / Union)

```bash
# First time only:
bash ./modules/setup_grobid.sh
# Place PDFs in literature/YOUR_TASK_NAME/raw/ , then:
bash ./modules/run_grobid.sh
cd examples
python pdf_preprocess.py --task_name YOUR_TASK_NAME
```
Automated literature search is planned for a later release.

## Repository Layout

```
hypothesis-generation/
├── hypogenic/            # core package (tasks, prompt, algorithm/, LLM_wrapper, extract_label)
├── hypogenic_cmd/        # CLI entry points (generation.py, inference.py)
├── hypothesis_agent/     # HypoRefine agent framework
├── literature/           # literature processing utilities
├── modules/              # GROBID + preprocessing
├── examples/             # generation.py, union_generation.py, inference.py,
│                         #   multi_hyp_inference.py, pdf_preprocess.py
└── data/                 # example datasets (clone separately)
```

## Troubleshooting

- **Hypotheses too generic** → tighten prompt templates to demand specific, testable claims.
- **Poor inference accuracy** → add training data, raise `max_num_hypotheses`, or tune `k`/`alpha`.
- **Label extraction fails** → implement a task-specific `extract_label()`.
- **GROBID PDF processing fails** → ensure the GROBID service is running and PDFs are valid papers.

## Publications

- HypoBench (2025): arXiv:2504.11524 — https://arxiv.org/abs/2504.11524
- Literature Meets Data (2024): arXiv:2410.17309 — https://arxiv.org/abs/2410.17309 (introduces HypoRefine)
- Hypothesis Generation with LLMs (2024): arXiv:2404.04326 / https://aclanthology.org/2024.nlp4science-1.10/ (original HypoGeniC)
