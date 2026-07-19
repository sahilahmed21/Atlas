# llm-d

**What it is:** Kubernetes-native distributed LLM inference stack (vLLM + intelligent routing, KV-aware scheduling, autoscaling). Backed by industry orgs as a reference architecture direction.

**Track:** https://github.com/llm-d/llm-d (verify upstream as you write Phase 6)

## Ideas Atlas borrows (concepts, not a fork)

- KV-aware / cache-aware routing  
- Prefix cache as a first-class scheduling signal  
- K8s-native autoscaling on inference signals  
- Separation of gateway / router / model servers  
