---
name: generate-visual
description: "Generates allspark/export/allspark.html, an interactive, animated 3D visualization of the cube (Three.js via CDN, nothing to install) from allspark/export/allspark.md. When opened, the cube 'builds itself': the axes are drawn, the camera focuses on each repo as it appears and its connections are drawn as neon curves. It is never generated on its own — it always asks for explicit confirmation (yes/no) before writing. It does not scan code or recalculate positions: it only reads the already compiled export."
---

# generate-visual

Converts the compiled cube export (`allspark/export/allspark.md`) into a
single self-contained HTML file that opens with a double click in any
browser, with no server or installation.

The template is already built and tested: `assets/allspark-template.html`.
This skill **does not write Three.js code**: it copies the template and
replaces a single data block. That way the result is identical on every run
and no tokens are spent generating the scene.

## Data source — only `allspark.md`

- Reads **only** `allspark/export/allspark.md`. It does not read the notes in
  `allspark/graphs/` or the repos' MOCs, does not scan code and does not
  recalculate positions, colors or curves.
- `allspark.md` already comes with the **X/Z swap applied to all coordinates**
  (axes, points, virtual points and curve control points). This skill **does no swap at all** and neither does the template. If something
  appears on the wrong plane, the error is in the export (see
  `find-connections/references/position-formula.md`); it is never fixed
  here.
- If `allspark.md` does not exist or has no points → nothing is generated;
  it suggests running Phase 2 of `find-connections` first.

## Step 0 — Preconditions

1. Vault path in `.kiro/config` (the same gate as Phase 0 of
   `find-connections`; if missing, it is requested the same way as there).
2. `allspark/export/allspark.md` exists, is valid YAML and has `points`.
3. `axes.pos_x == external` and `axes.pos_z == client` in the export. If
   not, the export was left without the swap: **it stops**
   and suggests regenerating it with `find-connections` instead of drawing
   an inverted cube.

## Step 1 — CONFIRMATION GATE (mandatory, blocking)

Before writing any file, show on screen:

- Output path: `allspark/export/allspark.html`.
- If it already exists: date of the current HTML vs date of `allspark.md`
  (and whether it is outdated).
- What will be drawn: repos, systems without a repo (virtual), connections,
  and how many connections are `no-target-evidence` (they appear fainter).
- Requirement when opening it: an internet connection to load Three.js and
  the fonts from CDN (see "Limitations").

And ask literally: **"Generate the HTML visualization? (yes / no)"**.

- Without an explicit "yes", nothing is written. Silence, "maybe" or a change
  of topic count as no.
- If the answer is "no", it closes without further ado; it is not offered
  again in the same session unless requested.
- The gate does not depend on cost (this skill is cheap: it does not scan
  code); it is a user decision so the HTML never appears by surprise.

## Step 2 — Convert `allspark.md` to JSON

The YAML block of `allspark.md` is translated **1 to 1** to JSON, without
transforming values. Exact contract (fields, types, required) in
`references/data-contract.md`. Validations before continuing:

- Every `source`/`target` in `vectors` exists in `points`. Those
  that do not are listed as a warning (the template omits them and reports it
  on screen) — no points are invented to fill them in.
- Point coordinates numeric in `0..100`. Only `curve.cy` of the
  internal → external arcs may exceed 100, on purpose (the arc falls onto the
  external point from above).
- Colors within the three names of the contract.

## Step 3 — Write the HTML

1. Copy `assets/allspark-template.html` to `allspark/export/allspark.html`
   (sibling folder of `graphs/`: it never shows up when browsing the vault in
   Obsidian).
2. Replace **only** the text `__ALLSPARK_JSON__` (it appears only once,
   inside `<script id="allspark-data" type="application/json">`) with the
   JSON from step 2, escaping each `<` as `\u003c` so that no value
   can close the `<script>` tag.
3. Do not modify anything else in the template: not styles, scripts or CDN
   URLs. If a visual change is needed, the power's template is changed
   (and versioned), not the generated HTML.
4. Add `meta.generated` (date) and `meta.workspace` if the export does not
   include them.

## Step 4 — Verification

- The file no longer contains `__ALLSPARK_JSON__`.
- The data block is parseable JSON.
- The counts (points by type and vectors) match
  `allspark.md`.

## What it looks like (what the template does)

- **Build sequence on open, with a guided camera** (it can be
  skipped with a button and replayed with "Rebuild"): the three axes and the
  cube frame are drawn → the camera moves in close to the first point and each
  repo or system appears in process order (frontend, client, monolith,
  backend, Acme without a repo, worker, external), **focused with zoom**; as
  soon as it appears, its connections to the points already present are drawn
  → with each point the camera pulls back a bit more (from 30% to 78% of the
  final distance) → the camera ends in the full view. Connections are neon curves (valley
  toward internal points, an arc that falls onto external points from above, a
  straight coral line when the client calls an external directly, an arc toward
  the client) with an arrow at the target and a light pulse showing the
  direction. The step per point gets shorter with many repos (between 1.1 s and
  0.35 s); if the user drags the camera, it stops following the tour.
- **Shapes and colors**: repos = glowing spheres, colored by dominant axis
  (blue client, green internal, orange external); systems without a repo =
  wireframe sphere. Connections colored by the connection's axis (the direct
  client → external one, in coral); `no-target-evidence` ones appear faint.
- **Size and names**: the more repos and systems there are, the smaller all
  points are drawn (100% up to 14, minimum 50% from 56), so that
  the cube does not get cluttered. The names of repos (front, backends,
  workers) and of systems without a repo are always visible.
- **View angle**: camera at ~15° elevation, the Internal axis
  vertical, Client opening down to the left and External to the
  right. Once the build finishes, a gentle sway oscillates around the
  center without inverting that reading.
- **Interaction**: drag rotates, wheel zooms; hovering over a point
  shows id, type, coordinates in Client/Internal/External and counts; click
  highlights the point with its connections and dims the rest (Esc clears);
  buttons to toggle connections and names on/off.
- Respects `prefers-reduced-motion` (shows the cube already built, without
  motion), works on mobile and adjusts the framing to the screen size.

## When it is offered

This skill is invoked manually, and it is also **offered** (with the same
yes/no gate, never runs on its own) when these finish:

- Phase 2 of `find-connections` (`allspark.md` was regenerated),
- `sync` of `manage-allspark` if it brought changes to the export.

`manage-allspark status` reports whether `allspark.html` does not exist or
is older than `allspark.md`.

## Known limitations

- **Requires internet when opened** (Three.js r128 from cdnjs/jsdelivr and
  fonts from Google Fonts). Without a connection, the page shows a clear
  notice instead of staying blank. Corporate networks that block those
  CDNs will see the notice.
- `allspark.html` is a derivative, just like `allspark.md`: it is never merged
  by hand between teams. On conflict, it is discarded and regenerated
  (going through the gate).

## Expected output

Gate result (yes/no). If it was "yes": path written, whether it was a
creation or a replacement, counts drawn by type, warnings (references to
nonexistent points, `no-target-evidence` connections), and the instruction
to open it with a double click.
