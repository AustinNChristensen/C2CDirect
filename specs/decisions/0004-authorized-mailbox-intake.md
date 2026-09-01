# ADR 0004: Authorized mailbox intake

- Status: accepted
- Date: 2026-08-29

## Context

Direct employer ATS feeds are authoritative but rarely state whether an engagement permits C2C.
Recruiter mail and saved job alerts carry the missing commercial evidence, but mailbox access is
sensitive and must not rely on passwords, browser automation, forwarding private mail to a shared
service, or tokens pasted into chat.

## Decision

C2CDirect supports Gmail and Microsoft mail intake through provider-hosted OAuth authorization with
PKCE. Access is read-only and tenant/user scoped. Access and refresh tokens are encrypted before
database persistence using an installation-specific key that is never committed. Raw message bodies
are processed transiently; the durable receipt stores message identifiers, sender, subject, timestamp,
content hash, processing status, and canonical job link. The application does not send, delete, label,
or otherwise mutate mailbox content.

Only tenant owners with `jobs:write` may initiate authorization or synchronize a mailbox. OAuth state
is encrypted, expires after ten minutes, and binds provider, tenant, user, and PKCE verifier. Callback
processing trusts only that state, not browser-supplied tenant identifiers.

## Consequences

- A self-hosted operator must register a localhost callback with Google or Microsoft and place the
  public OAuth client ID directly in the private server environment.
- Mailbox passwords, provider secrets, private keys, and tokens never belong in support chat.
- A source email is evidence, not proof of its claimed end client or vendor depth; unknown claims stay
  in the verification lane.
- Public deployment remains blocked until production OAuth callbacks, authentication, rate limiting,
  and tenant-isolation tests pass in that environment.

## Intentionally not chosen

- IMAP username/password or app-password access.
- Browser automation of Gmail, Outlook, LinkedIn, or Dice.
- Broad `Mail.ReadWrite`, send-mail, delete, label, or contact scopes.
- Storing raw mailbox bodies indefinitely.
