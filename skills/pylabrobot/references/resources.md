# Resources and Deck Layout

Everything physical in a PyLabRobot protocol is a **Resource**: the deck, a
carrier, a plate, a single well, a tip. Resources form one tree (an arborescence)
with parent/child links and millimetre coordinates, so any item is addressable
and every position is known in space.

## What a resource is

A resource models a piece of labware (plate, tip rack, trough, tube), a device, a
part of labware (well, tip), or a container of labware (deck, carrier). All
subclass `Resource`, which carries:

- `name` — unique identifier within the protocol.
- `size_x`, `size_y`, `size_z` — bounding-box dimensions in millimetres.
- `location` — coordinate relative to the parent origin, set when assigned.

```python
from pylabrobot.resources import Resource
r = Resource(name="my_resource", size_x=127.76, size_y=85.48, size_z=14.5)
```

## Labware types

PyLabRobot ships a large catalog of concrete, vendor-specific labware classes.
The names below are representative; browse `pylabrobot.resources` for the exact
class for your consumable.

```python
from pylabrobot.resources import Cos_96_DW_1mL, TIP_CAR_480_A00

plate = Cos_96_DW_1mL(name="sample_plate")   # 96 deep wells, 1 mL
tip_rack = TIP_CAR_480_A00(name="tips")
```

### Addressing items

Wells and tips are indexed by well name, ranges, or as a flat list:

```python
plate["A1"]        # single well
plate["A1:H1"]     # a column (A1..H1)
plate["A1:A12"]    # a row (A1..A12)
plate["A1:C3"]     # a rectangular block
plate.children     # every well as a list
```

Troughs expose channels (`trough["channel_1"]`), tube racks expose tube
positions (`tube_rack["A1"]`), and carriers provide slots for plates/tips.

## The deck

The deck is the robot's work surface and the root of the placed-resource tree.
Pick the deck that matches your backend:

```python
from pylabrobot.resources import STARLetDeck, OTDeck
deck = STARLetDeck()   # Hamilton STARlet
deck = OTDeck()        # Opentrons OT-2
```

### Assigning resources

Hamilton decks use **rail** positions; others use explicit coordinates:

```python
lh.deck.assign_child_resource(tip_rack, rails=1)
lh.deck.assign_child_resource(source_plate, rails=10)
lh.deck.assign_child_resource(dest_plate, rails=15)

# or by coordinate (x, y, z in mm)
lh.deck.assign_child_resource(tip_rack, location=(100, 200, 0))

lh.deck.unassign_child_resource(tip_rack)   # remove
[r.name for r in lh.deck.children]          # what is on the deck
```

## Coordinate system

Right-handed Cartesian, origin at the bottom-front-left of the parent:

- **X** left→right, **Y** front→back, **Z** down→up.

```python
plate.get_absolute_location()   # relative to the deck/root
plate.location                  # relative to its parent
```

Verify placements do not physically overlap on the deck — assignment does not
collision-check for you.

## State: tips and volumes

State (tip presence, liquid contents) is tracked separately from geometry. Enable
tracking **before** creating resources.

```python
from pylabrobot.resources import set_tip_tracking, set_volume_tracking
set_tip_tracking(True)
set_volume_tracking(True)

plate["A1"].tracker.set_liquids([(None, 200)])          # (liquid_type, µL)
plate["A2"].tracker.set_liquids([("water", 100), ("ethanol", 50)])
plate["A1"].tracker.get_volume()                         # total µL in the well
plate["A1"].tracker.get_liquids()                        # list of (type, µL)

tip_rack["A1"].tracker.has_tip                            # bool
```

Tip presence updates automatically as you `pick_up_tips` / `return_tips`.

## Serialization

Persist both the layout (geometry) and the state (contents) as JSON for
reproducible, version-controlled protocols. Method names vary slightly by
version — confirm against your installed release.

```python
plate.save("plate_definition.json")            # geometry
lh.deck.save("deck_layout.json")

from pylabrobot.resources import Deck
deck = Deck.load_from_json_file("deck_layout.json")

state = lh.deck.serialize_all_state()          # tips + volumes across the tree
lh.deck.load_all_state(state)
```

## Custom labware

When no built-in class matches your consumable, subclass `Plate` (or the relevant
base) and supply the grid geometry. Field names for well spacing and offsets have
changed across versions — treat this as a template and check the current
constructor:

```python
from pylabrobot.resources import Plate

class CustomPlate(Plate):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            size_x=127.76, size_y=85.48, size_z=14.5,
            # grid + per-well geometry: num_items_x/y, item spacing, offsets,
            # well max_volume, and bottom shape ("flat"/"u"/"v").
        )
```

For one-off geometry, measure carefully — the coordinates you provide drive real
robot motion.

## Navigation

```python
lh.deck.get_resource("source")                  # by name
for r in lh.deck.children:                       # iterate placed resources
    print(r.name, r.get_absolute_location())

from pylabrobot.resources import Plate, TipRack
isinstance(resource, Plate)                      # type-check before operating
```

## References

- Resource intro: <https://docs.pylabrobot.org/resources/introduction.html>
- Custom resources: <https://docs.pylabrobot.org/resources/custom-resources.html>
- API: <https://docs.pylabrobot.org/api/pylabrobot.resources.html>
