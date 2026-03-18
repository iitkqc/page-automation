import re

DEFAULT_CATEGORY = "campus_life"

IITK_CONTENT_CATEGORIES = [
    "hall_politics",
    "mess_disaster",
    "placement_meltdown",
    "exam_endsem_panic",
    "prof_moment",
    "lab_assignment_suffering",
    "secret_crush",
    "wing_nostalgia",
    "fest_energy",
    "cdc_intern_chaos",
    "convocation_feels",
    "campus_lore",
    "campus_life",
]

CATEGORY_DISPLAY_NAMES = {
    "hall_politics": "Hall Politics",
    "mess_disaster": "Mess Disaster",
    "placement_meltdown": "Placement Meltdown",
    "exam_endsem_panic": "Endsem Panic",
    "prof_moment": "Prof Moment",
    "lab_assignment_suffering": "Lab Suffering",
    "secret_crush": "Secret Crush",
    "wing_nostalgia": "Wing Nostalgia",
    "fest_energy": "Fest Energy",
    "cdc_intern_chaos": "CDC Chaos",
    "convocation_feels": "Convocation Feels",
    "campus_lore": "Campus Lore",
    "campus_life": "Campus Life",
}

CATEGORY_SERIES_LABELS = {
    "hall_politics": "Hall Files",
    "mess_disaster": "Mess Court",
    "placement_meltdown": "Placement Spiral",
    "exam_endsem_panic": "Endsem Emergency",
    "prof_moment": "Prof Files",
    "lab_assignment_suffering": "Lab Damage",
    "secret_crush": "Campus Crush",
    "wing_nostalgia": "Wing Archives",
    "fest_energy": "Fest Mode",
    "cdc_intern_chaos": "CDC Spiral",
    "convocation_feels": "Last Lap",
    "campus_lore": "Campus Lore",
    "campus_life": "Campus Mood",
}

CATEGORY_FOOTERS = {
    "hall_politics": "Hall politics, now on the timeline.",
    "mess_disaster": "Mess menu discourse never really ends.",
    "placement_meltdown": "Placement pressure has entered the chat.",
    "exam_endsem_panic": "Campus stress, fully invigilated.",
    "prof_moment": "Another prof story for the archives.",
    "lab_assignment_suffering": "Lab pain with attendance attached.",
    "secret_crush": "Campus romance, zero attendance grace.",
    "wing_nostalgia": "Wing memories hit harder after midnight.",
    "fest_energy": "Peak fest energy, zero chill.",
    "cdc_intern_chaos": "Intern season: calm outside, chaos inside.",
    "convocation_feels": "Campus endings always sneak up on you.",
    "campus_lore": "Another IITK legend in the making.",
    "campus_life": "One slide. Pure campus energy.",
}

CATEGORY_INTRO_FALLBACKS = {
    "hall_politics": "Hall politics just made the feed.",
    "mess_disaster": "Mess disaster report, live from campus.",
    "placement_meltdown": "Placement pressure is peaking again.",
    "exam_endsem_panic": "Endsem panic, now in public.",
    "prof_moment": "A prof moment worth preserving.",
    "lab_assignment_suffering": "Fresh assignment suffering from IITK.",
    "secret_crush": "This crush did not stay secret.",
    "wing_nostalgia": "Wing nostalgia just hit.",
    "fest_energy": "Fest energy has entered the chat.",
    "cdc_intern_chaos": "CDC chaos, straight from the timeline.",
    "convocation_feels": "Convocation feelings are getting real.",
    "campus_lore": "Campus lore found a new chapter.",
    "campus_life": "A campus confession worth reading.",
}

_ALIASES = {
    "hall politics": "hall_politics",
    "hall drama": "hall_politics",
    "hostel politics": "hall_politics",
    "mess disaster": "mess_disaster",
    "mess rant": "mess_disaster",
    "mess food": "mess_disaster",
    "placement meltdown": "placement_meltdown",
    "placement panic": "placement_meltdown",
    "placement stress": "placement_meltdown",
    "exam panic": "exam_endsem_panic",
    "endsem panic": "exam_endsem_panic",
    "exam endsem panic": "exam_endsem_panic",
    "exam stress": "exam_endsem_panic",
    "prof moment": "prof_moment",
    "prof story": "prof_moment",
    "lab assignment suffering": "lab_assignment_suffering",
    "assignment suffering": "lab_assignment_suffering",
    "lab suffering": "lab_assignment_suffering",
    "secret crush": "secret_crush",
    "crush": "secret_crush",
    "wing nostalgia": "wing_nostalgia",
    "hostel nostalgia": "wing_nostalgia",
    "fest energy": "fest_energy",
    "fest": "fest_energy",
    "cdc intern chaos": "cdc_intern_chaos",
    "cdc chaos": "cdc_intern_chaos",
    "intern chaos": "cdc_intern_chaos",
    "convocation feels": "convocation_feels",
    "campus legend": "campus_lore",
    "campus lore": "campus_lore",
    "campus legend lore": "campus_lore",
    "campus life": "campus_life",
}


def _clean_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_category(category: str | None) -> str:
    cleaned = _clean_key(category)
    if not cleaned:
        return DEFAULT_CATEGORY

    if cleaned in _ALIASES:
        return _ALIASES[cleaned]

    if "hall" in cleaned or "hostel" in cleaned or "wing politics" in cleaned:
        return "hall_politics"
    if "mess" in cleaned or "canteen" in cleaned:
        return "mess_disaster"
    if "placement" in cleaned:
        return "placement_meltdown"
    if "exam" in cleaned or "endsem" in cleaned or "midsem" in cleaned:
        return "exam_endsem_panic"
    if "prof" in cleaned or "faculty" in cleaned:
        return "prof_moment"
    if "lab" in cleaned or "assignment" in cleaned or "submission" in cleaned:
        return "lab_assignment_suffering"
    if "crush" in cleaned or "romance" in cleaned or "love" in cleaned:
        return "secret_crush"
    if "wing" in cleaned or "nostalgia" in cleaned or "hostel memory" in cleaned:
        return "wing_nostalgia"
    if "fest" in cleaned or "antaragni" in cleaned or "udghosh" in cleaned:
        return "fest_energy"
    if "cdc" in cleaned or "intern" in cleaned:
        return "cdc_intern_chaos"
    if "convocation" in cleaned or "farewell" in cleaned or "graduation" in cleaned:
        return "convocation_feels"
    if "legend" in cleaned or "lore" in cleaned:
        return "campus_lore"

    return DEFAULT_CATEGORY


def get_category_display_name(category: str | None) -> str:
    normalized = normalize_category(category)
    return CATEGORY_DISPLAY_NAMES.get(normalized, CATEGORY_DISPLAY_NAMES[DEFAULT_CATEGORY])


def get_category_series_label(category: str | None) -> str:
    normalized = normalize_category(category)
    return CATEGORY_SERIES_LABELS.get(normalized, CATEGORY_SERIES_LABELS[DEFAULT_CATEGORY])


def get_category_footer(category: str | None) -> str:
    normalized = normalize_category(category)
    return CATEGORY_FOOTERS.get(normalized, CATEGORY_FOOTERS[DEFAULT_CATEGORY])


def get_category_intro_fallback(category: str | None) -> str:
    normalized = normalize_category(category)
    return CATEGORY_INTRO_FALLBACKS.get(normalized, CATEGORY_INTRO_FALLBACKS[DEFAULT_CATEGORY])
