# Section Templates

Copy-paste templates for every README section. The **Core Section Templates**
cover the standard structure (used by almost every project). The **Extended
Section Templates** further down cover specialized sections you add as needed.

See `SKILL.md` for the Golden Structure, Critical Rules, and Anti-Patterns that
govern *how* to assemble these.

---

# Core Section Templates

## Hero Section

```markdown
# tool-name

<div align="center">
  <img src="illustration.webp" alt="tool-name - One-line description">
</div>

<div align="center">

[![CI](https://github.com/user/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/user/repo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

One-sentence description of what this tool does and its key differentiator.

<div align="center">
<h3>Quick Install</h3>

```bash
curl -fsSL https://raw.githubusercontent.com/user/repo/main/install.sh | bash
```

**Or build from source:**

```bash
cargo install --git https://github.com/user/repo.git
```

</div>
```

## TL;DR Section

```markdown
## TL;DR

**The Problem**: [Specific pain point in 1-2 sentences. Be concrete.]

**The Solution**: [What this tool does to solve it. Action-oriented.]

### Why Use tool-name?

| Feature | What It Does |
|---------|--------------|
| **Feature 1** | Concrete benefit, not abstract capability |
| **Feature 2** | Another specific value proposition |
| **Feature 3** | Quantify when possible (e.g., "<10ms search") |
```

## Quick Example

```markdown
### Quick Example

```bash
# Initialize (one-time setup)
$ tool init

# Core operation
$ tool do-thing --flag value

# See results
$ tool show results

# The killer feature
$ tool magic --auto
```
```

## Comparison Table

```markdown
## How tool-name Compares

| Feature | tool-name | Alternative A | Alternative B | Manual |
|---------|-----------|---------------|---------------|--------|
| Feature 1 | ✅ Full support | ⚠️ Partial | ❌ None | ❌ |
| Feature 2 | ✅ <10ms | 🐢 ~500ms | ✅ Fast | N/A |
| Setup time | ✅ ~10 seconds | ❌ Hours | ⚠️ Minutes | ❌ |

**When to use tool-name:**
- Bullet point of ideal use case
- Another use case

**When tool-name might not be ideal:**
- Honest limitation
- Another case where alternatives win
```

## Installation Section

```markdown
## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/user/repo/main/install.sh | bash
```

**With options:**

```bash
# Auto-update PATH
curl -fsSL https://... | bash -s -- --easy-mode

# Specific version
curl -fsSL https://... | bash -s -- --version v1.0.0

# System-wide (requires sudo)
curl -fsSL https://... | sudo bash -s -- --system
```

### Package Managers

```bash
# macOS/Linux (Homebrew)
brew install user/tap/tool

# Windows (Scoop)
scoop bucket add user https://github.com/user/scoop-bucket
scoop install tool
```

### From Source

```bash
git clone https://github.com/user/repo.git
cd repo
cargo build --release
cp target/release/tool ~/.local/bin/
```
```

## Command Reference Pattern

```markdown
## Commands

Global flags available on all commands:

```bash
--verbose       # Increase logging
--quiet         # Suppress non-error output
--format json   # Machine-readable output
```

### `tool command`

Brief description of what this command does.

```bash
tool command                    # Basic usage
tool command --flag value       # With options
tool command --help             # See all options
```
```

## Architecture Diagram

```markdown
## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Input Layer                              │
│   (files, API calls, user commands)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Processing Layer                            │
│   Component A → Component B → Component C                        │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Storage A        │ │ Storage B        │ │ Output           │
│ - Detail 1       │ │ - Detail 1       │ │ - Format 1       │
│ - Detail 2       │ │ - Detail 2       │ │ - Format 2       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```
```

## Troubleshooting Pattern

```markdown
## Troubleshooting

### "Error message here"

```bash
# Solution
command to fix it
```

### "Another common error"

Explanation of why this happens and how to fix it.

```bash
# Check the state
diagnostic command

# Fix it
fix command
```
```

## Limitations Section

```markdown
## Limitations

### What tool-name Doesn't Do (Yet)

- **Limitation 1**: Brief explanation, workaround if any
- **Limitation 2**: Why this is out of scope

### Known Limitations

| Capability | Current State | Planned |
|------------|---------------|---------|
| Feature X | ❌ Not supported | v2.0 |
| Feature Y | ⚠️ Partial | Improving |
```

## FAQ Pattern

```markdown
## FAQ

### Why "tool-name"?

Brief etymology or meaning.

### Is my data safe?

Yes/No with explanation. Privacy guarantees.

### Does it work with X?

Compatibility information.

### How do I [common task]?

```bash
# Command to accomplish it
tool do-thing
```
```

## Badge Reference

Common badges for GitHub READMEs:

```markdown
# CI Status
[![CI](https://github.com/USER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/ci.yml)

# License
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# Version/Release
[![GitHub release](https://img.shields.io/github/v/release/USER/REPO)](https://github.com/USER/REPO/releases)

# Downloads
[![Downloads](https://img.shields.io/github/downloads/USER/REPO/total)](https://github.com/USER/REPO/releases)

# Crates.io (Rust)
[![Crates.io](https://img.shields.io/crates/v/CRATE.svg)](https://crates.io/crates/CRATE)

# npm (JavaScript)
[![npm](https://img.shields.io/npm/v/PACKAGE.svg)](https://www.npmjs.com/package/PACKAGE)

# PyPI (Python)
[![PyPI](https://img.shields.io/pypi/v/PACKAGE.svg)](https://pypi.org/project/PACKAGE/)
```

---

# Extended Section Templates

Additional templates for specialized README sections.

---

## Performance Section

For tools where speed matters:

```markdown
## Performance

`tool-name` is designed for speed:

| Operation | Time | Notes |
|-----------|------|-------|
| Startup | <50ms | Lazy initialization |
| Search | <10ms | Memory-mapped indices |
| Indexing | 1000 docs/sec | Parallel processing |

### Benchmarks

On a typical workload (10,000 items):

| Operation | tool-name | Alternative A | Alternative B |
|-----------|-----------|---------------|---------------|
| Cold start | 45ms | 230ms | 890ms |
| Warm query | 3ms | 15ms | 120ms |
| Memory (idle) | 12MB | 45MB | 200MB |

*Tested on M2 MacBook Pro, 16GB RAM. Your results may vary.*

### Optimizations

- **Lazy initialization**: Resources compiled on first use
- **Memory-mapped files**: OS-level caching
- **Parallel processing**: Multi-core utilization via rayon
- **Incremental updates**: Only process changed items
```

---

## Security Section

For tools handling sensitive data:

```markdown
## Security

### Your Data Never Leaves Your Machine

`tool-name` is designed with privacy as a non-negotiable:

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR MACHINE                            │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Input     │───▶│   Process   │───▶│   Output    │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                                             │
│  ❌ No network calls                                        │
│  ❌ No telemetry                                            │
│  ❌ No cloud sync                                           │
│  ❌ No API keys required                                    │
└─────────────────────────────────────────────────────────────┘
```

### What's Stored Where

| Location | Contents | Sensitive? |
|----------|----------|------------|
| `~/.tool/db.sqlite` | Metadata, indices | ⚠️ Yes |
| `~/.tool/cache/` | Temporary files | Low |
| Config file | Settings only | No |

### Secure Deletion

```bash
# Remove all tool data
rm -rf ~/.tool/

# Verify removal
ls ~/.tool/  # Should not exist
```
```

---

## Data Model Section

For tools with complex data structures:

```markdown
## Data Model

### What Gets Indexed

| Field | Indexed | Stored | Notes |
|-------|---------|--------|-------|
| `id` | ✅ Term | ✅ | Primary key |
| `content` | ✅ Full-text | ✅ | Searchable |
| `created_at` | ✅ Date | ✅ | For filtering |
| `metadata` | ❌ | ✅ | JSON blob |

### Schema

```sql
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX idx_created ON items(created_at);
CREATE VIRTUAL TABLE items_fts USING fts5(content);
```
```

---

## API Reference Section

For libraries with programmatic APIs:

```markdown
## API Reference

### Basic Usage

```rust
use tool_name::Client;

let client = Client::new()?;
let results = client.search("query")?;
```

### Configuration

```rust
let client = Client::builder()
    .with_timeout(Duration::from_secs(30))
    .with_retry(3)
    .build()?;
```

### Error Handling

```rust
match client.operation() {
    Ok(result) => println!("Success: {:?}", result),
    Err(Error::NotFound) => println!("Item not found"),
    Err(Error::Timeout) => println!("Operation timed out"),
    Err(e) => return Err(e.into()),
}
```

### Types

| Type | Description |
|------|-------------|
| `Client` | Main API client |
| `Config` | Configuration options |
| `Result<T>` | Operation result |
| `Error` | Error variants |
```

---

## Migration/Upgrade Section

For tools with breaking changes:

```markdown
## Upgrading

### From v1.x to v2.x

**Breaking changes:**
- Config file location changed from `~/.toolrc` to `~/.config/tool/config.toml`
- Command `tool old-cmd` renamed to `tool new-cmd`
- Flag `--old-flag` removed, use `--new-flag` instead

**Migration steps:**

```bash
# 1. Backup existing config
cp ~/.toolrc ~/.toolrc.backup

# 2. Install v2
curl -fsSL https://... | bash

# 3. Migrate config
tool migrate --from v1

# 4. Verify
tool doctor
```

### From v2.x to v3.x

No breaking changes. Upgrade in place:

```bash
tool update
```
```

---

## Contributing Section (Expanded)

For projects accepting contributions:

```markdown
## Contributing

### Development Setup

```bash
# Clone
git clone https://github.com/user/repo.git
cd repo

# Install dependencies
cargo build

# Run tests
cargo test

# Run lints
cargo clippy --all-targets -- -D warnings
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`cargo test`)
5. Run lints (`cargo clippy`)
6. Commit (`git commit -m 'Add amazing feature'`)
7. Push (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

- Follow Rust standard formatting (`cargo fmt`)
- All public APIs must have doc comments
- Tests required for new features
- No warnings from clippy

### Commit Messages

Format: `type(scope): description`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(search): add fuzzy matching support
fix(parser): handle empty input gracefully
docs(readme): add troubleshooting section
```
```

---

## Ecosystem/Integration Section

For tools in a larger ecosystem:

```markdown
## Ecosystem Integration

`tool-name` integrates with the following tools:

| Tool | Integration | Use Case |
|------|-------------|----------|
| **Tool A** | Native | Primary workflow |
| **Tool B** | Via CLI | Automation |
| **Tool C** | Plugin | IDE integration |

### With Tool A

```bash
# tool-name provides data to Tool A
tool export --format tool-a | tool-a import
```

### With Tool B

```bash
# Use tool-name output in Tool B pipelines
tool search "query" --format json | tool-b process
```

### IDE Integration

- **VS Code**: Install extension `tool-name-vscode`
- **JetBrains**: Plugin available in marketplace
- **Vim/Neovim**: See [vim-tool-name](https://github.com/user/vim-tool-name)
```

---

## Environment Variables Reference

```markdown
## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TOOL_HOME` | Data directory | `~/.tool` |
| `TOOL_CONFIG` | Config file path | `~/.config/tool/config.toml` |
| `TOOL_LOG_LEVEL` | Logging verbosity | `info` |
| `TOOL_NO_COLOR` | Disable colored output | unset |
| `TOOL_OFFLINE` | Disable network access | unset |

### Example

```bash
# Use custom data directory
export TOOL_HOME=/data/tool

# Enable debug logging
export TOOL_LOG_LEVEL=debug

# Run tool
tool command
```
```

---

## Shell Completion Section

```markdown
## Shell Completions

### Bash

```bash
# Add to ~/.bashrc
eval "$(tool completions bash)"

# Or generate file
tool completions bash > ~/.local/share/bash-completion/completions/tool
```

### Zsh

```bash
# Add to ~/.zshrc
eval "$(tool completions zsh)"

# Or generate file
tool completions zsh > ~/.zfunc/_tool
```

### Fish

```bash
tool completions fish > ~/.config/fish/completions/tool.fish
```

### PowerShell

```powershell
tool completions powershell | Out-String | Invoke-Expression
```
```

---

## Release Notes Pattern

For CHANGELOG or release sections:

```markdown
## Release Notes

### v2.1.0 (2026-01-15)

**New Features:**
- Added `tool new-command` for X functionality
- Support for Y file format

**Improvements:**
- 40% faster search performance
- Better error messages for common failures

**Bug Fixes:**
- Fixed crash when input contains unicode
- Resolved memory leak in long-running sessions

**Breaking Changes:**
- None

### v2.0.0 (2025-12-01)

**Breaking Changes:**
- Config file format changed from JSON to TOML
- Removed deprecated `--old-flag`

See [Migration Guide](#upgrading) for upgrade instructions.
```

---

## Acknowledgments Section

```markdown
## Acknowledgments

Built with:
- [Rust](https://www.rust-lang.org/) — Systems programming language
- [Tantivy](https://github.com/quickwit-oss/tantivy) — Full-text search engine
- [SQLite](https://sqlite.org/) — Embedded database
- [clap](https://github.com/clap-rs/clap) — Command-line argument parsing

Inspired by:
- [ripgrep](https://github.com/BurntSushi/ripgrep) — Fast grep alternative
- [bat](https://github.com/sharkdp/bat) — Cat with wings

Special thanks to all [contributors](https://github.com/user/repo/graphs/contributors).
```
