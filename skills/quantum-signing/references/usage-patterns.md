# Quantum Signing — Usage Patterns

Concrete `QuantumSigner` / `JjWrapper` patterns for `agentic-jujutsu`. See `SKILL.md` for the core API.

## 1. Signed Agent Operations

Each agent signs its own operations; the public key is registered with the coordination system.

```javascript
const signer = new QuantumSigner();
const { publicKey, secretKey } = await signer.generateSigningKeypair();

// Register public key with coordination system
await jj.registerAgent(agentId, agentType, { publicKey });

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

## 2. Verifiable Audit Trail

Replay stored operations and confirm none were tampered with.

```javascript
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

## 3. Commit Signing

Sign commit metadata so downstream consumers can verify authorship.

```javascript
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

await jj.commit({ ...commitData, signature });
```

## 4. Learning Trajectory Integrity

Ensure trajectory data was not modified before training/replay.

```javascript
const trajectory = await jj.getTrajectory(trajectoryId);

const isValid = await signer.verifySignature(
  JSON.stringify(trajectory.operations),
  trajectory.signature,
  trajectory.agentPublicKey
);
```
