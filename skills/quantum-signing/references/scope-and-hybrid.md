# Scope Boundary & Hybrid Doctrine

Where this skill stops and where `rust-pq-crypto` begins, and why the signatures produced here
are *pure* post-quantum rather than hybrid. See `SKILL.md` for the JS API, `usage-patterns.md`
for end-to-end flows, and `best-practices.md` for key handling.

## What lives here vs. what lives in `rust-pq-crypto`

Both skills implement the *same* NIST FIPS 204 signature algorithm (ML-DSA-65). They differ in
**language, surface, and doctrine** — pick by where the signing runs, not by the algorithm name.

| Question | This skill (`quantum-signing`) | Sibling (`rust-pq-crypto`) |
|---|---|---|
| Language / runtime | JavaScript / Node / browser | Rust |
| Library | `agentic-jujutsu` `QuantumSigner` | RustCrypto `ml-dsa` / `ml-kem`, rustls, rust-hpke |
| Signature scheme | ML-DSA-65 **alone** (pure PQ) | Ed25519 **+** ML-DSA-65 (hybrid co-signature) |
| Also covers | SHA3-512 fingerprints, JS op/commit/trajectory signing | PQ-TLS transport, HPKE envelopes, KEM, tunnel hardening |
| Typical caller | agent op signing in a JS coordination layer | harness worker → remote-MCP action pipeline |

**Route to `rust-pq-crypto` when:** the signing or co-signing happens in the Rust harness; you need
the classical + PQ *hybrid* co-signature on a shipped artifact; you need PQ **key encapsulation**
(ML-KEM), PQ-TLS, envelope encryption, or tunnel hardening. None of those exist in this JS skill.

**Stay here when:** the code doing the signing is JavaScript/Node/browser and a single ML-DSA-65
signature over the operation payload is what you need.

## Hybrid-only doctrine — and why this JS path is the exception

The sibling skill enforces a hard rule: **never let a post-quantum primitive be the only barrier.**
Every PQ algorithm there rides alongside a classical one (Ed25519 alongside ML-DSA, X25519 alongside
ML-KEM), because every pure-Rust PQ crate ships with an explicit **"never independently audited"**
warning. If the young lattice code — or its young implementation — has a structural or side-channel
break, a hybrid construction degrades to today's classical security instead of to zero. An attacker
must break **both** legs, and the two failure modes are uncorrelated, so the combined strength is the
*max* of the two, not the *min*. The cost is a few KB and single-digit milliseconds — cheap insurance.

**This JS skill does not carry that classical leg.** `QuantumSigner` produces a single ML-DSA-65
signature. That is a deliberate, documented limitation, not an oversight:

- The `agentic-jujutsu` surface exposes ML-DSA-65 signing only; there is no paired-Ed25519 mode to
  call, so this skill cannot *offer* a hybrid construction it does not have.
- The signatures here protect JS-internal agent operations, audit trails, and trajectory integrity —
  a lower-stakes surface than the cross-boundary artifacts the Rust pipeline ships to remote actions.

The consequence is a routing rule, not a code change in this skill:

> If an artifact must survive a break in ML-DSA (or in a specific PQ implementation) — anything
> shipped across a trust boundary, signed once and verified by an independent party, or held
> long-term — sign it on the **Rust hybrid path** (`rust-pq-crypto`, Ed25519 + ML-DSA co-signature),
> not with the pure-PQ JS signer here.

### Anti-patterns

- **Do not present the JS ML-DSA-65 signature as "hybrid" or as belonging to the hybrid doctrine.**
  It is pure PQ. Call it what it is.
- **Do not reach for this skill to add a classical leg** — it has no Ed25519 mode. Cross to
  `rust-pq-crypto` for any paired co-signature.
- **Do not treat "FIPS 204 standardized" as "audited-in-implementation."** Standardized ≠ audited;
  that gap is exactly why the sibling pairs a classical primitive, and why high-value artifacts
  belong on the hybrid path.

## Related

- `rust-pq-crypto` — the Rust sibling: hybrid-only ML-KEM/ML-DSA, PQ-TLS, HPKE envelopes,
  `references/hybrid-doctrine.md` for the full per-layer "what is paired with what" map and the
  verifiable both-signatures-required construction.
- `SKILL.md` — the JS `QuantumSigner` API this boundary sits in front of.
