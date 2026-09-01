# Local mailbox authorization

C2CDirect reads only job-alert and recruiter messages from a mailbox the owner explicitly authorizes.
It does not accept mailbox passwords, app passwords, private keys, or access tokens in chat.

## Gmail

1. In the Google Cloud project owned by the operator, configure an OAuth consent screen.
2. Create an OAuth client that permits the localhost web callback below.
3. Enable the Gmail API and request only identity/email plus `gmail.readonly`.
4. Register this exact redirect URI:
   `http://127.0.0.1:8080/api/v1/email/oauth/gmail/callback`
5. Run `./scripts/configure-email-oauth.py gmail`. Enter the public client ID
   directly at the hidden prompt; do not paste it into chat or commit it.

## Microsoft Outlook

1. In the Microsoft identity admin portal owned by the operator, create an application registration.
2. Add a web or public-client localhost redirect URI matching the callback below.
3. Grant delegated `openid`, `email`, `offline_access`, `User.Read`, and read-only `Mail.Read` scopes.
4. Register this exact redirect URI:
   `http://127.0.0.1:8080/api/v1/email/oauth/microsoft/callback`
5. Run `./scripts/configure-email-oauth.py microsoft`. Enter the public client ID
   directly at the hidden prompt; do not paste it into chat or commit it.

## Finish and verify

Restart only the API service so it loads the new private setting. Open the local C2CDirect Workspace,
select the corresponding secure connection button, and approve the provider-hosted consent screen. The
window closes when authorization succeeds and the dashboard refreshes the connection automatically.
Use **Sync now** to ingest the last fourteen days of matching job mail.

The connection is acceptable only when:

- the provider grants the required read-only mailbox scope;
- the connection appears with the expected mailbox address;
- a sync completes without authorization errors;
- repeated syncs report already-seen messages rather than duplicate jobs;
- encrypted token columns do not contain plaintext access or refresh tokens; and
- another tenant cannot list, synchronize, or inspect the connection.
