from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SubscriptionRecommendation:
    kva: int
    label: str
    phase: str
    calibre_edf: str
    justification: str
    reasons: list = field(default_factory=list)
    profile: str = ""
    profile_label: str = ""


@dataclass
class DecisionExplanation:
    rule: str
    value: str
    reason: str


def build_subscription_recommendation(
    kva: int,
    phase: str,
    profile: str,
    profile_label: str,
    reasons: list,
) -> SubscriptionRecommendation:
    from core.business_rules.subscription_rules import SUBSCRIPTION_TIERS
    calibre = next((c for t, _, c in SUBSCRIPTION_TIERS if t == kva), "90A")
    label = f"{kva} kVA"
    parts = [profile_label]
    if reasons:
        parts.append("équipements : " + ", ".join(reasons))
    parts.append(f"abonnement conseillé {kva} kVA")
    if phase == "triphasé":
        parts.append("alimentation triphasée recommandée")
    return SubscriptionRecommendation(
        kva=kva,
        label=label,
        phase=phase,
        calibre_edf=calibre,
        justification=" — ".join(parts),
        reasons=reasons,
        profile=profile,
        profile_label=profile_label,
    )
