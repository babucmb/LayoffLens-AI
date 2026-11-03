# System architecture

```text
Investigation API / local monitor
          |
          v
Event-specific supervisor plan
          |
          v
AgentRuntime -> ToolRegistry -> deterministic aggregate tools
          |                         |
          v                         v
Execution trace, evidence       scenarios and alternatives
          |
          v
Independent evidence review -> persisted report/history
```

Tools are read-only by default, permission checked, dependency validated, and
never execute model-generated shell, SQL, Python, filesystem, or unrestricted
network requests. External research is an explicit provider capability and is
not supplied by the Meta model automatically.

The local mode is deterministic simulation. A future live provider may be
routed by role, but must preserve structured response validation, provenance,
human review, and the same deterministic calculation tools.
