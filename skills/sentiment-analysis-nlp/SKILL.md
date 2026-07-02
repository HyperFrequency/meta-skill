---
name: sentiment-analysis-nlp
version: 0.1.0
description: Sentiment scoring for financial text (news headlines, tweets, earnings transcripts, 10-K filings). Primary path uses Hugging Face `transformers` with a finance-tuned classifier (ProsusAI/finbert, yiyanghkust/finbert-tone). Fallback path uses VADER (`vaderSentiment`) — a rule/lexicon-based scorer — for lightweight, no-GPU, no-model-download cases. Use when you need polarity / tone features for downstream alpha or risk models. Not a replacement for full event extraction or entity-level sentiment; for those, combine with NER.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Sentiment Analysis for Financial NLP

## When to use

Reach for this skill when you need to convert unstructured financial text into a numeric polarity score per row (e.g., a `sentiment` column to merge with OHLCV bars). Typical inputs:

- News headlines or full article bodies (Bloomberg, Reuters, finBERT-pretrained on Reuters)
- Tweets (StockTwits, FinTwit) — short, noisy, lots of cashtags and emoji
- SEC filings sections (Item 1A risk factors, MD&A)
- Earnings call transcripts (broken into speaker turns)

Two paths:

1. **Finance-tuned transformer (default).** ProsusAI/finbert or yiyanghkust/finbert-tone. Handles "beat estimates", "missed guidance", "downgrade", "going concern" correctly — a general SST-2 DistilBERT will not.
2. **VADER (fallback).** Rule-based, no model download, ~1000x faster on CPU, but trained on social-media English. Use for tweets, intraday velocity, or when transformers are unavailable.

Skip this skill if you actually want event extraction, entity-level sentiment, or causal narrative parsing — those are different tasks.

## Install / setup

```bash
# Primary path: transformers + finance model
uv pip install "transformers[torch]>=4.51"

# Fallback path: VADER
uv pip install vaderSentiment
```

Models download on first use to `~/.cache/huggingface/hub/`. FinBERT is ~440 MB. Pre-download once in CI to avoid cold-start latency.

GPU optional but ~10-50x faster for batched inference. Pass `device=0` to `pipeline` for first CUDA device.

## Minimal example

```python
# --- Primary: FinBERT via transformers pipeline ----------------------------
import pandas as pd
from transformers import pipeline

# ProsusAI/finbert: labels = {positive, negative, neutral}
# yiyanghkust/finbert-tone is an alternative trained on analyst reports
classifier = pipeline(
    task="sentiment-analysis",
    model="ProsusAI/finbert",
    device=-1,  # set to 0 for first GPU, -1 for CPU
)

headlines = pd.Series([
    "Apple beats Q3 estimates on iPhone strength, raises guidance.",
    "Regulators open antitrust probe into the firm's ad business.",
    "Company reaffirms previously issued FY24 outlook.",
])

# Batch through the pipeline; truncation matters for long inputs (512 tok cap)
raw = classifier(headlines.tolist(), truncation=True, batch_size=16)
# raw = [{'label': 'positive', 'score': 0.93}, ...]

# Convert to a signed polarity in [-1, 1] for downstream features
sign = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
df = pd.DataFrame({"text": headlines})
df["label"] = [r["label"].lower() for r in raw]
df["score"] = [r["score"] for r in raw]
df["polarity"] = df["label"].map(sign) * df["score"]
print(df)

# --- Fallback: VADER (no model download, CPU only) -------------------------
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

vader = SentimentIntensityAnalyzer()
# Returns dict: {neg, neu, pos, compound}. `compound` is the signed [-1, 1] score.
scores = headlines.apply(lambda t: vader.polarity_scores(t)["compound"])
print(scores)
```

Pattern notes:

- `truncation=True` is required when headlines exceed the model's 512-token limit. Without it, the pipeline raises.
- `batch_size` is a pipeline kwarg, not a tokenizer kwarg — it controls forward-pass batching.
- For multi-paragraph filings, split into sentences first and aggregate (mean / max-abs) per document; transformers cap at 512 tokens.

## Key API surface

**`transformers.pipeline`** (canonical entry point):

- `pipeline(task="sentiment-analysis", model=<hf-id>, device=<int>, torch_dtype=<dtype>)`
- Call with a `str`, `List[str]`, or anything iterable. Returns `List[{"label": str, "score": float}]`.
- Common kwargs at call time: `truncation`, `padding`, `batch_size`, `top_k` (set `top_k=None` to get all class scores).

**`AutoModelForSequenceClassification` + `AutoTokenizer`** (manual path, when you need logits):

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
mdl = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
# mdl.config.id2label gives the label mapping
```

**`vaderSentiment.SentimentIntensityAnalyzer`**:

- `polarity_scores(text: str) -> {"neg": float, "neu": float, "pos": float, "compound": float}`
- `compound` is the normalized signed score in [-1, 1]; use this as the feature.

**Finance-tuned model IDs to know** (verified on Hugging Face Hub as of 2026-05-20):

- `ProsusAI/finbert` — 3-class (positive/neutral/negative), trained on Reuters financial news. Most cited.
- `yiyanghkust/finbert-tone` — 3-class, trained on analyst report sentences. Often better on equity research tone.
- `ahmedrachid/FinancialBERT-Sentiment-Analysis` — alternative, smaller community footprint (unverified for production).

## Workflow patterns

**Headline → feature column (typical pipeline).** Fetch news rows with a timestamp and ticker; run FinBERT with `truncation=True, batch_size=32-64`; map labels to a signed `[-1, 1]` polarity; aggregate per (ticker, day) with mean polarity and headline count; merge against your bar data on the close of the relevant session. Be careful about timezone alignment between news timestamps and bar closes — a stale news polarity from yesterday should not be assigned to today's bar.

**Filing or transcript chunking.** Split into sentences with `nltk.sent_tokenize` or a regex on periods; score each sentence; aggregate. Three aggregations are useful: mean polarity (overall tone), fraction of negative sentences (downside risk), and max-abs polarity (presence of strong language anywhere). The third often correlates with implied vol changes.

**Backtesting hygiene.** A finance-tuned model trained in 2019 has seen the language used by analysts up to its cutoff — using it on 2014 filings is fine (the language is forward-stationary enough), but applying current FinBERT to historical text is a mild form of look-ahead because the model's vocabulary tokenizer was trained on text including the future. The empirical bias is small but document it.

**Combining transformer + VADER.** Use VADER as a cheap prefilter to surface only the high-magnitude items (`abs(compound) > 0.5`), then re-score those with FinBERT. Cuts inference cost by 5-10x on news firehoses without losing the rare events that actually move tape.

## Common pitfalls

1. **Domain shift kills general models.** A DistilBERT fine-tuned on SST-2 movie reviews will score "shares plunge 20% on weak guidance" as mildly negative or even neutral because it never saw financial vocabulary. Always use a finance-tuned head for finance text.

2. **Neutral handling.** FinBERT's `neutral` class often dominates — short headlines without strong tone get bucketed there. If you map labels to a signed scalar, do not treat neutral as zero confidence; treat it as zero polarity but high confidence. Otherwise you wash out signal when averaging.

3. **Truncation silently caps at 512 tokens.** Long 10-K paragraphs get cut, and the trailing content (often the punchline) is dropped. Sentence-split first, then aggregate. The transformers pipeline will warn but not fail when `truncation=True`.

4. **VADER mishandles negation and finance jargon.** "Not a bad quarter" reads positive correctly, but "missed estimates" reads neutral. VADER is fine as a fast prefilter or for tweets — do not use it as the primary signal for filings or analyst reports.

5. **Score is calibrated within model, not across models.** A 0.85 FinBERT positive is not directly comparable to a 0.85 finbert-tone positive. If you swap models in production, recalibrate downstream thresholds.

## Performance notes

- CPU throughput for FinBERT (~110M params): ~50-100 short headlines/sec on a modern laptop. GPU: ~1-2k/sec with `batch_size=32+`.
- For high-volume ingest, prefer the explicit `AutoTokenizer` + `AutoModelForSequenceClassification` path with `torch.no_grad()` and manual batching — the `pipeline` wrapper has small per-call overhead that matters at scale.
- VADER throughput: ~10-50k items/sec on CPU; effectively free.
- ONNX-export of FinBERT via `optimum` gives roughly 2-3x CPU speedup; worth it for production pipelines but not for one-off analysis.

## Manual-path example (when you need logits or custom batching)

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
mdl = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").eval()

texts = ["Earnings beat by 12%, raising guidance.",
         "Class-action suit filed alleging accounting fraud."]

with torch.no_grad():
    enc = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    logits = mdl(**enc).logits
    probs = torch.softmax(logits, dim=-1)        # shape: (n_texts, n_labels)
    pred_idx = probs.argmax(dim=-1)
    labels = [mdl.config.id2label[i.item()] for i in pred_idx]
print(labels, probs.numpy().round(3))
```

This path is what you want when you need (a) the full class-probability distribution rather than just argmax, (b) custom truncation strategies (e.g., keep the last 512 tokens instead of the first), or (c) integration into an existing torch training loop.

## Selecting between FinBERT variants

| Variant | Trained on | Strengths | Watch out for |
|---|---|---|---|
| `ProsusAI/finbert` | Reuters financial news | Most-cited baseline, broad coverage | Slightly conservative; many neutrals |
| `yiyanghkust/finbert-tone` | Analyst report sentences | Better on equity research language, calibrated for tone | Less robust on tweet-style text |
| FinBERT + LoRA fine-tune | Your domain | Best for narrow domains (e.g., crypto, biotech filings) | Need labeled data and a train loop |

Rule of thumb: start with `ProsusAI/finbert` as a baseline, then evaluate `yiyanghkust/finbert-tone` on the same held-out set. If neither clears your threshold, the next step is domain-specific fine-tuning, not yet another off-the-shelf model.

## References

### Primary libraries
- [huggingface/transformers](https://github.com/huggingface/transformers) — upstream (issues, releases, the `pipeline("sentiment-analysis")` entry point)
- [Transformers docs](https://huggingface.co/docs/transformers/) — cross-checked against the current stable channel
- [cjhutto/vaderSentiment](https://github.com/cjhutto/vaderSentiment) — VADER upstream (Python port); the C&P-ready lexicon lives in `vader_lexicon.txt`
- [`huggingface_hub` model cards](https://huggingface.co/docs/huggingface_hub) — how the FinBERT model cards are fetched / cached
- Release notes: [transformers releases](https://github.com/huggingface/transformers/releases) — the `AutoModelForSequenceClassification` contract has been stable; check before upgrading across majors

### Deep-dive docs (specific pages worth bookmarking)
- [Sequence classification task page](https://huggingface.co/docs/transformers/tasks/sequence_classification) — the canonical fine-tune-FinBERT recipe; covers `Trainer`, label2id, eval metrics
- [`pipeline("sentiment-analysis")`](https://huggingface.co/docs/transformers/main_classes/pipelines#transformers.TextClassificationPipeline) — top-1 vs `return_all_scores=True`; the latter is what you want for thresholding
- [`AutoTokenizer`](https://huggingface.co/docs/transformers/main_classes/tokenizer) — padding, truncation, `max_length=512` for BERT-family
- [`AutoModelForSequenceClassification`](https://huggingface.co/docs/transformers/model_doc/auto#transformers.AutoModelForSequenceClassification) — the class behind the FinBERT loads
- [Mixed-precision + batching for fast inference](https://huggingface.co/docs/transformers/perf_infer_gpu_one) — required reading once you go beyond a few hundred headlines
- [PEFT / LoRA fine-tuning](https://huggingface.co/docs/peft/index) — domain-adapt FinBERT on a few thousand labelled examples without full-finetuning
- [ProsusAI/FinBERT model card](https://huggingface.co/ProsusAI/finbert) — the Reuters-trained baseline
- [yiyanghkust/finbert-tone model card](https://huggingface.co/yiyanghkust/finbert-tone) — analyst-report calibrated variant
- [VADER lexicon file](https://github.com/cjhutto/vaderSentiment/blob/master/vaderSentiment/vader_lexicon.txt) — the actual word-level intensities; you can extend it for crypto / fintwit slang

### Adjacent / alternative libraries
- [`spaCy`](https://github.com/explosion/spaCy) — when you need named-entity tagging (companies, tickers) alongside sentiment; works well with `spacy-huggingface-hub`
- [`flair`](https://github.com/flairNLP/flair) — easy ensemble of transformer + classic-NLP; the `flair.models.TextClassifier` API
- [`TextBlob`](https://github.com/sloria/TextBlob) — older lexicon baseline (Pattern-based); useful as a third sanity-check next to VADER
- [`distilbert-base-uncased-finetuned-sst-2-english`](https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english) — generic English sentiment baseline; useful as the non-financial reference point

### Academic papers
- Hutto, C. J. & Gilbert, E. (2014). "VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text." *ICWSM '14*. [paper PDF](http://eegilbert.org/papers/icwsm14.vader.hutto.pdf) — the VADER paper; covers the gold-standard lexicon + the five syntactic rules (negation, intensifier, contrastive conjunction, capitalisation, punctuation emphasis)
- Araci, D. (2019). "FinBERT: Financial Sentiment Analysis with Pre-trained Language Models." [arXiv:1908.10063](https://arxiv.org/abs/1908.10063) — the paper behind `ProsusAI/finbert`; covers the Financial PhraseBank fine-tuning corpus
- Yang, Y., UY, M. C. S., Huang, A. (2020). "FinBERT: A Pretrained Language Model for Financial Communications." [arXiv:2006.08097](https://arxiv.org/abs/2006.08097) — the paper behind `yiyanghkust/finbert-tone`; pretrained on 4.9B-token analyst-report corpus
- Devlin, J. et al. (2019). "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding." *NAACL 2019*. [arXiv:1810.04805](https://arxiv.org/abs/1810.04805) — the encoder architecture every FinBERT variant is built on
- Loughran, T. & McDonald, B. (2011). "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks." *Journal of Finance* 66(1), 35–65. [doi:10.1111/j.1540-6261.2010.01625.x](https://doi.org/10.1111/j.1540-6261.2010.01625.x) — the classic finance-specific sentiment dictionary; still useful when you can't fit a transformer (e.g. low-resource sub-domains)

### Tutorials & write-ups
- [HF blog: Sentiment analysis with VADER + Transformers](https://huggingface.co/blog/sentiment-analysis-python) — accessible end-to-end walkthrough
- [Loughran-McDonald master dictionary (sraf.nd.edu)](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) — the standard finance lexicon, downloadable
- [Financial PhraseBank dataset](https://huggingface.co/datasets/financial_phrasebank) — the corpus FinBERT fine-tunes on; good for held-out evaluation

### Standard datasets / benchmarks
- `financial_phrasebank` — [HF datasets](https://huggingface.co/datasets/financial_phrasebank) — 4,840 sentences from financial news, gold-labelled (50%/66%/75%/100% annotator agreement splits)
- `FiQA-SA` — [task page](https://sites.google.com/view/fiqa/home) — Financial Opinion Mining and Question Answering challenge, sentiment subtask
- `FPB` (alias of Financial PhraseBank above) and the [FLUE benchmark](https://salt-nlp.github.io/FLANG/) — Financial Language Understanding Evaluation; broader than just sentiment

### Last cross-checked
2026-05-20 — via Context7 `/huggingface/transformers` + upstream VADER repo; Auggie not indexed.
