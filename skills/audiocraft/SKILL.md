---
name: audiocraft
description: Meta's PyTorch library for audio generation - text-to-music (MusicGen), text-to-sound-effects (AudioGen), and neural audio codec (EnCodec). Use when generating music or ambient/sound-effect audio from text descriptions, doing melody- or style-conditioned music generation, producing stereo music, or encoding/decoding audio with EnCodec. NOT for speech synthesis or text-to-speech (use Bark/Tortoise), audio transcription / speech-to-text (use Whisper), lyric-aligned vocal generation (use Jukebox), or real-time/streaming generation (AudioCraft is offline batch).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Multimodal, Audio Generation, Text-to-Music, Text-to-Audio, MusicGen]
dependencies: [audiocraft, torch>=2.0.0, transformers>=4.30.0]
---

# AudioCraft: Audio Generation

Router for Meta's AudioCraft (MusicGen, AudioGen, EnCodec). Detailed runnable
code lives in `references/examples.md`; training/deployment in
`references/advanced-usage.md`; errors in `references/troubleshooting.md`.

## When to use

Use AudioCraft to generate music or sound effects from text, condition music on
a melody or a reference style, produce stereo music, or compress/reconstruct
audio with EnCodec. It is offline/batch (not streaming).

Do NOT use for:
- Speech synthesis / TTS -> Bark, Tortoise
- Speech-to-text / transcription -> Whisper
- Vocals with aligned lyrics -> Jukebox
- Longer commercial-grade tracks -> Stable Audio
- Spectrogram-based music -> Riffusion

## Models at a glance

| Model | Size | Purpose | Sample rate |
|-------|------|---------|-------------|
| `musicgen-small/medium/large` | 300M / 1.5B / 3.3B | Text-to-music | 32 kHz |
| `musicgen-melody[-large]` | 1.5B / 3.3B | Text + melody conditioning | 32 kHz |
| `musicgen-stereo-*` | varies | Stereo music | 32 kHz |
| `musicgen-style` | 1.5B | Reference-style conditioning | 32 kHz |
| `audiogen-medium` | 1.5B | Text-to-sound-effects | 16 kHz |
| `encodec_32khz` | - | Neural audio codec | 32 kHz |

Larger = higher quality, more VRAM (see GPU table in `references/examples.md`).

## Generation parameters

Set via `model.set_generation_params(...)` before `generate()`:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `duration` | 8.0 | Output length in seconds (reliable up to ~30) |
| `top_k` | 250 | Top-k sampling diversity |
| `top_p` | 0.0 | Nucleus sampling (0 disables) |
| `temperature` | 1.0 | Creativity / variation |
| `cfg_coef` | 3.0 | Classifier-free guidance (text adherence) |

MusicGen-Style adds `cfg_coef_beta` (double CFG) and
`set_style_conditioner_params(eval_q, excerpt_length)`.

## Minimal start

```bash
pip install audiocraft   # or: pip install git+https://github.com/facebookresearch/audiocraft.git
```

```python
import torchaudio
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=8)
wav = model.generate(["happy upbeat electronic dance music"])
torchaudio.save("output.wav", wav[0].cpu(), sample_rate=32000)
```

Key API methods: `MusicGen.generate(descriptions)`,
`generate_with_chroma(descriptions, melody, sr)` (melody),
`generate_with_style(descriptions, style_audio, sr)` (style);
`AudioGen.generate(descriptions)`;
`CompressionModel.encode/decode` (EnCodec). Note 32 kHz for music, 16 kHz for
AudioGen. AudioCraft is also usable via HuggingFace
`MusicgenForConditionalGeneration`.

## Recipes (see `references/examples.md`)

- Native API and HuggingFace Transformers text-to-music
- Melody-conditioned, stereo, and audio-continuation generation
- MusicGen-Style: style-conditioned and style-only generation
- AudioGen sound-effect generation
- EnCodec compression/reconstruction
- Workflows: reusable generator class, batch sound design, Gradio demo
- Performance: half precision, batching, VRAM table

## References

- [Code examples](references/examples.md) - runnable snippets for every model
- [Advanced usage](references/advanced-usage.md) - fine-tuning, training, deployment
- [Troubleshooting](references/troubleshooting.md) - install/CUDA/quality issues

## Resources

- GitHub: https://github.com/facebookresearch/audiocraft
- MusicGen paper: https://arxiv.org/abs/2306.05284
- AudioGen paper: https://arxiv.org/abs/2209.15352
- HuggingFace: https://huggingface.co/facebook/musicgen-small
- Demo space: https://huggingface.co/spaces/facebook/MusicGen
