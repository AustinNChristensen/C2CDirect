import re

from .models import C2CStatus, JobPostingIn, ScreenedJob, SearchProfile

C2C_POSITIVE = ("c2c", "corp to corp", "corporation to corporation", "1099/c2c")
C2C_NEGATIVE = ("no c2c", "w2 only", "cannot work c2c", "no third parties")


def screen(posting: JobPostingIn, profile: SearchProfile) -> ScreenedJob:
    text = f"{posting.title} {posting.description}".lower()
    if any(term in text for term in C2C_NEGATIVE):
        status = C2CStatus.rejected
    elif any(term in text for term in C2C_POSITIVE):
        status = C2CStatus.confirmed
    elif "contract" in text:
        status = C2CStatus.likely
    else:
        status = C2CStatus.unknown
    all_skills = profile.core_skills + profile.ai_skills
    matches = [s for s in all_skills if s in text]
    gaps = [s for s in profile.ai_skills if s not in text]
    score = 30 + min(35, len(matches) * 5)
    reasons, risks = [], []
    if status == C2CStatus.confirmed:
        score += 15
        reasons.append("C2C language is explicit")
    elif status == C2CStatus.rejected:
        score -= 45
        risks.append("Posting explicitly rejects C2C")
    elif profile.require_c2c:
        risks.append("C2C must be confirmed with recruiter")
    if posting.rate_max:
        if posting.rate_max >= profile.target_rate:
            score += 15
            reasons.append("Rate reaches target band")
        elif posting.rate_max < profile.min_rate:
            score -= 25
            risks.append("Rate is below configured floor")
    else:
        risks.append("Rate is not disclosed")
    if any(loc.lower() in posting.location.lower() for loc in profile.locations):
        score += 5
    feedback = profile.feedback_penalties
    location_match = any(loc.lower() in posting.location.lower() for loc in profile.locations)
    if feedback.get("location_mismatch", 0) >= 2 and not location_match:
        score -= min(15, feedback["location_mismatch"] * 3)
        risks.append("Your recent decisions frequently reject location mismatches")
    if feedback.get("skill_mismatch", 0) >= 2 and len(matches) < 2:
        score -= min(15, feedback["skill_mismatch"] * 2)
        risks.append("Your recent decisions favor stronger skill overlap")
    if feedback.get("c2c_not_accepted", 0) >= 2 and status not in {
        C2CStatus.confirmed,
        C2CStatus.rejected,
    }:
        score -= min(10, feedback["c2c_not_accepted"] * 2)
        risks.append("Your recent decisions require clearer C2C evidence")
    title = posting.title.lower()
    if (
        profile.seniority_levels
        and not any(level in title for level in profile.seniority_levels)
        and feedback.get("seniority_mismatch", 0) >= 2
    ):
        score -= min(12, feedback["seniority_mismatch"] * 2)
        risks.append("Seniority differs from your learned preference")
    layers = None
    m = re.search(r"(\d+)\s+(?:vendor\s+)?layers?", text)
    if m:
        layers = int(m.group(1))
        score -= max(0, layers - 1) * 5
    score = max(0, min(100, score))
    reasons.extend([f"Matches {s}" for s in matches[:4]])
    action = (
        "Pass"
        if score < 55
        else "Confirm C2C and rate"
        if status != C2CStatus.confirmed
        else "Contact recruiter now"
    )
    return ScreenedJob(
        posting=posting,
        c2c_status=status,
        fit_score=score,
        skill_matches=matches,
        skill_gaps=gaps,
        reasons=reasons,
        risks=risks,
        vendor_layers=layers,
        recommended_action=action,
    )
