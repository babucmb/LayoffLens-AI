# Agent evaluation

The local evaluation is a transparent policy check over synthetic fixtures with
explicit expected first tools. It reports policy path correctness, tool calls, and
fixture precision/recall. These labels are not inferred from outcomes and are not
production predictive accuracy.

The existing `/api/evaluation` endpoint continues to report synthetic forecast MAE
and WAPE. Neither metric updates the policy automatically. Any future policy change
requires a new evaluation and human approval.

Reinforcement learning is not justified for this prototype: there is no validated
environment transition model, reward function, or episode corpus. PPO is therefore
not included.
