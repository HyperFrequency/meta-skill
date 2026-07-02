# GGUF Conversion and Quantization

Detailed conversion workflows and quantization reference. See `../SKILL.md` for the lean overview.

## Quantization types

### K-quant methods (recommended)

| Type | Bits | Size (7B) | Quality | Use Case |
|------|------|-----------|---------|----------|
| Q2_K | 2.5 | ~2.8 GB | Low | Extreme compression |
| Q3_K_S | 3.0 | ~3.0 GB | Low-Med | Memory constrained |
| Q3_K_M | 3.3 | ~3.3 GB | Medium | Balance |
| Q4_K_S | 4.0 | ~3.8 GB | Med-High | Good balance |
| Q4_K_M | 4.5 | ~4.1 GB | High | **Recommended default** |
| Q5_K_S | 5.0 | ~4.6 GB | High | Quality focused |
| Q5_K_M | 5.5 | ~4.8 GB | Very High | High quality |
| Q6_K | 6.0 | ~5.5 GB | Excellent | Near-original |
| Q8_0 | 8.0 | ~7.2 GB | Best | Maximum quality |

### Legacy methods

| Type | Description |
|------|-------------|
| Q4_0 | 4-bit, basic |
| Q4_1 | 4-bit with delta |
| Q5_0 | 5-bit, basic |
| Q5_1 | 5-bit with delta |

### IQ types (importance-aware, ultra-low bit)

`IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_XS, IQ3_S, IQ4_XS` — require an imatrix; deliver
better quality than legacy/K-quants at the same low bit width. See `advanced-usage.md`.

**Recommendation**: Use K-quant methods (Q4_K_M, Q5_K_M) for the best quality/size ratio.

## Conversion workflows

### Workflow 1: HuggingFace to GGUF

```bash
# 1. Download model
huggingface-cli download meta-llama/Llama-3.1-8B --local-dir ./llama-3.1-8b

# 2. Convert to GGUF (FP16)
python convert_hf_to_gguf.py ./llama-3.1-8b \
    --outfile llama-3.1-8b-f16.gguf \
    --outtype f16

# 3. Quantize
./build/bin/llama-quantize llama-3.1-8b-f16.gguf llama-3.1-8b-q4_k_m.gguf Q4_K_M

# 4. Test
./build/bin/llama-cli -m llama-3.1-8b-q4_k_m.gguf -p "Hello!" -n 50
```

### Workflow 2: With importance matrix (better low-bit quality)

```bash
# 1. Convert to GGUF
python convert_hf_to_gguf.py ./model --outfile model-f16.gguf

# 2. Create calibration text (diverse samples)
cat > calibration.txt << 'EOF'
The quick brown fox jumps over the lazy dog.
Machine learning is a subset of artificial intelligence.
Python is a popular programming language.
# Add more diverse text samples...
EOF

# 3. Generate importance matrix
./build/bin/llama-imatrix -m model-f16.gguf \
    -f calibration.txt \
    --chunk 512 \
    -o model.imatrix \
    -ngl 35  # GPU layers if available

# 4. Quantize with imatrix
./build/bin/llama-quantize --imatrix model.imatrix \
    model-f16.gguf \
    model-q4_k_m.gguf \
    Q4_K_M
```

### Workflow 3: Multiple quantizations from one imatrix

```bash
#!/bin/bash
MODEL="llama-3.1-8b-f16.gguf"
IMATRIX="llama-3.1-8b.imatrix"

# Generate imatrix once
./build/bin/llama-imatrix -m $MODEL -f wiki.txt -o $IMATRIX -ngl 35

# Create multiple quantizations
for QUANT in Q4_K_M Q5_K_M Q6_K Q8_0; do
    OUTPUT="llama-3.1-8b-${QUANT,,}.gguf"
    ./build/bin/llama-quantize --imatrix $IMATRIX $MODEL $OUTPUT $QUANT
    echo "Created: $OUTPUT ($(du -h $OUTPUT | cut -f1))"
done
```
