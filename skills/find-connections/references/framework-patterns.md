# Detection patterns per framework

**Human-readable description of the patterns.** Since v1.10.0 the executable
version of these same patterns lives in `assets/prescan/rules/<language>.json`
and is applied by the deterministic prescan (step 2.B.1, see `prescan.md`).
This document remains the reference for understanding what is searched for
and for manual reading (repos without prescan or stacks in
`stacks_without_pattern`). When a pattern is added, it is added on both
sides: here in prose and in the rules JSON.

Covered by the prescan: Spring (Java), Express/NestJS and TS/JS fronts,
Django/Flask/FastAPI, Rails, ASP.NET (.NET) — plus gRPC, queues and S3
in all of them. Kotlin, Go, PHP and others: manual reading until their
rules are added.

Used in step 2.B of Phase 2 (exhaustive scan), in step 1 of the resolution
chain ("Literal URL/name in code"), in the endpoint count and in reverse
validation (step 2.C), which needs the target repo's **inbound** ones. An
explicit distinction is made between **outbound** (calls the repo makes to
the outside, they feed the x/y/z position) and **inbound** (endpoints the
repo exposes, they feed the per-axis count). A repo can have both types and
they must not be confused.

## Spring (Java/Kotlin)

### Outbound (for position)

- `RestTemplate` — injected bean, look for `restTemplate.getForObject(...)`,
  `.postForEntity(...)`, `.exchange(...)`. The URL can be in the method's
  literal or in a configuration constant/variable (`@Value`) — if it is
  `@Value`, resolve against `application.yml`/`application.properties`
  (counts as step 3, non-secret config).
- `WebClient` — `webClient.get().uri(...)`, `.post().uri(...)`. Same
  treatment of literal URL vs `@Value`.
- `RestClient` (Spring 6.1+) — same pattern as WebClient but synchronous.
- `FeignClient` — **the URL is not in a method call, it is in the
  interface annotation**: `@FeignClient(name = "...", url = "...")`.
  Look for all interfaces annotated with `@FeignClient` in the repo, not
  only where they are invoked.
- SOAP — `WebServiceTemplate` (Spring-WS): look for `.marshalSendAndReceive(...)`
  and the WSDL/endpoint configured in the bean. Generated JAX-WS: look for
  client classes generated from WSDL (they usually live in
  `target/generated-sources` or similar, not always versioned — if they are
  not versioned, fall back to step 3/4 looking for the source WSDL in
  config).

### Inbound (for count)

- `@RequestMapping`, `@GetMapping`, `@PostMapping`, `@PutMapping`,
  `@DeleteMapping`, `@PatchMapping` — at method AND class level (the class
  path is concatenated with the method path; count the resulting endpoint
  once, not twice).

## Express / NestJS (Node/TypeScript)

### Outbound

- `axios.get/post/...(url)`, `axios.create({ baseURL })` instances
- `fetch(url)`
- NestJS `HttpService` (`this.httpService.get(...)`)
- SOAP clients like `soap.createClientAsync(wsdlUrl)`

### Inbound

- Express — `router.get/post/put/delete(path, ...)`
- NestJS — `@Get()`, `@Post()`, etc. at method level + `@Controller(prefix)`
  at class level (concatenate the same as Spring)

## Django (Python)

### Outbound

- `requests.get/post(url)`, `requests.Session()` sessions
- SOAP clients like `zeep.Client(wsdl)`

### Inbound

- `urls.py` / `urlpatterns` — each `path(...)` or `re_path(...)` entry

## Rails (Ruby)

### Outbound

- `Net::HTTP`, `HTTParty.get/post(url)`, `Faraday.get(url)`
- SOAP clients like `Savon.client(wsdl: ...)`

### Inbound

- `config/routes.rb` — each declared route entry

## gRPC (all stacks)

Contract: versioned `.proto` files — they declare `package`, `service` and
each `rpc`. They count as step 2 of the chain (versioned contract) and are
the key to crossing source and target in reverse validation: the same
`package.Service` on both sides.

### Outbound

- Java/Kotlin — `ManagedChannelBuilder.forAddress(host, port)` /
  `.forTarget(...)`, stubs `XxxGrpc.newBlockingStub(channel)` /
  `newStub` / `newFutureStub`; `@GrpcClient("name")` (grpc-spring-boot) with
  the address in `application.yml` (`grpc.client.<name>.address`).
- Node/TS — `@grpc/grpc-js`: `new grpc.Client(...)`, generated clients
  `new XxxServiceClient(host, credentials)`; NestJS `ClientsModule` with
  `transport: Transport.GRPC`.
- Python — `grpc.insecure_channel(target)` / `secure_channel`, stubs
  `XxxStub(channel)`.
- .NET — `GrpcChannel.ForAddress(url)`, generated clients.
- Front (gRPC-web) — `grpc-web`/`@improbable-eng/grpc-web` with the proxy
  URL; it is treated as front HTTP for the "front without intermediate
  backend" rule.

### Inbound

- Java/Kotlin — classes `extends XxxGrpc.XxxImplBase`, `@GrpcService`.
- Node/TS — `server.addService(XxxService, impl)`; NestJS `@GrpcMethod`.
- Python — `add_XxxServicer_to_server(...)`.
- .NET — `app.MapGrpcService<XxxService>()`.

## Message queues — RabbitMQ and Kafka

Connection identifier: **broker + exchange/queue (RabbitMQ) or topic
(Kafka)**. The broker host comes from step 3 of the chain (non-secret
config: `application.yml`, `docker-compose`, k8s). Direction: the
**producer is the source** of the vector and the **consumer the target**. A
topic produced by a workspace repo and consumed by another workspace repo
is **Y**; a broker/topic without a mapped producer or consumer exhausts the
chain and goes to **Z** by default, like any other connection.

### Outbound (publish)

- Spring — `RabbitTemplate.convertAndSend(exchange, routingKey, ...)`,
  `AmqpTemplate`, `KafkaTemplate.send(topic, ...)`, Spring Cloud Stream
  (`StreamBridge.send`, `*-out-*` bindings in config).
- Node/TS — `amqplib` (`channel.publish`, `channel.sendToQueue`), `kafkajs`
  (`producer.send({ topic })`), NestJS `ClientProxy.emit` with RMQ or KAFKA
  transport.
- Python — `pika` (`basic_publish`), `confluent_kafka.Producer.produce`,
  `kafka-python` `KafkaProducer.send`, Celery `.delay()`/`.apply_async()`
  (the Celery broker counts as a queue).
- Ruby — `bunny` (`exchange.publish`), `ruby-kafka`/`karafka` producers,
  Sidekiq `perform_async` (Redis as broker).
- .NET — `IModel.BasicPublish`, MassTransit `Publish/Send`,
  `Confluent.Kafka` `ProduceAsync`.

### Inbound (consume)

- Spring — `@RabbitListener(queues = ...)`, `@KafkaListener(topics = ...)`,
  Spring Cloud Stream `*-in-*` bindings.
- Node/TS — `channel.consume(queue, ...)`, `consumer.subscribe({ topic })`,
  NestJS `@EventPattern`/`@MessagePattern`.
- Python — `basic_consume`, `Consumer.subscribe`, `@app.task` tasks
  (Celery), `KafkaConsumer(topic)`.
- Ruby — `queue.subscribe`, Karafka consumers, Sidekiq workers
  (`include Sidekiq::Worker`).
- .NET — `BasicConsume`, MassTransit `IConsumer<T>`.

A repo whose only "inbound" are queue consumers (or scheduled jobs:
`@Scheduled`, cron, `node-cron`, Celery beat) is a strong signal of role
`worker` (see `repo-roles.md`).

## MVC monolith signals (for step 2.A)

- Rails — `app/views/` + `app/controllers/` in the same repo.
- Laravel — `resources/views/` (Blade) + `app/Http/Controllers/`.
- Django — `templates/` + views that return `render(...)`.
- ASP.NET MVC — `Views/` + `Controllers/` with `return View(...)`.
- Spring MVC — `@Controller` (not `@RestController`) that returns view
  names + Thymeleaf or JSP `templates/`.
- Next.js / Nuxt with API routes or server actions that call other
  services.

In a monolith, the outbound calls that are counted are the server-side
ones; the inbound ones are its routes/controllers.

## General note

This list grows with each new stack that shows up in the workspace. If a
repo uses a framework not listed here, do not assume it has no outbound
calls — report it as an uncovered stack and ask for the corresponding
pattern to be added before trusting its x/y/z position. For the prescan to
cover it, follow "Adding a new framework or stack" in `prescan.md`.
