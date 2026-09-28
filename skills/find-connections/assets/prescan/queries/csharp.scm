; Generic shapes for C# (.NET). Rules in rules/csharp.json.

; Attributes: [HttpGet], [HttpPost("ping")], [Route("api/x")]
(attribute name: (identifier) @annotation.name (attribute_argument_list)? @annotation.args) @annotation

; Member calls: httpClient.PostAsync(url, c), channel.BasicPublish(exchange: "x"), app.MapGrpcService<T>()
(invocation_expression function: (member_access_expression expression: (_) @call.object name: (_) @call.method) arguments: (argument_list) @call.args) @call
(invocation_expression function: (identifier) @call.method arguments: (argument_list) @call.args) @call

; Constructors
(object_creation_expression type: (_) @new.type arguments: (argument_list)? @new.args) @new

; Initializers: new PutObjectRequest { BucketName = "x" }
(initializer_expression (assignment_expression left: (identifier) @pair.key right: (_) @pair.value) @pair)
