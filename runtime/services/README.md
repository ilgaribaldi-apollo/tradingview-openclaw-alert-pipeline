# Runtime Services

Shared service boundaries expected here:
- dedupe-key construction for signal replay safety
- promotion gate checks before runtime entry
- read-model publishing for frontend summaries
- runtime config loading/validation

Keep this layer pure business logic; leave transport/process concerns to workers/adapters.
