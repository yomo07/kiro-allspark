# Steering doc templates

All use standard Kiro frontmatter. Default is `inclusion: always` unless
stated otherwise.

## product.md

```markdown
---
inclusion: always
---
# Product

## Purpose
- What the repo does, in one or two lines

## Users
- Who uses it (end client, internal team, other systems)

## Main features
-

## Business context
- Where it fits in the company's product (optional)
```

## tech.md

```markdown
---
inclusion: always
---
# Tech Stack

## Language / runtime
-

## Main framework
-

## Key dependencies
-

## Build / test tools
-
```

## structure.md

```markdown
---
inclusion: always
---
# Repo structure

## Folder organization
-

## Layers / architectural patterns
-

## Naming conventions
-

## Main modules
- path/to/module — what it is, in one line

## Role signals
- Own UI: yes/no — exposes endpoints: yes/no — consumes queues or jobs: yes/no
  (find-connections decides the role from this: frontend, backend,
  mvc-monolith or worker)
```

## .kiroignore

Standard patterns. If the file already exists, only the missing lines are
added (line-by-line merge); it is never replaced.

```
# dependencies and build output
node_modules/
dist/
build/
target/
bin/
obj/
.venv/
__pycache__/
coverage/

# local secrets
.env
.env.local

# kiro-allspark: prescan environment and results (working artifacts)
.kiro/allspark/
```

## database.md (ON-DEMAND, not automatic)

Only generated if the session prompt explicitly asks for it.

```markdown
---
inclusion: manual
---
# Database

## Engine
-

## Main schema
-
```
