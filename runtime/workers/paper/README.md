# Paper Execution Worker

Responsibilities:
- consume approved signal events
- simulate fills and position lifecycle only
- persist paper positions/fills with strategy-version pinning

Explicitly out of scope here:
- live order routing
- broker/exchange write credentials
- unattended capital deployment
