---
name: rust-pq-crypto
version: 0.1.0
description: >
  Post-quantum cryptography in Rust under a strict HYBRID-ONLY doctrine — ML-KEM (FIPS 203) key
  encapsulation and ML-DSA (FIPS 204) signatures always PAIRED with a classical primitive, because
  every pure-Rust PQ crate is explicitly unaudited. Covers the verified crate shortlist (rustls
  X25519MLKEM768 PQ-TLS, rust-hpke X-Wing envelopes, RustCrypto ml-kem 0.3.2 / ml-dsa 0.1.1,
  liboqs/pqcrypto DEV-only oracles, ngrok TCP/TLS-only tunnels, WireGuard+Rosenpass,
  age at rest), key lifecycle (generation, secret storage, rotation, hybrid co-signing), and tunnel
  hardening for a harness↔remote-MCP pipeline. Use when adding quantum-resistant TLS, encrypting
  agent/remote-MCP payloads end-to-end, hybrid co-signing skills/eval-artifacts/workflow bundles,
  choosing a Rust PQ crate + Cargo feature flags, or hardening a remote tunnel. NOT for JS/browser PQ
  signing (use quantum-signing), classical-only choices with no PQ requirement (RSA/AES/ECDSA/plain
  TLS), general non-PQ key management, or non-Rust stacks.
license: >
  HyperFrequency original. Written from the neuro-centrifuge autoresearch §f crate shortlist
  (live-verified 2026-07-02) and public crate documentation; no code copied from any donor. rustls /
  ngrok-rust API facts cross-checked against upstream. Cross-links the sibling quantum-signing skill.
---

# Rust Post-Quantum Crypto

Add post-quantum resistance to a Rust service **without ever betting on an unaudited primitive
alone.** The whole skill is one rule with a supporting stack: **hybrid-only** — every PQ algorithm
rides alongside a battle-tested classical one, so a break in the young PQ code (or the young Rust
implementation of it) degrades to today's security, never to zero.

This is the Rust counterpart to the JS-only `quantum-signing` skill. It targets the D4
remote-MCP-actions pipeline: `harness worker → [HPKE X-Wing envelope] → rustls PQ-TLS →
{ngrok TCP/TLS tunnel | WireGuard+Rosenpass VPN} → mcp-context-forge → remote MCP action`, with
Ed25519+ML-DSA hybrid signatures on every shipped artifact.

## When to use vs. when not

Use this skill when the task is Rust and post-quantum:
- Turning on quantum-resistant TLS (`X25519MLKEM768`) on a link and **proving** the negotiated group.
- Envelope-encrypting remote-MCP / agent payloads so plaintext never exists at a tunnel edge.
- Hybrid co-signing skills, eval artifacts, or workflow bundles (Ed25519 **+** ML-DSA).
- Picking a PQ crate and its Cargo features, or wiring a dev-only KAT cross-check oracle.
- Hardening a harness↔remote tunnel (ngrok / WireGuard / Rosenpass) as defense-in-depth.

Do NOT use this skill for:
- **JS / browser / Node PQ signing** — that is `quantum-signing` (ML-DSA-65 via `agentic-jujutsu`).
- **Classical-only crypto** with no stated PQ requirement — plain TLS, RSA, AES, ECDSA, password
  hashing, HMAC integrity. PQ adds cost and immature code; do not impose it unasked.
- **General key management** unrelated to PQ (secret rotation for an API token, etc.).
- **Non-Rust stacks** — the crate choices here are Rust-specific.

## The doctrine in one paragraph

Standardized ≠ audited-in-Rust. FIPS 203/204 are final, but the pure-Rust `ml-kem` and `ml-dsa`
crates carry an explicit "**never independently audited**" warning, and hybrid-Rust PQ-TLS is new.
So **PQ is additive, never substitutive**: classical X25519/Ed25519 stays load-bearing underneath.
An attacker must break **both** the classical and the PQ leg to win. This costs a few KB and a few
ms — cheap insurance. Full reasoning, the "what does paired mean per layer" table, and the
downgrade/negotiation checks are in `references/hybrid-doctrine.md`.

## The stack (two crypto layers, two network legs)

Route to `references/crate-shortlist.md` for the full table with versions, feature flags, and
adopt/skip decisions. The shape:

| Concern | Crate | One-line rule |
|---|---|---|
| Transport TLS | **rustls** (aws-lc-rs provider) | `X25519MLKEM768` is default-on; **assert** the negotiated group. |
| E2E message envelope | **rust-hpke 0.13** (X-Wing) | Envelope every payload at the harness boundary; edge sees only ciphertext. |
| PQ primitives (app) | **RustCrypto ml-kem 0.3.2 / ml-dsa 0.1.1** | Hybrid-only co-signing; unaudited — never sole protection. |
| Test oracles | **liboqs (oqs) / pqcrypto** | **DEV-DEPENDENCY ONLY** — known-answer cross-validation; C-FFI stays out of runtime. |
| Tunnel ingress | **ngrok-rust** | `TcpTunnelBuilder`/`TlsTunnelBuilder` **only** — never HTTP endpoints (edge-terminated TLS). |
| VPN leg | **WireGuard + Rosenpass** | Defense-in-depth beneath TLS/HPKE; never build on abandoned boringtun master. |
| At rest | **age (rage) 0.11** | Artifacts/config at rest only; no PQ recipient — pair with the HPKE envelope for PQ-sensitive data. |

## References

- `references/crate-shortlist.md` — the full two-layer/two-leg adoption table: exact crate versions,
  Cargo feature flags, the FIPS/audit status of each, `SKIP`ped alternatives (snow, HTTP tunnels,
  boringtun) and adjacents (rpxy, cryptography.rs).
- `references/hybrid-doctrine.md` — why hybrid-only, the per-layer "what is paired with what" map,
  the Ed25519+ML-DSA co-signature construction, and the negotiation/downgrade assertions that make
  the doctrine *verifiable* rather than aspirational.
- `references/tunnel-hardening.md` — the full pipeline blueprint, the ngrok TCP/TLS-only rule and why
  HTTP endpoints leak, the WireGuard+Rosenpass PSK-rotation leg, and the D1/D9 container constraints.
- `references/key-lifecycle.md` — generation, secret-key storage (env/secret-manager, never logged),
  rotation + re-registration, at-rest encryption with `age`, and the artifact-signing lifecycle.
- `references/api-sketches.md` — concrete, version-pinned Rust snippets for each crate (rustls
  provider config + group assertion, ml-kem encaps/decaps, ml-dsa sign/verify, HPKE seal/open, ngrok
  tcp/tls builder, age encrypt), each flagged "verify current signature on docs.rs".

## Boundaries & failure modes

- **Never ship a pure-PQ path.** If a design has ML-KEM or ML-DSA as the *only* barrier, it is wrong
  by this skill's doctrine — add the classical leg or stop.
- **Assert, don't assume.** "PQ-TLS is on by default" is not proof. A conformance test must read the
  negotiated `NamedGroup` and fail if it is not `X25519MLKEM768`; a silent classical-only downgrade
  is the exact failure this skill exists to catch.
- **Keep C-FFI out of the runtime tree.** liboqs/pqcrypto are `[dev-dependencies]` for KAT oracles
  only; a C dependency in the shipped binary violates the own-code (D1) doctrine.
- **ngrok is a dumb pipe.** HTTP endpoints terminate TLS at the ngrok edge — plaintext there. Only
  TCP/TLS tunnels, and the HPKE envelope holds *regardless* of the tunnel type.
- **Version drift.** These crates move fast (ml-dsa is 0.1.x, hpke 0.13→0.14 pending). Treat pinned
  versions and method signatures as of-a-date; re-verify against docs.rs before relying on an exact
  API. `references/api-sketches.md` marks every signature that must be re-checked.
- **age has no PQ recipient.** Do not mistake at-rest `age` for quantum-safe storage; quantum-
  sensitive artifacts also need the HPKE X-Wing envelope.

## Related skills

- **quantum-signing** — the sibling: ML-DSA-65 signing in **JavaScript** via `agentic-jujutsu`. Same
  FIPS 204 algorithm, different language and no hybrid doctrine. Use it for JS/Node; use this for Rust.
- **temporal-developer / temporal-design** — the durable workflows that carry these signed artifacts
  and drive the remote-MCP actions this pipeline protects.
- **trajectory-miner / hitl-interview** — downstream consumers of the signed eval artifacts and the
  HITL gates that sit in front of destructive remote actions.
