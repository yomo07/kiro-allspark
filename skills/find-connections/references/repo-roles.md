# Repo roles — defined BEFORE generating any connection

Mandatory first step of Phase 2 (step 2.A in `SKILL.md`). No repo enters the
connection scan without having its role defined and written in its
`moc.md`. The role is not discovered "on the fly" while scanning: it is
decided first, with `tech.md` and `structure.md` as the source, and then the
scan uses it to know what to look for and how to interpret what it finds.

## The five roles

| Role | What it is | Signals in `tech.md` / `structure.md` |
|---|---|---|
| `frontend` | Repo with client-facing UI that consumes APIs but does not expose them | Angular, React, Vue, Flutter, Ionic, etc.; folders `components/`, `pages/`, `views/`, `layouts/`; no controllers or server routes of its own |
| `backend` | Repo that exposes endpoints/services and has no UI of its own | Spring, NestJS, Express, Django REST, .NET Web API, etc.; folders `controllers/`, `routes/`, `services/`; no rendered views |
| `mvc-monolith` | All in one: the same repo renders the UI and handles the server logic (Model-View-Controller) | Rails, Laravel, Django with templates, ASP.NET MVC, Spring MVC + Thymeleaf/JSP, JSF, etc.; `views/`/`templates/` and `controllers/` coexist in the same repo |
| `worker` | Processes background tasks: consumes from a queue/topic or runs on a schedule. Does not serve client requests | `@RabbitListener`, `@KafkaListener`, `amqplib`/`kafkajs`/`pika` consumers, Celery, Sidekiq, `@Scheduled` jobs, cron; no public HTTP controllers (or only a healthcheck) |
| `external` | Not a repo in the workspace — it is a virtual point (domain, bucket, broker or service not mapped here) | Not applicable: assigned when resolving a connection that exhausts the chain (see `resolution-chain.md`) |

`external` is the only role not assigned to a scanned repo: it is the role
of virtual points. The other four are only assigned to real repos in the
workspace (with steering docs).

## Decision rules

1. **`mvc-monolith` is not "front + back"**. It is its own category: it is
   not split into two points nor classified as whichever role "weighs
   more". A repo that renders views and also has server controllers is
   `mvc-monolith`, period.
2. **A backend that also consumes queues is still `backend`** if it exposes
   endpoints that others consume. It is only `worker` if it does not serve
   requests (its input is queues/schedule, not inbound calls).
3. **A frontend with a BFF (backend-for-frontend) in the same repo**
   (e.g. Next.js with API routes that call other services) is treated as
   `mvc-monolith` — it renders UI and runs server logic in the same
   repo.
4. **Tie or real doubt** → it is reported in the Phase 2 output with the
   evidence that caused the doubt, and the role with the most signals is
   assigned. It can be pinned by hand in the vault's `allspark/roles.yaml`
   (override, highest priority), just like `domains.yaml` for domains.
5. The role is written in the repo's `moc.md` (`role:` in the header) and
   in the point's note in the vault (`role:` in the frontmatter). If a
   later run changes the role, traceable evidence is required, just as
   for reclassifying an axis.

## What changes by role

| Role | What is scanned as outbound | What is scanned as inbound |
|---|---|---|
| `frontend` | HTTP/SOAP/gRPC-web/webhook calls from the client | — (does not expose) |
| `backend` | HTTP, SOAP, gRPC, publishing to queues, S3 | Routes/controllers, gRPC services |
| `mvc-monolith` | HTTP, SOAP, gRPC, queues, S3 (from the server side) | Routes/controllers |
| `worker` | HTTP, SOAP, gRPC, publishing to queues, S3 | Consuming queues/topics, scheduled jobs |
| `external` | — | — |

The role also decides the position category in the cube (see
`position-formula.md`) and the first valid node of a path (a path always
starts at `frontend`, `mvc-monolith` or a Virtual Client).

## Frontend without an intermediate backend

The rule in `axis-classification.md` ("front without intermediate backend →
Z external confirmed") applies to repos with role `frontend`. It does not
apply to `mvc-monolith`: there the call goes out from its own server side,
which is already Acme.
