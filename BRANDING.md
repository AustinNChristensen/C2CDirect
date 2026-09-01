# C2CDirect brand

## Product identity

- Product name: **C2CDirect**
- Display wordmark: **C2CDirect**
- Community edition: **C2CDirect Core**
- Managed edition: **C2CDirect Cloud**
- Matching and classification component: **Signal Engine**
- Primary tagline: **Find the contract. Verify the chain. Win the work.**
- Descriptor: **Opportunity intelligence for independent engineers.**

“Direct” describes direct access to commercial evidence, source provenance, and the vendor chain. It
does not claim that every indexed opportunity comes directly from an end client or accepts C2C.

## Public identifiers

New public installations use:

- PostgreSQL database and role names containing `c2cdirect`
- the `c2cdirect-api` JWT audience
- the `c2cdirect` Docker Compose project name
- `C2CDIRECT_*` n8n environment variables and the existing webhook path
- historical backup filenames, private repository paths, and Git remotes

These identifiers intentionally match the C2CDirect product name. The initial public repository does
not publish the private pre-release history or its legacy operational configuration.

## Release configuration

Set `NEXT_PUBLIC_SITE_URL` to the final canonical HTTPS origin when the purchased domain is attached.
Set `NEXT_PUBLIC_SOURCE_URL` to `https://github.com/AustinNChristensen/C2CDirect`.
Do not infer either URL from the product name during deployment.

`NEXT_PUBLIC_SHOW_EXPERIMENTAL_TABS` defaults to `false`. Build Lab and Workspace are intentionally
absent from the core product navigation until each has a complete, documented user journey. A local
development build may set it to `true` when those experiments need review.
