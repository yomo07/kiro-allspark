# Vault notes — points and navigable graph

They are generated/updated at the **whole vault** level, not per workspace
or per individual repo — the vault is the single shared source (see the
deterministic ID per point/vector in SKILL.md). Each run of
`find-connections`, regardless of which workspace triggers it, does an
upsert against these same notes.

## Export file — allspark.md (for the renders, not for browsing in Obsidian)

Besides the individual notes per point (which are browsed in Obsidian),
a compiled file is generated with the full state of the cube — all
points, coordinates, colors and vectors in a single place — meant for
the renders (such as `generate-visual`) to read in one go, not to open as
a note.

**Structure inside the vault's `allspark/` folder:**

```
allspark/
├── graphs/                     ← root opened in Obsidian: one note per point
│   ├── .obsidian/graph.json    ← Graph View color groups (see below)
│   ├── <repo-id>.md
│   └── External/
│       └── <virtual-id>.md
├── export/                     ← sibling folder, never opened as a vault
│   ├── allspark.md             ← compiled export (consumed by the renders)
│   └── allspark.html           ← 3D visualization, only if confirmed in generate-visual
├── repos-master.yaml
├── roles.yaml
└── domains.yaml
```

`allspark.html` is written only by the `generate-visual` skill, always
behind its yes/no gate. It is derived from `allspark.md`, just as that one
is derived from the notes.

There is no subfolder of "unclassified" points: a domain not mapped
within the workspace is directly confirmed external (see
`axis-classification.md`).

Since `allspark/export/` is a sibling of `allspark/graphs/` (not contained
inside it), it never shows up when browsing the vault in Obsidian: Obsidian
only shows what is inside the root folder it is given as the vault.
It is still in the same git repo, accessible to the renders.

It is fully regenerated (not partially upserted) on every run of
`find-connections`, since it is a derivative — it never contains information
that is not also in the individual notes of `allspark/graphs/`. If at
some point it is lost or accidentally deleted, it can be rebuilt 100% from
those notes.

### Format of `allspark.md`

A single YAML block inside the `.md`. **All coordinates already come with
the X/Z swap applied** — axes, points, virtual points and arc control
points (see "Final axis transformation" in `position-formula.md`).
The render consumes it as is, without its own swap.

```yaml
meta:
  power_version: 1.0.0
  generated: 2026-09-25
  workspace: digital-channels
axes:                      # declaration for the render — already swapped
  pos_x: external          # orange #F97316
  pos_y: internal          # green  #22C55E
  pos_z: client            # blue   #3B82F6
points:
  - id: org/channels-front
    type: repo
    role: frontend
    pos_x: 18              # semantic value Z (External)
    pos_y: 50
    pos_z: 88              # semantic value X (Client)
    color: blue            # by dominant semantic axis, before the swap
    count_client: 4        # counts per semantic axis — NOT swapped
    count_internal: 14
    count_external: 1
  - id: org/payments-api
    type: repo
    role: backend
    pos_x: 25
    pos_y: 75
    pos_z: 25
    color: green
  - id: external-payments-provider
    type: virtual
    role: external
    axis: Z
    pos_x: 90
    pos_y: 50
    pos_z: 50
    color: orange
vectors:
  - id: org/channels-front->org/payments-api:http
    source: org/channels-front
    target: org/payments-api
    protocol: http
    axis: Y
    reverse_validation: validated
    curve:                 # Bezier control point, already swapped
      cx: 21.5
      cy: 97.2
      cz: 56.5
  - id: org/channels-front->maps-provider:http   # client zone directly to an external
    source: org/channels-front
    target: maps-provider
    protocol: http
    axis: Z
    direct: true           # drawn straight and in coral (#F43F5E)
    curve:                 # control = midpoint: the curve is a straight line
      cx: 37.1
      cy: 27.5
      cz: 38.0
  - id: org/payments-api->external-payments-provider:soap
    source: org/payments-api
    target: external-payments-provider
    protocol: soap
    axis: Z
    curve:
      cx: 57.5
      cy: 98.1
      cz: 37.5
```

Full export contract in
`skills/generate-visual/references/data-contract.md`.

## Real point notes (repo with steering docs)

Suggested path inside the vault: `allspark/graphs/<deterministic-id>.md`

```markdown
---
type: point
id: org/repo-name
role: backend
pos_x: 40
pos_y: 0
pos_z: 5
color: green
count_x: 12
count_y: 30
count_z: 2
---
# repo-name

## Outbound vectors
- [[org-quoter]] (Y, http, confirmed, validated)
- [[org-notifier-worker]] (Y, queue-kafka, confirmed, validated)
- [[external-payments-provider]] (Z, soap, confirmed)

## Inbound vectors
- [[system-clientbank]] (X, http, confirmed)

```

Each entry under "Outbound/Inbound vectors" is a real `[[wikilink]]` to
the note of the target/source point — that is all Obsidian needs to
draw the native graph in its Graph View, without vectorizing anything.

**`pos_x`/`pos_y`/`pos_z` in this note are the computed values as is**
(`pos_x` = Client, `pos_y` = Internal, `pos_z` = External, no swap) — these
notes are for a human to browse in Obsidian, they do not need to
carry any render adjustment. The `pos_x`/`pos_z` swap (see
"Final axis transformation" in `references/position-formula.md`) is
applied **only** when generating `allspark/export/allspark.md`, the compiled
export consumed by the render — never to the individual notes of
`allspark/graphs/`.

## Virtual point note (no repo of its own — pure client or external)

Suggested path: `allspark/graphs/External/<deterministic-id>.md`

```markdown
---
type: virtual-point
id: external-payments-provider
role: external
axis: Z
pos_x: 6           # close to the Client plane ≈ 0 (external zone)
pos_y: 18
pos_z: 86          # along the External axis
color: orange
---
# external-payments-provider

## Repos pointing to it
- [[org-repo-name]]
```

It has no traffic of its own to provide (it is not a repo, it has no MOC).
There are three variants according to its `axis` — Virtual Client, Virtual
Internal, Virtual External (see table in `position-formula.md`) — each with
its own anchor, migrating toward the pure end of its axis according to how
many repos reference it. The example above is a Virtual External: it lives
in the external zone, close to the Client plane ≈ 0 and spread along the
External axis. Points close to each other are spread in a ring (see
"Anti-overlap rings" in `position-formula.md`).

## Colors and shapes in the Obsidian Graph View

Obsidian's native Graph View supports **color groups**. The power
maintains those groups in `allspark/graphs/.obsidian/graph.json`, key
`colorGroups`, with these three entries (one per axis):

```json
"colorGroups": [
  { "query": "[color:blue]",   "color": { "a": 1, "rgb": 3900150 } },
  { "query": "[color:green]",  "color": { "a": 1, "rgb": 2278750 } },
  { "query": "[color:orange]", "color": { "a": 1, "rgb": 16347926 } }
]
```

Merge rules for `graph.json`:

- Upsert: only those three entries are added or replaced (identified by
  their exact `query`). Groups the user has created and the rest of the
  file's keys (forces, filters, etc.) are preserved.
- If the file does not exist, it is created with only `colorGroups`;
  Obsidian fills in the rest when opening the vault.
- If Obsidian is open on the vault, it may rewrite the file with its
  in-memory state: it is best to apply the change with the vault closed
  or reopen the graph view.

## Virtual point merged into a real point

When the merge described in `axis-classification.md` applies (a domain that
was a virtual point turns out to have its own repo), the virtual point's
note is NOT deleted — it is kept as a redirect:

```markdown
---
type: virtual-point
id: external-payments-provider
axis: Z
status: merged-into: org/real-repo-name
---
# external-payments-provider (merged)

This point was merged into the real point [[org-real-repo-name]]. The
vectors that used to point here now point directly to the real point.
```

And in the note of the newly created/updated real point a line is added
that leaves a trace of the origin:

```markdown
## Origin
- Merged from virtual point [[external-payments-provider]]
```

Each repo note that previously had a wikilink to the virtual point is
updated to point to the real point instead — it is the same upsert
operation already applied to those notes, not a separate step.

## Upsert rule

When regenerating, the whole note is never replaced if there is human
content added manually outside the generated sections (frontmatter,
"Outbound/Inbound vectors", "Repos pointing to it"). If the user
added their own notes in another
section of the note, that section is preserved — the upsert only touches
the sections this skill generates.
