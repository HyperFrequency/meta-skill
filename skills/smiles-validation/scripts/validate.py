#!/usr/bin/env python3
"""
Strict SMILES validation, structural comparison, and modification verification.

Rejects un-parseable or chemically impossible machine-generated molecules and
checks that a claimed structural edit actually happened.

Usage:
    python validate.py --smiles "c1ccccc1"
    python validate.py --original "c1ccccc1" --proposed "c1ccc(O)cc1" \
        --check-modification "Added hydroxyl group"
    python validate.py --input molecules.csv --smiles-col SMILES --output report.json

Requires RDKit (`pip install rdkit`; the legacy "rdkit-pypi" package is
unmaintained). Batch mode also needs pandas.
"""

import argparse
import json
import sys

try:
    from rdkit import Chem, DataStructs, RDLogger
    from rdkit.Chem import Descriptors
    from rdkit.Chem import rdFMCS
    from rdkit.Chem.Scaffolds import MurckoScaffold

    RDLogger.DisableLog("rdApp.*")  # keep RDKit's C++ warnings off stdout
except ImportError:
    print("Error: RDKit is required. Install with `pip install rdkit`.", file=sys.stderr)
    sys.exit(1)


# Prefer the modern generator API; fall back to the legacy call on old RDKit.
try:
    from rdkit.Chem import rdFingerprintGenerator

    _MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

    def morgan_fingerprint(mol):
        return _MORGAN_GENERATOR.GetFingerprint(mol)

except ImportError:  # RDKit < 2022.09
    from rdkit.Chem import AllChem

    def morgan_fingerprint(mol):
        return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)


# Warning thresholds — advisory only, they do not fail validation.
MIN_ATOMS = 3
MAX_ATOMS = 150
MAX_MW = 1000

# Similarity cutoffs for the change classification (see cli-reference.md).
LEAD_OPTIMIZATION_MIN = 0.6
SIGNIFICANT_MODIFICATION_MIN = 0.4

# Keyword -> query pattern for modification verification. Order is not
# significant; each entry is checked independently against the claim.
GROUP_PATTERNS = [
    (["hydroxyl", "hydroxy", "oh"], "[OH]"),
    (["fluorine", "fluoro", "f"], "[F]"),
    (["chlorine", "chloro", "cl"], "[Cl]"),
    (["bromine", "bromo", "br"], "[Br]"),
    (["amine", "amino", "nh2"], "[NH2]"),
    (["methyl", "ch3"], "[CH3]"),
    (["nitro", "no2"], "[N+](=O)[O-]"),
    (["cyano", "nitrile", "cn"], "C#N"),
    (["pyridine"], "c1ccncc1"),
    (["piperazine"], "C1CNCCN1"),
    (["morpholine"], "C1COCCN1"),
]


def validate(smiles):
    """Parse, sanitize, and canonicalize one SMILES, returning diagnostics."""
    result = {"smiles": smiles, "valid": False, "issues": []}

    if not smiles or not isinstance(smiles, str):
        result["issues"].append("Empty or non-string input")
        return result

    smiles = smiles.strip()

    # Cheap, human-readable syntactic hints before handing off to RDKit.
    if smiles.count("(") != smiles.count(")"):
        result["issues"].append(
            f"Unbalanced parentheses: {smiles.count('(')} open, {smiles.count(')')} close"
        )
    if smiles.count("[") != smiles.count("]"):
        result["issues"].append(
            f"Unbalanced brackets: {smiles.count('[')} open, {smiles.count(']')} close"
        )

    mol = Chem.MolFromSmiles(smiles)  # already sanitizes; None on any failure
    if mol is None:
        result["issues"].append("RDKit parse failure")
        return result

    # MolFromSmiles sanitizes by default, but re-run explicitly so a valence
    # or kekulization problem surfaces as a readable message rather than None.
    try:
        Chem.SanitizeMol(mol)
    except Exception as error:
        result["issues"].append(f"Sanitization error: {error}")
        return result

    result["valid"] = True
    result["canonical"] = Chem.MolToSmiles(mol)
    result["num_atoms"] = mol.GetNumAtoms()
    result["num_heavy_atoms"] = Descriptors.HeavyAtomCount(mol)
    result["mw"] = round(Descriptors.MolWt(mol), 1)
    result["formula"] = Chem.rdMolDescriptors.CalcMolFormula(mol)

    if mol.GetNumAtoms() < MIN_ATOMS:
        result["issues"].append(f"Very small molecule (<{MIN_ATOMS} atoms)")
    if mol.GetNumAtoms() > MAX_ATOMS:
        result["issues"].append(f"Very large molecule (>{MAX_ATOMS} atoms)")
    if Descriptors.MolWt(mol) > MAX_MW:
        result["issues"].append(f"MW > {MAX_MW} - beyond typical drug-like space")

    return result


def generic_scaffold(mol):
    """Generic (topology-only) Murcko scaffold SMILES, or None if none exists."""
    try:
        bemis_murcko = MurckoScaffold.GetScaffoldForMol(mol)
        generic = MurckoScaffold.MakeScaffoldGeneric(bemis_murcko)
        return Chem.MolToSmiles(generic)
    except Exception:
        return None


def compare(original_smiles, proposed_smiles):
    """Quantify how far the proposed molecule sits from the original."""
    original = Chem.MolFromSmiles(original_smiles)
    proposed = Chem.MolFromSmiles(proposed_smiles)
    if original is None or proposed is None:
        return {"error": "One or both SMILES invalid"}

    similarity = round(
        DataStructs.TanimotoSimilarity(
            morgan_fingerprint(original), morgan_fingerprint(proposed)
        ),
        4,
    )

    original_scaffold = generic_scaffold(original)
    proposed_scaffold = generic_scaffold(proposed)
    if original_scaffold is None or proposed_scaffold is None:
        scaffold_preserved = None
    else:
        scaffold_preserved = original_scaffold == proposed_scaffold

    try:
        # MCS is NP-hard; always cap it so symmetric molecules cannot hang.
        mcs = rdFMCS.FindMCS([original, proposed], timeout=10)
        mcs_atoms = mcs.numAtoms if mcs else 0
    except Exception:
        mcs_atoms = 0

    if similarity >= LEAD_OPTIMIZATION_MIN:
        classification = "lead_optimization"
    elif similarity >= SIGNIFICANT_MODIFICATION_MIN:
        classification = "significant_modification"
    else:
        classification = "de_novo_design"

    return {
        "tanimoto": similarity,
        "scaffold_preserved": scaffold_preserved,
        "mcs_atoms": mcs_atoms,
        "atom_delta": proposed.GetNumAtoms() - original.GetNumAtoms(),
        "classification": classification,
    }


def query_pattern(pattern):
    """Build a query Mol from SMARTS, falling back to SMILES."""
    return Chem.MolFromSmarts(pattern) or Chem.MolFromSmiles(pattern)


def check_modification(original_smiles, proposed_smiles, claim):
    """Confirm the structural edit described by `claim` actually happened."""
    original = Chem.MolFromSmiles(original_smiles)
    proposed = Chem.MolFromSmiles(proposed_smiles)
    if original is None or proposed is None:
        return {"verified": False, "reason": "Invalid SMILES"}

    claim_text = claim.lower()
    is_add = any(verb in claim_text for verb in ("add", "introduc", "insert"))
    is_remove = any(verb in claim_text for verb in ("remov", "delet"))
    is_replace = "replac" in claim_text

    checks = []
    for keywords, pattern in GROUP_PATTERNS:
        if not any(keyword in claim_text for keyword in keywords):
            continue
        query = query_pattern(pattern)
        if query is None:
            continue

        in_original = original.HasSubstructMatch(query)
        in_proposed = proposed.HasSubstructMatch(query)

        if is_add:
            checks.append(
                {"group": keywords[0], "expected": "added",
                 "passed": in_proposed and not in_original}
            )
        elif is_remove:
            checks.append(
                {"group": keywords[0], "expected": "removed",
                 "passed": in_original and not in_proposed}
            )
        elif is_replace:
            checks.append(
                {"group": keywords[0], "expected": "present_in_new",
                 "passed": in_proposed}
            )
        else:
            checks.append(
                {"group": keywords[0], "expected": "present", "passed": in_proposed}
            )

    verified = all(check["passed"] for check in checks) if checks else None

    return {
        "claim": claim,
        "checks": checks,
        "verified": verified,
        "note": "No matching structural checks for this claim" if not checks else None,
    }


def print_validation(smiles, result):
    status = "VALID" if result["valid"] else "INVALID"
    print(f"[{status}] {smiles}")
    if result.get("canonical"):
        print(f"  Canonical: {result['canonical']}")
        print(
            f"  Formula: {result.get('formula')} | "
            f"MW: {result.get('mw')} | Atoms: {result.get('num_atoms')}"
        )
    for issue in result.get("issues", []):
        print(f"  Warning: {issue}")


def main():
    parser = argparse.ArgumentParser(description="SMILES validation and verification")
    parser.add_argument("--smiles", type=str, help="Single SMILES to validate")
    parser.add_argument("--original", type=str, help="Original SMILES for comparison")
    parser.add_argument("--proposed", type=str, help="Proposed SMILES")
    parser.add_argument("--check-modification", type=str, help="Claimed modification to verify")
    parser.add_argument("--input", type=str, help="CSV input file for batch validation")
    parser.add_argument("--smiles-col", type=str, default="SMILES", help="SMILES column name")
    parser.add_argument("--output", type=str, default=None, help="Write full JSON result here")

    args = parser.parse_args()
    result = {}

    if args.smiles:
        result = validate(args.smiles)
        print_validation(args.smiles, result)

    elif args.original and args.proposed:
        original_result = validate(args.original)
        proposed_result = validate(args.proposed)
        result = {"original": original_result, "proposed": proposed_result}

        if original_result["valid"] and proposed_result["valid"]:
            comparison = compare(args.original, args.proposed)
            result["comparison"] = comparison
            print(f"Similarity: {comparison['tanimoto']}")
            print(f"Scaffold preserved: {comparison['scaffold_preserved']}")
            print(f"Classification: {comparison['classification']}")
            print(f"Atom delta: {comparison['atom_delta']:+d}")

            if args.check_modification:
                modification = check_modification(
                    args.original, args.proposed, args.check_modification
                )
                result["modification"] = modification
                if modification["verified"] is True:
                    status = "VERIFIED"
                elif modification["verified"] is False:
                    status = "FAILED"
                else:
                    status = "INCONCLUSIVE"
                print(f"\nModification check [{status}]: {args.check_modification}")
                for check in modification.get("checks", []):
                    icon = "PASS" if check["passed"] else "FAIL"
                    print(f"  [{icon}] {check['group']}: expected {check['expected']}")
        else:
            if not original_result["valid"]:
                print(f"Original INVALID: {original_result['issues']}")
            if not proposed_result["valid"]:
                print(f"Proposed INVALID: {proposed_result['issues']}")

    elif args.input:
        import pandas as pd

        frame = pd.read_csv(args.input)
        results = [validate(smiles) for smiles in frame[args.smiles_col]]
        valid_count = sum(1 for entry in results if entry["valid"])
        print(f"Validated {len(results)}: {valid_count} valid, {len(results) - valid_count} invalid")
        result = results

    else:
        print("Error: provide --smiles, --original/--proposed, or --input", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w") as handle:
            json.dump(result, handle, indent=2)
        print(f"Saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
