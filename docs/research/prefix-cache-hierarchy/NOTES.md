# Prefix cache hierarchy

## Levels

1. **Engine:** vLLM automatic prefix caching inside a replica  
2. **Router:** send request to replica most likely to hit  
3. **Distributed (future):** shared KV / transfer across nodes  

Atlas free path implements (1) via vLLM and (2) via `platform/router`. Level (3) is Phase 6.

## Failure mode to hunt (Phase 5)

Router affinity that overloads one replica while another sits cold — "smart" routing can worsen tail latency.
