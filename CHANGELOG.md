# Changelog — kiro-allspark

## [3.3.1] — 2026-10-05

### Changed
- **Level 2 is the module, and it is consolidated.** Promoting a module now
  documents everything about it in **one step, with one gate and one file**:
  the experience of the client, each endpoint with its hops and data access,
  the databases and external providers it touches, and the shared
  functionalities it reuses. There is no separate Level 3 (endpoints) or Level 4
  (data access) to promote afterwards: they are sections of the module file.
  The endpoints are `###` subsections of `product/features/.../<module>.md`
  (heading = what the client does + `` `METHOD /route` ``), each with its own
  `summary`, `Hops` and `Data access`. The `functionalities/` folder and the
  per-endpoint files are no longer generated.
- **Line-count gate** counts the whole module (endpoints and data access
  included), per repo. Its method now lives in `find-connections` itself.
- **Export and 3D data**: every endpoint of a module points (`doc`) to the
  module document (its path inside the repo, `.kiro/steering/product/features/...`);
  `summary`, `hops`, `entities` and `operations` are unchanged, so
  `allspark.html` needs no new data. The format of `allspark.md` now has its
  own reference, `skills/find-connections/references/export-format.md`, and the
  `allspark/` folder sits at the workspace root.
- **Journeys are modules.** The view, the legend, the breadcrumb and the tooltips
  say *Modules*; the three views are **Global → Modules → Detail** (the endpoints
  of the open module). The internal mode name stays `journeys`.
- Verification 8 now reads "no module without a document, no document without
  a module".

### Removed
- **`manage-allspark`** and the shared vault. The power no longer asks for a
  vault path, no longer syncs work between teams, and no longer keeps a master
  registry of repos (`repos-master.yaml`) or reports new repos pending
  notification.
- **Knowledge base generation.** The Obsidian vault (`allspark-knowledgesbases/`
  with its `graphs/` notes, the `docs/` mirror, `index.md` and the Graph View
  colors) and its guide to connect a model are no longer generated. The
  documentation lives where Kiro loads it: the steering docs and MOCs of each
  repo (`inclusion: auto`). `find-connections` now ends at the export
  `allspark/export/allspark.md`, which `generate-visual` turns into the 3D cube.

### Added
- **Global view summary**: next to the endpoint count of each color, one **large
  vector** that stands for all the vectors, with the total number of endpoints on
  top (computed from the Level 1 `vectors`, nothing new to write in the export).
  It appears with the other bundles when the build ends and only in Global.
- **Description of the universe and of each point (top left)**: the Global text is a
  plain-language description of the whole application universe, computed from the
  export; hovering or clicking a point changes it to what that point does (role,
  who it calls and who calls it, databases, modules through it).
- **New layout of the 3D view, four areas**: top left, a dynamic text (the Global
  description by default, and the name, summary and document of the selected
  module or endpoint); bottom left, the fixed legend (unchanged); top right, the
  modules panel with an endpoint dropdown and dynamic counts of points and
  endpoints; bottom right, the controls only. The search box, the separate side
  panel and the breadcrumb line are gone (their text lives in the new areas).
- **Modules panel, adjusted**: no entry-point filter (the modules are all listed at
  once); with none, it says "No modules documented yet." and the Modules view stays
  reachable; **shared endpoints** (same method and route under several modules) are
  marked; and the **route step by step also plays for an endpoint** in the Detail view
  (numbered hops, flash in order, camera and caption per step, "Replay route").
- **List of modules and route animation, in the Modules view only**: a panel lists
  the modules (filtered by entry point); choosing one plays its route step by step
  (hops traced one by one in order, camera on each step, points lighting up, a
  caption per step, "Replay route" button). Nothing of this appears in Global or
  Detail.
- **Numbered route in the Modules view**: each hop of a module carries its step
  number (the order in which the module's endpoints reach it), shown on the module
  you highlight, and the flash that marks the direction of the vectors walks the
  hops in that order (1, 2, 3...). The tooltip of a hop shows "Step in the route".
- **Generic demo**: `skills/generate-visual/assets/demo/` has `demo-data.json`
  (a made-up company, "acme": two entry points, a gateway, payments and accounts
  APIs, a worker, five providers, three databases, two modules with five
  endpoints) and `build_demo.py`, which fills the template with it. No real
  workspace data lives in the repo.
- `Shared functionalities` section in the module template: base files and
  services other modules also use, linked instead of copied.

### Migration
Repos documented with 3.2.0 keep working: on the next promotion of a module the
content of its existing `functionalities/*.md` files is merged into the module
file (upsert). The old files are never deleted by the power; it lists them so the
team removes them when it decides to. Likewise, an `allspark-knowledgesbases/`
folder left by an earlier version is not touched or deleted: it is simply no
longer updated.

## [3.2.0] — 2026-09-30

### Changed
- **Steering loading for multi-repo workspaces.** Per-repo docs are no longer
  `inclusion: always`, which loaded every repo's steering into every
  interaction. `product.md`, `tech.md`, `structure.md`, `moc.md` and Level 2
  files are `inclusion: auto`, loaded only when the request is about them;
  Level 3, base files and the workspace MOC are `manual`.
- **Unique names** for every document (`<repo>-tech`, `<repo>-moc`,
  `<repo>-<feature>`), since every repo has a `tech.md`: they are what `auto`
  and `#name` rely on. Descriptions name the repo, its role and its stack; a
  Level 2 description starts with its `summary`.

### Added
- **`allspark-index.md`**: the only `always` document, one line per repo (role,
  stack, entry point, names of its steering). Written by `generate-steering`,
  completed by `find-connections`.
- **Optimizing existing steering**: `generate-steering` offers to rewrite only
  the front matter of older docs that are `always`, without touching their
  content.
- `references/loading-strategy.md`, with the fallback to `manual` when the
  Kiro version in use does not support `auto`.

## [3.1.0] — 2026-09-30

The power now starts from where the client interacts, and the cube stays
readable with dozens of repos, databases and names.

### Added
- **Experience first, one entry point at a time.** The purpose is to document
  how the client consumes the service, in natural language for Kiro and for
  people. The unit of work is an **entry point** (a `frontend` or an
  `mvc-monolith`): Kiro lists them, asks which to document, classifies and
  documents only what it reaches, and leaves the rest as *not documented
  yet*. Mapping the whole workspace is still possible but **recommended
  against**, with a **soft gate** that shows the cost and the alternative
  first and never blocks. New `references/entry-points.md`.
- **`assets/reach/reach.py`**: from the prescan results it computes which repos
  each entry point reaches (route, topic, gRPC service, domain) and what
  documenting them would cost, with what is measured and what is an
  assumption labeled. It reads no source code and spends no tokens.
  Verified with real prescan output.
- **`references/experience-docs.md`**: writing guide for Levels 2 and 3 from
  the experience of the client (what they see and do, then what happens
  behind), in plain language. Level 2 and 3 templates now carry a one-sentence
  `summary`, and live in the entry points.
- **Concordance between the knowledge base and the 3D view**: the `summary`
  and `doc` of each feature and endpoint are exported and shown in a side
  panel; entry points documented are drawn with a **ring**; repos **not
  documented yet** are small, hollow and dotted; the header counts the
  coverage; the Journeys view can be filtered **by entry point**. New
  verifications: no journey without a document, no document without a journey.
- Prescan: `lines_scanned` in the summary (1.1.0).

### Changed
- **Database atoms**: databases are a zone of their own next to the origin,
  rising like a column and filled in 3D like every zone (more used = lower).
  Their orbits are limited by the script (`orbit`) so atoms never cross, and
  they are dimmer. The 3.0.0 ring put coordinates outside the cube from 12
  databases on; now 1 to 40 stay inside their box.
- **Names never overlap**: labels are ordered by priority in screen space
  (bundle labels slide along their curve, colliding names hide until
  hovered); 79 overlapping pairs became 0 in the test workspace. A new
  "All names" button shows them all.
- **Animation with a moving camera**: each process has its own angle, slow
  orbit and framing; the data stage looks at the atoms from outside the origin
  corner; a final stage shows the repos not documented yet. Individual lines
  glow less when there are many.
- The workspace MOC lists the entry points and the repos not documented yet;
  Level 1 is no longer generated for the whole workspace by default.
- Layout script 1.2.0: `documented` and `entry_point` flags.

## [3.0.0] — 2026-09-29

The three levels of the documentation and of the 3D cube now mean the same
thing, and the cube stays readable with workspaces of dozens of repos.

### Changed
- **Three levels instead of four.** Level 1 (connections) now also records
  **the databases each repo uses**. Level 2 (feature) is a **journey**: the
  path its endpoints draw from the client to the externals and the database.
  Level 3 (functionality) is **one endpoint** with its `Hops` and its `Data
  access`. **Level 4 is removed**: the database lives in all three levels
  (which repos use it, which journeys reach it, which entities and
  operations each endpoint runs on it). The `data/` folder disappears.
- **Features and functionalities are no longer points of the cube** (no more
  pyramids and tetrahedra, no positions, no relative sample). The 3D view
  draws them over the existing points. Their vault notes remain as
  documentation and carry no `pos_*`.
- **The 3D view has three levels of detail**, selectable with buttons,
  search, clicks and Esc, with a breadcrumb:
  - **Global**: repos, systems and database nuclei, with the connections
    grouped into **bundles per pair of zones** (thickness and label = number
    of endpoints). Selecting a point shows its own connections.
  - **Journeys**: one tree per promoted feature, one color each, with the
    thickness of each hop = endpoints that go through it.
  - **Detail**: one strand per endpoint of the opened feature, with method,
    route, entities and operations in the tooltip.
- Database nuclei: electrons now count the **repos** that use the database.
- Export contract: `vectors[].endpoints` (weight), `links` only of type
  `data` (repo → database), and two new keys, `modules` and `endpoints`
  (with `hops`). Points of type `feature`/`functionality` are gone.
- Prescan `database` candidates are recorded in Level 1 (`Databases used`).

### Added
- **`assets/layout/layout.py`**: the positions are computed by a
  deterministic script (Python standard library) instead of by hand. It
  groups systems without a repo **by provider**, merges connections with
  their weight, computes every position, places the database nuclei and
  returns coordinates ready for the notes and already swapped for the
  export. It reports a warning when a zone does not fit.
- **Volume fill** replaces the anti-overlap rings: each zone is a box filled
  evenly in 3D, with the largest separation the box allows. The rings grew
  linearly with the number of points and, with dozens of them, exceeded the
  cube (radius 151 for 56 external systems: 49 points pressed against the
  walls, some on the same position). No overlaps up to 450 points.
- **Grouping by provider** of systems without a repo: registrable domain for
  client and external systems, name without role suffix for internal ones.

## [2.0.0] — 2026-09-29

A single version: the complete power, in English and public.

### Added
- **Four-level MOC.** Level 1 (connections, mandatory) plus optional
  Levels 2 (features, mirrored from `structure.md`), 3 (functionalities,
  endpoint by endpoint) and 4 (data access), promoted per connection, repo
  or workspace in Phase 3, always after a blocking line-count gate.
- **Level 4 = data access.** For each functionality: which database it uses
  (engine, host and name — never credentials), which entities and which
  operations. Stored in `product/features/.../data/`.
- **Database nuclei in the cube.** Each database is a gold nucleus near the
  origin of the axes, reached by a gold line from every functionality that
  uses it, with 1–5 electrons orbiting according to how many functionalities
  use it (relative to the workspace). One nucleus per engine + host + name,
  shared by every repo.
- **Prescan database candidates**: identity only (`engine://host/name`)
  from URLs, JDBC and .NET connection strings in non-secret config. User,
  password and parameters are never copied, not even in the evidence
  snippet. They are kept for Level 4, never turned into Level 1
  connections.
- **Knowledge base `allspark-knowledgesbases/`**: vault root with the graph
  (`graphs/`, now with `Features/`, `Functionalities/` and `Databases/`) and
  a mirror of every repo's documentation (`docs/`), linked in both
  directions, plus `index.md`. Guide to connect a model in
  `knowledge-base.md`.
- **Features and functionalities in the cube**: violet pyramids and lilac
  tetrahedra on the path they represent.
- **3D view**: relative sample of features and functionalities (at most
  √n per repo and per feature) to avoid noise; a search box and click to show
  the **full path** of any feature or functionality — repos involved,
  externals and its database — dimming the rest; new animation stages
  (features → functionalities → reaching the data).
- `structure.md` template: feature hierarchy, UI base pieces and data layer.
- `manage-allspark`: line-count gate method, sync of Levels 2–4 and of the
  knowledge base mirrors.

### Changed
- The vault root moves to `allspark/allspark-knowledgesbases/`
  (`allspark/graphs/` → `allspark/allspark-knowledgesbases/graphs/`).
- Examples no longer use the word "channels".

## [1.1.0] — 2026-09-28

### Changed
- **Animation in process order**: instead of drawing each connection when
  its second point appears, the build tells the journey in stages — client
  front → lines toward the internals (each internal appears when its line
  arrives) → connections between internals (the camera stays on the
  internals) → lines toward the externals (each external appears when its
  arc arrives) → response to the client (e.g. a webhook notification) →
  red direct client → external connections → full view.
- **Repos colored by type**: frontend blue, **MVC monolith teal
  `#2EA3AA`** (a blend of blue and green), backend and worker green.
  Systems without a repo keep the color of their dominant axis. New
  `[color:teal]` group in `graph.json`.
- **Legend by repo type**: Frontend, MVC monolith, Backend / Worker and
  System without repo (color of its axis).
- **Worker next to the Y axis**: anchor `(2, 66, 30)`, green; its Client
  value stays between 1 and 7 (base 1–4 by hash + up to 3 from real traffic
  toward the client) and its ring spreads over (y, z) keeping that value.

## [1.0.0] — 2026-09-26

First public release.

### Includes
- **`generate-steering`**: basic per-repo steering docs (`product.md`,
  `tech.md`, `structure.md`) and a standard `.kiroignore`.
- **`find-connections`**: each repo's role (frontend, backend,
  MVC monolith, worker), detection of all its connections (HTTP, SOAP,
  gRPC, Kafka/RabbitMQ queues, webhooks, S3), validation from both
  ends, and a connections MOC per repo and per workspace. Updates the
  shared graph in Obsidian.
- **Deterministic prescan** in Python with tree-sitter: a script does the
  mechanical search for connections, and Kiro only classifies. Covers
  NestJS, Express, TS/JS frontends, Django, Flask, FastAPI, Spring, ASP.NET
  and Rails; other stacks go through manual reading.
- **XYZ cube**: client (X), internal service (Y) and third parties (Z), with
  position driven by real traffic, zones, anti-overlap rings and curves
  shaped by connection type.
- **`generate-visual`**: interactive 3D cube in a single HTML file
  (Three.js via CDN), with animated build-up and a guided camera. Always
  behind a confirmation.
- **`manage-allspark`**: non-destructive vault sync between teams, with
  conflicts reported for human decision.
