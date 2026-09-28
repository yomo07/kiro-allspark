# Changelog — kiro-allspark

## [1.0.0] — 2026-09-26

First public release.

### Includes
- **`generate-steering`**: basic per-repo steering docs (`tech.md`,
  `structure.md`) and a standard `.kiroignore`.
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
