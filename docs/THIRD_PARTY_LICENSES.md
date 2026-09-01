# Third-party license review

This review covers the locked C2CDirect Core dependency graph and the container images referenced by
the repository as of 2026-08-31. It is an engineering review, not legal advice. Exact package names,
versions, integrity hashes, and dependency relationships remain authoritative in `pnpm-lock.yaml` and
`backend/uv.lock`.

## Application dependencies

The direct web dependencies use MIT, Apache-2.0, or MIT/Apache-2.0 dual licenses. The locked transitive
web graph additionally contains BSD, ISC, MPL-2.0, Python-2.0, BlueOak-1.0.0, CC0-1.0, CC-BY-4.0,
and LGPL-3.0-or-later components. The LGPL component is the separately packaged libvips binary used
by Sharp; C2CDirect does not modify or statically incorporate it.

The direct API dependencies use MIT, BSD-3-Clause, Apache-2.0, MIT/Apache-2.0, and LGPL-3.0-only
licenses. Psycopg and its separately installed binary/pool packages account for the LGPL entries;
C2CDirect uses them as unmodified libraries. The locked transitive API graph additionally contains
BSD-2-Clause, MPL-2.0, PSF, CNRI-Python, 0BSD, Zlib, and CC0 terms.

`scripts/check-licenses.py` inventories the installed locked graphs and fails when a new or unknown
license expression appears. Run it through `scripts/release-gate.sh` before each tagged release.

## Container images

| Image or base | Use | Upstream license posture | Review result |
| --- | --- | --- | --- |
| `node:22-alpine` | Web build/runtime base | Node.js MIT; Alpine packages retain their own notices | Approved |
| `python:3.12-slim` | API runtime base | Python PSF; Debian packages retain their own notices | Approved |
| `postgres:17-alpine` | Development database | PostgreSQL License | Approved |
| `pgvector/pgvector:pg17` | Core database | PostgreSQL License; includes PostgreSQL | Approved |
| `searxng/searxng:latest` | Optional self-hosted Web Scout search | AGPL-3.0-or-later, separate service | Approved for optional aggregation; source and notices must remain available |
| `caddy:2.10-alpine` | Local reverse proxy | Apache-2.0; Alpine packages retain their own notices | Approved |
| `cloudflare/cloudflared:2026.8.0` | Private deployment tunnel | Apache-2.0 | Approved |
| `n8nio/n8n:1.108.2` | Development/private automation only | Sustainable Use License / Enterprise License | Not part of the public Core runtime; do not redistribute it as a C2CDirect hosted service |

Container tags can move even when a major/minor label is stable. Production operators should resolve
and record image digests during deployment, monitor upstream security advisories, and preserve all
upstream license and notice files. A release owner must re-review this table whenever an image or
locked dependency changes.
