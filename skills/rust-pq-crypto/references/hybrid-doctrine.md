# Hybrid-only doctrine — the one rule, made verifiable

Everything in this skill descends from a single principle. This file explains *why* it holds, *what*
"paired" means at each layer, and *how* to assert it so the doctrine is checkable in CI rather than a
comment in a design doc.

## Why hybrid-only

Three independent risks stack on any pure-Rust post-quantum deployment:

1. **The algorithm might be wrong.** ML-KEM (FIPS 203) and ML-DSA (FIPS 204) are final standards, but
   lattice cryptanalysis is young relative to RSA/ECC. A structural break, while unlikely, is not the
   decades-tested "unlikely" of X25519.
2. **The Rust implementation might be wrong.** `ml-kem` and `ml-dsa` ship with an explicit
   **"never independently audited"** warning. Constant-time bugs, decapsulation-failure handling,
   and side channels are exactly where young implementations fail — and those bugs don't show up in
   functional tests.
3. **The integration might be wrong.** Hybrid PQ-TLS, X-Wing HPKE, and Rosenpass-into-WireGuard are
   all recent glue. New glue has new edges.

Against all three, the mitigation is the same: **never let a PQ primitive be the only barrier.** Pair
it with a classical primitive that has 15+ years of scrutiny. To win, an attacker must break **both**
legs — the classical one (needs a large fault-tolerant quantum computer that does not yet exist) *and*
the PQ one (needs a classical break of the lattice scheme or its Rust code). The two failure modes are
uncorrelated, so the combined security is the *max*, not the *min*, of the two.

The cost is small and bounded: a few KB of extra handshake/signature bytes and single-digit
milliseconds of CPU. That is cheap insurance against a catastrophic-but-plausible tail.

**The corollary is a hard gate:** any design where ML-KEM or ML-DSA is the *sole* protection is wrong
by this skill's doctrine. Add the classical leg or do not ship.

## What "paired" means, layer by layer

| Layer | Classical leg | PQ leg | How they are combined |
|---|---|---|---|
| Transport TLS | X25519 | ML-KEM-768 | `X25519MLKEM768` hybrid group — the TLS 1.3 key schedule mixes **both** shared secrets; breaking one still leaves the other. rustls does this natively and by default. |
| Message envelope | X25519 | ML-KEM-768 | **X-Wing** KEM inside HPKE (RFC 9180). The KEM combiner derives one shared secret from both; ChaCha20Poly1305 does the AEAD. |
| Artifact signatures | Ed25519 | ML-DSA-65 | **Two independent signatures** over the same message digest. A verifier requires **both** to validate. This is a concatenation/co-signature, not a combined scheme — keep both keys, ship both signatures. |
| VPN | WireGuard's Noise (X25519) | Rosenpass PQ PSK | Rosenpass feeds a rotating PQ pre-shared key into WireGuard's existing PSK slot; WireGuard's classical handshake stays intact underneath. |
| At rest | age (X25519 recipients) | *(none available)* | age has no PQ recipient — so PQ-sensitive data at rest must **also** carry the HPKE X-Wing envelope. This is the one layer where "paired" means "wrap it a second way." |

## The Ed25519 + ML-DSA co-signature construction

For signing skills, eval artifacts, and workflow bundles:

- **Sign:** compute `digest = SHA3-512(canonical_bytes)` once; produce `sig_ed = Ed25519.sign(digest)`
  and `sig_mldsa = ML-DSA-65.sign(digest)`. Attach **both** plus **both** public keys (or key ids).
- **Verify:** accept **only if both** verify against their respective keys over the same digest. A
  single valid signature is a **reject** — that is the whole point; a break in either scheme cannot
  forge an accepted artifact.
- **Canonicalization first.** Both signatures cover the *same* canonical byte serialization. If the
  serialization is ambiguous, an attacker can craft two decodings with one signature — canonicalize
  before hashing, and pin the codec version in the signed envelope.
- **Store keys separately, rotate together.** See `key-lifecycle.md`.

This mirrors the JS `quantum-signing` skill's ML-DSA-65 signing, but adds the classical Ed25519 leg
the JS skill does not carry — because in Rust we control both and pairing is free.

## Making the doctrine *verifiable* (not just aspirational)

A doctrine you cannot test will silently rot into a classical-only or PQ-only deployment. Assert it:

- **Negotiated-group assertion (TLS).** After the handshake, read the negotiated key-exchange group
  and **fail closed** if it is not `NamedGroup::X25519MLKEM768`. A middlebox, an old peer, or a
  provider misconfig can silently drop you to classical-only X25519 — this test is the tripwire. Make
  it a D2 conformance test on every link, not a one-time manual check.
- **Both-signatures-required assertion.** A unit test that (a) a valid Ed25519-only artifact is
  **rejected**, (b) a valid ML-DSA-only artifact is **rejected**, (c) only both-valid passes, and
  (d) tampering either signature or the payload fails. Negative tests are the ones that catch a
  verifier that "helpfully" accepts one leg.
- **KAT cross-validation.** In the parity suite (dev-only), cross-check `ml-kem`/`ml-dsa`/X-Wing
  against liboqs/pqcrypto known-answer vectors so an implementation regression in the unaudited Rust
  crate is caught before it ships. See `key-lifecycle.md`.
- **Downgrade / stripping tests.** Confirm that removing the PQ leg (forcing a classical-only tunnel,
  or stripping the ML-DSA signature) is *detected and rejected*, not silently tolerated.

## Anti-patterns this doctrine forbids

- Shipping a pure-PQ path "because FIPS says it's standardized."
- Trusting "PQ-TLS is on by default" without asserting the negotiated group.
- Accepting an artifact on a *single* valid signature.
- Pulling liboqs/pqcrypto (C-FFI) into the runtime to "just use the mature one" — it defeats the
  own-code doctrine and doesn't remove the need for the classical leg anyway.
- Treating at-rest `age` as quantum-safe.
