#!/usr/bin/env python3
"""Predict N- and O-linked glycosylation sites from a protein sequence.

Scans for canonical N-glycosylation sequons (N-X-S/T, X != P) with proline
efficiency notes, and flags O-glycosylation hotspots by sliding-window Ser/Thr
density. Writes a per-site CSV and an annotated-sequence text file.

Rule-based triage only: a sequon or an S/T-rich window marks a *candidate*, not
an occupied site. Confirm with NetNGlyc / NetOGlyc and UniProt.

Usage:
    predict_glycosylation.py --sequence MNKTSLYIFLIFLAG --output-dir ./results
    predict_glycosylation.py --sequence protein.fasta --output-dir ./results \\
        --threshold 0.25 --window-size 15
"""

import argparse
import csv
import os
import re
import sys

AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")


def read_sequence(sequence_input):
    """Return (header, sequence) from a raw string or a single-record FASTA path."""
    if os.path.isfile(sequence_input):
        return parse_fasta(sequence_input)
    seq = re.sub(r"\s+", "", sequence_input).upper()
    invalid = set(seq) - AMINO_ACIDS
    if invalid:
        raise ValueError(f"Invalid amino-acid characters in sequence: {invalid}")
    return "input_sequence", seq


def parse_fasta(filepath):
    """Read the first record of a FASTA file as (header, sequence)."""
    header = None
    seq_lines = []
    with open(filepath) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    break  # stop at the second record
                header = line[1:].strip()
            else:
                seq_lines.append(line.upper())
    sequence = re.sub(r"[^A-Z]", "", "".join(seq_lines))
    if not sequence:
        raise ValueError(f"No sequence data found in {filepath}")
    return header or os.path.basename(filepath), sequence


def predict_n_glycosylation(sequence):
    """Find N-X-S/T sequons (X != P), annotating proline efficiency modifiers."""
    sites = []
    seq_len = len(sequence)
    for i in range(seq_len - 2):
        if sequence[i] != "N" or sequence[i + 1] == "P":
            continue
        if sequence[i + 2] not in ("S", "T"):
            continue
        note = "canonical_sequon"
        if i + 3 < seq_len and sequence[i + 3] == "P":
            note = "reduced_efficiency_proline_after_sequon"
        elif i > 0 and sequence[i - 1] == "P":
            note = "reduced_efficiency_proline_before_asn"
        sites.append({
            "position": i + 1,
            "type": "N-glycosylation",
            "motif": sequence[i:i + 3],
            "flanking_sequence": sequence[max(0, i - 5):min(seq_len, i + 8)],
            "confidence_note": note,
        })
    return sites


def predict_o_glycosylation(sequence, window_size=11, threshold=0.3):
    """Flag O-glyc hotspot S/T residues by sliding-window S+T density."""
    seq_len = len(sequence)
    if seq_len < window_size:
        return []

    flagged = set()
    for i in range(seq_len - window_size + 1):
        window = sequence[i:i + window_size]
        density = (window.count("S") + window.count("T")) / window_size
        if density > threshold:
            for j in range(i, i + window_size):
                if sequence[j] in ("S", "T"):
                    flagged.add(j)

    sites = []
    for pos in sorted(flagged):
        near_p = (pos > 0 and sequence[pos - 1] == "P") or (
            pos < seq_len - 1 and sequence[pos + 1] == "P")
        sites.append({
            "position": pos + 1,
            "type": "O-glycosylation",
            "motif": sequence[pos],
            "flanking_sequence": sequence[max(0, pos - 5):min(seq_len, pos + 6)],
            "confidence_note": "reduced_probability_proline_neighbor"
            if near_p else "o_glyc_hotspot",
        })
    return sites


def merge_regions(o_sites, max_gap=2):
    """Collapse nearby O-glyc residues into (start, end) regions (1-based)."""
    if not o_sites:
        return []
    positions = sorted(s["position"] for s in o_sites)
    regions, start, end = [], positions[0], positions[0]
    for pos in positions[1:]:
        if pos <= end + max_gap:
            end = pos
        else:
            regions.append((start, end))
            start = end = pos
    regions.append((start, end))
    return regions


def build_annotated_sequence(sequence, n_sites, o_sites, width=60):
    """Wrap the sequence at `width` with a marker track (^ N, o O, * both)."""
    n_pos = {s["position"] - 1 for s in n_sites}
    o_pos = {s["position"] - 1 for s in o_sites}
    markers = []
    for i in range(len(sequence)):
        if i in n_pos and i in o_pos:
            markers.append("*")
        elif i in n_pos:
            markers.append("^")
        elif i in o_pos:
            markers.append("o")
        else:
            markers.append(" ")

    lines = []
    for start in range(0, len(sequence), width):
        end = min(start + width, len(sequence))
        lines.append(f"{start + 1:>6}  {sequence[start:end]}")
        track = "".join(markers[start:end])
        if track.strip():
            lines.append(f"{'':>6}  {track}")
        lines.append("")
    lines.append("Legend: ^ = N-glyc sequon, o = O-glyc hotspot, * = both")
    return "\n".join(lines)


def write_csv(filepath, sites):
    fields = ["position", "type", "motif", "flanking_sequence", "confidence_note"]
    with open(filepath, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for site in sorted(sites, key=lambda s: s["position"]):
            writer.writerow(site)


def print_summary(header, sequence, n_sites, o_sites, o_regions):
    print("Glycosylation Prediction Report")
    print("=" * 50)
    print(f"Sequence: {header}")
    print(f"Length:   {len(sequence)} aa\n")
    print(f"N-glycosylation sequons: {len(n_sites)}")
    for s in n_sites:
        extra = f"  ({s['confidence_note']})" if "reduced" in s["confidence_note"] else ""
        print(f"  N{s['position']:>5}: {s['motif']}  [{s['flanking_sequence']}]{extra}")
    print(f"\nO-glycosylation hotspot residues: {len(o_sites)}")
    print(f"O-glycosylation hotspot regions:  {len(o_regions)}")
    for start, end in o_regions:
        print(f"  Region {start}-{end} ({end - start + 1} aa)")
    print(f"\nTotal candidate positions: {len(n_sites) + len(o_sites)}")


def main():
    parser = argparse.ArgumentParser(
        description="Predict N- and O-glycosylation sites in a protein sequence.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Notes:\n"
                "  N-glyc: canonical N-X-S/T sequon (X != P)\n"
                "  O-glyc: sliding-window S/T density heuristic (candidate only)\n"),
    )
    parser.add_argument("--sequence", required=True,
                        help="Amino-acid string or path to a single-record FASTA")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for output files (created if absent)")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="O-glyc S/T density threshold (default: 0.3)")
    parser.add_argument("--window-size", type=int, default=11,
                        help="O-glyc sliding-window size (default: 11)")
    args = parser.parse_args()

    try:
        header, sequence = read_sequence(args.sequence)
    except (ValueError, OSError) as exc:
        print(f"Error reading sequence: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(sequence) < 3:
        print("Error: sequence must be at least 3 residues long.", file=sys.stderr)
        sys.exit(1)

    n_sites = predict_n_glycosylation(sequence)
    o_sites = predict_o_glycosylation(sequence, args.window_size, args.threshold)
    o_regions = merge_regions(o_sites)

    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, "glycosylation_predictions.csv")
    write_csv(csv_path, n_sites + o_sites)

    annotated_path = os.path.join(args.output_dir, "annotated_sequence.txt")
    with open(annotated_path, "w") as handle:
        handle.write(f">{header}\n")
        handle.write(build_annotated_sequence(sequence, n_sites, o_sites))
        handle.write("\n")

    print_summary(header, sequence, n_sites, o_sites, o_regions)
    print(f"\nOutputs:\n  {csv_path}\n  {annotated_path}")


if __name__ == "__main__":
    main()
