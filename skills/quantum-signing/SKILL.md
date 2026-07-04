---
name: quantum-signing
version: 0.2.0
description: |
  Implement quantum-resistant (post-quantum) cryptographic signing in JavaScript / Node / browser with
  the agentic-jujutsu QuantumSigner (ML-DSA-65 / NIST FIPS 204) and SHA3-512 fingerprints, for
  signing/verifying agent operations, audit trails, commits, and learning trajectories. This is the
  JS/browser signing surface; the Rust harness / hybrid co-signing path (ML-KEM + ML-DSA, hybrid-only)
  lives in rust-pq-crypto. Triggers: "quantum signing", "ML-DSA", "post-quantum", "operation signing",
  "quantum-resistant", "sign an agent operation in JS/browser". NOT for: standard/classical encryption
  (RSA, AES, ECDSA), TLS setup, password hashing, or non-cryptographic integrity checks; Rust PQ, PQ-TLS,
  key encapsulation, or hybrid (classical+PQ) co-signing (use rust-pq-crypto); agent coordination (use
  agent-coordination).
---

# Quantum Signing

Expert guidance for quantum-resistant cryptographic operations **in JavaScript / Node / browser**,
using the `agentic-jujutsu` `QuantumSigner` (ML-DSA-65).

## Scope & Boundary

This skill is the **JS/browser** post-quantum signing surface. The **Rust** harness and the
**hybrid** (classical + PQ paired) co-signing path are a separate skill.

- **Signing runs in JavaScript / Node / browser** → you are in the right place.
- **Signing or co-signing runs in the Rust harness**, or you need a **hybrid Ed25519 + ML-DSA
  co-signature**, PQ key encapsulation (ML-KEM), PQ-TLS, or envelope encryption →
  route to **`rust-pq-crypto`**.

One doctrine note up front: the sibling `rust-pq-crypto` is **hybrid-only** — it always pairs a
classical primitive with the PQ one, because the pure-Rust PQ crates are explicitly *unaudited*, so a
break degrades to classical security instead of to zero. **This JS signer is pure ML-DSA-65, not
hybrid** — a deliberate, documented limitation. For anything that must cross a trust boundary or
survive a break in one PQ implementation, sign on the Rust hybrid path. Full rationale, the JS-vs-Rust
decision table, and the anti-patterns live in `references/scope-and-hybrid.md`.

## Core Concepts

### Why Quantum-Resistant?

Traditional cryptography (RSA, ECDSA) will be broken by quantum computers. ML-DSA-65 is:

- **NIST FIPS 204** - Standardized post-quantum algorithm
- **Level 3 Security** - Equivalent to AES-192
- **Future-proof** - Safe against quantum attacks

### Cryptographic Primitives

| Primitive | Algorithm | Use Case |
|-----------|-----------|----------|
| Signatures | ML-DSA-65 | Operation signing |
| Fingerprints | SHA3-512 | Fast integrity checks |
| Encryption | HQC-128 | Optional data encryption |

## API Reference

### QuantumSigner Class

```javascript
const { QuantumSigner } = require('agentic-jujutsu');

const signer = new QuantumSigner();
```

### Generate Keypair

```javascript
// Generate ML-DSA-65 keypair
const { publicKey, secretKey } = await signer.generateSigningKeypair();

// Keys are Base64-encoded strings
console.log('Public key length:', publicKey.length);  // ~2KB
console.log('Secret key length:', secretKey.length);  // ~4KB
```

### Sign a Message

```javascript
// Sign operation data
const message = JSON.stringify({
  operationId: 'op-123',
  agentId: 'agent-001',
  timestamp: Date.now(),
  files: ['src/auth.ts']
});

const signature = await signer.signMessage(message, secretKey);
// Signature is Base64-encoded, ~3KB
```

### Verify Signature

```javascript
// Verify operation integrity
const isValid = await signer.verifySignature(
  message,
  signature,
  publicKey
);

if (!isValid) {
  throw new Error('Operation tampered with!');
}
```

### Get Algorithm Info

```javascript
const info = signer.getAlgorithmInfo();
// {
//   name: 'ML-DSA-65',
//   standard: 'NIST FIPS 204',
//   securityLevel: 3,
//   publicKeySize: 1952,
//   secretKeySize: 4032,
//   signatureSize: 3293
// }
```

## Fast Fingerprints

For quick integrity checks (not cryptographic signing):

```javascript
const { JjWrapper } = require('agentic-jujutsu');

const jj = new JjWrapper();

// Generate fingerprint (<1ms)
const fingerprint = await jj.generateOperationFingerprint({
  files: ['src/auth.ts'],
  action: 'edit',
  content: fileContent
});

// Verify later
const isValid = await jj.verifyOperationFingerprint(
  { files, action, content },
  fingerprint
);
```

## Use Cases

End-to-end patterns live in `references/usage-patterns.md`:

1. **Signed agent operations** — sign each op, register the public key with the coordinator.
2. **Verifiable audit trail** — replay stored ops and reject any with an invalid signature.
3. **Commit signing** — sign commit metadata for downstream verification.
4. **Learning trajectory integrity** — confirm trajectory data was not modified before replay/training.

## Best Practices

Details and code in `references/best-practices.md`:

1. **Secure key storage** — load secret keys from a secret manager / env; never hardcode or log them.
2. **Key rotation** — rotate periodically and re-register the new public key.
3. **Fingerprints for speed** — use SHA3-512 fingerprints for frequent checks; reserve ML-DSA signatures for high-value ops (commits, merges).
4. **Verify before trust** — always verify external operations before acting on them.

## Performance

| Operation | Time | Size |
|-----------|------|------|
| Key generation | ~10ms | - |
| Sign | ~2ms | 3.3KB |
| Verify | ~1ms | - |
| Fingerprint | <1ms | 64B |

## Current Status

**v2.3.6**: Placeholder cryptography (functional but not production-hardened)
**v2.4.0**: Production cryptography via @qudag/napi-core

## Related

- `references/scope-and-hybrid.md` - JS-vs-Rust boundary, hybrid-only doctrine, routing rules
- `references/usage-patterns.md` - End-to-end signing flows
- `references/best-practices.md` - Key storage, rotation, verification
- `rust-pq-crypto` - The Rust sibling: hybrid-only ML-KEM/ML-DSA, PQ-TLS, HPKE envelopes, tunnel hardening
- `/agentic-flow` - Agent coordination commands
- `agent-coordination` - QuantumDAG patterns
- `agentsdb-patterns` - Learning with integrity
- `docs/JJ-INTEGRATION.md` - Full API reference
