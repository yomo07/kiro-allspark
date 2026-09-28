# Reverse connection validation (double check between internal repos)

Step 2.C of Phase 2 (see `SKILL.md`). Applies to every connection whose
source and target are **both repos in the workspace** (roles `frontend`,
`backend`, `mvc-monolith` or `worker`). It does not apply to connections to
virtual points (`external`) — there is no code on the other side to review.

## The idea

If repo A has evidence of calling repo B, that is only half of the proof.
The connection is considered confirmed when **B also has evidence of
receiving that call**. Source and target are both validated.

## What counts as evidence on the target side

| Protocol | Evidence at the source (A) | Evidence sought at the target (B) |
|---|---|---|
| HTTP / REST | Call to a route (`GET /api/payments/...`) | Route/controller exposing that same route (method + path, after concatenating class prefixes) |
| SOAP | Call to a WSDL operation | Endpoint/service implementing that operation (or the WSDL published by B) |
| gRPC | Stub of `Service.Method` from the `.proto` | Implementation of the same `Service` (e.g. `extends ServiceImplBase`, `@GrpcService`, `server.addService`) with the same `.proto` |
| Queue (RabbitMQ/Kafka) | Publishing to exchange/queue/topic `T` | Consumer subscribed to `T` (`@RabbitListener`, `@KafkaListener`, `consumer.subscribe`, etc.) |
| Webhook | Registration/sending to a callback of B | Route of B that receives that callback |
| S3 | Write/read on bucket `b` | B declares being the owner of `b` (config, IaC) or reads/writes it with the inverse role |

For queues, the "direction" is producer → consumer: the producer is the
source of the vector and the consumer the target, even though technically
neither calls the other.

## Validation result

Each internal connection gets a `reverse_validation` field in the MOC:

- `validated` — there is evidence on both sides. It is the only case
  reported as a 100% confirmed internal connection.
- `no-target-evidence` — A calls B, but the corresponding route, service
  or consumer was not found in B.

`no-target-evidence` **is not a pending status and does not change the
axis**: the connection is still **Y** (the target is a repo in the
workspace) and still goes into the MOC and the vault. It is a quality mark
reported separately at the end of Phase 2, with the route/service sought,
because it almost always points to one of these real causes:

- The route in B is built dynamically and the patterns do not see it.
- A calls an old version of B's API (a route that no longer exists).
- The service name resolved to the wrong repo in step 4 of the
  resolution chain.
- A publishes to a topic that nobody consumes anymore.

A `no-target-evidence` is never "fixed" by inventing the route in B or
changing the target by intuition — it is reported and the user decides (or
it is corrected via `domains.yaml`).

## Reverse direction too

Validation runs in both directions: when scanning B, each inbound endpoint
that B exposes is cross-checked against the MOCs of the repos in the
workspace. An endpoint of B that nobody in the workspace calls is not an
error (it may have external or client consumers), but it is used for the
inbound count per axis and is listed in the report as "inbound without a
known internal source".

## Cost

Reverse validation does not require a separate scan: it uses what was
already collected in step 2.B (outbound and inbound of each repo). It is a
cross-check of data already gathered, not a second pass over the code. With
prescan (see `prescan.md`) the cross-check is done between the JSON files in
`.kiro/allspark/prescan/`: outbound `path` of A against inbound `path` of B
(with class prefixes already composed by the script), `topic`/`queue`
produced against consumed, and gRPC `service` consumed against implemented
(or declared in the same `.proto`). That is why the
roles are defined first (2.A) and inbound connections are always collected,
even if the repo is not the focus of the run.
