# Export file — allspark.md

`find-connections` compiles the full state of the cube — all points,
coordinates, colors, vectors, modules and endpoints — into a single file,
`allspark/export/allspark.md`, meant for the renders (such as
`generate-visual`) to read in one go. It is not a note to browse.

**Structure of the `allspark/` folder**, at the workspace root (the same
place as `.kiro/moc.md`):

```
<workspace>/allspark/
├── export/
│   ├── allspark.md             ← compiled export (consumed by the renders)
│   └── allspark.html           ← 3D visualization, only if confirmed in generate-visual
├── roles.yaml                  ← optional: pins the role of a repo (see repo-roles.md)
└── domains.yaml                ← optional: overrides the axis of a domain (see resolution-chain.md)
```

`allspark.html` is written only by the `generate-visual` skill, always
behind its yes/no gate. It is derived from `allspark.md`.

There is no "unclassified" category: a domain not mapped within the workspace
is directly confirmed external (see `axis-classification.md`).

`allspark.md` is regenerated on every run of `find-connections` from the
repos' MOCs (`.kiro/steering/moc.md` and the Level 2 module documents) and from
the `layout.json` computed by `assets/layout/layout.py`. The previous export is
loaded first and used as the base (see "Idempotency" in `SKILL.md`), so nothing
that existed disappears without a trace.

## Format of `allspark.md`

A single YAML block inside the `.md`. **All coordinates already come with
the X/Z swap applied** — axes, points, virtual points and arc control
points (see "Final axis transformation" in `position-formula.md`).
The render consumes it as is, without its own swap.

```yaml
meta:
  power_version: 3.3.1
  generated: 2026-09-29
  workspace: demo-workspace
axes:                      # declaration for the render — already swapped
  pos_x: external          # orange #F97316
  pos_y: internal          # green  #22C55E
  pos_z: client            # blue   #3B82F6
points:
  - id: org/front-web
    type: repo
    role: frontend
    pos_x: 18              # semantic value Z (External)
    pos_y: 50
    pos_z: 88              # semantic value X (Client)
    color: blue            # repos by type (frontend blue); virtual points by dominant axis
    count_client: 4        # counts per semantic axis — NOT swapped
    count_internal: 14
    count_external: 1
    entry_point: true      # a documented frontend or monolith: drawn with a ring
  - id: org/legacy-reports
    type: repo
    role: backend
    documented: false      # in the workspace but no MOC yet: drawn small, hollow and dotted
    pos_x: 44
    pos_y: 62
    pos_z: 58
    color: green
  - id: org/payments-api
    type: repo
    role: backend
    pos_x: 25
    pos_y: 75
    pos_z: 25
    color: green
  - id: payflow.io
    type: virtual
    role: external
    axis: Z
    pos_x: 90
    pos_y: 50
    pos_z: 50
    color: orange
  - id: postgres://payments-db/payments         # database nucleus (Level 1)
    type: database
    engine: postgresql
    name: payments
    repos: [org/payments-api, org/reconciliation-worker]
    electrons: 5           # 1..5, relative use among the databases of the workspace
    orbit: 6.2             # largest electron orbit allowed, in cube units: the script keeps atoms from crossing
    pos_x: 14              # near the origin
    pos_y: 9
    pos_z: 12
    color: gold
links:                     # repo -> database usage (not network calls)
  - source: org/payments-api
    target: postgres://payments-db/payments
    type: data
  - source: org/reconciliation-worker
    target: postgres://payments-db/payments
    type: data
vectors:                   # the curve is optional: the render computes the same shape when it is omitted
  - id: org/front-web->org/payments-api:http
    source: org/front-web
    target: org/payments-api
    protocol: http
    axis: Y
    endpoints: 5           # endpoints this connection stands for (weight of the bundle)
    reverse_validation: validated
  - id: org/front-web->maps-provider:http   # client zone directly to an external
    source: org/front-web
    target: maps-provider
    protocol: http
    axis: Z
    endpoints: 2
    direct: true           # drawn straight and in coral (#F43F5E)
  - id: org/payments-api->payflow.io:http
    source: org/payments-api
    target: payflow.io     # the group of the provider (see position-formula.md)
    protocol: http
    axis: Z
    endpoints: 3
modules:                   # Level 2 (only promoted modules): one tree per module
  - id: org/front-web#modules/payments
    repo: org/front-web    # an entry point
    name: payments
    summary: Customers pay a bill in three steps and get a receipt.   # the same text as the Level 2 file
    doc: .kiro/steering/product/features/modules/payments/payments.md   # path of the module document, inside its repo
endpoints:                 # the endpoints of each promoted module: one strand each
  - id: org/front-web#modules/payments::POST /payments/confirm
    module: org/front-web#modules/payments
    method: POST
    route: /payments/confirm
    summary: The customer confirms the payment and the card provider authorizes it.
    doc: .kiro/steering/product/features/modules/payments/payments.md   # the module document: every endpoint of the module points to it
    hops:
      - { source: org/front-web,   target: org/payments-api, kind: call, protocol: http }
      - { source: org/payments-api, target: payflow.io,       kind: call, protocol: http }
      - { source: org/payments-api, target: "postgres://payments-db/payments", kind: data, protocol: sql }
    entities: [payments, transactions]      # optional, only with a data hop
    operations: [read, write]
```

A module (Level 2) is a `modules[]` entry and each of its endpoints an
`endpoints[]` entry: neither is a point of the cube, so they carry no
coordinates. The tree of a module is not written anywhere: the render builds
it from the `hops` of its endpoints. The counts per color and the total shown
in the Global view are not written either: the render adds up the `endpoints`
of the `vectors`.

Full export contract in
`skills/generate-visual/references/data-contract.md`.

## Virtual point merged into a real point

When the merge described in `axis-classification.md` applies (a domain that
was a virtual point turns out to have its own repo), the export carries only
the real point: the virtual point is removed from `points`, and every vector
and hop that named it names the real point instead. The merge is reported at
the end of Phase 2 (virtual id → real id), and the repos' MOCs that named the
virtual id are updated to the real one.
