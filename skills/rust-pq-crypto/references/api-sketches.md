# API sketches — concrete, version-pinned Rust

Copy-adaptable snippets for each crate in the stack. **These crates move fast** (ml-dsa is 0.1.x,
hpke 0.13→0.14 pending, rustls provider split evolving). Every snippet is flagged with a
**⚠ verify** note — re-check the exact type paths and method signatures on docs.rs for the version you
pin before relying on them. Versions here are as of the 2026-07-02 shortlist.

## Cargo.toml

```toml
[dependencies]
rustls = "0.23.41"                     # aws-lc-rs provider is default; X25519MLKEM768 default-on
# rustls-post-quantum = "0.x"          # ONLY for pure MLKEM768 / experimental ML-DSA certs
hpke = "0.13.0"                        # rust-hpke — X-Wing (MLKEM768-X25519)
ml-kem = "0.3.2"                       # FIPS 203 — UNAUDITED
ml-dsa = "0.1.1"                       # FIPS 204 — UNAUDITED
ed25519-dalek = "2"                    # classical co-signing leg
sha3 = "0.10"                          # SHA3-512 digest
age = "0.11.2"                         # at-rest (no PQ recipient)
ngrok = "0.14"                         # in-process agent SDK; TCP/TLS builders only
rand = "0.8"

[dev-dependencies]
oqs = "0.11.0"                         # liboqs — KAT oracle ONLY, never runtime
pqcrypto = "0.18.1"                    # PQClean — KAT oracle / SPHINCS+ breadth
```

## 1. rustls — PQ-TLS with a fail-closed group assertion

The hybrid group is on by default; the load-bearing part is **asserting** it post-handshake.

```rust
// ⚠ verify: NamedGroup path and the negotiated-group accessor for your rustls version.
use rustls::NamedGroup;

// A default client config on the aws-lc-rs provider already offers X25519MLKEM768.
// After the handshake completes, read the negotiated key-exchange group and FAIL CLOSED
// if it is not the hybrid PQ group. This is the D2 conformance tripwire.
fn assert_pq_kx(conn: &rustls::ClientConnection) -> Result<(), &'static str> {
    match conn.negotiated_key_exchange_group() {      // ⚠ verify accessor name
        Some(g) if g.name() == NamedGroup::X25519MLKEM768 => Ok(()),
        _ => Err("PQ downgrade: negotiated group is not X25519MLKEM768"),
    }
}
```

If you must restrict to *only* the hybrid group (reject classical-only peers), configure the
provider's `kx_groups` to the single `X25519MLKEM768` entry. For the `fips` posture, enable the
`fips` feature and construct the provider accordingly (⚠ verify the FIPS provider constructor).

## 2. ml-kem — encapsulate / decapsulate (FIPS 203)

```rust
// ⚠ verify: trait imports (Encapsulate/Decapsulate) and generate() signature for ml-kem 0.3.2.
use ml_kem::{MlKem768, KemCore};
use ml_kem::kem::{Encapsulate, Decapsulate};

let mut rng = rand::rngs::OsRng;

// Recipient keypair
let (decaps_key, encaps_key) = MlKem768::generate(&mut rng);

// Sender encapsulates to the recipient's public (encapsulation) key
let (ciphertext, shared_secret_sender) = encaps_key.encapsulate(&mut rng).expect("encapsulate");

// Recipient decapsulates
let shared_secret_recipient = decaps_key.decapsulate(&ciphertext).expect("decapsulate");

assert_eq!(shared_secret_sender, shared_secret_recipient);
```

**Hybrid rule:** this raw ML-KEM secret is *never* used alone as the channel key. Combine it with an
X25519 shared secret (KDF over both) — or just use the X-Wing HPKE construction below, which does the
combining for you.

## 3. HPKE X-Wing — seal / open a payload envelope

```rust
// ⚠ verify: the exact X-Wing KEM type path in rust-hpke 0.13 (KEM types shift between minors).
// Conceptual RFC 9180 single-shot shape; wire the concrete X-Wing Kem, ChaCha20Poly1305 Aead,
// and an HKDF Kdf per the crate's generics.

// setup_sender(&OpModeS, recipient_pubkey, info, &mut rng)
//   -> (encapsulated_key, sender_context)
// sender_context.seal(plaintext, aad) -> ciphertext

// setup_receiver(&OpModeR, recipient_privkey, &encapsulated_key, info)
//   -> receiver_context
// receiver_context.open(ciphertext, aad) -> plaintext
```

Apply this **at the harness boundary** so the payload is sealed to the true endpoint before it ever
touches TLS or a tunnel. The X-Wing KEM already pairs ML-KEM-768 with X25519 — this is the message-
layer hybrid leg.

## 4. ml-dsa + Ed25519 — the hybrid co-signature

```rust
// ⚠ verify: ml-dsa 0.1.1 key-gen/sign/verify API names (KeyGen / signing_key / verify).
use sha3::{Digest, Sha3_512};

fn digest(canonical_bytes: &[u8]) -> [u8; 64] {
    let mut h = Sha3_512::new();
    h.update(canonical_bytes);
    h.finalize().into()
}

// SIGN: both legs over the same digest of the canonical serialization.
// let d = digest(&canonical);
// let sig_ed    = ed25519_signing_key.sign(&d);            // ed25519-dalek
// let sig_mldsa = mldsa_signing_key.sign(&d);              // ml-dsa — ⚠ verify

// VERIFY: BOTH must pass, else REJECT. One-of-two is a reject by doctrine.
fn verify_hybrid(ed_ok: bool, mldsa_ok: bool) -> bool {
    ed_ok && mldsa_ok        // never `||` — the whole point of hybrid signing
}
```

Attach both signatures + both public keys (or key ids) + the codec version + key validity window. See
`key-lifecycle.md` for the full signing lifecycle and `hybrid-doctrine.md` for the negative tests
(Ed25519-only and ML-DSA-only artifacts must both be rejected).

## 5. ngrok — TCP/TLS tunnel only (never HTTP)

```rust
// ⚠ verify: builder/entry-point names for the ngrok version you pin (0.14 / 0.18).
// Authtoken comes from the NGROK_AUTHTOKEN env var — never hardcode.

// let sess = ngrok::Session::builder()
//     .authtoken_from_env()          // env only
//     .connect().await?;

// GOOD — opaque byte pipe; ngrok never sees plaintext:
// let tunnel = sess.tcp_endpoint().listen().await?;      // TcpTunnelBuilder
// let tunnel = sess.tls_endpoint().listen().await?;      // TlsTunnelBuilder

// BANNED — TLS terminates at the ngrok edge = plaintext there:
// sess.http_endpoint()   // ❌ never
```

The HPKE envelope holds regardless of tunnel type — ngrok is a dumb pipe. Edge OIDC/Policy/IP-
restrictions (via `ngrok-api-rs`) are additive defense-in-depth only.

## 6. age — at-rest encryption (classical; pair with HPKE for PQ)

```rust
// ⚠ verify: age 0.11 Encryptor/Decryptor API (recipient vs passphrase constructors).
// Encrypt an artifact or a wrapped secret key to an X25519 recipient (or a passphrase).
// age has NO post-quantum recipient — for quantum-sensitive data, ALSO apply the HPKE X-Wing
// envelope (§3). age is the classical leg of at-rest; HPKE is the PQ leg.
```

## 7. KAT cross-validation (dev-only)

```rust
// In [dev-dependencies] tests only — the C-FFI never enters the runtime binary (D1).
// Feed fixed NIST/FIPS vectors through ml-kem/ml-dsa and assert outputs match liboqs (`oqs`)
// and/or pqcrypto (PQClean). Also round-trip properties:
//   decapsulate(encapsulate()) == shared_secret
//   verify(sign(m), m) == true ; verify(sign(m), m') == false
//   seal-then-open round-trips for X-Wing HPKE
// Run in CI so an unaudited-crate regression is caught before it ships.
```

## Re-verification reminder

Before trusting any signature above in real code, open docs.rs for the **exact pinned version** and
confirm: the type paths (`NamedGroup`, X-Wing KEM, ml-dsa key/sign types), the RNG trait bounds, and
whether a method is `Result`-returning. The doctrine (hybrid-only, assert-the-group, both-signatures)
is stable; the surface API names are not.
