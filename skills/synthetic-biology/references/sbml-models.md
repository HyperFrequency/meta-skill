# SBML Model Construction

Build standards-compliant **SBML Level 3 Version 2** models programmatically
with python-libsbml, so a reaction network can be exchanged with COPASI, Tellurium,
COBRApy, BioModels, or any SBML-aware tool. Covers compartments, species,
reactions with kinetic laws parsed from infix formulas, local parameters,
validation, and writing.

## Install

```bash
uv pip install python-libsbml     # package name has the python- prefix
```

The **package** is `python-libsbml` but the **import** is `import libsbml`.
libSBML is a C++ library with a SWIG Python wrapper; the wheel bundles the
native library, so no separate C++ build is normally needed. If a wheel is
missing for your platform, `pip install python-libsbml-experimental` sometimes
provides one.

## The checked-return idiom

Most libSBML setters return an integer status code, not a raised exception.
Wrap them so silent failures surface immediately:

```python
import libsbml

def check(value, message):
    if value is None:
        raise RuntimeError(f"libSBML returned None: {message}")
    if isinstance(value, int) and value != libsbml.LIBSBML_OPERATION_SUCCESS:
        raise RuntimeError(f"libSBML error ({value}): {message} - "
                           f"{libsbml.OperationReturnValue_toString(value)}")
```

## Document, model, and units

```python
def create_document():
    doc = libsbml.SBMLDocument(3, 2)                  # Level 3, Version 2
    model = doc.createModel()
    check(model, "create model")
    check(model.setId("model"), "set id")
    check(model.setTimeUnits("second"), "time units")
    check(model.setSubstanceUnits("mole"), "substance units")
    check(model.setExtentUnits("mole"), "extent units")
    # a reusable per-second unit for rate constants
    ud = model.createUnitDefinition(); ud.setId("per_second")
    u = ud.createUnit()
    u.setKind(libsbml.UNIT_KIND_SECOND); u.setExponent(-1); u.setScale(0); u.setMultiplier(1.0)
    return doc, model
```

Declaring model-level units up front is the single biggest lever on passing
validation cleanly — undeclared units are the most common warning.

## Compartments

```python
def add_compartment(model, cid, size=1.0, dims=3):
    c = model.createCompartment()
    check(c.setId(cid), f"id {cid}")
    check(c.setConstant(True), "constant")
    check(c.setSpatialDimensions(dims), "dims")
    check(c.setSize(size), "size")
    check(c.setUnits("litre"), "units")
    return cid
```

## Species

A species can be initialized by **amount** (`setInitialAmount`, moles) or by
**concentration** (`setInitialConcentration`, amount/size). Pick one and be
consistent; concentration requires the compartment size to be set.

```python
def add_species(model, sid, compartment, initial=0.0):
    s = model.createSpecies()
    check(s.setId(sid), f"id {sid}")
    check(s.setCompartment(compartment), "compartment")
    check(s.setInitialConcentration(initial), "initial")   # or setInitialAmount
    check(s.setBoundaryCondition(False), "boundary")
    check(s.setConstant(False), "constant")
    check(s.setHasOnlySubstanceUnits(False), "substance units")
    return sid
```

Set `boundary_condition=True` for a species held fixed by the environment (a
source/sink not produced/consumed by the model's own rules).

## Reactions and kinetic laws

Reactants/products need a stoichiometry and `setConstant(True)`. The rate law is
an **infix formula string** parsed to a MathML AST with `parseL3Formula`; local
parameters live inside the kinetic law.

```python
def add_reaction(model, rid, reactants, products, rate_law, parameters,
                 reversible=False, modifiers=()):
    r = model.createReaction()
    check(r.setId(rid), f"id {rid}")
    check(r.setReversible(reversible), "reversible")
    for sid, stoich in reactants.items():
        sr = r.createReactant(); check(sr.setSpecies(sid), sid)
        sr.setStoichiometry(float(stoich)); sr.setConstant(True)
    for sid, stoich in products.items():
        sp = r.createProduct(); check(sp.setSpecies(sid), sid)
        sp.setStoichiometry(float(stoich)); sp.setConstant(True)
    for mid in modifiers:                              # e.g. an enzyme in the rate law
        r.createModifier().setSpecies(mid)
    kl = r.createKineticLaw()
    ast = libsbml.parseL3Formula(rate_law)
    if ast is None:
        raise ValueError(f"bad rate law '{rate_law}': {libsbml.getLastParseL3Error()}")
    check(kl.setMath(ast), "set math")
    for pid, val in parameters.items():
        lp = kl.createLocalParameter()
        check(lp.setId(pid), pid); lp.setValue(float(val)); lp.setConstant(True)
    return rid
```

Rate-law examples: mass action `"k1 * A"`, reversible `"kf*X - kr*Y"`,
Michaelis-Menten `"Vmax * S / (Km + S)"`. Any species referenced only in the
rate law (not as reactant/product) should be declared a **modifier** or
validation will flag an undefined symbol.

## Validation

```python
def validate(doc):
    doc.checkConsistency()
    errors, warnings = [], []
    for i in range(doc.getNumErrors()):
        e = doc.getError(i)
        msg = f"[{e.getSeverityAsString()}] line {e.getLine()}: {e.getMessage()}"
        (errors if e.getSeverity() >= libsbml.LIBSBML_SEV_ERROR else warnings).append(msg)
    return errors, warnings
```

Distinguish severities: `LIBSBML_SEV_ERROR` (and `_FATAL`) block a correct model;
`_WARNING` and `_INFO` are advisory (often missing units). Always run this before
writing. Note `getNumErrors()` after `checkConsistency()` counts all diagnostics,
not only fatal ones.

## Writing and inspecting

```python
writer = libsbml.SBMLWriter()
if not writer.writeSBMLToFile(doc, "model.xml"):
    raise RuntimeError("write failed")

# read a kinetic law back as infix for a human-readable summary
kl = model.getReaction(0).getKineticLaw()
print(libsbml.formulaToInfix(kl.getMath()))
```

## Common errors

- **`import libsbml` fails** — you installed the wrong package; use
  `python-libsbml` (not `libsbml`).
- **`parseL3Formula` returns `None`** — malformed rate law (unbalanced parens,
  unknown function). Inspect `getLastParseL3Error()`.
- **"undeclared units" warnings** — set model time/substance/extent units and
  compartment/species units; they are warnings, not fatal, but pollute exchange.
- **Species referenced in a rate law but not declared** — add it as a species
  and mark it a reaction modifier.
- **Concentration set without a compartment size** — `setInitialConcentration`
  needs a sized compartment; otherwise use `setInitialAmount`.
- **Level/Version mismatch** — some `setFast` / stoichiometry conventions differ
  between L2 and L3; this reference targets L3V2 throughout.
