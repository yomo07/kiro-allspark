# MOC schema

## MOC levels

> **Loading.** In a multi-repo workspace no document of this power is
> `inclusion: always` except the short workspace index: each repo's `moc.md` and
> Level 2 (module) files are `auto` (with a unique `name` and a `description`),
> base files are `manual`. See
> `skills/generate-steering/references/loading-strategy.md`.

Two levels of documentation. **Only Level 1 is mandatory** and it is generated
in full for **what the chosen entry point reaches** (Phase 2; see
`entry-points.md`). **Level 2 is the module** and it is **consolidated**:
promoting a module documents **everything about it in one step and one
file** — the experience, its endpoints with their hops, the databases and
external providers it touches, and the shared functionalities it reuses.
There is no separate Level 3 or Level 4 to promote afterwards. Modules belong
to the entry points (a module is something the client can do) and are chosen
**per module**, always after the line-count gate with explicit user
confirmation (Phase 3). They are written from the experience of the client,
in natural language (see `experience-docs.md`).

| Level | What it documents | Where it lives | Mandatory | In the 3D view |
|---|---|---|---|---|
| 1 — Global connections | Repo role, all its connections at domain/service/topic level, and **the databases it uses** | `.kiro/steering/moc.md` | Yes, for what the entry point reaches | Global view: points, connection bundles, database nuclei and the per-color endpoint counts |
| 2 — Module (consolidated) | A module (mirrored from `structure.md`) **and everything under it**: its endpoints (each with its hops and data access), the journey they draw from the client to the externals and the database, the databases and providers it touches, and the shared functionalities it reuses (layout, sidebar, services other modules also use) | `.kiro/steering/product/features/.../<module>.md` | No | Modules view: one tree per module. Detail view: one strand per endpoint of the module |

Generation order is always macro to micro: repo global
(`product.md` + `moc.md`) → base files → modules. A module is never written
without its Level 1.

**How the levels read in the cube.** Each level answers a different
question over the same points: *who talks to whom* (Level 1: **Global**) and
*which path does a module draw and what does each of its endpoints do along
that path* (Level 2: **Modules**, and **Detail** for the endpoints of the
open module). The database is part of both: which repos use it (Level 1) and
which modules and endpoints reach it, with which entities and operations
(Level 2). There is no separate data level.

## Folder structure — `product/` mirrored from `structure.md`

```
.kiro/steering/
├── product.md                               ← repo global (generate-steering)
├── moc.md                                   ← Level 1, the repo's global connections
└── product/
    └── features/                            ← mirror of the structure.md hierarchy
        ├── layout.md                        ← base file (frontend / mvc-monolith)
        ├── sidebar.md                       ← base file
        ├── <folder-per-structure>/          ← same nesting as the code
        │   └── <feature>/
        │       └── <feature>.md             ← Level 2: the module, endpoints and data included
        └── ...
```

- The folder hierarchy under `features/` **replicates the one already
  described by the repo's `structure.md`** (e.g. if the code has
  `src/app/modules/payments/`, the documentation lives in
  `features/modules/payments/`). No new organization is invented. Only
  meaningless technical prefixes are omitted (`src/`, `app/`, `lib/`); each
  feature `.md` records its full `code_path`, so the mapping is never lost.
- **Base files** (only `frontend` and `mvc-monolith` repos): they document
  how the client perceives the application as a whole — the layout that
  wraps everything, the sidebar/menu used to navigate, header, etc. They are
  created with the first feature promoted in that repo. `backend` and
  `worker` have no visual base files: the hierarchy starts at the features.
- Folders are created only when something inside them is promoted: the full
  empty tree is never generated.

## Level 1 — `.kiro/steering/moc.md` (per repo)

```markdown
---
inclusion: auto
name: <repo>-moc
description: "Connections of <repo>: which repos, providers and databases it talks to. Use when asking what <repo> connects to or what breaks if it fails."
---
# MOC — Connections

## Repo role
- role: backend             # frontend | backend | mvc-monolith | worker
- evidence: Spring Boot, controllers/ and services/, no views

## Reached from
- entry_points: [org/front-web]   # the entry point(s) whose walk reached this repo (empty for an entry point itself)

## Detected connections

- domain: provider-x.com
  type: soap
  direction: outbound
  source: wsdl-local
  axis: Z
  status: confirmed
  detection_source: prescan       # prescan | manual
  endpoints: 3                    # candidates grouped into this connection

- domain: quoter.internal
  type: http
  direction: outbound
  target_repo: org/quoter
  source: service-name-match
  axis: Y
  status: confirmed
  reverse_validation: validated

- grpc_service: scoring.v1.ScoringService
  host: scoring.internal:9090
  type: grpc
  direction: outbound
  target_repo: org/scoring
  source: proto-local
  axis: Y
  status: confirmed
  reverse_validation: no-target-evidence

- topic: payments.confirmed
  broker: kafka.internal
  type: queue-kafka            # queue-rabbitmq | queue-kafka
  direction: outbound          # producer → consumer
  target_repo: org/notifier-worker
  source: config-non-secret
  axis: Y
  status: confirmed
  reverse_validation: validated

- domain: system.clientbank.com
  type: http
  direction: inbound
  source: override
  axis: X
  status: confirmed

- bucket: third-party-assets
  type: s3
  source: unresolved
  axis: Z
  status: confirmed-default

- webhook: payment-notifications
  type: webhook
  source: unresolved
  axis: Z
  status: confirmed-default

## Databases used
- id: postgres://payments-db/payments      # engine://host/name, never credentials
  engine: postgresql | mysql | sqlserver | oracle | mongodb | redis | ...
  identified_by: config (key, never the secret value) | orm | code

## Count by axis
- count_X:
- count_Y:
- count_Z:

## Count by protocol
- http:
- soap:
- grpc:
- queue:
- webhook:
- s3:

## Computed position
- x:
- y:
- z:

## Promoted to Level 2 (modules)
- module: payments
  file: product/features/modules/payments/payments.md
  connections: [quotes.internal, provider-x.com]
  endpoints: 4

```

`Databases used` lists the databases the repo uses, identified **only** by
engine, host and name — never by credentials. They come from the `database`
candidates of the prescan (see `prescan.md`) and, for those the script cannot
see (configured in code or split across keys), from reading the data layer
described in `structure.md`. Two repos that use the same database write the
same `id`, and that is what makes them share **a single nucleus** in the
cube.

`status` values: `confirmed`, `confirmed-default` (the chain was exhausted
without resolving → Z external, no intermediate state), and
`not-detected-last-run` (a connection that existed in the previous run and the
new run did not detect: it is kept for review, never deleted silently — see
"Idempotency" in `SKILL.md`).

`detection_source` says how the connection was found: `prescan`
(candidate from the JSON in `.kiro/allspark/prescan/`, classified by Kiro) or
`manual` (manual reading of the code: repo without prescan, stack in
`stacks_without_pattern`, or a connection the script did not see). Many
`manual` connections in a covered stack are a sign that a rule is missing.
`endpoints` is the number of candidates grouped into that domain connection.

`reverse_validation` only appears on connections with `target_repo` (both
sides are repos in the workspace): `validated` or `no-target-evidence` (see
`reverse-validation.md`). It is not a connection status — the axis does not
change.

The `Promoted to Level N` sections are only pointers — the actual content
lives in its own files, not inflating this MOC.

## Base files — `features/layout.md`, `features/sidebar.md`, ...

```markdown
---
inclusion: manual
name: <repo>-<base>          # e.g. front-web-layout
---
# Base: <layout | sidebar | header | ...>

## How the client perceives it
What the client sees and how they navigate through this piece (in product
language, not code).

## Where it lives in the code
- path: (per structure.md)
- components:

## Features it wraps / gives access to
- `<repo>-<feature-slug>` → path to the feature .md (if already promoted)

## Own connections (if any)
- (e.g. the sidebar queries permissions or a dynamic menu from a backend) —
  taken from Level 1
```

## Level 2 — `features/.../<feature>/<feature>.md` (the module, consolidated)

One file per promoted module, `inclusion: auto`: Kiro loads it when someone
asks how the client does that. `<feature>` is the name of the module folder
exactly as it appears in `structure.md`. **It is the only file generated by a
promotion**: endpoints, hops, data access, databases, external providers and
shared functionalities are sections of this file, not files of their own.

```markdown
---
inclusion: auto
name: <repo>-<module-slug>          # unique in the workspace, e.g. front-web-paying-a-bill
description: "<summary> Use when asking how <the client does it> in <repo>."   # starts with the summary, word for word
summary: One sentence, at most 200 characters, from the client's point of view.   # the same text the 3D view shows
---
# <What the client can do, in the client's own words>

## What the client does
1. (the step the client takes, in plain language)
2. (what they see or get)

## What happens behind
In plain language: which services and providers take part and what each one
does. No class or file names.

## Location
- repo: (an entry point: frontend or mvc-monolith)
- repo_role:
- code_path: (per structure.md)
- wrapping_base_files: [layout, sidebar]
- promoted_by:
- date:

## Shared functionalities
What this module reuses that other modules also use, so it is documented
once and linked, never copied:
- base files: `<repo>-layout`, `<repo>-sidebar`
- shared with other modules: (a service, guard, interceptor or endpoint that
  another module also calls, with a link to that module if it is promoted)
- shared across repos: (a module of another entry point that reaches the same
  backend functionality)

## Endpoints
One `###` subsection per endpoint of the module, in the order the client
reaches them. The heading says what the client does, in their words, followed
by the endpoint in code format (gRPC: `service/method`; queues:
`publish topic` / `consume topic`): that is how an endpoint is found inside
the file.

### Confirming the payment (`POST /payments/confirm`)
summary: One sentence, at most 200 characters, from the client's point of view.   # the same text the 3D view shows for this endpoint

**When it happens.** The action of the client that triggers it: the screen,
the button, the event.

**What it does.** In plain language, from the client's side and then behind:
what they see, what is checked, which services and providers take part and
what each one does (every connection to an external provider it touches
along the way).

- protocol: http | soap | grpc | queue | webhook
- source_repo: (where it is triggered)
- target_repo: (where it is implemented / consumed)
- reverse_validation:

**Hops** (in order; every id must exist in the export: repos, systems without
a repo, databases). This is what the 3D Detail view draws as one strand:
- source: org/front-web
  target: org/api-payments
  kind: call                  # call | data
  protocol: http
- source: org/api-payments
  target: payflow.io          # the group of the provider, not the host
  kind: call
  protocol: http
- source: org/api-payments
  target: postgres://payments-db/payments
  kind: data
  protocol: sql

**Data access** (only if the endpoint reads or writes a database):
- database: postgres://payments-db/payments   # engine://host/name, never credentials
- entities: payments (read, write), transactions (write)
- operations: what it reads and writes, in order, at code level (repository,
  ORM call or query), with `file:line` references

**Specific external connections** (only the ones this endpoint adds):
- domain/provider:
  axis:
  purpose:

### Checking the status of a payment (`GET /payments/{id}`)
(same structure)

## Journey
The path the module draws, as the union of the hops of its endpoints, from
the client to the externals and the database. Each hop lists how many
endpoints of the module go through it:
- hop: org/front-web -> org/api-payments       # protocol http, 3 endpoints
- hop: org/api-payments -> payflow.io          # protocol http, 1 endpoint
- hop: org/api-payments -> postgres://payments-db/payments   # data, 3 endpoints

## External connections of the module (aggregate)
- domain/provider:
  axis:
  via_endpoint:

## Databases touched
- database: postgres://payments-db/payments
  entities: payments (read, write), transactions (write)
  via_endpoint: [POST /payments/confirm, GET /payments/{id}]   # the `METHOD /route` of each endpoint
```

Module content **starts from the connections already validated in Level 1**
(they decide which endpoints belong to it) and then goes down to the code of
each endpoint. Because everything is written in the same pass, the `Journey`
is always complete: it is derived from the `Hops` of the endpoints in the
same file.

A module is **not a point in the cube**: the Modules view draws it as a tree
over the existing points, one color per module, with the thickness of each
hop proportional to the number of its endpoints that go through it, and the
Detail view draws each endpoint as a strand along its `Hops` (see
`generate-visual`). The `Data access` of an endpoint shows in the tooltip of
the hop that reaches the database. Credentials are never written: user,
password and tokens are masked (`***`) exactly as in the prescan.

**Where the endpoint text lives in the export.** Each endpoint of the module
becomes an entry of `endpoints` in `allspark.md` (format in
`export-format.md`) whose `summary` is the `summary:` line of its subsection,
whose `hops`, `entities` and `operations` are the ones written under it, and
whose `doc` is the module document itself
(`.kiro/steering/product/features/.../<module>.md`): all the endpoints of a
module point to the same file, and each is found inside it by its
`METHOD /route`.

## Per-workspace MOC — `.kiro/moc.md`

```markdown
---
inclusion: manual
name: workspace-moc
---
# MOC — Workspace

## Roles
| repo | role | evidence |
|---|---|---|

## Entry points
| entry point | role | documented | repos it reached | last documented |
|---|---|---|---|---|

## Not documented yet
- (repos of the workspace that have no MOC: no documented entry point reaches them)

## Referenced virtual points (external role, no repo in this workspace)
-

## Internal connections without evidence at the target
-

## Known promotions (Level 2)
- (pointers, to avoid promoting the same module twice)

## Last run of find-connections
- date:
- scanned repos:
```

Scoping note: `axis: Z` in a repo's MOC means "external to what this
workspace can see", not necessarily external to the company's whole
universe — a workspace with more context may resolve it differently. That is
why each entry carries `source`, so that a later run with more information can
reclassify with traceable evidence instead of by intuition.
