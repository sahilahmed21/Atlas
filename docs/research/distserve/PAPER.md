# DistServe

**Citation:** Zhong et al., "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving" (OSDI 2024).  
**Link:** https://arxiv.org/abs/2401.09670

## Core claim

Co-locating prefill and decode causes interference; disaggregating onto different GPUs improves goodput.

## Why Atlas does not fake this on free path

Prefill/decode disaggregation at production quality assumes multiple GPUs and fast interconnect. One T4 cannot honestly claim DistServe.
