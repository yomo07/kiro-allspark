# Changelog — kiro-allspark

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
