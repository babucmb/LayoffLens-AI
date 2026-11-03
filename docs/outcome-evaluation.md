# Outcome evaluation

The current local evaluation uses explicit synthetic fixtures and reports forecast
MAE/WAPE plus deterministic policy-path checks. It does not silently infer labels,
update a policy, or claim production accuracy.

An eventual production workflow should record the source snapshot, scenario
assumptions, human-approved intervention, observation timestamp, and explicitly
supplied observed outcome. Policy changes must be evaluated against the current
baseline and approved before promotion.

Reinforcement learning is not included: the project does not have a validated
environment transition model, reward function, episode corpus, safety evaluation,
or measured baseline comparison.
