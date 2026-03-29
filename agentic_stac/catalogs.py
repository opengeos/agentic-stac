"""Pre-configured STAC catalog registry."""

CATALOGS = {
    "planetary-computer": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "pc": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "earth-search": "https://earth-search.aws.element84.com/v1",
    "es": "https://earth-search.aws.element84.com/v1",
    "nasa-cmr": "https://cmr.earthdata.nasa.gov/stac/",
    "cmr": "https://cmr.earthdata.nasa.gov/stac/",
}


def resolve_catalog(catalog):
    """Resolve a catalog alias or URL to a STAC API endpoint URL.

    Args:
        catalog: A catalog alias (e.g., "pc", "earth-search") or a full URL.

    Returns:
        The STAC API endpoint URL string.

    Raises:
        ValueError: If the alias is not recognized and the value does not
            look like a URL.
    """
    if catalog in CATALOGS:
        return CATALOGS[catalog]
    if catalog.startswith("http://") or catalog.startswith("https://"):
        return catalog
    raise ValueError(
        f"Unknown catalog '{catalog}'. Use a URL or one of: "
        f"{', '.join(sorted(set(CATALOGS.values())))}"
    )
