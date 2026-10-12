# Data contract — allspark.md → allspark.html

The `<script id="allspark-data" type="application/json">` block of the
template receives the YAML of `allspark/export/allspark.md` translated 1 to 1
to JSON. Nothing is renamed, recalculated or reordered: same keys, same
values. The coordinates **already come with the X/Z swap** of the export.

Most of this file is produced by `find-connections/assets/layout/layout.py`
(points, vectors, links): copy its `export` coordinates, do not compute them.

## Structure

```json
{
  "meta":      { "power_version": "3.3.1", "generated": "2026-09-30", "workspace": "my-workspace" },
  "axes":      { "pos_x": "external", "pos_y": "internal", "pos_z": "client" },
  "points":    [ ... ],
  "vectors":   [ ... ],
  "links":     [ ... ],
  "modules":   [ ... ],
  "endpoints": [ ... ]
}
```

| Key | Required | Use in the template |
|---|---|---|
| `meta` | No | Header text (workspace, date). |
| `axes` | Yes | Color and name of each drawn axis. It must be `pos_x: external`, `pos_z: client` (with swap). |
| `points` | Yes (at least 1) | Repos (solid spheres), systems without a repo (wireframe spheres, one per provider) and databases (nuclei with electrons). |
| `vectors` | No | Level 1 connections: the bundles of the Global view (with the number of endpoints of each color) and the large vector with the total are computed from them, and each connection is drawn when its point is selected. |
| `links` | No | Repo → database usage (gold lines and the repos ↔ databases bundle). |
| `modules` | No | Level 2: one tree per module. Without them the Modules and Detail views are disabled. |
| `endpoints` | No | The endpoints of each module, with the hops of each one; the modules' trees and the strands of the Detail view are built from them. |

An endpoint that several modules use is written once **under each module**, with
the same `method` and `route`; the view recognizes it as **shared** and marks it
in the modules panel. A module (Level 2) and its endpoints are **not points**: they have no
coordinates and are drawn over the existing points.

## `points[]`

| Field | Required | Values | Notes |
|---|---|---|---|
| `id` | Yes | string | Deterministic ID: `org/repo` for repos, the provider group for systems without a repo (`payflow.io`), `engine://host/name` for databases. |
| `type` | Recommended | `repo` \| `virtual` \| `database` | If missing: `role: external` → `virtual`, otherwise → `repo`. |
| `role` | Repos and virtual points | `frontend` \| `backend` \| `mvc-monolith` \| `worker` \| `external` | Order of appearance in the animation and zone of the point. |
| `axis` | Virtual points | `X` \| `Y` \| `Z` | Client, Internal (Acme), External. |
| `hosts` | No (virtual) | list of strings | Hosts grouped into the provider (tooltip). |
| `pos_x`, `pos_y`, `pos_z` | Yes | number `0..100` | With the swap applied. |
| `color` | Yes | `blue` \| `teal` \| `green` \| `orange` \| `gold` | Repos by type (frontend blue, MVC monolith teal, backend/worker green); systems without a repo by axis; `gold` = database. |
| `count_client`, `count_internal`, `count_external` | No (repos) | integers | Sphere size and tooltip. Named by semantic axis on purpose: they are counts, not coordinates, and do not go through the swap. |
| `engine`, `name`, `repos` | Databases | strings / list of ids | Tooltip and nucleus size (by number of repos). Never credentials. |
| `electrons` | Databases | integer `1..5` | Relative use among the databases of the workspace. |
| `orbit` | Databases | number, cube units | Largest electron orbit allowed (0.42 × the distance to the nearest database). The render shrinks the nucleus and its orbits to fit, so atoms never cross. If missing, the natural size is used. |
| `documented` | No (repos) | `false` | Only written for a repo of the workspace that has no MOC yet: drawn small, hollow and dotted, without connections. Missing means documented. |
| `entry_point` | No (repos) | `true` | A documented frontend or monolith, where the client interacts: drawn with a ring. |

## `vectors[]`

| Field | Required | Notes |
|---|---|---|
| `id`, `source`, `target` | Yes | `source`/`target` must exist in `points`. |
| `protocol` | Yes | `http`, `soap`, `grpc`, `queue-kafka`, `queue-rabbitmq`, `webhook`, `s3`. |
| `axis` | Yes | `X` \| `Y` \| `Z` — color of the curve. |
| `endpoints` | Recommended | Number of endpoints the connection stands for (merged connections add up). It is the weight of the bundles; if missing it counts as 1. |
| `direct` | No | `true` on the client zone → external connection that does not go through Acme: drawn straight and in coral `#F43F5E`. If missing, the template deduces it (origin `frontend` or client system, target external system). |
| `reverse_validation` | No | `no-target-evidence` is drawn faint and with a slow pulse. |
| `curve.cx/cy/cz` | No | Bezier control point already swapped. If missing, the template computes the shape from the target: concave toward an internal point, arc toward an external one, straight if it is direct, convex toward the client (`ALTURA_BASE=12`, `FACTOR_ALTURA=0.15` in `position-formula.md`). |

## `links[]`

| Field | Values | Meaning |
|---|---|---|
| `source` | id of a repo | |
| `target` | id of a database | |
| `type` | `data` | The repo uses that database (gold line down to the nucleus). |

A link is not a vector: it is not a network call between systems.

## `modules[]` — Level 2, one tree each

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | `org/repo#path/of/the/feature`. |
| `repo` | Yes | Repo that owns the feature; must exist in `points`. |
| `name` | No | Shown in the search and the tooltips (defaults to the last path segment). |
| `summary` | Recommended | One sentence, at most 200 characters, from the client's point of view. It is **the `summary` of the module file**, word for word, and the 3D view shows it in the side panel and in the tooltips. |
| `doc` | Recommended | Path of the module document (`.kiro/steering/product/features/.../<feature>.md`, inside its repo), shown as "Read more: …" under the summary. |

A module belongs to an entry point: `repo` is a documented `frontend` or `mvc-monolith`.

The tree of a module is **not stored**: the template builds it as the
union of the hops of its endpoints, with each hop as thick as the number of
endpoints that go through it.

## `endpoints[]` — the endpoints of a module, one strand each

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | `<module id>::<METHOD> <route>`. |
| `module` | Yes | Must exist in `modules`. |
| `method`, `route` | Yes | Shown in the search, the breadcrumb and the tooltip. |
| `summary` | Recommended | One sentence from the client's point of view: **the `summary` of its `###` subsection** inside the module file, word for word. Shown in the side panel when the strand is isolated. |
| `doc` | Recommended | Path of the **module document** that contains the endpoint (all the endpoints of a module share it), shown as "Read more: …". |
| `hops` | Yes | Ordered list of `{ source, target, kind, protocol }`. `source` and `target` must exist in `points`; use the provider group for external systems. `kind` is `call` (a connection between systems) or `data` (a repo reaching a database). |
| `entities` | No | Tables/entities touched; only with a `data` hop. |
| `operations` | No | `read` \| `write`; only with a `data` hop. |

The tooltip of the `data` hop shows `entities` and `operations`.

## Escaping

Before inserting, replace each `<` of the JSON with `\u003c`. No other escape
is needed: the block is `application/json`, the browser does not run it.
