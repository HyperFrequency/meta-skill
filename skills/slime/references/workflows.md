# slime Workflows

Step-by-step recipes for installation and the three primary training workflows.
For exhaustive argument/data-structure details see `api-reference.md`; for failure
modes see `troubleshooting.md`.

## Hardware requirements

slime needs GPUs for **both** Megatron training and SGLang rollout at once — size for
both, or share them with `--colocate`.

- **Minimum**: ~2x A100 80 GB (160 GB total) for a ~7B dense model run with `--colocate`.
- **Larger dense (30–70B) and MoE models**: multi-node. Full-parameter 70B RL needs far
  more than a single 4-GPU node once fp32 master weights + Adam optimizer states + SGLang
  KV cache are counted — plan for 8+ GPUs across nodes and shard with TP/PP plus Megatron's
  distributed optimizer.
- **Multi-node**: InfiniBand required for cross-node NCCL weight-sync (see
  `troubleshooting.md` → weight-sync).
- **Checkpoint storage**: NVMe, 5+ TB free for large-model checkpoints.

**Cost**: a single GPU node runs roughly $10–25/hr on budget clouds (more on
hyperscalers); multi-node scales ~linearly. RL post-training runs are long — budget for
hours-to-days.

## Installation

```bash
# Recommended: Docker
docker pull slimerl/slime:latest
docker run --rm --gpus all --ipc=host --shm-size=16g \
  -it slimerl/slime:latest /bin/bash

# Inside container
cd /root/slime && pip install -e . --no-deps
```

### From source

```bash
git clone https://github.com/THUDM/slime.git
cd slime
pip install -r requirements.txt
pip install -e .
```

## Quick start: GRPO training

```bash
# Source model configuration (sets MODEL_ARGS / CKPT_ARGS arrays)
source scripts/models/qwen3-4B.sh

python train.py \
    --actor-num-nodes 1 \
    --actor-num-gpus-per-node 4 \
    --rollout-num-gpus 4 \
    --advantage-estimator grpo \
    --use-kl-loss --kl-loss-coef 0.001 \
    --rollout-batch-size 32 \
    --n-samples-per-prompt 8 \
    --global-batch-size 256 \
    --num-rollout 3000 \
    --prompt-data /path/to/data.jsonl \
    ${MODEL_ARGS[@]} ${CKPT_ARGS[@]}
```

---

## Workflow 1: Standard GRPO training

Train reasoning models with group-relative advantages.

**Prerequisites**: Docker env or Megatron-LM + SGLang installed; model checkpoint
(HuggingFace or Megatron format); training data in JSONL.

### Step 1: Prepare data

```python
# data.jsonl — flat format
{"prompt": "What is 2 + 2?", "label": "4"}
{"prompt": "Solve: 3x = 12", "label": "x = 4"}
```

```python
# chat format
{
    "prompt": [
        {"role": "system", "content": "You are a math tutor."},
        {"role": "user", "content": "What is 15 + 27?"}
    ],
    "label": "42"
}
```

### Step 2: Configure model

```bash
ls scripts/models/   # glm4-9B.sh, qwen3-4B.sh, qwen3-30B-A3B.sh, deepseek-v3.sh, llama3-8B.sh, ...
source scripts/models/qwen3-4B.sh
```

### Step 3: Launch training

```bash
python train.py \
    --actor-num-nodes 1 \
    --actor-num-gpus-per-node 8 \
    --rollout-num-gpus 8 \
    --advantage-estimator grpo \
    --use-kl-loss \
    --kl-loss-coef 0.001 \
    --prompt-data /path/to/train.jsonl \
    --input-key prompt \
    --label-key label \
    --apply-chat-template \
    --rollout-batch-size 32 \
    --n-samples-per-prompt 8 \
    --global-batch-size 256 \
    --num-rollout 3000 \
    --save-interval 100 \
    --eval-interval 50 \
    ${MODEL_ARGS[@]}
```

### Step 4: Monitor

- TensorBoard: `tensorboard --logdir outputs/`
- Verify reward curves are increasing.
- Monitor GPU utilization across nodes.

---

## Workflow 2: Asynchronous training

Use async to overlap rollout and training for higher throughput — best for large
models with long generation times, high GPU idle time in sync mode, and sufficient
memory for buffering. Note: async is incompatible with `--colocate`.

```bash
python train_async.py \
    --actor-num-nodes 1 \
    --actor-num-gpus-per-node 8 \
    --rollout-num-gpus 8 \
    --advantage-estimator grpo \
    --async-buffer-size 4 \
    --prompt-data /path/to/train.jsonl \
    ${MODEL_ARGS[@]}
```

Async-specific parameters:

```bash
--async-buffer-size 4        # number of rollouts to buffer
--update-weights-interval 2  # sync weights every N rollouts
```

---

## Workflow 3: Multi-turn agentic training

Train agents with tool use or multi-step reasoning.

**Prerequisites**: custom generate function for multi-turn logic; tool/environment interface.

### Step 1: Define custom generate function

```python
# custom_generate.py
async def custom_generate(args, samples, evaluation=False):
    """Multi-turn generation with tool calling."""
    for sample in samples:
        conversation = sample.prompt
        for turn in range(args.max_turns):
            response = await generate_single(conversation)
            tool_call = extract_tool_call(response)
            if tool_call:
                tool_result = execute_tool(tool_call)
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "tool", "content": tool_result})
            else:
                break
        sample.response = response
        sample.reward = compute_reward(sample)
    return samples
```

### Step 2: Launch with custom function

```bash
python train.py \
    --custom-generate-function-path custom_generate.py \
    --max-turns 5 \
    --prompt-data /path/to/agent_data.jsonl \
    ${MODEL_ARGS[@]}
```

See `examples/search-r1/` in the slime repo for a complete multi-turn search example.

---

## Advanced topics

### Co-location mode

Share GPUs between training and inference to reduce memory:

```bash
python train.py \
    --colocate \
    --actor-num-gpus-per-node 8 \
    --sglang-mem-fraction-static 0.4 \
    ${MODEL_ARGS[@]}
```

### Custom reward model

```python
# custom_rm.py
class CustomRewardModel:
    def __init__(self, model_path):
        self.model = load_model(model_path)

    def compute_reward(self, prompts, responses):
        inputs = self.tokenize(prompts, responses)
        scores = self.model(inputs)
        return scores.tolist()
```

```bash
--custom-rm-path custom_rm.py
```

### Multi-task evaluation

```bash
--eval-prompt-data aime /path/to/aime.jsonl \
--eval-prompt-data gsm8k /path/to/gsm8k.jsonl \
--n-samples-per-eval-prompt 16
```
