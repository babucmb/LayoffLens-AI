from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


DOMAINS = (
    "finance",
    "sales",
    "projects",
    "hiring",
    "workforce",
    "learning",
    "ai_transformation",
    "cloud",
    "facilities",
    "external_intelligence",
)


def _source(domain: str, index: int, period: str) -> dict[str, str]:
    return {
        "source_id": f"synthetic:{domain}:v1",
        "source_timestamp": f"{period}-28T00:00:00+00:00",
        "ingestion_timestamp": "2026-10-31T00:00:00+00:00",
        "record_id": f"{domain}:{period}:{index:03d}",
    }


def build_enterprise_dataset() -> dict[str, Any]:
    """Create one deterministic, aggregate-only enterprise data environment."""
    periods = [f"2025-{month:02d}" for month in range(11, 13)] + [f"2026-{month:02d}" for month in range(1, 11)]
    units = ["cloud-infrastructure", "enterprise-delivery", "data-ai", "business-operations"]
    skills = ["Cloud", "Engineering", "Data", "Product", "Operations"]
    data: dict[str, Any] = {
        "organization": {"organization_id": "org:meridian", "name": "Meridian Digital Services", "base_currency": "USD"},
        "business_units": [{"business_unit_id": f"bu:{name}", "name": name.replace("-", " ").title()} for name in units],
        "skill_families": [{"skill_family_id": f"skill:{name.lower()}", "skill_family": name} for name in skills],
    }
    finance: list[dict[str, Any]] = []
    sales: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    hiring: list[dict[str, Any]] = []
    workforce: list[dict[str, Any]] = []
    learning: list[dict[str, Any]] = []
    ai_transformation: list[dict[str, Any]] = []
    cloud: list[dict[str, Any]] = []
    facilities: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []

    for index, period in enumerate(periods):
        revenue = round(18.5 - index * 0.18 + (0.25 if index < 5 else 0), 2)
        opex = round(11.2 + index * 0.16, 2)
        finance.append({
            **_source("finance", index, period), "organization_id": "org:meridian",
            "business_unit_id": "bu:enterprise-delivery", "cost_center_id": "cc:delivery",
            "reporting_period": period, "revenue": revenue, "recurring_revenue": round(revenue * .62, 2),
            "operating_expenses": opex, "payroll_budget": round(opex * .58, 2),
            "gross_margin": round((revenue - opex * .42) / revenue, 4),
            "operating_margin": round((revenue - opex) / revenue, 4),
            "cash_flow": round(revenue - opex, 2), "forecast_revenue": round(revenue + .35, 2),
            "actual_revenue": revenue, "currency": "USD",
        })
        sales.append({
            **_source("sales", index, period), "opportunity_id": f"opp:{index:03d}",
            "customer_id": f"customer:{index % 4 + 1}", "business_unit_id": units[index % 4],
            "project_id": f"project:{index % 6 + 1}", "opportunity_value": round(7.5 - index * .08, 2),
            "probability": round(max(.45, .78 - index * .015), 3),
            "weighted_pipeline_value": round((7.5 - index * .08) * max(.45, .78 - index * .015), 2),
            "opportunity_stage": "renewal" if index % 3 == 0 else "proposal",
            "expected_close_date": f"{period}-25", "renewal_date": f"{period}-20",
            "cancellation_status": "cancelled" if index in {8, 9} else "active",
            "customer_segment": "enterprise",
        })
        projects.append({
            **_source("projects", index, period), "project_id": f"project:{index % 6 + 1}",
            "business_unit_id": units[index % 4], "customer_id": f"customer:{index % 4 + 1}",
            "project_name": ("Atlas migration" if index >= 8 else "Delivery program"),
            "project_status": "delayed" if index in {8, 9} else "on_track",
            "planned_start": f"{period}-01", "actual_start": f"{period}-03",
            "planned_end": f"{period}-25", "forecast_end": f"{period}-30" if index in {8, 9} else f"{period}-25",
            "delay_days": 5 if index in {8, 9} else 0, "contract_value": 5.0,
            "delivery_cost": 3.1, "required_skill_family": skills[index % len(skills)],
            "required_capacity": 12 + index % 5, "project_priority": "high" if index in {8, 9} else "normal",
            "cancellation_reason": "demand change" if index == 9 else None,
        })
        hiring.append({
            **_source("hiring", index, period), "requisition_id": f"req:{index:03d}",
            "business_unit_id": units[index % 4], "skill_family": skills[index % len(skills)],
            "approved_positions": 4, "committed_positions": 3, "planned_joining_date": f"{period}-15",
            "requisition_status": "approved", "estimated_cost": 0.42, "hiring_priority": "high" if index >= 8 else "normal",
        })
        workforce.append({
            **_source("workforce", index, period), "business_unit_id": units[index % 4],
            "skill_family": skills[index % len(skills)], "reporting_period": period,
            "available_capacity": 40 + index % 4, "allocated_capacity": 36 + index % 6,
            "utilization_rate": round((36 + index % 6) / (40 + index % 4), 4),
            "attrition_rate": .012, "aggregate_headcount": 48 + index % 5,
            "cost_per_capacity_unit": 0.11, "location_group": "North America",
        })
        learning.append({
            **_source("learning", index, period), "skill_family": skills[index % len(skills)],
            "reporting_period": period,
            "current_skill_supply": 40 + index % 4, "proficiency_distribution": {"advanced": .3, "standard": .55, "developing": .15},
            "training_capacity": 5, "training_cost": .08, "training_duration": 8,
            "certification_coverage": .72, "future_skill_demand": 43 + index % 6,
        })
        ai_transformation.append({
            **_source("ai_transformation", index, period), "business_unit_id": units[index % 4],
            "process_category": "service-delivery", "task_category": "case-analysis",
            "automation_adoption": round(.18 + index * .012, 3), "task_coverage": .44,
            "productivity_change": .08, "quality_score": .91, "exception_rate": .06,
            "implementation_cost": .14, "operating_cost": .09, "reporting_period": period,
        })
        cloud_total = round(1.7 + index * .07, 2)
        cloud.append({
            **_source("cloud", index, period), "business_unit_id": "bu:cloud-infrastructure",
            "cloud_provider": "synthetic-cloud", "reporting_period": period,
            "compute_cost": round(cloud_total * .5, 2), "gpu_cost": round(cloud_total * .25, 2),
            "storage_cost": round(cloud_total * .15, 2), "network_cost": round(cloud_total * .1, 2),
            "total_cost": cloud_total, "gpu_utilization": round(.71 - index * .008, 3),
            "compute_utilization": .68, "capacity_consumption": round(.62 + index * .01, 3),
        })
        facilities.append({
            **_source("facilities", index, period), "business_unit_id": "bu:business-operations",
            "facility_id": "facility:na-01", "reporting_period": period,
            "energy_cost": .28, "maintenance_cost": .19, "vendor_cost": .23,
            "operational_capacity": 120, "capacity_utilization": round(.71 + index * .006, 3),
            "location_group": "North America",
        })
        external.append({
            **_source("external_intelligence", index, period), "publisher": "Synthetic Industry Brief",
            "title": "Enterprise technology demand outlook", "url": "https://example.invalid/synthetic",
            "publication_date": f"{period}-20", "retrieval_timestamp": f"{period}-28T00:00:00+00:00",
            "company_or_industry": "enterprise technology", "topic": "demand",
            "extracted_claim": "Demand is volatile in the synthetic scenario.", "evidence_excerpt": "Synthetic fixture.",
            "relevance": .7, "source_type": "synthetic",
        })
    data.update({
        "finance": finance, "sales": sales, "projects": projects, "hiring": hiring,
        "workforce": workforce, "learning": learning, "ai_transformation": ai_transformation,
        "cloud": cloud, "facilities": facilities, "external_intelligence": external,
    })
    return data


def validate_enterprise_dataset(data: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for domain in DOMAINS:
        rows = data.get(domain, [])
        if not isinstance(rows, list):
            records.append({"domain": domain, "valid": False, "error": "domain must be a list"})
            continue
        ids: set[str] = set()
        for index, row in enumerate(rows):
            record_id = row.get("record_id") if isinstance(row, dict) else None
            duplicate = bool(record_id and record_id in ids)
            if record_id:
                ids.add(record_id)
            missing = [field for field in ("source_id", "ingestion_timestamp") if not isinstance(row, dict) or not row.get(field)]
            records.append({"domain": domain, "index": index, "valid": not duplicate and not missing, "duplicate": duplicate, "missing": missing})
    return {"valid": all(item["valid"] for item in records), "records": records, "domains": list(DOMAINS), "record_count": sum(len(data.get(domain, [])) for domain in DOMAINS)}
