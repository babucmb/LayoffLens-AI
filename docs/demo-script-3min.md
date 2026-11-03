# Three-minute demo script

**0:00–0:25** Introduce LayoffLens AI and frame the problem: fragmented planning hides aggregate risk. Show the synthetic-data badge.  
**0:25–0:55** Show Overview and Intelligence: revenue trend, capacity gap, project risk, forecast bounds, signals, and data freshness.  
**0:55–1:35** Select `revenue_decline` and click **Run investigation**. Show specialist steps, evidence IDs, source snapshot, uncertainty, and the complete/incomplete status.  
**1:35–2:15** Open **Scenario planning**. Compare baseline, downside, and intervention outputs, then inspect preventive alternatives and their constraints.  
**2:15–2:45** Open **Human review**, select the investigation, create a linked review, inspect the evidence snapshot, and show the activity timeline.  
**2:45–3:00** Open **System status** and explain that Meta is demo/no-network and Tavily is not configured unless explicitly enabled. Close: “See the risks. Find the alternatives. Protect the workforce.” This is planning support, not an employee layoff score or an automatic action.

For an alternate path during a technical demo, POST `{"event_type":"infrastructure_cost","budget":4}`
to `/api/investigate`; it starts with Finance analyst and visibly selects a different
bounded path. Both paths remain synthetic and aggregate-only.
