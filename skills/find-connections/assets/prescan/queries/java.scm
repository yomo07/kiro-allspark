; Generic shapes for Java. Rules in rules/java.json.

; Annotations: @GetMapping("/x"), @FeignClient(url = "..."), @PostMapping
(annotation name: (identifier) @annotation.name arguments: (annotation_argument_list) @annotation.args) @annotation
(marker_annotation name: (identifier) @annotation.name) @annotation

; Calls: restTemplate.postForEntity(url, ...), kafkaTemplate.send("t", m), builder().bucket("b")
(method_invocation object: (_) @call.object name: (identifier) @call.method arguments: (argument_list) @call.args) @call
(method_invocation !object name: (identifier) @call.method arguments: (argument_list) @call.args) @call

; Constructors
(object_creation_expression type: (_) @new.type arguments: (argument_list) @new.args) @new

; Inheritance: class X extends YGrpc.YImplBase
(class_declaration superclass: (superclass (_) @inheritance.base)) @inheritance
