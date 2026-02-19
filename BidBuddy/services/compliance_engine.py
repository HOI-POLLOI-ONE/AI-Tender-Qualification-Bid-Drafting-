# =============================================================
#  services/compliance_engine.py — Compliance Scoring Engine
# =============================================================
#
#  Two-layer architecture:
#   Layer 1 (Rule Engine): Fast, deterministic, transparent scoring
#                          based on hard eligibility criteria
#   Layer 2 (AI Layer):    Gemini generates nuanced narrative
#                          and strategic recommendations
#
#  Scoring model (100 points total):
#   - Turnover compliance:         30 pts
#   - Experience / Years:          20 pts
#   - Required certifications:     20 pts
#   - Past project value:          15 pts
#   - Document readiness:          10 pts
#   - MSME bonus (if applicable):  +5 pts bonus (can exceed 100)
# =============================================================

from typing import Dict, List, Tuple


# ── Severity levels ───────────────────────────────────────────
DISQUALIFYING = "DISQUALIFYING"   # Automatic rejection if unmet
MAJOR         = "MAJOR"           # Significant weakness
MINOR         = "MINOR"           # Minor gap, fixable


# ── Point deductions per rule ─────────────────────────────────
DEDUCTIONS = {
    "turnover":          30,
    "years_experience":  20,
    "certifications":    20,   # Per missing cert: deduction / num_required
    "past_project":      15,
    "documents":         10,
}


def score_compliance(tender_data: Dict, company_data: Dict) -> Dict:
    """
    Main compliance scoring function.

    Args:
        tender_data:   Extracted tender JSON (from Gemini)
        company_data:  Company profile dict

    Returns:
        {
            "score": 72.5,
            "verdict": "LIKELY ELIGIBLE",
            "gaps": [...],
            "met_criteria": [...],
            "recommendations": [...],
            "breakdown": {...}
        }
    """
    gaps          = []
    met_criteria  = []
    deducted      = 0.0
    breakdown     = {}

    eligibility   = tender_data.get("eligibility", {})

    # ── Rule 1: Annual Turnover ───────────────────────────────
    required_turnover = eligibility.get("min_turnover")
    company_turnover  = company_data.get("annual_turnover", 0)

    if required_turnover:
        if company_turnover >= required_turnover:
            met_criteria.append({
                "field": "Annual Turnover",
                "detail": f"✓ ₹{company_turnover}L meets requirement of ₹{required_turnover}L"
            })
            breakdown["turnover"] = DEDUCTIONS["turnover"]  # Full points
        else:
            shortfall = required_turnover - company_turnover
            pct_of_requirement = (company_turnover / required_turnover) * 100

            # Partial credit: if within 30% of requirement, softer deduction
            if pct_of_requirement >= 70:
                deduction = DEDUCTIONS["turnover"] * 0.5   # 50% deduction
                severity  = MAJOR
            else:
                deduction = DEDUCTIONS["turnover"]
                severity  = DISQUALIFYING

            gaps.append({
                "field":     "Annual Turnover",
                "required":  f"₹{required_turnover}L",
                "actual":    f"₹{company_turnover}L",
                "shortfall": f"₹{shortfall}L",
                "severity":  severity,
                "deduction": deduction,
                "note": (
                    f"Company turnover is {pct_of_requirement:.0f}% of the required amount. "
                    "Consortium formation may bridge this gap."
                )
            })
            deducted += deduction
            breakdown["turnover"] = max(0, DEDUCTIONS["turnover"] - deduction)
    else:
        breakdown["turnover"] = DEDUCTIONS["turnover"]   # No requirement = full score


    # ── Rule 2: Years of Experience ───────────────────────────
    required_years = eligibility.get("years_experience")
    company_years  = company_data.get("years_in_operation", 0)

    if required_years:
        if company_years >= required_years:
            met_criteria.append({
                "field": "Years of Experience",
                "detail": f"✓ {company_years} years meets requirement of {required_years} years"
            })
            breakdown["experience"] = DEDUCTIONS["years_experience"]
        else:
            years_short = required_years - company_years
            gaps.append({
                "field":     "Years of Experience",
                "required":  f"{required_years} years",
                "actual":    f"{company_years} years",
                "shortfall": f"{years_short} years",
                "severity":  DISQUALIFYING,
                "deduction": DEDUCTIONS["years_experience"],
                "note": "Experience requirement is a common hard disqualification criterion."
            })
            deducted += DEDUCTIONS["years_experience"]
            breakdown["experience"] = 0
    else:
        breakdown["experience"] = DEDUCTIONS["years_experience"]


    # ── Rule 3: Required Certifications ───────────────────────
    required_certs = set(eligibility.get("required_certifications", []))
    company_certs  = set(company_data.get("certifications", []))

    if required_certs:
        # Case-insensitive matching
        company_certs_lower   = {c.lower() for c in company_certs}
        missing_certs         = []
        certs_matched         = []

        for cert in required_certs:
            if cert.lower() in company_certs_lower:
                certs_matched.append(cert)
            else:
                missing_certs.append(cert)

        if certs_matched:
            met_criteria.append({
                "field": "Certifications (partial)",
                "detail": f"✓ Has: {', '.join(certs_matched)}"
            })

        if missing_certs:
            # Proportional deduction based on fraction missing
            fraction_missing = len(missing_certs) / len(required_certs)
            deduction = DEDUCTIONS["certifications"] * fraction_missing
            severity  = DISQUALIFYING if fraction_missing == 1.0 else MAJOR

            gaps.append({
                "field":    "Required Certifications",
                "required": list(required_certs),
                "missing":  missing_certs,
                "has":      certs_matched,
                "severity": severity,
                "deduction": round(deduction, 1),
                "note": (
                    "Missing certifications often cause technical bid rejection. "
                    "Fast-track certification is available through QCI India, BIS, and STQC."
                )
            })
            deducted += deduction
            breakdown["certifications"] = round(DEDUCTIONS["certifications"] - deduction, 1)
        else:
            met_criteria.append({
                "field": "Certifications",
                "detail": f"✓ All required certifications present: {', '.join(required_certs)}"
            })
            breakdown["certifications"] = DEDUCTIONS["certifications"]
    else:
        breakdown["certifications"] = DEDUCTIONS["certifications"]


    # ── Rule 4: Past Project Value ─────────────────────────────
    required_project_value = eligibility.get("min_single_project_value")
    company_max_project    = company_data.get("max_single_project_value", 0)

    # Calculate from past_projects if max not set
    if not company_max_project:
        past_projects = company_data.get("past_projects", [])
        if past_projects:
            company_max_project = max(p.get("value", 0) for p in past_projects)

    if required_project_value:
        if company_max_project >= required_project_value:
            met_criteria.append({
                "field": "Past Project Value",
                "detail": f"✓ Max project ₹{company_max_project}L meets ₹{required_project_value}L requirement"
            })
            breakdown["past_project"] = DEDUCTIONS["past_project"]
        else:
            gaps.append({
                "field":    "Past Project Value",
                "required": f"₹{required_project_value}L (single project)",
                "actual":   f"₹{company_max_project}L (highest single project)",
                "severity": MAJOR,
                "deduction": DEDUCTIONS["past_project"],
                "note": (
                    "Lack of qualifying past projects is a major weakness. "
                    "Consider highlighting similar work, even from different sectors."
                )
            })
            deducted += DEDUCTIONS["past_project"]
            breakdown["past_project"] = 0
    else:
        breakdown["past_project"] = DEDUCTIONS["past_project"]


    # ── Rule 5: Document Readiness ────────────────────────────
    required_docs  = set(tender_data.get("documents_required", []))
    available_docs = set(company_data.get("available_documents", []))

    if required_docs:
        missing_docs = []
        for doc in required_docs:
            # Fuzzy match: check if any available doc contains the required doc keyword
            found = any(
                doc.lower() in avail.lower() or avail.lower() in doc.lower()
                for avail in available_docs
            )
            if not found:
                missing_docs.append(doc)

        if missing_docs:
            fraction_missing = len(missing_docs) / len(required_docs)
            deduction        = DEDUCTIONS["documents"] * fraction_missing

            gaps.append({
                "field":   "Document Readiness",
                "missing": missing_docs,
                "severity": MINOR if fraction_missing < 0.5 else MAJOR,
                "deduction": round(deduction, 1),
                "note": (
                    "Some required documents are not listed as available. "
                    "Gather these before bid submission."
                )
            })
            deducted += deduction
            breakdown["documents"] = round(DEDUCTIONS["documents"] - deduction, 1)
        else:
            met_criteria.append({
                "field": "Document Readiness",
                "detail": "✓ All required documents appear to be available"
            })
            breakdown["documents"] = DEDUCTIONS["documents"]
    else:
        breakdown["documents"] = DEDUCTIONS["documents"]


    # ── MSME Preference Bonus ─────────────────────────────────
    msme_preference = eligibility.get("msme_preference", False)
    msme_category   = company_data.get("msme_category", "")
    msme_bonus      = 0

    if msme_preference and msme_category:
        msme_bonus = 5
        met_criteria.append({
            "field": "MSME Preference",
            "detail": f"✓ Tender has MSME preference, company is registered as {msme_category} enterprise"
        })


    # ── Final Score ───────────────────────────────────────────
    raw_score = 100.0 - deducted + msme_bonus
    score     = max(0.0, min(105.0, raw_score))    # Allow up to 105 with MSME bonus

    verdict = _determine_verdict(score, gaps)
    recommendations = _generate_recommendations(gaps, eligibility, company_data)

    return {
        "score":           round(score, 1),
        "verdict":         verdict,
        "gaps":            gaps,
        "met_criteria":    met_criteria,
        "recommendations": recommendations,
        "breakdown":       breakdown,
        "msme_bonus":      msme_bonus,
    }


def _determine_verdict(score: float, gaps: List[Dict]) -> str:
    """Determine overall eligibility verdict."""
    has_disqualifying = any(g["severity"] == DISQUALIFYING for g in gaps)

    if has_disqualifying:
        if score >= 60:
            return "CONDITIONALLY INELIGIBLE"    # Could qualify with fixes
        return "INELIGIBLE"

    if score >= 80:
        return "ELIGIBLE"
    elif score >= 60:
        return "LIKELY ELIGIBLE"
    elif score >= 40:
        return "BORDERLINE"
    else:
        return "INELIGIBLE"


def _generate_recommendations(
    gaps: List[Dict],
    eligibility: Dict,
    company_data: Dict
) -> List[str]:
    """Generate specific, actionable recommendations for each gap."""
    recs = []

    for gap in gaps:
        field = gap.get("field", "")

        if "Turnover" in field:
            recs.append(
                "📊 Turnover Gap: Consider forming a consortium or joint venture (JV) "
                "with another eligible company. Under GFR Rule 160, JV turnover is "
                "typically aggregated for eligibility purposes."
            )
            recs.append(
                "📋 Alternative: Check if the tender allows NSIC/MSME exemption on "
                "turnover criteria — many central government tenders exempt MSMEs "
                "from turnover requirements up to certain contract values."
            )

        elif "Experience" in field:
            recs.append(
                "🏆 Experience Gap: Document any projects that are even partially related "
                "to the tender scope. Reframe experience from adjacent sectors if applicable. "
                "Check if apprenticeship/sub-contract experience counts under tender rules."
            )

        elif "Certification" in field:
            missing = gap.get("missing", [])
            for cert in missing:
                if "ISO" in cert:
                    recs.append(
                        f"📜 Certification: Obtain {cert} through a BIS-accredited certification body. "
                        "Fast-track ISO certification typically takes 4–8 weeks and costs ₹25,000–₹80,000. "
                        "Bodies: TÜV SÜD, Bureau Veritas, DNV."
                    )
                elif "MSME" in cert or "Udyam" in cert:
                    recs.append(
                        "📜 Udyam Registration: Register at udyamregistration.gov.in — it's free, "
                        "instant, and based on Aadhaar. This is critical for accessing MSME benefits."
                    )
                elif "GeM" in cert:
                    recs.append(
                        "🛒 GeM Registration: Register as a seller at gem.gov.in. "
                        "It's free and enables direct access to government procurement opportunities."
                    )
                else:
                    recs.append(
                        f"📜 Certification: Pursue {cert} through the relevant regulatory body "
                        "before bid submission."
                    )

        elif "Past Project" in field:
            recs.append(
                "🏗️ Project Experience: If direct experience is lacking, explore sub-contracting "
                "to a prime bidder who qualifies, then bid independently once you have qualifying projects. "
                "Alternatively, form a JV with a company that has the required project experience."
            )

        elif "Document" in field:
            missing_docs = gap.get("missing", [])
            recs.append(
                f"📁 Documents: Gather missing documents before bid submission: "
                f"{', '.join(missing_docs)}. "
                "Most documents like audited balance sheets, IT returns, and registration "
                "certificates should be collected 2–3 weeks before the deadline."
            )

    if not recs:
        recs.append(
            "✅ Company appears to meet all major eligibility criteria. "
            "Focus on preparing a strong technical bid with well-documented past projects "
            "and a competitive financial proposal."
        )

    return recs
