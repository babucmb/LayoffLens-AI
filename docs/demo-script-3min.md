# Three-minute demo script

**0:00–0:20** Introduce LayoffLens AI — Enterprise Workforce Resilience Intelligence Platform. Frame the problem: fragmented planning hides aggregate risk.  
**0:20–0:45** Show the synthetic badge and overview KPIs. Point to Cloud capacity and delayed projects.  
**0:45–1:20** Click **Run investigation**. Explain that the project-delay event selects project demand first, then passes its result into capacity/scenario analysis; cite the evidence IDs and step reasons.  
**1:20–1:55** Open **Scenario studio**. Move delay/conversion/hiring-delay/mobility sliders and recalculate Baseline, Downside, and Intervention.  
**1:55–2:25** Show preventive options: mobility, reskilling, hiring timing, and infrastructure review. State that costs are illustrative synthetic assumptions, not validated savings.  
**2:25–2:45** Read the evidence-grounded brief. Say “Demo fallback” unless a live Meta call was actually made.  
**2:45–3:00** Open Human review, record a rationale, and close: “See the risks. Find the alternatives. Protect the workforce.” This is planning support, not an employee layoff score or an automatic action.

For an alternate path during a technical demo, POST `{"event_type":"infrastructure_cost","budget":4}`
to `/api/investigate`; it starts with Finance analyst and visibly selects a different
bounded path. Both paths remain synthetic and aggregate-only.
