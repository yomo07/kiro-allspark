# Data contract — allspark.md → allspark.html

The template's `<script id="allspark-data" type="application/json">` block
receives the YAML from `allspark/export/allspark.md` translated 1 to 1 to
JSON. Nothing is renamed, recalculated or reordered: same keys, same
values. The coordinates **already come with the X/Z swap** from the export.

## Structure

```json
{
  "meta":    { "power_version": "1.0.0", "generated": "2026-09-26", "workspace": "my-workspace" },
  "axes":    { "pos_x": "external", "pos_y": "internal", "pos_z": "client" },
  "points":  [ ... ],
  "vectors": [ ... ]
}
```

| Key | Required | Use in the template |
|---|---|---|
| `meta` | No | Header text (workspace, date). |
| `axes` | Yes | Color and name of each drawn axis. Must be `pos_x: external`, `pos_z: client` (with swap). |
| `points` | Yes (at least 1) | Spheres: repos (solid) and systems without a repo (wireframe). |
| `vectors` | No | Neon curves with arrow and pulse. |

## `points[]`

| Field | Required | Values | Notes |
|---|---|---|---|
| `id` | Yes | string | Deterministic ID (`org/repo` for repos, system name for virtual points). |
| `type` | Recommended | `repo` \| `virtual` | If missing: `role: external` → `virtual`, otherwise → `repo`. |
| `role` | Yes | `frontend` \| `backend` \| `mvc-monolith` \| `worker` \| `external` | Order of appearance in the animation. |
| `axis` | Virtual points | `X` \| `Y` \| `Z` | |
| `pos_x`, `pos_y`, `pos_z` | Yes | number `0..100` | With swap applied. |
| `color` | Yes | `blue` \| `green` \| `orange` | By dominant axis. |
| `count_client`, `count_internal`, `count_external` | No (repos) | integers | Sphere size and tooltip. Named by semantic axis on purpose: they are counts, not coordinates, and do not go through the swap. |

## `vectors[]`

| Field | Required | Notes |
|---|---|---|
| `id`, `source`, `target` | Yes | `source`/`target` must exist in `points`. |
| `protocol` | Yes | `http`, `soap`, `grpc`, `queue-kafka`, `queue-rabbitmq`, `webhook`, `s3`. |
| `axis` | Yes | `X` \| `Y` \| `Z` — arc color. |
| `reverse_validation` | No | `no-target-evidence` is drawn faint and with a slow pulse. |
| `direct` | No | `true` on the client zone → external vector that does not go through Acme: drawn straight and in coral `#F43F5E`. If missing, the template infers it (source `frontend` or Virtual Client, target Virtual External). |
| `curve.cx/cy/cz` | Recommended | Bezier control point already with swap. If missing, the template calculates it with the same formula from `position-formula.md`: concave toward an internal point, arc toward an external point (`cy` may exceed 100), straight if it is direct client → external, convex toward the client (`BASE_HEIGHT=12`, `HEIGHT_FACTOR=0.15`). |

## Escaping

Before inserting, replace each `<` in the JSON with `\u003c`. No other
escaping is needed: the block is `application/json`, the browser does not
execute it.
