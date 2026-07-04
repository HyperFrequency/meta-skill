# Key lifecycle — generation, storage, rotation, signing, KAT validation

PQ keys are bigger, the crates are younger, and hybrid means you carry *two* keypairs per identity.
This file is the operational discipline: how keys are born, stored, rotated, used to sign, and
validated against a trusted oracle — all under the hybrid-only doctrine.

## Key sizes (plan storage and payloads accordingly)

| Key / output | Approx size | Notes |
|---|---|---|
| ML-KEM-768 encapsulation (public) key | ~1184 B | app-layer KEM public key |
| ML-KEM-768 decapsulation (secret) key | ~2400 B | keep secret; never logged |
| ML-KEM-768 ciphertext | ~1088 B | per-encapsulation |
| ML-DSA-65 public key | ~1952 B | ships with every signed artifact (or by key id) |
| ML-DSA-65 secret key | ~4032 B | secret |
| ML-DSA-65 signature | ~3309 B | attached per artifact |
| Ed25519 public / secret / signature | 32 / 32 / 64 B | the classical co-key — negligible next to ML-DSA |

The classical leg is tiny; the PQ leg dominates. A hybrid co-signature is ~3.4 KB — budget for it in
payload-size ceilings and CAS-offload thresholds.

## Generation

- Generate from a **CSPRNG** (`rand::rngs::OsRng` or the crate's required `CryptoRng`). Never a seeded
  or reused RNG for real keys.
- **Hybrid identities are two keypairs generated together:** an Ed25519 pair *and* an ML-DSA-65 pair
  (for signing identities), or an X25519 pair *and* an ML-KEM-768 pair (for KEM identities). Bind them
  under one logical identity id so they rotate as a unit.
- For **very long-lived** keys where you want a hash-based fallback, `pqcrypto`'s **SPHINCS+** is the
  conservative option (larger signatures, minimal structural assumptions).

## Secret-key storage (credential safety)

- Load secret keys from a **secret manager or environment variable** at runtime — **never** hardcode,
  never commit, never write to logs or traces. This holds for the ngrok authtoken too.
- **Never `cat`/`echo`/print a secret key** to verify it exists — check length or a public fingerprint
  instead. A secret in the transcript or a log line is a leak.
- At rest, wrap secret-key material with **`age`** (see below). For quantum-sensitive secret material,
  `age` alone is not enough (no PQ recipient) — add the HPKE X-Wing envelope.
- Zeroize in-memory secret buffers after use where the crate exposes it (`Zeroizing`/`zeroize`).

## At-rest encryption with age

- `age` 0.11.2 encrypts artifacts, config, and wrapped secret keys **at rest**.
- **PQ caveat (repeat):** age has no post-quantum recipient. It protects against *classical* disk
  compromise today. Anything that must resist a future quantum adversary at rest also gets the HPKE
  X-Wing envelope — age is the classical leg, HPKE is the PQ leg, and that pairing keeps the doctrine.

## Rotation

- **Rotate the hybrid pair as a unit** — both the classical and PQ key at once — and **re-register the
  new public keys** with whatever verifies them (the coordinator, the artifact registry, the peer).
- Keep the previous public keys valid for a grace window so in-flight artifacts signed under the old
  keys still verify; expire them on a schedule.
- Rotation cadence is policy, not crypto: rotate signing identities periodically and on any suspected
  compromise. The Rosenpass PSK rotates automatically (~2 min) — that is a *different*, transport-leg
  rotation and is handled by Rosenpass, not this lifecycle.
- Record key id + valid-from/valid-until in the signed envelope so a verifier can select the right
  public key deterministically.

## The signing lifecycle (Ed25519 + ML-DSA co-signature)

1. **Canonicalize** the artifact to a pinned byte serialization (codec version recorded in the
   envelope). Ambiguous serialization + one signature = forgeable; canonicalize first.
2. `digest = SHA3-512(canonical_bytes)`.
3. `sig_ed = Ed25519.sign(digest)` **and** `sig_mldsa = ML-DSA-65.sign(digest)`.
4. Attach both signatures, both public keys (or key ids), the codec version, and the key
   valid-from/until window.
5. **Verify = both must pass** over the same digest against the registered keys. One-of-two is a
   **reject** (test this explicitly — see `hybrid-doctrine.md`). Tampering payload or either signature
   fails.

This is the Rust hybrid analogue of the JS `quantum-signing` flow (which signs with ML-DSA-65 alone);
here the classical Ed25519 leg is added because pairing is free when you own both keys.

## KAT cross-validation (the unaudited-crate safety net)

Because `ml-kem`/`ml-dsa` are unaudited, the parity/conformance suite (dev-only) must catch an
implementation regression before it ships:

- **Known-answer tests:** feed fixed NIST/FIPS test vectors through the pure-Rust crate and assert the
  outputs match. Cross-check against **liboqs (`oqs`)** and **`pqcrypto`** (PQClean) — mature C
  implementations — as independent oracles. `[dev-dependencies]` only; the C-FFI never enters the
  runtime binary (D1).
- **Round-trip properties:** `decapsulate(encapsulate()) == shared_secret`; `verify(sign(m), m)` true;
  `verify(sign(m), m')` false for `m' != m`; decapsulation-failure paths handled (implicit rejection,
  not a panic).
- **X-Wing / HPKE:** seal-then-open round-trips and cross-checks against a reference X-Wing vector.
- Run these in CI so a bad crate bump is caught by the parity suite, not in production.

## Lifecycle checklist

- [ ] Keys from a CSPRNG; hybrid pairs generated and rotated as a unit.
- [ ] Secret keys from secret-manager/env; never logged, printed, or committed; zeroized after use.
- [ ] At-rest via `age`; PQ-sensitive material *also* HPKE-enveloped.
- [ ] Signing canonicalizes → SHA3-512 → **both** Ed25519 and ML-DSA; verify requires both.
- [ ] Rotation re-registers new public keys with a grace window; key ids recorded in the envelope.
- [ ] KAT cross-validation vs liboqs/pqcrypto in the dev-only parity suite, in CI.
