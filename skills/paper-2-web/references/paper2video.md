# Paper2Video: Presentation Video

Generates a narrated presentation video from a paper. Best driven from **LaTeX source**. The video component is `showlab/Paper2Video`, orchestrated inside Paper2All.

## Module chain

1. **Slides** — extract key content, allocate across slides, embed figures/tables/equations, keep text density readable.
2. **Subtitles/script** — natural narration script, timed to slide transitions, TTS-friendly, multi-language capable.
3. **Speech** — synthesize narration (voice/accent/pacing controls), handle technical terms.
4. **Cursor** — simulated presenter cursor that highlights and guides attention, synced to narration.
5. **Talking-head (optional)** — realistic lip-synced presenter via **Hallo2**. Needs a reference image/clip and a large NVIDIA GPU; adds ~2–3× runtime.

## Invocation

Lightweight (no talking-head), the corroborated entry point:

```bash
python pipeline_light.py \
  --model_name_t <text_model> \
  --model_name_v <visual_model> \
  --result_dir <out_dir> \
  --paper_latex_root <paper_dir>
```

`--model_name_t` drives script/subtitle generation; `--model_name_v` drives slide/visual generation. Talking-head is documented upstream via an `--enable-talking-head`-style flag on the combined pipeline — **the exact flag and any duration/pacing/voice/resolution flags are version-dependent; confirm with `--help`.** Do not assume flags like `--video-duration`, `--slides-per-minute`, `--voice`, `--video-resolution`, or `--video-fps` exist verbatim in your build.

## Output tree (approximate)

```
<out_dir>/<paper_name>/video/
├── final_video.mp4
├── slides/            # slide_001.png ...
├── audio/             # narration + optional background
├── subtitles/         # .srt / .vtt
├── script/            # full narration + per-slide notes
└── metadata/          # timings.json, video_info.json
```

## Pacing and duration guidance

- Video abstract: ~3–5 min. Conference talk: ~10–20 min. Detailed walkthrough: ~30–45 min.
- ~2–3 slides/minute for technical content.
- 1920×1080 standard; 3840×2160 for high quality. Audio ≥192 kbps for clear speech.

## Presentation styles

Academic (formal, comprehensive), Conference (key findings, faster), Public (simplified, story-driven), Tutorial (step-by-step). Choose to match the venue.

## Resources and time

- Without talking-head: ~10–30 min/paper. With talking-head: ~30–120 min/paper.
- CPU multi-core; RAM 16 GB min (32 GB for large papers); talking-head requires a large NVIDIA GPU (upstream cites an A6000-class 48 GB card for Hallo2); storage 1–5 GB/video.

## Troubleshooting

- **LaTeX parse errors** → confirm the source compiles; check custom packages and missing referenced files.
- **Speech artifacts** → adjust audio settings, reformat problem text, try another voice.
- **Render failures** → check disk space and that system deps (LibreOffice, Poppler) are installed; read the run's error log.
- **Talking-head errors** → verify GPU memory and CUDA drivers; check reference-image quality/format.

## Review

Watch the whole video: audio/slide sync, figure legibility, subtitle accuracy, and that narration faithfully reflects the paper. Cursor motion should feel natural.

## Combine with

Embed the video in the Paper2Web homepage; reuse the Paper2Poster color scheme for a consistent look.
