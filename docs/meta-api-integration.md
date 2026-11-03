# Meta Model API integration

Checked against official Meta documentation on **2026-10-29**:

- Overview: https://dev.meta.ai/docs/overview
- Authentication: https://dev.meta.ai/docs/authentication
- Models: https://dev.meta.ai/docs/models
- Responses protocol: https://dev.meta.ai/docs/protocols/responses
- Create response reference: https://dev.meta.ai/docs/api-reference/responses/create-response
- Structured output: https://dev.meta.ai/docs/structured-output
- Pricing and rate limits: https://dev.meta.ai/docs/pricing-rate-limits

## Verified contract

The documented base URL is `https://api.meta.ai/v1`, with `POST /responses`,
an `Authorization: Bearer <API key>` header, and hosted model IDs including
`muse-spark-1.3` and `muse-wonder-1.0`. Meta's authentication documentation
shows API keys beginning with `LLM_`; the key remains server-side and is never
sent to the frontend.

The adapter sends text `input` and uses Responses structured output via
`text.format` with `type: "json_schema"`. It accepts both the SDK-style
`output_text` convenience field used by mocks and the documented raw response
shape at `output[].content[].text`. It records the response ID and usage
metadata when present.

## Bounded capability

The optional model call drafts an evidence-grounded executive brief from
validated specialist outputs. Deterministic calculations remain authoritative.
The model cannot calculate or alter financial results, change scenario ranking
or feasibility, invent evidence IDs, approve actions, execute interventions,
or make employee-level recommendations.

Structured output is a response-format guarantee, not a substitute for
application validation. Evidence IDs are checked against the validated
investigation inventory after parsing.

## Configuration and fallback

`META_MODEL_MODE=demo` is the default and makes no outbound request.
`META_MODEL_MODE=live` requires `MODEL_API_KEY`; `META_MODEL_ID` defaults to
`muse-spark-1.3`, and `META_MODEL_BASE_URL` defaults to
`https://api.meta.ai/v1`.

If live mode is unavailable because of missing credentials, a timeout, a rate
limit, an invalid response, fabricated evidence, or a service error, the
application returns a clearly labeled deterministic fallback. It never labels
that fallback as live model output and never bypasses the final evidence-review
gate.

## Pricing and limits

As documented on 2026-10-29:

- Muse Spark 1.3 Standard: $1.25 per 1M input tokens and $4.25 per 1M output
  tokens.
- Muse Spark 1.3 Standard: 3,000 requests per minute and 4,000,000 tokens per
  minute per team.
- Responses include usage fields when available; the adapter preserves them.

These are documentation values, not a project cost estimate. A live call
requires explicit authorization and available credits.

## Verification status

Mocked tests cover structured output, raw Responses extraction, authorization
format, fabricated evidence rejection, malformed output, missing credentials,
timeouts, rate limits, server errors, and explicit deterministic fallback.

No live Meta request was made during Phase 6H because no authorized credential
or explicit credit approval was available. Live inference remains unverified
and must not be claimed in the submission.

The authoritative consolidated Phase 6 status is in
[PHASE6_FINAL_REPORT.md](../PHASE6_FINAL_REPORT.md). The safe readiness endpoint
is `GET /api/providers/status`; it never returns the API key.
