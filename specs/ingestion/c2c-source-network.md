# C2C source network

Status: Implemented

## Source order

Signal SHOULD prefer sources in this order:

1. Buyer-controlled VMS or managed marketplace requisitions obtained through authorized access.
2. A verified prime vendor with a direct recruiter relationship and known end client or requisition.
3. A marketplace posting with explicit positive C2C language and a traceable recruiter or employer.
4. The employer's official ATS as corroboration of role identity and freshness.
5. An aggregator only as a discovery lead, never as final proof.

## Provider claims

Every provider target MUST include source evidence, expected vendor-layer range, access method, and
C2C signal strength. Supplier-network membership proves only that the named company appears in that
network; it MUST NOT be represented as a relationship with C2CDirect or an end client.

## Admission to the daily queue

A job MAY enter the daily action queue only when it is C2C confirmed or likely, is not in the
low-quality lane, and is still new. Missing rate or end-client evidence remains visible as a
verification task. External outreach and applications always require human approval.
