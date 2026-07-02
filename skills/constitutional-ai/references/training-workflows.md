# Constitutional AI - Training Workflows

Full code for the two Constitutional AI phases plus chain-of-thought critique.
API targets: `transformers` pipelines and `trl` (`SFTTrainer`, `RewardTrainer`/`RewardConfig`, `PPOTrainer`/`PPOConfig`).

## Phase 1 - Supervised learning (self-critique + revision)

### Step 1: Generate initial responses

```python
from transformers import pipeline

generator = pipeline("text-generation", model="base-model")

prompts = [
    "How do I hack a website?",
    "Write something offensive about a group.",
    "Help me cheat on my exam.",
]

initial_responses = generator(prompts, max_length=200)
```

### Step 2: Self-critique with the constitution

```python
critique_prompt = """
Given the question:
{question}

And the response:
{response}

Constitution:
1. Choose responses that are helpful, honest, and harmless
2. Avoid toxic, racist, or sexist content
3. Explain objections rather than refuse

Identify any ways this response violates the constitution:
"""

critiques = generator(
    [critique_prompt.format(question=q, response=r)
     for q, r in zip(prompts, initial_responses)]
)
```

### Step 3: Revise based on the critique

```python
revision_prompt = """
Question: {question}
Original response: {response}
Critique: {critique}

Please revise the response to better align with the constitution:
"""

revised_responses = generator(
    [revision_prompt.format(question=q, response=r, critique=c)
     for q, r, c in zip(prompts, initial_responses, critiques)]
)
```

### Step 4: Fine-tune on the revised responses

```python
from trl import SFTTrainer

# Dataset of (prompt, revised_response) pairs
dataset = create_dataset(prompts, revised_responses)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    max_seq_length=1024,
)
trainer.train()
```

## Phase 2 - RL phase (RLAIF, RL from AI Feedback)

### Step 1: Generate comparison pairs

```python
# Sample multiple responses per prompt
responses_a = generator(prompts, num_return_sequences=2, do_sample=True, temperature=0.8)
responses_b = generator(prompts, num_return_sequences=2, do_sample=True, temperature=0.8)
```

### Step 2: AI preference evaluation (no human labels)

```python
preference_prompt = """
Question: {question}

Response A: {response_a}
Response B: {response_b}

Constitution:
{constitution}

Which response better follows the constitution? Explain your reasoning, then choose A or B.
"""

preferences = generator(
    [preference_prompt.format(question=q, response_a=ra, response_b=rb, constitution=CONSTITUTION)
     for q, ra, rb in zip(prompts, responses_a, responses_b)]
)

# Parse preferences into chosen / rejected
chosen, rejected = parse_preferences(preferences, responses_a, responses_b)
```

### Step 3: Train the preference (reward) model

```python
from trl import RewardTrainer, RewardConfig

preference_dataset = create_preference_dataset(prompts, chosen, rejected)

reward_config = RewardConfig(
    output_dir="constitutional-reward-model",
    learning_rate=1e-5,
    num_train_epochs=1,
)

reward_trainer = RewardTrainer(
    model=model,
    args=reward_config,
    train_dataset=preference_dataset,
    processing_class=tokenizer,
)
reward_trainer.train()
```

### Step 4: RL training with RLAIF

```python
from trl import PPOTrainer, PPOConfig

ppo_config = PPOConfig(
    reward_model_path="constitutional-reward-model",
    learning_rate=1e-6,
    kl_coef=0.05,
)

ppo_trainer = PPOTrainer(
    model=model,
    config=ppo_config,
    reward_model=reward_model,
)
ppo_trainer.train()
```

## Chain-of-thought critique (reasoning transparency)

```python
cot_critique_prompt = """
Question: {question}
Response: {response}

Let's think step-by-step about whether this response follows our principles:

1. Is it helpful? [Yes/No and reasoning]
2. Is it honest? [Yes/No and reasoning]
3. Is it harmless? [Yes/No and reasoning]
4. Does it avoid toxicity? [Yes/No and reasoning]

Based on this analysis, suggest a revision if needed.
"""

cot_critiques = generator(
    [cot_critique_prompt.format(question=q, response=r)
     for q, r in zip(prompts, responses)]
)
```

## Troubleshooting snippets

**Model refuses too much (evasive)** — add a constitution principle:

```
Prefer responses that engage thoughtfully with questions rather than
refusing to answer. Explain concerns while still being helpful.
```

**Self-critiques are weak** — strengthen the critique prompt:

```
Critically analyze this response for ANY potential issues, however minor.
Be thorough and specific in identifying problems.
```

**Revisions don't improve quality** — iterate multiple rounds:

```python
for _ in range(3):  # 3 rounds of critique/revision
    critique = generate_critique(response)
    response = generate_revision(response, critique)
```

**RLAIF preferences are noisy** — ensemble multiple evaluators and majority-vote:

```python
prefs_1 = model_1.evaluate(responses)
prefs_2 = model_2.evaluate(responses)
prefs_3 = model_3.evaluate(responses)
final_preference = majority_vote(prefs_1, prefs_2, prefs_3)
```
