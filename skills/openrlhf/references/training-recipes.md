# OpenRLHF Training Recipes

Copy-paste command recipes for the OpenRLHF CLI. Entrypoint modules
(`openrlhf.cli.train_ppo_ray`, `train_rm`, `train_dpo`, `train_sft`) are stable.

## CLI flag namespaces — version note

OpenRLHF's **main branch** refactored the CLI into **nested dot-notation flags**
grouped by component (`ref.*`, `reward.*`, `critic.*`, `actor.*`, `vllm.*`,
`train.*`, `data.*`, `ds.*`, `algo.*`, `ckpt.*`, `rollout.*`). Examples below use the
**flat-flag** form from released/stable versions. Translate as needed:

| Flat (stable)                       | Nested (main)                          |
|-------------------------------------|----------------------------------------|
| `--advantage_estimator group_norm`  | `--algo.advantage.estimator group_norm`|
| `--colocate_all_models`             | `--train.colocate_all`                 |
| `--init_kl_coef 0.01`               | `--algo.kl.init_coef 0.01`             |
| `--train_batch_size 128`            | `--train.batch_size 128`               |
| `--ref_num_nodes 1`                 | `--ref.num_nodes 1`                    |

Verify the exact flags against `examples/scripts/` for the version you installed.

## Installation

```bash
# Launch NVIDIA PyTorch container (25.02+)
docker run --runtime=nvidia -it --rm --shm-size="10g" --cap-add=SYS_ADMIN \
  -v $PWD:/openrlhf nvcr.io/nvidia/pytorch:25.02-py3 bash

# Remove conflicting packages, then install with vLLM
sudo pip uninstall xgboost transformer_engine flash_attn pynvml -y
pip install openrlhf[vllm]
```

## Recipe 1 — Full RLHF pipeline (Reward Model → PPO)

Step 1, train the reward model:

```bash
deepspeed --module openrlhf.cli.train_rm \
  --save_path ./output/llama3-8b-rm \
  --save_steps -1 --logging_steps 1 \
  --eval_steps -1 --train_batch_size 256 \
  --micro_train_batch_size 1 --pretrain meta-llama/Meta-Llama-3-8B \
  --bf16 --max_epochs 1 --max_len 8192 \
  --zero_stage 3 --learning_rate 9e-6 \
  --dataset OpenRLHF/preference_dataset_mixture2_and_safe_pku \
  --apply_chat_template --chosen_key chosen \
  --rejected_key rejected --flash_attn --gradient_checkpointing
```

Step 2, PPO with the Hybrid Engine (Ray + vLLM, all models colocated):

```bash
ray start --head --node-ip-address 0.0.0.0 --num-gpus 8

ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json='{"working_dir": "/openrlhf"}' \
  -- python3 -m openrlhf.cli.train_ppo_ray \
  --ref_num_nodes 1 --ref_num_gpus_per_node 8 \
  --reward_num_nodes 1 --reward_num_gpus_per_node 8 \
  --critic_num_nodes 1 --critic_num_gpus_per_node 8 \
  --actor_num_nodes 1 --actor_num_gpus_per_node 8 \
  --vllm_num_engines 4 --vllm_tensor_parallel_size 2 \
  --colocate_all_models \
  --vllm_gpu_memory_utilization 0.5 \
  --pretrain OpenRLHF/Llama-3-8b-sft-mixture \
  --reward_pretrain ./output/llama3-8b-rm \
  --save_path ./output/llama3-8b-ppo \
  --micro_train_batch_size 8 --train_batch_size 128 \
  --micro_rollout_batch_size 16 --rollout_batch_size 1024 \
  --max_epochs 1 --prompt_max_len 1024 --generate_max_len 1024 \
  --zero_stage 3 --bf16 \
  --actor_learning_rate 5e-7 --critic_learning_rate 9e-6 \
  --init_kl_coef 0.01 --normalize_reward \
  --gradient_checkpointing --packing_samples \
  --vllm_enable_sleep --deepspeed_enable_sleep
```

## Recipe 2 — GRPO (no critic model needed)

Same `train_ppo_ray` entrypoint; switch the advantage estimator and drop the
critic allocation:

```bash
ray job submit --address="http://127.0.0.1:8265" \
  -- python3 -m openrlhf.cli.train_ppo_ray \
  --advantage_estimator group_norm \
  --ref_num_nodes 1 --ref_num_gpus_per_node 8 \
  --reward_num_nodes 1 --reward_num_gpus_per_node 8 \
  --actor_num_nodes 1 --actor_num_gpus_per_node 8 \
  --vllm_num_engines 4 --vllm_tensor_parallel_size 2 \
  --colocate_all_models \
  --pretrain OpenRLHF/Llama-3-8b-sft-mixture \
  --reward_pretrain OpenRLHF/Llama-3-8b-rm-700k \
  --save_path ./output/llama3-8b-grpo \
  --micro_train_batch_size 8 --train_batch_size 128 \
  --micro_rollout_batch_size 16 --rollout_batch_size 1024 \
  --max_epochs 1 --bf16 \
  --actor_learning_rate 5e-7 \
  --init_kl_coef 0.01 --use_kl_loss --kl_estimator k3 \
  --normalize_reward --no_advantage_std_norm
```

Key GRPO flags:
- `--advantage_estimator group_norm` — enables GRPO (group-normalized advantage)
- `--use_kl_loss` — KL loss term from the GRPO paper
- `--kl_estimator k3` — KL estimator (k2 ≈ k1)
- `--no_advantage_std_norm` — disables advantage std normalization (Dr. GRPO style)

Other estimators on the same entrypoint: `--advantage_estimator reinforce`
(REINFORCE++), `reinforce_baseline` (REINFORCE++-baseline), `rloo` (RLOO).

## Recipe 3 — DPO (preference optimization, no reward model)

```bash
deepspeed --module openrlhf.cli.train_dpo \
  --save_path ./output/llama3-8b-dpo \
  --save_steps -1 --logging_steps 1 \
  --eval_steps -1 --train_batch_size 256 \
  --micro_train_batch_size 2 --pretrain meta-llama/Meta-Llama-3-8B \
  --bf16 --max_epochs 1 --max_len 8192 \
  --zero_stage 3 --learning_rate 5e-7 --beta 0.1 \
  --dataset OpenRLHF/preference_dataset_mixture2_and_safe_pku \
  --apply_chat_template --chosen_key chosen \
  --rejected_key rejected --flash_attn --gradient_checkpointing
```

## Troubleshooting

**GPU OOM with large models** — disable colocation and give each model its own GPUs:
drop `--colocate_all_models` and set `--actor_num_gpus_per_node` /
`--critic_num_gpus_per_node` / `--reward_num_gpus_per_node` / `--ref_num_gpus_per_node`
separately.

**DeepSpeed "GPU index out of range"** — `export RAY_EXPERIMENTAL_NOSET_CUDA_VISIBLE_DEVICES=1`.

**Training instability** — prefer the Hybrid Engine (`--colocate_all_models
--vllm_enable_sleep --deepspeed_enable_sleep`) over async; raise the KL coefficient
(`--init_kl_coef 0.05`).

**Slow generation during PPO** — enable/scale vLLM (`--vllm_num_engines 4
--vllm_tensor_parallel_size 2 --vllm_gpu_memory_utilization 0.5`).
