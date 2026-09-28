# Kiro Allspark

A [Kiro](https://kiro.dev) power that **documents the connections between
the repos of a workspace** and draws them as a navigable universe: a graph
in Obsidian and an interactive 3D cube.

For each repo in the workspace, Kiro Allspark answers a single question:
**what does it connect to?** It detects its role (frontend, backend, MVC
monolith, worker) and all of its connections — HTTP, SOAP, gRPC,
Kafka/RabbitMQ queues, webhooks and S3 — to other repos, to client systems
and to third parties. It does not document how the code works internally:
only the connections.

## The cube

Each repo or system is a point on three axes:

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
third party).

## Skills

| Skill | What it does |
|---|---|
| `generate-steering` | Generates `product.md`, `tech.md`, `structure.md` and `.kiroignore` per repo. It is the basis for detecting the stack and the role. |
| `find-connections` | Defines roles, detects and validates the connections, writes the connections MOC and updates the graph. |
| `generate-visual` | Generates the 3D cube as a single HTML file. Always asks first. |
| `manage-allspark` | Syncs the vault shared between teams without overwriting other teams' work. |

## Flow

1. `generate-steering` on the workspace repos.
2. `find-connections`: the first time it asks for the path to the Obsidian
   vault; after that it scans and documents.
3. When it finishes, it offers to generate the 3D cube (`generate-visual`).
4. If the vault is shared between teams, `manage-allspark feed` and
   `sync`.

## Requirements

- **Kiro** with a workspace (ideally multi-root) of Git repos.
- **Python 3.10+** for the prescan. The power creates an isolated
  environment in `.kiro/allspark/` and installs its dependencies from PyPI
  (or the company's internal mirror). Without Python, the scan falls back to
  manual reading, just slower.
- **Obsidian** (optional) to browse the graph.
- **Internet connection when opening the 3D cube** (Three.js and fonts via
  CDN).

## What gets generated

```
<repo>/.kiro/steering/
├── product.md
├── tech.md
├── structure.md
└── moc.md                  ← the repo's connections

<workspace>/.kiro/moc.md    ← roles and workspace summary

allspark/                   ← in the vault
├── graphs/                 ← opened in Obsidian: one note per repo or system
└── export/
    ├── allspark.md         ← compiled state of the cube
    └── allspark.html       ← 3D cube (only if you confirm it)
```

It never reads real `.env` files, Kubernetes Secrets or credential keys.

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
