import re
from typing import List, Dict, Tuple

# Expand anytime. Keep canonical names on the left.
COMPANY_ALIASES: Dict[str, List[str]] = {
    "Tesla": ["tesla"],
    "Volvo Cars": ["volvo", "volvo cars"],
    "Polestar": ["polestar"],
    "Volkswagen": ["volkswagen", "vw"],
    "BMW": ["bmw"],
    "Mercedes-Benz": ["mercedes", "mercedes-benz", "daimler"],
    "Toyota": ["toyota"],
    "Honda": ["honda"],
    "Nissan": ["nissan"],
    "Hyundai": ["hyundai"],
    "Kia": ["kia"],
    "Stellantis": ["stellantis", "fiat", "peugeot", "citroen", "jeep", "ram"],
    "Ford": ["ford"],
    "General Motors": ["gm", "general motors", "chevrolet", "cadillac", "buick"],
    "BYD": ["byd"],
    "Geely": ["geely"],
    "SAIC": ["saic", "mg motor", "mg"],
    "Renault": ["renault"],
    "NVIDIA": ["nvidia"],
    "Qualcomm": ["qualcomm"],
    "Mobileye": ["mobileye"],
    "Bosch": ["bosch"],
    "Continental": ["continental", "conti"],
    "ZF": ["zf"],
    "Aptiv": ["aptiv"],
    "Magna": ["magna", "magna international"],
    "CATL": ["catl", "contemporary amperex"],
    "Panasonic": ["panasonic"],
    "LG Energy Solution": ["lg energy solution", "lg es", "lg chem"],
    "Samsung SDI": ["samsung sdi"],
    "Northvolt": ["northvolt"],
    "Rivian": ["rivian"],
    "Lucid": ["lucid", "lucid motors"],
    "XPeng": ["xpeng"],
    "NIO": ["nio"],
}
EXCLUDE_ENTITIES = {
    "BlackRock", "Mubadala", "Goldman Sachs", "Morgan Stanley", "JPMorgan", "JP Morgan",
    "Sequoia", "Andreessen Horowitz", "a16z", "SoftBank", "Tiger Global",
    "TechCrunch", "Reuters", "Bloomberg"

    # Places
    "San Francisco", "Singapore", "US", "UK", "EU",

    # Generic words that slip through
    "Electricity", "Scientific", "Clearly", "She", "New", "First", "Travel",

    # Units/abbreviations that are not companies
    "CO2", "EV", "AI",

    # Orgs you may want to exclude (you can decide)
    "IEA",
}

def _compile_patterns() -> List[Tuple[str, re.Pattern]]:
    patterns = []
    for canonical, aliases in COMPANY_ALIASES.items():
        # Sort aliases longest first to reduce partial matches
        aliases_sorted = sorted(aliases, key=len, reverse=True)
        # Word-boundary-ish matching; allow spaces/hyphens inside aliases
        escaped = []
        for a in aliases_sorted:
            a = a.lower().strip()
            escaped.append(re.escape(a))
        pat = r"(?<![a-z0-9])(" + "|".join(escaped) + r")(?![a-z0-9])"
        patterns.append((canonical, re.compile(pat, re.IGNORECASE)))
    return patterns

_PATTERNS = _compile_patterns()

def extract_companies(title: str, text: str, max_companies: int = 8) -> List[str]:
    hay = f"{title}\n{text}"
    found = []
    for canonical, pat in _PATTERNS:
        if pat.search(hay):
            found.append(canonical)
            if len(found) >= max_companies:
                break

    # Fallback: if no known companies matched, try to infer from title
    if not found:
        found = fallback_from_title(title, max_names=3)

    found = [c for c in found if c not in EXCLUDE_ENTITIES]

    return found

def fallback_from_title(title: str, max_names: int = 3) -> List[str]:
    """
    Heuristic: extract likely company names from the title by capturing capitalized words.
    Examples: "Moove takes in..." -> ["Moove"]
             "Smart bus startup Zeelo..." -> ["Zeelo"]
             "VanMoof makes a move..." -> ["VanMoof"]
    """
    if not title:
        return []

    # Capture sequences of Capitalized words (allow internal caps like VanMoof)
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,2}\b", title)
    # Remove candidates that start with "The " (often section titles: The Equity, The Daily, etc.)
    candidates = [c for c in candidates if not c.startswith("The ")]
    
    lower_title = title.lower()
    startup_context = any(k in lower_title for k in [
        "startup", "raises", "funding", "series", "acquires", "acquired",
        "launches", "secures", "partners", "merger", "valuation"
    ])

    # Filter out common non-company words
    blacklist = {
    "The", "A", "An", "And", "Or", "But", "EU", "US", "UK",
    "EV", "AI", "CEO", "CFO", "IPO", "VC", "VCs", "Series",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December", "Mubadala", "BlackRock"

    # Common non-company words that appear capitalized in headlines
    "Smart", "First", "New", "Latest", "Travel", "Remote", "Equity", "Crew", "Podcast"
    }

    cleaned = []
    for c in candidates:
        c = c.strip()

        # Drop anything that contains quotes-like characters (often not a company name)
        if "‘" in c or "’" in c or "“" in c or "”" in c:
            continue

        # Drop if it is exactly a blacklisted word
        if c in blacklist:
            continue

        # Drop if it is 1 word and looks generic (e.g. Smart)
        if " " not in c and c.lower() in {"smart", "new", "first", "latest", "travel", "remote"}:
            continue

        if len(c) < 3:
            continue

        # before cleaned.append(c)
        if not startup_context and c not in {"Tesla","Toyota","Ford","Volkswagen","BMW","BYD","Hyundai","Kia","NIO","XPeng","CATL"}:
            continue

        cleaned.append(c)


    # Deduplicate while keeping order
    seen = set()
    result = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            result.append(c)
        if len(result) >= max_names:
            break
    return result