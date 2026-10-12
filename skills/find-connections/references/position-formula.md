# Position and count formula

> **The positions are computed by a script, not by hand.** This document is
> the specification of `assets/layout/layout.py` (pure Python standard
> library, deterministic): in phase 2.F Kiro writes the Level 1 data to a
> JSON file, runs the script and copies its result into the export.
> Do not compute coordinates mentally. See "The layout script"
> at the end of the position sections.

## Position (x, y, z) — defines WHERE the repo lives in the cube

Each point belongs to one of three **categories**, each with a fixed anchor
and a pure extreme toward which it migrates according to its traffic
volume. It is not a free proportion among the three axes, nor the exclusive
base-axis rule — it is anchor + smooth migration.

### Categories — derived from the repo role (see `repo-roles.md`)

| Category (role) | Applies to | Anchor (x,y,z) | Pure extreme (x,y,z) | Growth axis |
|---|---|---|---|---|
| `frontend` | Repo with client-facing UI that does not expose an API | (58, 48, 5) → client zone | (100, 0, 100) | `count_Z` (direct external connections it makes) |
| `mvc-monolith` | All in one: UI + server logic | (72, 76, 62) | (40, 100, 20) | `count_Y` (internal traffic toward other Acme repos) |
| `backend` | Exposes endpoints, no UI | (70, 70, 70) | (0, 100, 0) | `count_Y` (own internal traffic) |
| `worker` | Processes queues/jobs, does not serve requests | (2, 66, 30) → worker zone | (0, 100, 100) | `count_Z` (connections toward external systems) |
| Virtual Client (`external`, axis X) | A client's system, no repo | (60, 30, 5) → client zone | (100, 0, 0) | number of repos that reference it |
| Virtual Internal (`external`, axis Y) | Acme system outside the workspace | (70, 72, 70) | (0, 100, 0) | number of repos that reference it |
| Virtual External (`external`, axis Z) | Real third party | (40, 30, 95) → external zone | (0, 0, 100) | number of repos that reference it |

The three "Virtual" categories never have their own count (there is no code
to scan) — they all migrate according to how many repos in the workspace
reference them as target, using the same migration formula.

**Four zones.** The business is providing a software service, so the bulk
of the cube — top and center — is the internal work; the client and the
third parties stay on the edges, each one stuck to its face of the cube.
Each zone is a **box** that is filled evenly (see "Volume fill"):

| Zone | Who | Box (semantic x, y, z) | Stuck to | Reading |
|---|---|---|---|---|
| **Client** | `frontend`, Virtual Client | x 30–100, y 5–75, z from `CLIENT_PLANE = 4`, thickness 8–30 | plane z ≈ 0 (almost no external traffic) | Left, on the Client axis |
| **Internal** | `backend`, `mvc-monolith`, Virtual Internal | x 38–96, y 40–100, z 38–96 | — (the whole box) | Top, center |
| **Worker** | `worker` | x from 1, thickness 6–20, y 56–100, z 8–70 | plane x ≈ 0, next to the Y axis | Up, stuck to the Internal axis |
| **External** | Virtual External | x from `EXTERNAL_PLANE = 6`, thickness 8–28, y 0–52, z 36–100 | plane x ≈ 0 | Right, on the External axis |

The four boxes are disjoint from each other and from the database box next
to the origin, so points of different zones can never overlap. Client sits on
the left and External on the right of the screen, and Internal on top (see
the camera angle in `generate-visual`). The values are an adjustable
starting point, just like `K` and `DELTA_MAX`.

The growth axis of **Front** is still Z: the more direct external
connections it accumulates, the further it moves away from its plane toward
the external side — it is the position reflecting real traffic, with no
separate state or mark.

**Worker Client value between 1 and 7.** A worker serves Acme and third
parties, almost never the client, so it lives next to the Y axis:

```
jitter = (hash(id) % 100) / 100                      # deterministic spread
x      = 1 + 3 × jitter + 3 × count_X / (count_X + K_fine)
# base 1–4 so two workers never share the exact same plane,
# plus up to 3 from its real traffic toward the client: range 1..7
```

### Migration formula

```
factor = dominant_count / (dominant_count + K)      # K = 20 by default, adjustable
final_point = anchor + factor × (pure_extreme − anchor)
```

`factor` approaches 1 as the dominant count grows (it never gets to exceed
the pure extreme), and 0 when the count is low (the point stays near the
center of its category). The displacement is smooth, not a jump — two repos
with similar counts end up visually close to each other, instead of falling
into discrete steps.

### Examples (K=20, dominant axis only; secondary axes and zones are applied afterwards)

- `backend` repo with `count_Y = 0` → `y` stays at the anchor `70`
- `backend` repo with `count_Y = 20` → factor 0.5 → `y = 70 + 0.5 × 30 = 85`
- Front with `count_Z = 0` → `z` on its plane (`4`); `x` (Client) ends up
  near `70` and `y` near `30`: at the back, on the Client axis
- Front with `count_Z = 20` → factor 0.5 → it detaches from its plane toward
  the external side, because it accumulates direct external connections
- Virtual External → `x = 6` (its plane), low `y`, spread along the
  External axis around `86`

### Secondary axes — position by real importance, not decoration ("floating")

The two axes that are not the category's dominant one **no longer stay
frozen at the anchor nor get displaced by an arbitrary angle** (hash +
jitter). Each secondary axis migrates toward its own extreme with the same
logic as the dominant axis — anchor + migration factor — only with a lower
ceiling (`DELTA_MAX`) so that it never competes visually with the dominant
axis. The underlying idea: **every point participates in all three axes at
once** (a front does not belong only to the client, it also has a role
toward Y and toward Z), and the final position has to show that mix of real
importance, not only that of the axis that won.

```
K_fine = 8                # smaller than K, noticeable even with little traffic
DELTA_MAX = 25             # displacement ceiling of a secondary axis —
                           # large on purpose so that the
                           # points float with more space between them, instead
                           # of feeling stuck to the anchor plane
FLOOR_RADIUS = 0.4          # minimum fraction of DELTA_MAX, ALWAYS > 0 —
                           # no point sits exactly on the anchor

# For each of the two secondary axes (i = the one that is not dominant):
fine_factor_i = count_axis_i / (count_axis_i + K_fine)
offset_i = max(fine_factor_i, FLOOR_RADIUS) × DELTA_MAX

# Direction of the offset: toward the pure extreme OF THE CATEGORY on that axis
# (not toward the anchor, nor in an arbitrary circle around it).
#   sign_toward_extreme(axis_i) = sign(pure_extreme[i] - anchor[i])
#   if that difference is 0 (e.g. mvc-monolith in Z: 20 -> 20) → +1
secondary_axis_value_i = anchor_that_axis + offset_i × sign_toward_extreme(axis_i)

# deterministic jitter (by point ID) ONLY as a final tie-breaker, not
# as the driver of the position — separates two points that would end up exactly
# on the same triple because they have identical counts on all three axes.
jitter = hash(point_id) % 100 / 100          # 0..1, deterministic
secondary_axis_value_i += jitter × 0.15 × DELTA_MAX × sign_toward_extreme(axis_i)
```

**Sign clarification.** "Extreme" is the pure extreme of the category (the
"Pure extreme" column of the table), not the value 100 of the axis. With the
"always toward 100" reading, a `backend` with little traffic ended up with
its secondary axes (x, z ≈ 60) above its dominant axis (y ≈ 60) and was
painted blue or orange despite being internal. With the category sign the
backend moves away from client and external (x, z go down) and keeps its
green color.

**MANDATORY for Virtual categories — it is neither optional nor conditional.**
Virtual points (Virtual Client/Internal/External) **have no real
`count_axis_i`** — there is never own code to scan, only the number of
repos that reference them (which is already used for the dominant axis).
For their two secondary axes, `count_axis_i` is always treated as **0** —
the calculation is never skipped, nor is the point left stuck to the anchor
for "not having a count". The result follows the same path as any point
with `count_axis_i = 0`:

```
fine_factor_i = 0
offset_i = FLOOR_RADIUS × DELTA_MAX      # the floor, never 0
+ the deterministic jitter by ID, same as for any other point
```

This is the most common overlap case (several virtual points on the same
axis, referenced by the same number of repos, end up with identical anchor
and dominant) — that is why the `FLOOR_RADIUS` floor and the `jitter` by ID
are what guarantee they do not fall on the exact same triple. If two or more
virtual points on the same axis appear with the same rounded `(x,y,z)`
triple, it is a sign that this rule was not applied — not a legitimate tie.

The position on the secondary axes is not decorative (it does not come
from a hash only meant to avoid visual overlap): **the full position
(all three axes) is a combination of the number of mapped endpoints
(inbound and outbound) and the relative importance of each axis against the
other two** — a point with a lot of real traffic on its secondary axis
visibly moves toward that extreme, not only toward the dominant one.

**The vector curvature is no longer merely emergent** — see section "Curved
vector (arc)" below: a control point is explicitly calculated per vector.

`FLOOR_RADIUS` still guarantees that no point sits exactly on the anchor
even without secondary traffic — so the points always "float" a minimum,
instead of feeling stuck to the plane of their category.

**This is not shown as a separate piece of data** — what is recorded is only
`pos_x`, `pos_y`, `pos_z` (the already calculated values, anchor + dominant +
the two secondary ones, all together; in `layout.json` and in the repo's MOC
they come **without any swap** — see section "Final axis transformation"
below, which applies only when generating the `allspark.md` export). The
intermediate factors are part of the power's internal calculation, not fields
that are written anywhere.

### Final result per point

```
(x, y, z) = dominant axis according to main factor (anchor → pure extreme) +
the two secondary axes, each one migrating independently toward its
own extreme according to its own real count (anchor → extreme, ceiling
DELTA_MAX), all starting from the same category anchor
```

If all three counts are 0, the point stays at its anchor plus the minimum
`FLOOR_RADIUS` floor on each secondary axis — that is not an error, it is
the starting position before having a signal. Different is a repo with
signals that were badly detected (see `framework-patterns.md`), which is a
scanning problem, not a formula problem.

## Grouping of systems without a repo, and volume fill

### Grouping by provider

A system without a repo is not one point per host: `api.stripe.com`,
`files.stripe.com` and `cdn.stripe.com` are **one provider**. Before
positioning, the script groups them:

| Axis | Group key | Example |
|---|---|---|
| X (Client) and Z (External) | Registrable domain: the last 2 labels (3 if the TLD has two levels: `com.ve`, `gob.ve`, `co.uk`, `com.br`...) | `api.stripe.com`, `files.stripe.com` → `stripe.com` |
| Y (Internal, Acme) | Name without role suffix (`-batch`, `-reports`, `-sso`, `-api`, `-web`, `-ui`, `-db`), because every internal system shares one domain | `core-banking.acme.local`, `core-banking-batch.acme.local` → `core-banking.acme.local` |

Connections are merged per `(source, target group, protocol)` and their
`endpoints` are **added up**: the weight of the merged connection is the
number of endpoints it stands for. The host-level detail stays in the MOC of
each repo and in Levels 2 and 3.

### Volume fill

Each zone is a box (table above) that is **filled evenly in 3D**, never a
ring: the radius of a ring grows linearly with the number of points, so
with dozens of points it exceeds the cube, the points end up pressed against
the walls and some fall on the very same position. The volume fill has no
such limit.

```
FILL = 0.7        SEP_MAX = 20        SEP_FLOOR = 5.5

sep    = min(SEP_MAX, (FILL × box_volume / n) ^ (1/3))      # the LARGEST separation the box allows
# stuck zones (client, external, worker): the box volume is area × T, with the thickness
T      = clamp(tk × n^(1/3), tmin, tmax)                    # tk = 5 (client, external), 3.2 (worker)
if sep < 9 and T < tmax:  T = tmax and sep is recomputed    # thicker before a tighter separation

# even initial position on each FREE axis, keeping the order of importance
target = box_lo + (box_hi − box_lo) × (0.5 × rank + 0.5 × normalized_value)
#        rank = order among the zone's points on that axis (ties broken by hash),
#        normalized_value = the formula's value between the zone's min and max
# stuck axis: spread over the whole thickness with a golden-ratio sequence

repeat up to 600 times:
    every pair closer than sep is pushed apart, half each
    every point is pulled 3% toward its target
    every point is clamped inside its box
    stop when the worst overlap is < 0.05
```

- **Order of importance is kept, magnitude only in part.** A repo with more
  traffic still sits toward its extreme, but 50% of the position is its
  order among its zone's points and 50% its real value: distances are no
  longer proportional to counts.
- **Deterministic**: ids are sorted, the jitter is a hash of the id and the
  number of iterations is fixed. The same input gives the same output.
- **Achieved separation is measured**, not estimated: if any zone ends with
  two points closer than 6, the script reports a warning (`overflow`) with
  the zone and the separation achieved, instead of hiding it.
- **Capacity (measured):** no overlapping pairs up to 450 points in a
  workspace (about 0.3 s for 79 points, 18 s for 450 in pure Python).
  Beyond that, or if a warning appears, enlarge the box of that zone in
  `ZONES` or split the workspace.

## Coordinate range

All point positions go from `0` to `100`. The only thing that can leave the
cube are **the control points of the internal → external arcs**: their `cy`
can exceed `100` on purpose (see "Curved vector — shape according to
source and target"), so that the arc falls
onto the external point from above. Renders draw the cube from `0` to `100`
and those arcs naturally stay outside.

## Curved vector — shape according to source and target

Each vector is drawn as a **curve**, not as a straight line between two
points (except the direct case). It is still a vector: it has source,
target, direction and sense (arrow at the target). The shape depends on the
**target**, and in one case on the **source**:

| Vector | Shape | Reading |
|---|---|---|
| Toward an internal point (workspace repo or Virtual Internal) | **Concave**: goes down and up, inside the cube | The process starts low and rises toward Acme: front → backend, client → backend, backend → worker |
| From an internal point toward an external one (Virtual External) | **Arc over the external point**: rises above the higher of the two and falls onto the external point from above (it may pass above the cube) | Acme goes out toward a third party |
| From the client zone (`frontend`, Virtual Client) directly to an external point | **Straight**, coral color `#F43F5E` | The client calls a third party without going through Acme: distinguished on purpose |
| Directly toward the client (Virtual Client) | **Convex**: goes up and down, inside the cube | Acme responds to or notifies the client, e.g. a webhook back |

**One control point per vector** is calculated (quadratic Bezier curve), in
semantic coordinates (before the swap):

```
BASE_HEIGHT = 12
HEIGHT_FACTOR = 0.15
midpoint = (source + target) / 2
distance = |target - source|                       # euclidean
offset = BASE_HEIGHT + HEIGHT_FACTOR × distance

concave (internal target):
    control_y = max(0, min(source.y, target.y) - offset)
arc over the external point (internal → external):
    control_y = max(source.y, target.y) + offset      # no cap: may exceed 100
straight (client zone → external):
    control = midpoint                                    # the Bezier degenerates into a straight line
convex (client target):
    control_y = min(100, max(source.y, target.y) + offset)

control_x = midpoint.x
control_z = midpoint.z
curve(t) = (1-t)² × source + 2(1-t)t × control + t² × target,  t ∈ [0,1]
```

- Chained together, the vectors of a process tell its journey: it leaves
  the front and rises to Acme (concave); from Acme it rises and falls onto
  the third party (arc). If the front jumps directly to the third party,
  the coral straight line gives it away.
- Long vectors curve more (because of `distance`), so that they are not
  hidden by the short ones from the same source.
- Two vectors with the same source-target pair and different protocol are
  distinct vectors (the ID includes the protocol): they are separated by
  adding `protocol_index × 4` to `offset` (on the straight line, shifting
  the midpoint `protocol_index × 4` in Y).
- The straight vector is marked in the export with `direct: true` (see
  `export-format.md`), so that the render paints it coral without
  recalculating.

The control point **is written into the export** (`allspark.md`, field
`curve` of each vector — see `export-format.md`) so that the render does not
have to recalculate it. It does not appear in the repos' MOCs.

## Database nuclei

Modules (Level 2) and their endpoints are **not points of the
cube**: they are shown as trees and strands over the points that already
exist (see `generate-visual`), so they need no position. Databases, on the
other hand, are points from Level 1: every database that a repo of the
workspace uses is **a nucleus near the origin of the axes**. Data is the
foundation all three axes rest on, and the origin is the only empty region
of the cube.

### Identity

```
id = <engine>://<host>/<database-name>        # e.g. postgres://payments-db/payments
```

Built from the database configuration (connection string, datasource or ORM
config — see `prescan.md`), **never including credentials**. Two repos that
point to the same engine + host + name share **a single nucleus**.

### Position

Databases are a fifth zone: a **box of their own next to the origin**, filled
in 3D with the same volume fill as every other zone (see "Volume fill"). It is
the only region of the cube that no other zone uses, it starts a little away
from the origin and it rises like a column, so the nuclei spread upward.

```
DB_BOX = x 8–26 (Client), y 6–50 (Internal), z 8–30 (External)       # semantic
DB_SEP_MAX = 24        DB_SEP_FLOOR = 6

sep = clamp((FILL × box_volume / n_db) ^ (1/3), DB_SEP_FLOOR, DB_SEP_MAX)

# the more used, the lower: on the Internal axis the order is by uses, the most
# used at the bottom; on the other two axes the order comes from a hash of the id
y_target = 6 + 44 × (1 − normalized_uses)
```

The relaxation is the same as for the other zones (pairs closer than `sep` are
pushed apart, weak pull toward the target, clamped to the box). A single
database sits at the center of the box. Positions are written into
`pos_x/y/z` like any point (and swapped in the export). Measured from 1 to 40
databases: no coordinate outside 0–100, everything inside the box, and no
neighbour closer than 6.

### Size and electrons

```
nucleus radius ∝ 1 + 0.5 × log2(repos that use it)

uses_k    = repos of the workspace that use database k
electrons = 3                                            if every database has the same uses
          = round(1 + 4 × (uses_k − min) / (max − min))  otherwise   → 1..5
```

The most used database of the workspace has 5 electrons and the least used
1. In the 3D view the electrons **orbit slowly** on tilted orbits, like an
atom.

**The orbit never crosses a neighbour.** The script exports, for each
database, `orbit`: the largest electron orbit allowed, in cube units.

```
orbit = 0.42 × distance to the nearest other database        # 14 if it is the only one
```

The render takes the smaller of this and the natural orbit of the nucleus and
shrinks the nucleus and its orbits to fit, so atoms get smaller when there are
many (2.8 units with 40 databases, 14 with one).

### Data links

Each repo–database usage is a `data` link (gold `#FACC15`) from the repo
down to the nucleus. In the global view the many links are shown as a single
bundle, and each repo's own links appear when the repo is selected.

| Type | Color | Hex | Shape (3D cube) |
|---|---|---|---|
| Database | Gold | `#FACC15` | Nucleus with 1–5 orbiting electrons |

## Repos not documented yet

A repo of the workspace that has no MOC (no documented entry point reached
it) has no connections, so its counts are zero. The script still positions it
like any repo of its category — it lands in its zone, among the documented
ones — takes part in the volume fill like every point, and exports it with
`documented: false`. The 3D view draws it **small, hollow and dotted**, so the
cube shows the coverage: how much is documented and how much is still to tell.
A documented frontend or monolith is exported with `entry_point: true` and is
drawn with a ring. Positions are recomputed from everything documented so far,
so a repo moves a little when it goes from not documented to documented
(deterministically).

A repo marked as not documented that turns out to have connections is treated
as documented, with a warning.

## The layout script

`assets/layout/layout.py` implements everything above (anchors, migration,
secondary axes, grouping, volume fill, database nuclei, merging of
connections) and additionally applies the **X/Z swap** of the export, so
that Kiro never has to. Input and output are documented in the script
header; in short:

```bash
python3 <skill>/assets/layout/layout.py --input .kiro/allspark/level1.json --output .kiro/allspark/layout.json
python3 <skill>/assets/layout/layout.py --selftest      # checks determinism, grouping, no overlaps and the swap
```

- **Input:** repos with their role (and `documented: false` for the ones without a
  MOC yet), systems without a repo with their axis,
  connections with their endpoints, and databases with the repos that use
  them.
- **Output:** `points` (with `pos` in semantic coordinates for the MOCs
  and `export` already swapped), `vectors` (merged, with `endpoints`
  and `direct` when the client zone calls an external point straight),
  `links` (repo → database), per-zone `zones` diagnostics and `warnings`.
- Only the standard library of Python 3.8+ is needed: no environment to set
  up. If Python is not available, Kiro reports it and the visualization is
  not generated (the MOCs are not affected).

## Color — repos by type, systems without a repo by dominant axis

**Workspace repos: color by type.** Every repo in the workspace is one of
Acme's own systems, so its color does not come from the axis with the most
traffic but from who it serves:

| Repo type | Color | Hex | Why |
|---|---|---|---|
| `frontend` | Blue | `#3B82F6` | Its axis is the client |
| `mvc-monolith` | Teal | `#2EA3AA` | Blend of blue and green: influenced by both front and back |
| `backend` | Green | `#22C55E` | Internal service |
| `worker` | Green | `#22C55E` | Internal service: it serves Acme (Y) and third parties, not the client |

**Systems without a repo (virtual points): color by dominant axis**, as
always — the axis with the highest value in the final position:

```
color = axis with the highest value among {x, y, z}
# tie: priority X > Y > Z (arbitrary but deterministic)
```

| Axis | Color | Hex |
|---|---|---|
| X — Client | Blue | `#3B82F6` |
| Y — Internal (Acme) | Green | `#22C55E` |
| Z — External | Orange | `#F97316` |

Systems without a repo are drawn dashed (wireframe), so an orange external
is never mistaken for a repo.

Vectors take the color of the connection's axis, with a single exception:
the **direct** vector client zone → external is coral `#F43F5E`.

## Final axis transformation — X/Z swap only in the export (mandatory)

**This applies only when
generating `allspark/export/allspark.md`** (the compiled export consumed by
`generate-visual`) — **never** to `layout.json`'s `pos` or to the position
recorded in the repos' MOCs, which keep `pos_x`/`pos_y`/`pos_z` exactly as
they were calculated, without swap.

**Everything above in this document (anchors, extremes, migration, color by
dominant axis) stays exactly the same, untouched, and that is how it is
recorded in the MOCs.** `axis X` is still the Client
semantics, `axis Y` the Internal one, `axis Z` the External one — all the
internal calculation of this file uses those names unchanged. The swap is a
**last, mechanical step, applied only once, only when building the
export**, right before writing each point entry into `allspark.md`:

```
# Only inside allspark.md — the MOCs and layout.json's `pos` do NOT go through this
pos_x_export = value_computed_for_axis_Z   (External)
pos_y_export = value_computed_for_axis_Y   (Internal, unchanged)
pos_z_export = value_computed_for_axis_X   (Client)
```

That is: inside `allspark.md`, the number this document calculated for the
Client axis (X) is written in the `pos_z` field, and the number calculated
for the External axis (Z) is written in the `pos_x` field. `pos_y`
(Internal) is not touched.

**The swap applies to ALL coordinates of the export, not only to the axes.**
A typical mistake is inverting the axis lines but leaving the points with
their coordinates not inverted: the axes look right and the points fall
near the wrong plane. Inside `allspark.md` the following go
through the same swap, without exception:

1. The export's axis declaration (`axes:` — which field is which axis).
2. Each real point (`frontend`, `backend`, `mvc-monolith`, `worker`).
3. Each virtual point (Client, Internal, External).
4. Each database nucleus.
5. Each curve control point (`curve.cx`, `curve.cz`).

The render consumes `allspark.md` as is, **without doing any swap of its
own** — neither on the axis lines nor on the points. If the render inverts
axes on its own in addition to the export, the same mismatch happens in
reverse.

Mandatory check when writing the export: for each point,
`pos_x_export == semantic_value_Z` and `pos_z_export == semantic_value_X`.
Quick sanity check: a well-behaved `frontend` has to come out in the export
with a very low `pos_x` (stuck to the ZY plane) and a medium-high `pos_z`
(on the Client axis); and every Virtual External, with a very low `pos_z`
(stuck to the Client ≈ 0 plane) and a high `pos_x` (on the External axis).
The MOCs keep the original values without swap — they are two
representations of the same calculation, each one for its consumer.

**The color is not affected by this swap.** The color of each point is
still determined by which semantic axis was dominant (Client/Internal/
External) **before** the swap — never by which field (`pos_x` or `pos_z`)
the value ended up written in within `allspark.md`. A Front point that
migrated toward External is still painted orange, regardless of that value
now living in `pos_x` of the export.

**Why the swap only in the export and not in the MOCs:** the MOCs are for
direct human reading — there `pos_x = Client` has to remain intuitive for
whoever opens them. `allspark.md` on the other hand is consumption data for the render, where
what matters is that a simple render, without any special camera rotation,
already reads client on the left and external on the right correctly.

## Path — sequence order, not derived from the position

The visual path of a process (the sequence of points it goes through) is
never calculated by comparing position values between points — it
exclusively follows the explicit connections (source → target) of the MOCs
and the `vectors` and `hops` of the export. Fixed rule:

- The first node of any path is always a `frontend`, `mvc-monolith` or
  **Virtual Client** point. A `backend` or `worker` can never be the first
  node of a sequence. This is consistent with the Front anchor at high X:
  the path starts on the client face (X), goes through the Acme backend (Y)
  and ends at the external systems (Z), tracing the X -> Y -> Z curve that
  we want to visualize.
- If the MOC generated a path where a backend appears before the frontend
  that originates it, it is a signal that the vector ended up with
  source/target inverted — it is fixed in the MOC (or via override), never
  by adjusting the render to "accommodate" the order.

## Count per axis — real quantity, not proportion

It counts the repo's **concrete endpoints** grouped by the axis of the
domain they belong to — not only whether the connection exists, but how
many local endpoints use it. With prescan, each classified (and not
discarded) candidate is an endpoint: `count_X/Y/Z` is the number of
candidates classified on each axis. Without prescan, they are counted by
hand with the framework-specific detection (the language/stack is already
identified in `tech.md`):

- Express/NestJS → route decorators (`@Get`, `@Post`, `router.get(...)`)
- Spring → `@RequestMapping`, `@GetMapping`, etc.
- Django → `urls.py` / `urlpatterns`
- Rails → `routes.rb`
- (add the corresponding pattern when detecting a new stack)

```
count_X = number of the repo's endpoints classified toward X
count_Y = number of the repo's endpoints classified toward Y
count_Z = number of the repo's endpoints classified toward Z
```

Each endpoint inherits the axis classification of the domain it is
associated with (the same domain already resolved for the MOC). For virtual
points (External category) it does not apply — they have no own code to
scan, their growth metric is the number of repos that reference them, not
an endpoint count.

## Difference between position and count

- **Position** — where the repo is in the cube: anchor of its category +
  smooth migration toward the pure extreme according to a single dominant
  count.
- **Count** — the three absolute numbers per axis (`count_X/Y/Z`),
  complete, without being reduced to a single one. The position only uses
  the dominant one of its category; the rest of the counts remain available
  as separate data (e.g. to show in the tooltip of a point in the 3D cube).
