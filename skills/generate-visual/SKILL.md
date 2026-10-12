---
name: generate-visual
description: "Generates allspark/export/allspark.html, an interactive, animated 3D visualization of the cube (Three.js via CDN, nothing to install) from allspark/export/allspark.md. It reads the same universe at three levels: Global (repos, systems and database nuclei, with the connections grouped into bundles), Journeys (one tree per promoted feature, from the client to the externals and the database) and Detail (one strand per endpoint of a feature), with a search, click navigation and a guided build animation. It is never generated on its own — it always asks for explicit confirmation (yes/no) before writing. It does not scan code or recalculate positions: it only reads the already compiled export."
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

- Reads **only** `allspark/export/allspark.md`. It does not read the repos'
  MOCs, does not scan code and does not recalculate positions, colors or
  curves.
- `allspark.md` already comes with the **X/Z swap applied to all coordinates**
  (axes, points, virtual points and curve control points). This skill **does no swap at all** and neither does the template. If something
  appears on the wrong plane, the error is in the export (see
  `find-connections/references/position-formula.md`); it is never fixed
  here.
- If `allspark.md` does not exist or has no points → nothing is generated;
  it suggests running Phase 2 of `find-connections` first.

## Step 0 — Preconditions

1. `allspark/export/allspark.md` exists, is valid YAML and has `points`.
2. `axes.pos_x == external` and `axes.pos_z == client` in the export. If
   not, the export was left without the swap: **it stops**
   and suggests regenerating it with `find-connections` instead of drawing
   an inverted cube.

## Step 1 — CONFIRMATION GATE (mandatory, blocking)

Before writing any file, show on screen:

- Output path: `allspark/export/allspark.html`.
- If it already exists: date of the current HTML vs date of `allspark.md`
  (and whether it is outdated).
- What will be drawn: repos, systems without a repo (virtual, grouped by
  provider), databases, connections (and how many are `no-target-evidence`,
  which appear fainter), and, if any were promoted, how many modules
  (`modules`) and endpoints will be available in the Modules and Detail
  views.
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

- Every `source`/`target` in `vectors` and `links`, every `module.repo` and
  every hop of every endpoint exists in `points`. Those
  that do not are listed as a warning (the template omits them and reports it
  on screen) — no points are invented to fill them in.
- Point coordinates numeric in `0..100`. `vectors[].curve` is optional (the
  template computes the same shape when it is omitted); its `cy` may exceed
  100 on purpose for the internal → external arcs.
- Colors within the names of the contract.
- No database point or `data` link contains credentials (the id is
  `engine://host/name`).

## Step 3 — Write the HTML

1. Copy `assets/allspark-template.html` to `allspark/export/allspark.html`
   (next to `allspark.md`).
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

The same universe is read at **three levels of detail**, selected with the
Global / Modules / Detail buttons (bottom right), by clicking on the scene, or
with Esc to go up one level. **Four fixed areas, each with one job:**

- **Top left — dynamic text.** In Global it is a **description of the whole
  application universe** in plain language (where the client enters, what it
  connects to, how many connections and endpoints it carries, how many modules are
  documented) followed by the counts and the generation date. **Hovering a point**
  changes it to what that point does — its role, who it calls and who calls it (with
  endpoint counts), its databases and the modules that go through it —, and clicking
  keeps it. For a module or an endpoint it shows its name, its summary and the path of
  its document. It returns to the universe description when nothing is under the
  pointer or selected. Everything is computed from the export; nothing new to write.
- **Bottom left — fixed legend** of repos, colors and symbols.
- **Top right — modules** (Modules and Detail views only): the list of modules,
  each with its entry point, number of **points** and number of **endpoints**;
  the selected module opens a dropdown with its endpoints (each with its number
  of points), and a line under the list gives the dynamic counts of what is
  selected. "Open detail ›" lives here.
- **Bottom right — controls**: the three views, "Replay route", the animation
  ("Skip animation" / "Rebuild"), "Initial view" and the layers (Connections,
  Names, All names). There is no search box.

The text it tells is
the one written in the documentation: the view and the documentation are two
readings of the same data (see `find-connections/references/experience-docs.md`).

- **Global (Level 1).** Repos (colored by type: frontend blue, MVC monolith
  teal, backend and worker green), systems without a repo (wireframe sphere
  with a dot at the centre, colored by axis, one per provider) and
  **database nuclei** in their own box next to the origin, rising like a
  column (gold, dim, with 1–5 electrons slowly orbiting: more electrons =
  used by more repos; the orbits shrink so atoms never cross).
  - **Coverage.** A documented **entry point** (frontend or monolith) carries
    a ring. A repo that is **not documented yet** is small, hollow and dotted,
    without connections, so the coverage is readable at a glance; the header
    counts both ("3 entry points documented, 17 repos not documented yet").
  - **Bundles.** Connections are grouped into bundles per pair of zones
    (client → internal, internal → external, response to the client, the coral
    direct client → external one, and repos ↔ databases), with the thickness and
    the label showing how many endpoints each stands for. Individual connections
    are not drawn (in small workspaces they appear faintly); **selecting a
    repo, system or database shows its own connections** and dims the rest.
    Connections between internal points have no bundle: they appear when their
    repo is selected.
  - **Names.** Names and bundle labels never sit on top of each other: they are
    placed by priority in screen space (hovered or selected first, then bundle
    labels, repos by weight, databases, systems); a bundle label slides along
    its curve to a free spot and a name that would collide is hidden until it is
    hovered, selected or there is room after zooming in. "All names" shows every
    name anyway and "Names" turns them off.
- **Modules (Level 2).** One tree per promoted module, in its own color,
  from the client to the externals and the database. Every hop is the union
  of the hops of the module's endpoints and its thickness is the number of
  endpoints that go through it. All the modules are listed at once in
  the panel on the top right (there is no entry-point filter); if there are none,
  the panel says **"No modules documented yet."** Choosing a module highlights its tree, shows "Open detail ›"
  and, in the top-left text, **its summary in natural language and the path of
  its document**; clicking a repo lights every module that goes through it. Points no module reaches fade out.
  **Only in this view** there is a **list of the modules** (name, entry point,
  endpoints and steps) and, when one is chosen — from the list, by clicking its
  hops —, an **animation of its route step by step**: the hops
  appear one by one in the order its endpoints reach them, the camera goes to each
  step, the points it reaches light up and a caption says what happens ("Step 2 of 4
  · api-gateway → payments-api · POST /payments/confirm +1"; on a data hop, which
  entities). When it ends, the numbers stay on the hops and the flash keeps walking
  them in order. "Replay route" repeats it; with `prefers-reduced-motion` the route
  is shown already drawn. **Shared endpoints** — the same method and route listed
  under more than one module — are marked in the list ("shared with …", and the
  count of shared endpoints of each module) and in the top-left text.
- **Detail (the endpoints of the open module).** The opened module shows **one strand per
  endpoint**, each in its own color, following the endpoint's hops. The
  dropdown of the module panel lists the endpoints; choosing one (there or by
  clicking its strand) isolates it and **plays its route step by step like a
  module's** (its hops traced in order with their numbers, the camera on each step
  and a caption; "Replay route" repeats it), and the top-left text shows its summary
  and the path of its document while the tooltip shows
  the method, the route and, on the hop that reaches a database, its entities
  and operations. Only one feature is open at a time.
- **Build sequence on open, in process order** (it can be skipped with a
  button and replayed with "Rebuild"). The camera does not only zoom: each
  process has its own **angle, slow orbit and framing**, taken from the size
  of its points:
  1. the three axes and the cube frame are drawn;
  2. **the client front**, seen from the client side and swinging toward the
     front as the frontends appear;
  3. **toward the internals**, then **between the internals**, orbiting the
     internal block (its depth only shows when the point of view moves);
  4. **toward the externals**, seen from the external side;
  5. **response to the client**, then the **direct** client → external lines,
     from a higher angle;
  6. **reaching the data**, from outside the origin corner where the atoms
     are, so they stay in front and the whole cloud behind them, circling
     slowly; each nucleus appears when its first line arrives;
  7. **not documented yet**: the hollow points appear all at once, if any;
  8. the camera returns to the standard view and the individual lines give way
     to the bundles.
  If the user drags the camera, it stops following the tour.
- **Curves.** Neon curves (valley toward internal points, an arc that falls
  onto external points from above, a straight coral line when the client
  calls an external directly, an arc toward the client) with an arrow at the
  target and a light pulse showing the direction. `no-target-evidence`
  connections appear faint; with many connections the individual lines glow
  less so the centre does not white out.
- **Size**: the more repos and systems there are, the smaller all points are
  drawn (100% up to 14, minimum 50% from 56), so that the cube does not get
  cluttered.
- **View angle**: camera at ~15° elevation, the Internal axis vertical,
  Client opening down to the left and External to the right. Once the build
  finishes, a gentle sway oscillates around the center without inverting
  that reading. Focusing on a selection keeps the angle the user left.
- **Interaction**: drag rotates, wheel zooms; hovering shows id, type and
  counts of a point, or the endpoints and hop of a bundle, module or
  strand; buttons to toggle connections and names on/off.
- Respects `prefers-reduced-motion` (shows the cube already built, without
  motion), works on mobile and adjusts the framing to the screen size.

## Demo without a workspace

`assets/demo/build_demo.py` fills this same template with `assets/demo/demo-data.json`
(a made-up company) and writes `allspark-demo.html`. Use it to see the cube, the
Modules view with its numbered routes and the Detail view without mapping anything.
The demo data follows `references/data-contract.md` and contains no real workspace.

## When it is offered

This skill is invoked manually, and it is also **offered** (with the same
yes/no gate, never runs on its own) when these finish:

- Phase 2 of `find-connections` (`allspark.md` was regenerated),
- Phase 3 of `find-connections` (modules were promoted).

Step 1 of this skill already reports whether `allspark.html` does not exist or
is older than `allspark.md`.

## Known limitations

- **Requires internet when opened** (Three.js r128 from cdnjs/jsdelivr and
  fonts from Google Fonts). Without a connection, the page shows a clear
  notice instead of staying blank. Corporate networks that block those
  CDNs will see the notice.
- `allspark.html` is a derivative of `allspark.md`: it is never edited by
  hand. To change it, it is regenerated (going through the gate).

## Expected output

Gate result (yes/no). If it was "yes": path written, whether it was a
creation or a replacement, counts drawn by type, warnings (references to
nonexistent points, `no-target-evidence` connections), and the instruction
to open it with a double click.
