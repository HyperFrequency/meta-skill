# Crate shortlist — the verified two-layer / two-leg stack

All versions and behaviors below were live-verified 2026-07-02 for the neuro-centrifuge D4
remote-MCP-actions pipeline. Two **crypto** layers (transport + message) and two **network** legs
(tunnel + VPN), plus at-rest. Every row obeys the hybrid-only doctrine; the pure-Rust PQ crates are
flagged unaudited on purpose.

Re-verify a version against docs.rs before pinning — this space moves monthly.

## Transport TLS — rustls (the backbone)

- **Crate:** `rustls` 0.23.41+ with the **aws-lc-rs** provider (default). In rustls the crypto
  provider is pluggable; `rustls-aws-lc-rs` is the recommended first-party provider and the one that
  ships PQ support. (`rustls-ring` exists for platform-compat but has a narrower feature set and is
  not the PQ path.)
- **What you get for free:** `X25519MLKEM768` hybrid key exchange is **on by default** for TLS 1.3
  handshakes. The named group is `rustls::NamedGroup::X25519MLKEM768` — a hybrid of classical X25519
  and ML-KEM-768. OpenSSL 3.5+ and BoringSSL default to the same group, so interop is real.
- **`rustls-post-quantum`** is a *separate* helper crate — only needed for *pure* MLKEM768 (non-
  hybrid) or experimental ML-DSA certificate work. You do **not** need it just to get the default
  hybrid KX; reach for it only for the experimental pure-PQ modes.
- **FIPS:** the `fips` feature is available; AWS-LC holds the first FIPS 140-3 validation that
  includes ML-KEM. Turn it on only if you actually need the validated-module posture (it constrains
  the build and provider).
- **Decision:** ADOPT as the transport backbone on every harness↔ContextForge↔remote-MCP link. The
  D2 conformance test **must assert** the negotiated group is `X25519MLKEM768` (see
  `hybrid-doctrine.md` — a silent classical-only downgrade is the failure mode this catches).

## End-to-end message envelope — rust-hpke (X-Wing)

- **Crate:** `rust-hpke` 0.13.0 — RFC 9180 Hybrid Public Key Encryption, `no_std`-capable.
- **PQ KEM:** the **X-Wing** hybrid KEM = ML-KEM-768 combined with X25519, paired with a
  ChaCha20Poly1305 AEAD. Cloudflare-reviewed; this is the best security posture available among
  pure-Rust PQ constructions today.
- **Why an envelope on top of PQ-TLS:** TLS protects a *hop*. The HPKE envelope protects the
  *payload* end-to-end, so plaintext never exists at the ngrok edge, at a reverse proxy, or at any
  intermediary — even one that terminates TLS. Belt and suspenders, by design.
- **Migration note:** move to 0.14 when it stabilizes; the X-Wing type path may shift between minor
  versions, so pin exactly and re-check the KEM type name on docs.rs.
- **Decision:** ADOPT — envelope-encrypt every remote-MCP-actions payload at the harness boundary.

## PQ primitives, app layer — RustCrypto

- **Crates:** `ml-kem` 0.3.2 (FIPS 203 final) and `ml-dsa` 0.1.1 (FIPS 204 final). Both are **pure
  Rust, `no_std`**, from the RustCrypto org.
- **Audit status — read this twice:** both crates carry an explicit **"this crate has never been
  independently audited"** warning. FIPS-standardized algorithm ≠ audited Rust implementation. That
  is the entire reason for hybrid-only.
- **Use:** hybrid co-signing — **Ed25519 + ML-DSA** over skills, eval artifacts, and workflow
  bundles (and the PQ wallet-signing item, testnet first). ml-kem is the app-layer KEM where you
  need PQ key agreement outside a TLS/HPKE channel.
- **Decision:** ADOPT **hybrid-only**. Never the sole protection on anything.

## Test oracles — liboqs / pqcrypto (DEV-ONLY)

- **Crates:** `oqs` 0.11.0 (liboqs-rust, bindings to the C liboqs) and `pqcrypto` 0.18.1 (PQClean C
  bindings).
- **Role:** `[dev-dependencies]` **only**. Cross-validate the pure-Rust `ml-kem`/`ml-dsa`/X-Wing
  outputs against these mature C implementations via known-answer tests (KATs) in the parity suite.
- **Hard rule:** the C-FFI stays **out of the runtime tree** (own-code / D1 doctrine — no C in the
  shipped binary). `pqcrypto` is also the breadth fallback for algorithms RustCrypto lacks — e.g.
  **SPHINCS+** for very long-lived keys where a hash-based signature's conservative security is worth
  the size.
- **Decision:** DEV-DEPENDENCY ONLY.

## Tunnel ingress — ngrok-rust

- **Crate:** `ngrok` (ngrok-rust) 0.14/0.18 — the official agent SDK, runs **in-process** (no
  sidecar binary; D1-clean). Companion `ngrok-api-rs` (0.12.0) for config automation.
- **Hard rule:** use `TcpTunnelBuilder` / `TlsTunnelBuilder` **only** — never `HttpTunnelBuilder`
  (HTTP endpoints are TLS-terminated at the ngrok edge → plaintext there). The builder methods are
  `Session::tcp_endpoint()` / `tls_endpoint()`; avoid `http_endpoint()`.
- **Defense-in-depth at the edge:** ngrok edge OIDC / Policy / IP-restrictions are fine as extra
  layers, but the HPKE envelope holds **regardless** — ngrok is treated as a dumb pipe. Authtoken via
  **env var only**, never committed.
- **Decision:** ADOPT with the TCP/TLS-only rule.

## VPN leg — WireGuard + Rosenpass

- **Primary:** kernel **WireGuard**, config-managed by the harness. If an embedded in-process Rust
  tunnel is required instead, **NepTUN v1.0.8** (Cloudflare's maintained boringtun successor).
- **PQ layer:** **Rosenpass** rotates post-quantum pre-shared keys into WireGuard every ~2 minutes;
  it is ProVerif-analyzed. Rosenpass runs as its own process → a supervised host binary or an
  explicit D9 container-allowlist amendment.
- **Never:** build on `cloudflare/boringtun` master — unmaintained, its own README warns off, Mullvad
  abandoned it. Use kernel WireGuard or NepTUN.
- **Decision:** ADOPT as defense-in-depth *beneath* TLS/HPKE, not as the primary boundary.

## At rest — age (rage)

- **Crate:** `age` 0.11.2 (the `rage` project's library).
- **Use:** encrypt artifacts and config **at rest only**.
- **Limitation — important:** age has **no PQ recipient type**. It is not quantum-safe storage. Any
  quantum-sensitive artifact must *also* (or instead) get the HPKE X-Wing envelope.
- **Decision:** ADOPT for at-rest artifacts/config, with the PQ caveat above.

## SKIP list (deliberate non-adoptions)

- **Noise — `snow`:** no PQ. SKIP. `clatter` (PQNoise) is young — note it only if a non-TLS channel
  is ever unavoidable; avoid standing up a second handshake stack next to TLS.
- **ngrok HTTP endpoints:** SKIP (edge-terminated TLS = plaintext at the edge).
- **boringtun master:** SKIP (abandoned).

## Adjacents (noted, not yet adopted)

- **`junkurihara/rust-rpxy`** — a PQ-TLS-capable reverse proxy; candidate front for the
  mcp-context-forge container.
- **`cryptography.rs`** — the vetting index to consult before pulling any future crypto dep.
