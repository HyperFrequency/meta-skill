# autoskill setup & prerequisites

Full install steps for the four dependencies autoskill needs. Run `python scripts/autoskill.py doctor` after setup to verify everything at once.

## 1. Screenpipe daemon

Either install the official release or build from source. Either way the daemon binds HTTP on `localhost:3030` by default.

**From source** (recommended if you want the CLI daemon without the desktop GUI):

```bash
git clone --depth 1 https://github.com/mediar-ai/screenpipe.git
cd screenpipe
cargo build -p screenpipe-engine --release
# System deps (macOS): cmake + full Xcode.app (not just Command Line Tools).
#   brew install cmake
#   # if xcodebuild plug-ins error: sudo xcodebuild -runFirstLaunch
./target/release/screenpipe doctor   # confirm permissions + ffmpeg
./target/release/screenpipe record --disable-audio --use-pii-removal
```

First run will prompt for macOS Screen Recording permission. Grant it and relaunch.

## 2. Screenpipe API token

The local API now requires bearer auth. Retrieve your token and export it:

```bash
export SCREENPIPE_TOKEN=$(screenpipe auth token)
```

(Or set `screenpipe.token` directly in `config.yaml` — env var is preferred since it keeps secrets out of version control.)

## 3. Python environment

Via `pipenv` from the repo root:

```bash
pipenv install httpx pyyaml sentence-transformers
```

The embedding model (`sentence-transformers/all-MiniLM-L6-v2`, ~80 MB) downloads on first run.

## 4. Local LLM (default path) — LM Studio

- Install [LM Studio](https://lmstudio.ai/).
- Download `Gemma-4-31B-it` (or another strong reasoning model; adjust `local.model` in `config.yaml`).
- Load it via the CLI for headless use (no GUI required):

```bash
lms load gemma-4-31b-it --context-length 131072 --gpu max -y
lms status   # confirm server running on :1234
```

## 5. Cloud LLM backends (optional, opt-in)

Only if you explicitly opt out of local:
- `claude`: set `ANTHROPIC_API_KEY`, flip `backend: claude` in `config.yaml`.
- `foundry`: set `FOUNDRY_API_KEY`, flip `backend: foundry`, set `foundry.endpoint` to your corporate gateway URL.
