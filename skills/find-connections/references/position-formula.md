# Position and count formula

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
| `worker` | Processes queues/jobs, does not serve requests | (8, 68, 62) | (15, 40, 100) | `count_Z` (connections toward external systems) |
| Virtual Client (`external`, axis X) | A client's system, no repo | (60, 30, 5) → client zone | (100, 0, 0) | number of repos that reference it |
| Virtual Internal (`external`, axis Y) | Acme system outside the workspace | (70, 72, 70) | (0, 100, 0) | number of repos that reference it |
| Virtual External (`external`, axis Z) | Real third party | (40, 30, 95) → external zone | (0, 0, 100) | number of repos that reference it |

The three "Virtual" categories never have their own count (there is no code
to scan) — they all migrate according to how many repos in the vault
reference them as target, using the same migration formula.

**Three zones.** The business is providing a software service, so the bulk
of the cube — top and center — is the internal work; the client and the
third parties stay on the edges, each one stuck to its face of the cube:

| Zone | Who | Where they live | Reading |
|---|---|---|---|
| **Client** | `frontend`, Virtual Client | Stuck to the ZY plane (`z = CLIENT_PLANE = 4`, almost no external traffic), along the Client axis but pulled back toward the origin (x ≈ 55–75), low in Y | Left, on the Client axis |
| **Internal** | `backend`, `mvc-monolith`, Virtual Internal | Center of the cube, shifted toward the corner near the camera (x, z ≈ 45–70), high in Y | Top, center |
| **External** | Virtual External (and the `worker` points on the External axis side) | Stuck to the Client ≈ 0 plane (`x = EXTERNAL_PLANE = 6`), spread along the External axis around `EXTERNAL_CENTER = 86`, low in Y | Right, on the External axis |

Client sits on the left and External on the right of the screen, and
Internal on top (see the camera angle in `generate-visual`). The values are
an adjustable starting point, just like `K` and `DELTA_MAX`.

The growth axis of **Front** is still Z: the more direct external
connections it accumulates, the further it moves away from its plane toward
the external side — it is the position reflecting real traffic, with no
separate state or mark.

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

**In the vault, this is not shown as a separate piece of data** — the
frontmatter of each note in `allspark/graphs/` still shows only `pos_x`,
`pos_y`, `pos_z` (the already calculated values, anchor + dominant + the two
secondary ones, all together, **without any swap** — see section "Final
axis transformation" below, which applies only when generating the
`allspark.md` export, never to these notes). The intermediate factors are
part of the power's internal calculation, not fields that appear on their
own in the note when opening the vault.

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

## Anti-overlap rings

The jitter and `FLOOR_RADIUS` prevent two points from falling on the same
triple, but not from being crowded: several backends with similar traffic
end up a few units apart and their names overlap. That is why, after
calculating all the positions, nearby points are spread over a **circular
orbit** (static) around their common center.

```
CLUSTER_THRESHOLD = 10     # two points closer than this belong to the same cluster
MIN_CHORD    = 17     # minimum separation between ring neighbors
MIN_RING_RADIUS  = 7
TILT   = 35°    # tilt of the ring plane (internal layers)

clusters = connected components of "distance < CLUSTER_THRESHOLD", per layer
for each cluster with n >= 2:
    center = average of its positions
    r = max(MIN_RING_RADIUS, MIN_CHORD / (2 × sin(π / n)))
    center is shifted inward so that the whole ring fits in 0..100
    order = by original angle around the center (tie-break by ID)
    angle_0 = 2π × (hash(id of the first) % 360) / 360
    member k → angle_k = angle_0 + 2π × k / n
```

**Layers and planes** — a ring never mixes layers, and each one is spread
**within the plane of its zone**:

| Layer | Ring plane |
|---|---|
| Client zone (`frontend`, Virtual Client) | ZY plane: `z` fixed at `CLIENT_PLANE`, spread over (x, y). |
| External zone (Virtual External) | Client ≈ 0 plane: `x` fixed at `EXTERNAL_PLANE`, spread over (y, z) centered at `z = EXTERNAL_CENTER`. |
| Internal zone (remaining repos and Virtual Internal) | Horizontal (x, z) tilted `TILT`: x and z are scaled by `cos(TILT)`, and each member adds to its `y` the value `r × depth × sin(TILT) × 1.4`, with `depth = -(cos a + sin a)/√2`. |

Order of application: positions of repos and systems → fix the plane of the
client zone and of the external zone → rings of each zone.

The result is written into `pos_x/y/z` like any position: the ring is not a
separate piece of data nor an animation. The "no overlap" check of Phase 2
is satisfied by construction.

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
  `vault-notes.md`), so that the render paints it coral without
  recalculating.

The control point **is written into the export** (`allspark.md`, field
`curve` of each vector — see `vault-notes.md`) so that the render does not
have to recalculate it. It does not appear in the notes of
`allspark/graphs/`: there the vector is a wikilink.

## Color — only 3, by dominant axis of the final position

There is no color per category (front/internal/external) — there is color
by **axis with the highest value** in the final coordinates (x,y,z),
calculated after applying the migration and the fine variation. A Front
point that migrated a lot toward Z ends up painted in the Z color, not the
color of its original category — the color follows the real position, not
the label.

```
color = axis with the highest value among {x, y, z}
# tie: priority X > Y > Z (arbitrary but deterministic)
```

Concrete colors per axis:

| Axis | Color | Hex |
|---|---|---|
| X — Client | Blue | `#3B82F6` |
| Y — Internal (Acme) | Green | `#22C55E` |
| Z — External | Orange | `#F97316` |

The orange of Z is intentional: a Front that migrates toward Z (more direct
external connections) ends up orange, visually reinforcing that it moves
away from the client face toward the external background.

Vectors take the color of the connection's axis, with a single exception:
the **direct** vector client zone → external is coral `#F43F5E`.

Only 3 colors for repos and virtual points, one per axis — not one per
category or connection type. Each point is painted with a single color
according to its dominant axis, without blends or shades, even if that point
has real presence on all three axes at once (that is already reflected by
the position, not the color).

## Final axis transformation — X/Z swap only in the export (mandatory)

**This applies only when
generating `allspark/export/allspark.md`** (the compiled export consumed by
`generate-visual`) — **never** to the individual notes of
`allspark/graphs/`, which keep showing `pos_x`/`pos_y`/`pos_z` exactly as
they were calculated, without swap, because those notes are for a human to
browse in Obsidian.

**Everything above in this document (anchors, extremes, migration, color by
dominant axis) stays exactly the same, untouched, and that is how it is
written in the notes of `allspark/graphs/`.** `axis X` is still the Client
semantics, `axis Y` the Internal one, `axis Z` the External one — all the
internal calculation of this file uses those names unchanged. The swap is a
**last, mechanical step, applied only once, only when building the
export**, right before writing each point entry into `allspark.md`:

```
# Only inside allspark.md — the notes of allspark/graphs/ do NOT go through this
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
4. Each curve control point (`curve.cx`, `curve.cz`).

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
The notes of `allspark/graphs/` keep the original values without swap —
they are two representations of the same calculation, each one for its
consumer.

**The color is not affected by this swap.** The color of each point is
still determined by which semantic axis was dominant (Client/Internal/
External) **before** the swap — never by which field (`pos_x` or `pos_z`)
the value ended up written in within `allspark.md`. A Front point that
migrated toward External is still painted orange, regardless of that value
now living in `pos_x` of the export.

**Why the swap only in the export and not in the notes:** the notes of
`allspark/graphs/` are for direct human reading in Obsidian — there
`pos_x = Client` has to remain intuitive for whoever opens them.
`allspark.md` on the other hand is consumption data for the render, where
what matters is that a simple render, without any special camera rotation,
already reads client on the left and external on the right correctly.

## Path — sequence order, not derived from the position

The visual path of a process (the sequence of points it goes through) is
never calculated by comparing position values between points — it
exclusively follows the explicit wikilink graph of each note (see
`vault-notes.md`, section "Outbound/inbound vectors"). Fixed rule:

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
