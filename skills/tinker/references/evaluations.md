# Evaluations

## Inline (during training)

Attach evaluators to the config; they run every N steps.

```python
# SFT
chz.Blueprint(train.Config).apply({
    "evaluator_builders": [my_evaluator],            # every eval_every steps
    "infrequent_evaluator_builders": [heavy_eval],   # every infrequent_eval_every steps
    "eval_every": 8, "infrequent_eval_every": 50,
})

# RL — evaluator_builders hold SamplingClientEvaluator instances
chz.Blueprint(train.Config).apply({"evaluator_builders": [sampling_eval], "eval_every": 5})
```

## Offline with Inspect AI

Run standard benchmarks on a saved checkpoint:

```bash
MODEL_PATH=tinker://YOUR_MODEL_PATH
python -m tinker_cookbook.eval.run_inspect_evals \
    model_path=$MODEL_PATH model_name=MODEL_NAME \
    tasks=inspect_evals/ifeval,inspect_evals/mmlu_0_shot renderer_name=RENDERER_NAME
```

### Custom Inspect task (LLM-as-judge)

`InspectAPIFromTinkerSampling` adapts a Tinker sampling client into an Inspect model, so you can use
your trained model as the grader (or any OpenAI-compatible API, e.g. OpenRouter).

```python
import tinker
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig as InspectAIGenerateConfig, Model as InspectAIModel
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate
from tinker_cookbook.eval.inspect_utils import InspectAPIFromTinkerSampling

service_client  = tinker.ServiceClient()
sampling_client = service_client.create_sampling_client(base_model="meta-llama/Llama-3.1-8B-Instruct")
api = InspectAPIFromTinkerSampling(renderer_name="llama3",
                                   model_name="meta-llama/Llama-3.1-8B-Instruct",
                                   sampling_client=sampling_client, verbose=False)
GRADER = InspectAIModel(api=api, config=InspectAIGenerateConfig())

@task
def example_lm_as_judge() -> Task:
    return Task(
        name="llm_as_judge",
        dataset=MemoryDataset(name="qa", samples=[
            Sample(input="What is the capital of France?", target="Paris"),
            Sample(input="What is the capital of Italy?", target="Rome")]),
        solver=generate(),
        scorer=model_graded_qa(
            instructions="Grade strictly. Respond 'GRADE: C' if correct or 'GRADE: I' otherwise.",
            partial_credit=False, model=GRADER),
    )
```

## Custom SamplingClientEvaluator

Lower-level, full control. Implement `__call__(sampling_client)` returning a metrics dict.

```python
from typing import Any, Callable
import tinker
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.evaluators import SamplingClientEvaluator
from tinker_cookbook.tokenizer_utils import get_tokenizer

class CustomEvaluator(SamplingClientEvaluator):
    def __init__(self, dataset, grader_fn, model_name, renderer_name):
        self.dataset, self.grader_fn = dataset, grader_fn
        self.renderer = renderers.get_renderer(name=renderer_name, tokenizer=get_tokenizer(model_name))

    async def __call__(self, sampling_client: tinker.SamplingClient) -> dict[str, float]:
        params = types.SamplingParams(max_tokens=100, temperature=0.7, top_p=1.0,
                                      stop=self.renderer.get_stop_sequences())
        correct = 0
        for datum in self.dataset:
            model_input = self.renderer.build_generation_prompt(
                [renderers.Message(role="user", content=datum["input"])])
            r = await sampling_client.sample_async(prompt=model_input, num_samples=1, sampling_params=params)
            response = self.renderer.parse_response(r.sequences[0].tokens)[0]
            correct += self.grader_fn(response["content"], datum["output"])
        return {"accuracy": correct / len(self.dataset)}
```

## Strategy

| Stage | Method | When |
|-------|--------|------|
| During SFT | `evaluator_builders` | every N steps |
| During RL | `SamplingClientEvaluator` | every N iterations |
| After training | `run_inspect_evals` CLI | final checkpoint |
| Custom | `SamplingClientEvaluator` | any time with a sampling client |
| LLM-as-judge | Inspect `model_graded_qa` | automated grading |
