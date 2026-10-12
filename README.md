# Kiro Allspark

A [Kiro](https://kiro.dev) power that **documents how the client experiences
your service** — in natural language, for Kiro and for people — and draws it
as a navigable universe: an interactive 3D cube.

**It starts from where the client interacts.** Developers already know how
the system works inside; what nobody has written down is what the client
sees and does, and what happens behind. So the power works **one entry point
at a time** — a frontend or a monolith — and follows what it reaches. It
computes what each entry point reaches and what documenting it would cost
before spending anything, and it **recommends against mapping the whole
workspace**. What is not documented yet stays in the cube as small hollow
points, so the coverage is visible.

For each repo it reaches, Kiro Allspark starts from one question:
**what does it connect to?** It detects its role (frontend, backend, MVC
monolith, worker) and all of its connections — HTTP, SOAP, gRPC,
Kafka/RabbitMQ queues, webhooks and S3 — to other repos, to client systems
and to third parties. From there, on demand, it goes deeper in a second level:

| Level | What it documents |
|---|---|
| **1 — Connections** (mandatory) | Role of each repo, all its connections and the databases it uses |
| **2 — Modules** (consolidated) | Each module of the entry point, mirrored from its `structure.md`, **and everything under it in one step and one file**: its endpoints with their hops and data access, the journey they draw from the client to the externals and the database, the databases and providers it touches, and the shared functionalities it reuses |

The 3D cube reads the same universe in three views: a **global** view (with
the number of endpoints of each color and the total), a **modules** view (one
tree per module) and a **detail** view (one strand per endpoint of the open
module).

## The cube

Each repo or system is a point on three axes (systems without a repo are
grouped by provider, so `api.` and `files.` of the same vendor are one
point):

| Axis | What it represents |
|---|---|
| **X — Client** | Whoever consumes the final service and pays the company for it |
| **Y — Internal** | The company's own repos and systems |
| **Z — External** | Third parties the company hires or integrates in order to operate |

In the documentation the company appears as **Acme**: it is the placeholder
name for "your company", the main provider whose application universe is
being mapped.

Each point's position comes from the real traffic it has toward each axis,
and each connection is a vector shaped according to its target (toward an
internal system, toward a third party, or from the client directly to a
third party), and in the global view they are grouped into bundles whose
thickness is the number of endpoints they stand for. **Databases are nuclei
near the origin** with 1–5 electrons orbiting according to how many repos
use them. Positions are computed by a deterministic script, and every zone of
the cube is filled evenly, so dozens of points never pile up.

## Skills

| Skill | What it does |
|---|---|
| `generate-steering` | Generates `product.md`, `tech.md`, `structure.md` and `.kiroignore` per repo. It is the basis for detecting the stack and the role. |
| `find-connections` | Lists the entry points (frontends and monoliths), computes what each one reaches and what documenting it costs, and — for the one you choose — defines roles, detects and validates the connections (Level 1). Promotes modules on demand (Level 2, consolidated: endpoints, data access and shared functionalities in the same pass, written from the experience of the client, always after a line-count confirmation), computes the positions with a script, and compiles the export the cube reads (`allspark/export/allspark.md`). |
| `generate-visual` | Generates the 3D cube as a single HTML file, with a guided build animation, three views (global, modules, detail) and click navigation. Always asks first. |

## Flow

1. `generate-steering` on the workspace repos.
2. `find-connections`: it lists the entry points with what each one reaches and
   what it costs, and asks which to document; then it scans and documents
   Level 1 for what that entry point reaches.
   Asking for the whole workspace works too, but it warns you first, with the
   numbers.
3. Optionally, promote the modules you care about to Level 2
   (`find-connections`, Phase 3). It shows how many lines of code it will
   read and waits for your confirmation.
4. When it finishes, it offers to generate the 3D cube (`generate-visual`).

## Requirements

- **Kiro** with a workspace (ideally multi-root) of Git repos.
- **Python 3.10+**. The prescan runs in an isolated environment that the
  power creates in `.kiro/allspark/` and fills from PyPI (or the company's
  internal mirror); without it, the scan falls back to manual reading, just
  slower. The layout and reach scripts only need the standard library; without Python
  the MOCs are written without positions and the 3D cube is not
  generated.
- **Internet connection when opening the 3D cube** (Three.js and fonts via
  CDN).

## Try the 3D cube without a workspace

```
python3 skills/generate-visual/assets/demo/build_demo.py
```

writes `allspark-demo.html` next to the script, with a made-up company. Open it
in a browser (it loads Three.js from a CDN).

## What gets generated

```
<repo>/.kiro/steering/
├── product.md
├── tech.md
├── structure.md
├── moc.md                  ← Level 1: the repo's connections
└── product/features/       ← Level 2, only what you promote
    └── <module>/
        └── <module>.md             (Level 2: the module, endpoints and data included)

<workspace>/.kiro/moc.md    ← roles and workspace summary

<workspace>/allspark/
└── export/
    ├── allspark.md         ← compiled state of the cube
    └── allspark.html       ← 3D cube (only if you confirm it)
```

It never reads real `.env` files, Kubernetes Secrets or credential keys.

**Light on context in multi-repo workspaces.** No steering document of a repo
is loaded in every interaction: `product`, `tech`, `structure`, the MOC and
the features load only when the request is about them (`inclusion: auto`,
with unique names such as `#api-payments-tech`), and endpoints are pulled on
demand. The only always-loaded document is a short workspace index, one line
per repo.
Databases are identified only by engine, host and name — never by their
credentials.

## Author

**Yoel Moreno**

- GitHub: [@yomo07](https://github.com/yomo07)
- Email: [yoel.moreno.ym@gmail.com](mailto:yoel.moreno.ym@gmail.com)
- Issues and suggestions: [github.com/yomo07/kiro-allspark/issues](https://github.com/yomo07/kiro-allspark/issues)

## License

MIT.

## Agradecimiento

A **[Intelix Synergy](https://intelix.biz)**, a su cultura y a su esencia, que influyeron para que construyera el profesional que soy hoy en día. Y a lo que aún queda de ella, que me llevó a una conclusión: no importa el dinero, ni el cargo que ejerzas; lo que importa es la persona en quien te conviertes en el proceso.

De nuevo, gracias.

— Yoel Moreno
