# AudioCraft Code Examples

Detailed, runnable examples for each model. For installation, training, and
deployment see `advanced-usage.md`; for errors see `troubleshooting.md`.

## Basic text-to-music (native AudioCraft API)

```python
import torchaudio
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=8, top_k=250, temperature=1.0)

descriptions = ["happy upbeat electronic dance music with synths"]
wav = model.generate(descriptions)  # shape: [batch, channels, samples]

torchaudio.save("output.wav", wav[0].cpu(), sample_rate=32000)
```

## Using HuggingFace Transformers

```python
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy

processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
model.to("cuda")

inputs = processor(
    text=["80s pop track with bassy drums and synth"],
    padding=True,
    return_tensors="pt",
).to("cuda")

audio_values = model.generate(**inputs, do_sample=True, guidance_scale=3, max_new_tokens=256)

sampling_rate = model.config.audio_encoder.sampling_rate
scipy.io.wavfile.write("output.wav", rate=sampling_rate, data=audio_values[0, 0].cpu().numpy())
```

## MusicGen

### Text-to-music with full parameter control

```python
from audiocraft.models import MusicGen
import torchaudio

model = MusicGen.get_pretrained('facebook/musicgen-medium')
model.set_generation_params(
    duration=30,          # up to 30s reliably; longer uses sliding-window
    top_k=250,            # sampling diversity
    top_p=0.0,            # 0 = use top_k only
    temperature=1.0,      # creativity (higher = more varied)
    cfg_coef=3.0,         # text adherence (higher = stricter)
)

descriptions = [
    "epic orchestral soundtrack with strings and brass",
    "chill lo-fi hip hop beat with jazzy piano",
    "energetic rock song with electric guitar",
]
wav = model.generate(descriptions)
for i, audio in enumerate(wav):
    torchaudio.save(f"music_{i}.wav", audio.cpu(), sample_rate=32000)
```

### Melody-conditioned generation

```python
from audiocraft.models import MusicGen
import torchaudio

model = MusicGen.get_pretrained('facebook/musicgen-melody')
model.set_generation_params(duration=30)

melody, sr = torchaudio.load("melody.wav")
wav = model.generate_with_chroma(["acoustic guitar folk song"], melody, sr)
torchaudio.save("melody_conditioned.wav", wav[0].cpu(), sample_rate=32000)
```

### Stereo generation

```python
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained('facebook/musicgen-stereo-medium')
model.set_generation_params(duration=15)
wav = model.generate(["ambient electronic music with wide stereo panning"])
# wav shape: [batch, 2, samples] for stereo
torchaudio.save("stereo.wav", wav[0].cpu(), sample_rate=32000)
```

### Audio continuation (Transformers)

```python
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torchaudio

processor = AutoProcessor.from_pretrained("facebook/musicgen-medium")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-medium")

audio, sr = torchaudio.load("intro.wav")
inputs = processor(
    audio=audio.squeeze().numpy(),
    sampling_rate=sr,
    text=["continue with an epic chorus"],
    padding=True,
    return_tensors="pt",
)
audio_values = model.generate(**inputs, do_sample=True, guidance_scale=3, max_new_tokens=512)
```

## MusicGen-Style

### Style-conditioned generation (text + reference audio)

```python
from audiocraft.models import MusicGen
import torchaudio

model = MusicGen.get_pretrained('facebook/musicgen-style')
model.set_generation_params(
    duration=30,
    cfg_coef=3.0,
    cfg_coef_beta=5.0,  # style influence (double CFG)
)
model.set_style_conditioner_params(
    eval_q=3,           # RVQ quantizers (1-6)
    excerpt_length=3.0, # style excerpt length in seconds
)

style_audio, sr = torchaudio.load("reference_style.wav")
wav = model.generate_with_style(["upbeat dance track"], style_audio, sr)
```

### Style-only generation (no text prompt)

```python
model.set_generation_params(duration=30, cfg_coef=3.0, cfg_coef_beta=None)
wav = model.generate_with_style([None], style_audio, sr)
```

## AudioGen (sound effects)

```python
from audiocraft.models import AudioGen
import torchaudio

model = AudioGen.get_pretrained('facebook/audiogen-medium')
model.set_generation_params(duration=10)

descriptions = [
    "thunderstorm with heavy rain and lightning",
    "busy city traffic with car horns",
    "ocean waves crashing on rocks",
    "crackling campfire in forest",
]
wav = model.generate(descriptions)
for i, audio in enumerate(wav):
    torchaudio.save(f"sound_{i}.wav", audio.cpu(), sample_rate=16000)
```

## EnCodec (neural audio codec)

```python
from audiocraft.models import CompressionModel
import torch
import torchaudio

model = CompressionModel.get_pretrained('facebook/encodec_32khz')
wav, sr = torchaudio.load("audio.wav")
if sr != 32000:
    wav = torchaudio.transforms.Resample(sr, 32000)(wav)

with torch.no_grad():
    encoded = model.encode(wav.unsqueeze(0))
    codes = encoded[0]            # discrete audio codes
    decoded = model.decode(codes) # reconstruct waveform

torchaudio.save("reconstructed.wav", decoded[0].cpu(), sample_rate=32000)
```

## Workflows

### Reusable music generator class

```python
import torch
import torchaudio
from audiocraft.models import MusicGen

class MusicGenerator:
    def __init__(self, model_name="facebook/musicgen-medium"):
        self.model = MusicGen.get_pretrained(model_name)
        self.sample_rate = 32000

    def generate(self, prompt, duration=30, temperature=1.0, cfg=3.0):
        self.model.set_generation_params(
            duration=duration, top_k=250, temperature=temperature, cfg_coef=cfg
        )
        with torch.no_grad():
            wav = self.model.generate([prompt])
        return wav[0].cpu()

    def generate_batch(self, prompts, duration=30):
        self.model.set_generation_params(duration=duration)
        with torch.no_grad():
            wav = self.model.generate(prompts)
        return wav.cpu()

    def save(self, audio, path):
        torchaudio.save(path, audio, sample_rate=self.sample_rate)

generator = MusicGenerator()
generator.save(generator.generate("epic cinematic orchestral music"), "epic_music.wav")
```

### Sound design batch processing

```python
from pathlib import Path
from audiocraft.models import AudioGen
import torchaudio

def batch_generate_sounds(sound_specs, output_dir):
    """sound_specs: list of {"name", "description", "duration"} dicts."""
    model = AudioGen.get_pretrained('facebook/audiogen-medium')
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    results = []
    for spec in sound_specs:
        model.set_generation_params(duration=spec.get("duration", 5))
        wav = model.generate([spec["description"]])
        output_path = output_dir / f"{spec['name']}.wav"
        torchaudio.save(str(output_path), wav[0].cpu(), sample_rate=16000)
        results.append({"name": spec["name"], "path": str(output_path)})
    return results

sounds = [
    {"name": "explosion", "description": "massive explosion with debris", "duration": 3},
    {"name": "footsteps", "description": "footsteps on wooden floor", "duration": 5},
]
batch_generate_sounds(sounds, "sound_effects/")
```

### Gradio demo

```python
import gradio as gr
import torch
import torchaudio
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained('facebook/musicgen-small')

def generate_music(prompt, duration, temperature, cfg_coef):
    model.set_generation_params(duration=duration, temperature=temperature, cfg_coef=cfg_coef)
    with torch.no_grad():
        wav = model.generate([prompt])
    path = "temp_output.wav"
    torchaudio.save(path, wav[0].cpu(), sample_rate=32000)
    return path

gr.Interface(
    fn=generate_music,
    inputs=[
        gr.Textbox(label="Music Description"),
        gr.Slider(1, 30, value=8, label="Duration (seconds)"),
        gr.Slider(0.5, 2.0, value=1.0, label="Temperature"),
        gr.Slider(1.0, 10.0, value=3.0, label="CFG Coefficient"),
    ],
    outputs=gr.Audio(label="Generated Music"),
    title="MusicGen Demo",
).launch()
```

## Performance optimization

```python
# Smaller model + half precision + shorter durations cut VRAM
model = MusicGen.get_pretrained('facebook/musicgen-small')
model = model.half()
model.set_generation_params(duration=10)
torch.cuda.empty_cache()  # clear cache between generations

# Batch prompts in one call rather than looping (faster)
wav = model.generate(["prompt1", "prompt2", "prompt3", "prompt4"])
```

### GPU memory requirements

| Model | FP32 VRAM | FP16 VRAM |
|-------|-----------|-----------|
| musicgen-small | ~4GB | ~2GB |
| musicgen-medium | ~8GB | ~4GB |
| musicgen-large | ~16GB | ~8GB |
</content>
</invoke>
