# Resolution chain

Applied in order. It stops at the first step that resolves the
source/owner/emitter of a connection. Never jump to the default just because
an early step found nothing — the chain must be exhausted.

1. **Literal URL/name in code** — the domain, bucket or webhook endpoint
   is hardcoded directly in the source code. With prescan, these are the
   `chain_step: 1` candidates with `high` confidence in the JSON (the
   `chain_step: 2` and `3` ones feed steps 2 and 3 below). See
   `framework-patterns.md` for the concrete outbound call
   detection patterns per stack (Spring, Express/NestJS, Django, Rails).
   Do not assume "there are no calls" without having reviewed the patterns
   specific to the repo's framework — many live in annotations/beans
   (e.g. `@FeignClient`) that a generic string scan does not find.

2. **Versioned contracts** — local WSDLs, committed OpenAPI/Swagger specs,
   gRPC `.proto` files, AsyncAPI definitions or topic schemas. They are
   usually not in `.gitignore` because they are contract, not secret.

3. **Versioned non-secret config** — `.env.example`, `docker-compose.yml`,
   k8s manifests, CI/CD pipelines, `application.yml` (includes
   `grpc.client.*.address`, RabbitMQ/Kafka brokers and topic/queue
   names). They often have the real hostname or the internal service name
   even though the real `.env` is gitignored.

4. **Cross by service name between repos of the same workspace** — if the
   identifier (environment variable, bucket name, gRPC service from the
   `.proto`, topic/queue with producer and consumer in the workspace, etc.)
   matches another workspace repo, it resolves as **Y** directly, without
   going through the axis rules of the next step. Every connection resolved
   here then goes through reverse validation (`reverse-validation.md`).

5. **Front without intermediate backend check** (only applies to repos with
   role `frontend` — not to `mvc-monolith` — and to HTTP/SOAP, gRPC-web and
   webhooks, not to S3 or queues) — if the connection is detected in a
   frontend repo and does not go through an Acme-owned backend before going
   out, it is classified **Z**, external, confirmed directly — just like any
   other external, with no mark or intermediate state. The workspace is the
   boundary that decides: if the backend is not mapped here, it is
   external, without ambiguity. It does not block the flow or require human
   confirmation. If the real backend repo shows up later (it is added to the
   workspace or another team maps it), the virtual-point→real-point merge
   rule applies (`axis-classification.md`), not a manual reclassification
   of this mark.

6. **Variable name heuristic** — patterns like `CLIENT_`, `EXTERNAL_`,
   `PROVEEDOR_` (Spanish for `PROVIDER_`), `INTERNAL_` in the identifier,
   when there is nothing better.

7. **Manual overrides** — `domains.yaml` in the vault (not in the repos, so
   that it is never lost to `.gitignore`). Highest priority over the
   automatic heuristics when an entry exists for that domain/bucket.

## Default when the chain is exhausted without resolving

**A single default for all connection types — no intermediate states.** If
the 7-step chain is exhausted without resolving anything, the connection is
**Z, external, confirmed directly**, regardless of whether it is
HTTP/SOAP, gRPC, queue, webhook or S3. The virtual point created has role
`external`. There is no `pending-confirmation` or any other
"review later" state — the workspace is the boundary that decides
everything (see "Front without intermediate backend" and "New repo outside
the master registry" in `axis-classification.md`). The `source: unresolved`
field in the MOC already records that the classification came by
elimination, not by direct evidence — that is enough traceability; there is
no need for a separate state that blocks or marks the connection as
pending.

## Client/external tie-break rule

If the classification is ambiguous between X and Z (outside the special
case of step 5), **X (client) always wins**. There is no domain that is both
a client and an external provider — if in practice it seems to be, the
company treats it as a client.
