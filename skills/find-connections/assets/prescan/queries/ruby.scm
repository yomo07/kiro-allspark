; Generic shapes for Ruby (Rails). Rules in rules/ruby.json.

; Calls with a receiver: Faraday.new(url: '...'), HTTParty.get("..."), exchange.publish(m)
(call receiver: (_) @call.object method: (identifier) @call.method arguments: (argument_list)? @call.args) @call

; Calls without a receiver: get '/health', to: '...'  |  resources :merchants
(call !receiver method: (identifier) @call.method arguments: (argument_list)? @call.args) @call

; Hash pairs: url: '...', wsdl: '...'
(pair key: (hash_key_symbol) @pair.key value: (_) @pair.value) @pair
