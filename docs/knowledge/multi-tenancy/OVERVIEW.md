# Multi-tenancy (Phase 4)

Minimum viable SaaS slice:

- API key → tenant  
- RPM / concurrency quota  
- Allowed model list  

Billing can be "quota counters only" on free path. Do not build Stripe unless needed for the story (it is not).
