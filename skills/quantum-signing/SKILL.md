---
name: quantum-signing
description: |
  Use when implementing quantum-resistant cryptographic signing.
  Triggers: "quantum signing", "ML-DSA", "post-quantum", "operation signing", "quantum-resistant".
  NOT for: Standard encryption or non-cryptographic integrity checks.
---

# Quantum Signing

Expert guidance for quantum-resistant cryptographic operations.

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

### 1. Signed Agent Operations

```javascript
// Each agent signs its operations
const signer = new QuantumSigner();
const { publicKey, secretKey } = await signer.generateSigningKeypair();

// Register public key with coordination system
await jj.registerAgent(agentId, agentType, { publicKey });

// Sign each operation
const operation = {
  id: 'op-123',
  agent: agentId,
  action: 'edit',
  files: ['src/auth.ts'],
  timestamp: Date.now()
};

const signature = await signer.signMessage(
  JSON.stringify(operation),
  secretKey
);

// Include signature in operation record
await jj.registerAgentOperation(agentId, operation.id, operation.files, {
  signature
});
```

### 2. Verifiable Audit Trail

```javascript
// Verify operations were not tampered
const operations = await jj.getAgentOperations(agentId);

for (const op of operations) {
  const isValid = await signer.verifySignature(
    JSON.stringify(op.data),
    op.signature,
    op.publicKey
  );

  if (!isValid) {
    console.error(`Operation ${op.id} signature invalid!`);
  }
}
```

### 3. Commit Signing

```javascript
// Sign commits for verification
const commitData = {
  message: 'feat: add authentication',
  author: 'agent-001',
  timestamp: Date.now(),
  tree: treeHash
};

const signature = await signer.signMessage(
  JSON.stringify(commitData),
  secretKey
);

await jj.commit({
  ...commitData,
  signature
});
```

### 4. Learning Trajectory Integrity

```javascript
// Ensure trajectory data wasn't modified
const trajectory = await jj.getTrajectory(trajectoryId);

const isValid = await signer.verifySignature(
  JSON.stringify(trajectory.operations),
  trajectory.signature,
  trajectory.agentPublicKey
);
```

## Best Practices

### 1. Secure Key Storage

```javascript
// DO - Store keys securely
const secretKey = process.env.AGENT_SECRET_KEY;

// DON'T - Hardcode or log keys
const secretKey = 'ABC123...'; // NEVER DO THIS
console.log(secretKey);         // NEVER DO THIS
```

### 2. Key Rotation

```javascript
// Rotate keys periodically
async function rotateKeys(agentId) {
  const { publicKey, secretKey } = await signer.generateSigningKeypair();

  // Update registration
  await jj.updateAgentKeys(agentId, { publicKey });

  // Securely store new secret key
  await secureStorage.set(`${agentId}_secret`, secretKey);

  return { publicKey };
}
```

### 3. Use Fingerprints for Speed

```javascript
// For frequent integrity checks, use fingerprints (fast)
const fingerprint = await jj.generateOperationFingerprint(data);

// Reserve full signatures for important operations
if (operation.type === 'commit' || operation.type === 'merge') {
  const signature = await signer.signMessage(data, secretKey);
}
```

### 4. Verify Before Trust

```javascript
// Always verify external operations
async function processExternalOperation(op) {
  const isValid = await signer.verifySignature(
    op.data,
    op.signature,
    op.publicKey
  );

  if (!isValid) {
    throw new SecurityError('Invalid signature');
  }

  // Safe to process
  return process(op);
}
```

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

- `/agentic-flow` - Agent coordination commands
- `agent-coordination` - QuantumDAG patterns
- `agentsdb-patterns` - Learning with integrity
- `docs/JJ-INTEGRATION.md` - Full API reference
