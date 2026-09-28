; Generic shapes for TypeScript, TSX and JavaScript (the same query compiles in all three grammars).
; Capture names shared by every language: annotation, call, new, pair, inheritance.
; Per-framework rules live in rules/typescript.json, not here.

; Decorators: @Get('x'), @Controller('api'), @Injectable
(decorator (call_expression function: (identifier) @annotation.name arguments: (arguments) @annotation.args)) @annotation
(decorator (identifier) @annotation.name) @annotation

; Member calls: axios.get(url), this.http.post(url), router.post(path, h), producer.send({topic})
(call_expression function: (member_expression object: (_) @call.object property: (property_identifier) @call.method) arguments: (arguments) @call.args) @call

; Plain calls: fetch(url)
(call_expression function: (identifier) @call.method arguments: (arguments) @call.args) @call

; Constructors: new ScoringServiceClient(host, creds), new PutObjectCommand({...})
(new_expression constructor: (_) @new.type arguments: (arguments) @new.args) @new

; key: value pairs in object literals: { Bucket: 'x' }
(pair key: (property_identifier) @pair.key value: (_) @pair.value) @pair
