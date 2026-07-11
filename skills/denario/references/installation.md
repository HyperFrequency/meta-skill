# Installation

## Requirements

- **Python 3.12+** (hard requirement — older interpreters fail at import).
- Linux, macOS, or Windows.
- A LaTeX distribution for paper compilation (or use the Docker image, which bundles one).
- A virtual environment is strongly recommended for isolation.

## Install methods

### uv (recommended)

```bash
uv init
uv add "denario[app]"      # [app] adds the Streamlit GUI dependency
```

### pip in a venv

```bash
python3 -m venv denario_env
source denario_env/bin/activate      # Windows: denario_env\Scripts\activate
uv pip install "denario[app]"        # or: pip install "denario[app]"
```

### From source (development / editable)

```bash
git clone https://github.com/AstroPilot-AI/Denario.git
cd Denario
python3 -m venv .venv && source .venv/bin/activate
uv pip install -e .
```

### Docker (bundles LaTeX)

```bash
docker pull pablovd/denario:latest
docker run -p 8501:8501 --rm pablovd/denario:latest              # GUI on :8501
docker run -p 8501:8501 --env-file .env --rm pablovd/denario:latest   # with API keys
```

Open `http://localhost:8501` once the container is up. If 8501 is taken, remap the host
side: `-p 8502:8501`.

## Verify

```bash
python -c "from denario import Denario; print('ok')"
python -c "import denario; print(denario.__version__)"
```

## Launch the GUI

```bash
denario run          # Streamlit app, default http://localhost:8501
```

## Bundled dependencies

Installing Denario pulls in the agent stack and common scientific libraries: **AG2**
(agent orchestration), **LangGraph** (graph workflows), plus pandas, scikit-learn,
scipy/numpy, and matplotlib/seaborn. The `[app]` extra adds Streamlit.

## LaTeX setup (for `get_paper` PDF output)

- **Linux**: `sudo apt-get install texlive-full`
- **macOS**: `brew install --cask mactex`
- **Windows**: install [MiKTeX](https://miktex.org/download) or TeX Live.
- **Docker**: the official image already contains a full LaTeX install — no host setup.

Without LaTeX, `get_paper()` still writes `paper.tex`; only the PDF compilation step fails.

## Update / uninstall

```bash
# update
uv add --upgrade denario        # or: uv pip install --upgrade "denario[app]"
docker pull pablovd/denario:latest

# uninstall
uv remove denario               # or: uv pip uninstall denario
docker rmi pablovd/denario:latest
```

## Install troubleshooting

- **Wrong Python version**: check `python --version`; if < 3.12, install a newer one or use
  `pyenv` to select it before creating the venv.
- **Permission errors**: prefer a virtual environment; `--user` installs are a fallback.
- **Dependency conflicts**: create a fresh venv rather than installing into a crowded
  environment.
- **Docker port conflict**: remap with `-p <free_host_port>:8501`.
- **venv not active**: re-run `source <env>/bin/activate` (Linux/macOS) or
  `<env>\Scripts\activate` (Windows).
