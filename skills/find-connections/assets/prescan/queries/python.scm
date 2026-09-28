; Generic shapes for Python. Rules in rules/python.json.

; Member calls (also inside decorators: @app.get('/x'), @router.post(...))
(call function: (attribute object: (_) @call.object attribute: (identifier) @call.method) arguments: (argument_list) @call.args) @call

; Plain calls: path('api/', v), grpc_channel(...), KafkaConsumer('t')
(call function: (identifier) @call.method arguments: (argument_list) @call.args) @call

; Decorators without a call: @shared_task, @app.task
(decorator (identifier) @annotation.name) @annotation
(decorator (attribute) @annotation.name) @annotation

; Keyword arguments and dictionaries: Bucket='x', {'Bucket': 'x'}
(keyword_argument name: (identifier) @pair.key value: (_) @pair.value) @pair
(pair key: (string) @pair.key value: (_) @pair.value) @pair
