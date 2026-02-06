import re
from collections import defaultdict


CATEGORY_KEYWORDS = {
    "EV": ["ev", "electric", "electrification", "charging", "charger", "range", "megawatt", "mcs"],
    "Battery": ["battery", "cells", "cell", "lithium", "lfp", "nmc", "solid-state", "anode", "cathode", "gigafactory"],
    "Autonomy": ["autonomous", "self-driving", "adas", "lidar", "camera", "radar", "robotaxi", "fisd", "level 2", "level 3", "level 4"],
    "Software": ["software-defined", "sdv", "ota", "over-the-air", "infotainment", "middleware", "cybersecurity", "linux"],
    "OEM": ["oem", "volkswagen", "vw", "toyota", "gm", "ford", "stellantis", "bmw", "mercedes", "volvo", "tesla", "byd", "geely"],
    "SupplyChain": ["supplier", "tier 1", "tier1", "semiconductor", "chip", "logistics", "shortage", "inventory", "raw materials"],
    "Policy": ["regulation", "eu", "ban", "tariff", "subsidy", "incentive", "compliance", "emissions", "carbon", "epa"],
    "Startups": ["startup", "funding", "series a", "series b", "venture", "seed", "acquisition"],
    "Manufacturing": ["plant", "factory", "production", "line", "capacity", "shutdown", "automation", "robotics"]
}


def pick_category(title: str, text: str, fallback_categories=None) -> str:
    hay = f"{title}\n{text}".lower()
    scores = defaultdict(int)

    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if re.search(r"\b" + re.escape(kw) + r"\b", hay):
                scores[cat] += 1

    if scores:
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[0][0]

    # fallback: use first category from source config if present
    if fallback_categories:
        return fallback_categories[0]

    return "General"