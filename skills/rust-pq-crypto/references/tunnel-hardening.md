# Tunnel hardening — the harness↔remote-MCP pipeline

The two crypto layers protect *data*; the two network legs protect *transport*. This file is the
concrete blueprint for getting a payload from a harness worker to a remote MCP action without ever
exposing plaintext at an edge, plus the container constraints (D1 own-code, D9 allowlist) that
constrain the choices.

## The pipeline blueprint

```
harness worker
   │  1. HPKE X-Wing envelope   (rust-hpke — payload sealed here; plaintext ends here)
   ▼
[ sealed payload ]
   │  2. rustls PQ-TLS          (X25519MLKEM768 — hop encryption)
   ▼
{ ngrok TCP/TLS tunnel   OR   WireGuard + Rosenpass VPN }   3. transport leg
   ▼
mcp-context-forge aggregator container
   │  4. Ed25519+ML-DSA hybrid signatures verified on any shipped artifact
   │  5. forgecode-style policy Confirm gate + D8 HITL spine BEFORE any destructive action
   ▼
remote MCP action
```

Read the layers as nested envelopes: **HPKE is innermost** (end-to-end, survives every hop), **TLS is
per-hop**, **the tunnel/VPN is the pipe**. Even if the tunnel or TLS terminates somewhere you don't
control, the HPKE envelope keeps the payload sealed to the true endpoint.

## Leg A — ngrok ingress (the TCP/TLS-only rule)

`ngrok-rust` is the official in-process agent SDK — no sidecar binary, so it is D1-clean (own-code:
the tunnel is a library call, not a spawned service).

**The rule:** `TcpTunnelBuilder` / `TlsTunnelBuilder` **only**. Never `HttpTunnelBuilder`.

- **Why HTTP endpoints are banned:** an ngrok HTTP endpoint is **TLS-terminated at the ngrok edge**.
  Your traffic is plaintext on ngrok's servers between the edge and your agent. That breaks the whole
  posture. A TCP or TLS tunnel is an opaque byte pipe — ngrok never sees inside.
- Builder entry points: `Session::tcp_endpoint()` and `Session::tls_endpoint()` (returning the
  respective builders); do **not** use `http_endpoint()`. Verify exact method names against the
  ngrok-rust version you pin (0.14/0.18) on docs.rs.
- **The HPKE envelope holds regardless.** ngrok is treated as a *dumb pipe* — even a TLS tunnel is
  belt to the HPKE suspenders. Never rely on the tunnel alone.
- **Edge defense-in-depth:** ngrok edge OIDC, Policy rules, and IP restrictions are welcome *extra*
  layers, configured via `ngrok-api-rs` (0.12.0). They are additive, never a substitute for HPKE.
- **Authtoken hygiene:** the ngrok authtoken comes from an **environment variable only** — never
  committed, never logged (see `key-lifecycle.md` for the secret-handling rules).

## Leg B — WireGuard + Rosenpass VPN (defense-in-depth beneath TLS/HPKE)

This leg is *underneath* TLS/HPKE, not a replacement for the primary boundary.

- **Data plane:** kernel **WireGuard**, config-managed by the harness. If an embedded in-process Rust
  tunnel is genuinely required (no kernel access), use **NepTUN v1.0.8** — Cloudflare's maintained
  boringtun successor.
- **PQ layer:** **Rosenpass** performs a post-quantum key-agreement and rotates a fresh PQ pre-shared
  key into WireGuard's PSK slot roughly every 2 minutes. WireGuard's classical Noise handshake stays
  intact underneath — this is exactly the hybrid pattern (classical WG + PQ PSK). Rosenpass is
  ProVerif-analyzed.
- **Deployment constraint:** Rosenpass runs as its **own process**, so it is either a supervised host
  binary or requires an explicit **D9 container-allowlist amendment**. Decide which before wiring it
  in; do not smuggle a process into an allowlisted container.
- **Hard don't:** never build on `cloudflare/boringtun` **master** — it is unmaintained, its README
  warns against production use, and Mullvad abandoned it. Kernel WireGuard or NepTUN only.

## Container / doctrine constraints that shape these choices

- **D1 (own-code):** the shipped runtime is Rust, no C-FFI. That is why liboqs/pqcrypto are dev-only,
  why ngrok-rust (in-process, no sidecar) is preferred over a spawned ngrok binary, and why a spawned
  Rosenpass process needs an explicit exception rather than a silent bundle.
- **D9 (container allowlist):** every network tool is a *feature* the harness links or supervises,
  never a free-floating service. A process that needs to run (Rosenpass) must be named in the
  allowlist.
- **rpxy (adjacent):** `junkurihara/rust-rpxy` is a PQ-TLS-capable reverse proxy — a candidate front
  for the mcp-context-forge container if a proxy tier is later needed. Noted, not yet adopted.

## The gate in front of destructive actions

Transport hardening does not authorize the action. Before any destructive remote MCP action:

- Verify the **Ed25519+ML-DSA hybrid signatures** on any shipped artifact (both required — see
  `hybrid-doctrine.md`).
- Pass a **forgecode-style policy Confirm gate** (Allow / Deny / Confirm) and the **D8 HITL spine** —
  a human approval signal — before the action fires. Crypto proves *authenticity and
  confidentiality*; the HITL gate provides *authorization*. Keep them distinct.

## Checklist

- [ ] Tunnel is `TcpTunnelBuilder` or `TlsTunnelBuilder` — **never** HTTP.
- [ ] HPKE X-Wing envelope applied at the harness boundary, independent of the tunnel type.
- [ ] rustls handshake asserts `X25519MLKEM768` (conformance test, fail-closed).
- [ ] Rosenpass process is allowlisted (D9) if used; not built on boringtun master.
- [ ] ngrok authtoken from env only; edge OIDC/IP-restriction as *extra* layers.
- [ ] Hybrid signatures verified + HITL Confirm gate passed before any destructive action.
