# Quantum Signing — Best Practices

Operational guidance for `QuantumSigner`. See `SKILL.md` for the core API and `usage-patterns.md` for end-to-end flows.

## 1. Secure Key Storage

Load secret keys from a secret manager / environment — never hardcode or log them.

```javascript
// DO - Store keys securely
const secretKey = process.env.AGENT_SECRET_KEY;

// DON'T - Hardcode or log keys
const secretKey = 'ABC123...'; // NEVER DO THIS
console.log(secretKey);         // NEVER DO THIS
```

## 2. Key Rotation

Rotate keys periodically and re-register the new public key.

```javascript
async function rotateKeys(agentId) {
  const { publicKey, secretKey } = await signer.generateSigningKeypair();

  // Update registration
  await jj.updateAgentKeys(agentId, { publicKey });

  // Securely store new secret key
  await secureStorage.set(`${agentId}_secret`, secretKey);

  return { publicKey };
}
```

## 3. Use Fingerprints for Speed

Reserve full ML-DSA signatures for high-value operations; use SHA3-512 fingerprints for frequent, low-stakes integrity checks.

```javascript
const fingerprint = await jj.generateOperationFingerprint(data);

if (operation.type === 'commit' || operation.type === 'merge') {
  const signature = await signer.signMessage(data, secretKey);
}
```

## 4. Verify Before Trust

Always verify externally-sourced operations before acting on them.

```javascript
async function processExternalOperation(op) {
  const isValid = await signer.verifySignature(
    op.data,
    op.signature,
    op.publicKey
  );

  if (!isValid) {
    throw new SecurityError('Invalid signature');
  }

  return process(op);
}
```
