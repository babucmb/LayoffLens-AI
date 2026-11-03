# Model routing

`ModelRouter` routes agent roles independently and reports provider and
execution mode in the agent catalog. The verified default is deterministic simulation. Set `WRI_AGENT_MODE=live`
to opt into the model-driven supervisor and specialist model-call path. The
live path uses the configured Meta Responses adapter and requires
`MODEL_API_KEY`; it has not been called in this project. Models do not
calculate authoritative financial values or retrieve external information.

Live provider routing requires credentials, current provider documentation,
strict output validation, and explicit authorization. Missing credentials and
provider failures must remain clearly labeled fallback states.
