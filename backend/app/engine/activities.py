from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityRule:
    key: str
    label: str
    # Each dict is an OR alternative; all listed tags in an alternative must match.
    tag_alternatives: tuple[dict[str, frozenset[str]], ...]
    comfortable_temperature_c: tuple[float, float]
    max_wind_kmh: float
    max_precipitation_probability: float


def _tags(**items: str | tuple[str, ...]) -> dict[str, frozenset[str]]:
    return {key: frozenset(value if isinstance(value, tuple) else (value,)) for key, value in items.items()}


ACTIVITY_RULES: dict[str, ActivityRule] = {
    "running": ActivityRule("running", "Running / jogging", (
        _tags(sport="running"), _tags(leisure="track"), _tags(leisure="park"), _tags(highway=("path", "track")),
    ), (10, 25), 25, 50),
    "cycling": ActivityRule("cycling", "Cycling", (
        _tags(highway="cycleway"), _tags(route="bicycle"), _tags(sport="cycling"),
    ), (8, 28), 30, 40),
    "golf": ActivityRule("golf", "Golf", (
        _tags(leisure="golf_course"), _tags(sport="golf"),
    ), (10, 28), 25, 35),
    "cricket": ActivityRule("cricket", "Cricket", (
        _tags(sport="cricket"), _tags(leisure="pitch", sport="cricket"),
    ), (12, 30), 28, 35),
    "football": ActivityRule("football", "Outdoor football / five-a-side", (
        _tags(sport=("football", "soccer")), _tags(leisure="pitch", sport=("football", "soccer")),
    ), (10, 28), 30, 40),
    "tennis": ActivityRule("tennis", "Outdoor tennis", (
        _tags(sport="tennis"), _tags(leisure="pitch", sport="tennis"),
    ), (10, 28), 25, 35),
    "hiking": ActivityRule("hiking", "Hiking / nature walk", (
        _tags(route="hiking"), _tags(highway=("path", "track", "bridleway")),
        _tags(leisure="nature_reserve"), _tags(natural=("wood", "peak", "heath")),
    ), (8, 26), 35, 45),
    "picnic": ActivityRule("picnic", "Picnic / park outing", (
        _tags(tourism="picnic_site"), _tags(leisure=("park", "garden", "recreation_ground")),
    ), (15, 30), 22, 30),
    "outdoor_event": ActivityRule("outdoor_event", "Outdoor event / gathering", (
        _tags(amenity="events_venue"), _tags(leisure=("park", "recreation_ground", "stadium")),
    ), (15, 30), 25, 25),
    "photography": ActivityRule("photography", "Outdoor photography", (
        _tags(tourism="viewpoint"), _tags(natural=("peak", "waterfall", "beach")),
        _tags(leisure="park"),
    ), (5, 32), 35, 50),
}


def classify_venue(activity: str, tags: dict[str, str]) -> bool:
    """Match an activity using OSM tags only; names are never used for classification."""
    rule = ACTIVITY_RULES.get(activity)
    if rule is None:
        return False
    normalized = {str(key).casefold(): str(value).casefold() for key, value in tags.items()}
    return any(
        all(normalized.get(key) in accepted_values for key, accepted_values in alternative.items())
        for alternative in rule.tag_alternatives
    )


def matching_activities(tags: dict[str, str]) -> list[str]:
    return [activity for activity in ACTIVITY_RULES if classify_venue(activity, tags)]
