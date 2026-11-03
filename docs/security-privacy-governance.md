# Security, privacy, and governance

The product is aggregate-only by design. Secrets stay server-side; `.env` is ignored; the model prompt treats supplied content as untrusted data; and no arbitrary tools are exposed. Live model output must cite supplied evidence and is shown with a live/demo indicator. Reviews are simulated and cannot trigger HR, payroll, hiring, or termination actions.

## Verified local reference controls

When `WRI_AUTH_ENABLED=true`, the API enforces server-side bearer tokens from
the local demo configuration, reviewer versus operator/admin write roles, and
the `demo-tenant` request boundary. Login, investigation, replay, review,
outcome, evaluation, and monitor actions create application-level SQLite audit
events. Security response headers are added by the API middleware. Invalid
credentials and tenant mismatches are rejected before route execution.

The default judge mode keeps authentication disabled for a simple local
startup. The demo credentials are intentionally synthetic and must be
replaced before any deployment.

These controls are not enterprise SSO, encryption-at-rest, tamper-proof audit,
complete multi-tenant storage isolation, or compliance certification.
Production controls should include SSO, least privilege, encryption, audit
immutability, retention/deletion, tenant isolation in every persisted record,
prompt/output logging minimization, red-team testing, incident response, and
an approval gate for any model or policy change.
