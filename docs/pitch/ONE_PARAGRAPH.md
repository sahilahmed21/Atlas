# One-paragraph pitch (draft)

Atlas is a research-oriented LLM serving platform that demonstrates production multi-tenant serving *behavior*—OpenAI-compatible APIs, cache-aware routing, and measured latency/throughput—on constrained free-tier GPUs rather than assuming multi-node RDMA infrastructure. I start from first-principles KV memory math and a naive HuggingFace baseline that I drive to failure on my own hardware, rebuild the core mechanisms as readable simulations, reconcile them against vLLM, then run an honest routing experiment that includes cases where the “smart” router loses. The public artifacts are the failure curve, the before/after chart, and a live dashboard backed by real metrics—not a tutorial redeploy of someone else’s stack.

_Rehearse until every clause has a file or chart behind it._
