"""STAC search tools and LLM tool schemas."""

import json
import logging

import requests
from pystac_client import Client

logger = logging.getLogger(__name__)


def search_stac_items(
    catalog_url,
    collections=None,
    bbox=None,
    datetime_range=None,
    query=None,
    max_items=10,
):
    """Search for items in a STAC catalog.

    Args:
        catalog_url: STAC API endpoint URL.
        collections: List of collection IDs to search.
        bbox: Bounding box as [west, south, east, north] in WGS84 degrees.
        datetime_range: ISO 8601 date or range string, e.g. "2024-01-01/2024-01-31".
        query: Property filters, e.g. {"eo:cloud_cover": {"lt": 20}}.
        max_items: Maximum number of items to return.

    Returns:
        JSON string with search results.
    """
    try:
        bbox = _parse_list(bbox)
        collections = _parse_list(collections)
        if isinstance(max_items, str):
            max_items = int(max_items)

        client = Client.open(catalog_url)

        search_kwargs = {"max_items": max_items}
        if collections:
            search_kwargs["collections"] = collections
        if bbox:
            search_kwargs["bbox"] = bbox
        if datetime_range:
            search_kwargs["datetime"] = datetime_range
        if query:
            if isinstance(query, str):
                query = json.loads(query)
            search_kwargs["query"] = query

        search = client.search(**search_kwargs)
        items = []
        for item in search.items():
            assets = {}
            for key, asset in item.assets.items():
                assets[key] = {
                    "title": asset.title or key,
                    "type": asset.media_type,
                    "href": asset.href,
                }

            properties = {}
            for prop in [
                "eo:cloud_cover",
                "platform",
                "instruments",
                "gsd",
                "datetime",
                "created",
                "updated",
            ]:
                if prop in item.properties:
                    properties[prop] = item.properties[prop]

            items.append(
                {
                    "id": item.id,
                    "collection": item.collection_id,
                    "datetime": item.datetime.isoformat() if item.datetime else None,
                    "bbox": list(item.bbox) if item.bbox else None,
                    "geometry": item.geometry,
                    "properties": properties,
                    "assets": assets,
                }
            )

        return json.dumps(
            {"count": len(items), "items": items},
            indent=2,
            default=str,
        )
    except Exception as e:
        logger.exception("Error searching STAC items")
        return json.dumps({"error": str(e)})


def list_collections(catalog_url, keyword=None):
    """List available collections in a STAC catalog.

    Args:
        catalog_url: STAC API endpoint URL.
        keyword: Optional keyword to filter collections by id, title,
            or description (case-insensitive).

    Returns:
        JSON string with collection summaries.
    """
    try:
        client = Client.open(catalog_url)
        results = []
        for collection in client.get_collections():
            if keyword:
                keyword_lower = keyword.lower()
                searchable = " ".join(
                    filter(
                        None,
                        [
                            collection.id,
                            collection.title or "",
                            collection.description or "",
                        ],
                    )
                ).lower()
                if keyword_lower not in searchable:
                    continue

            temporal = None
            spatial = None
            if collection.extent:
                if collection.extent.temporal and collection.extent.temporal.intervals:
                    interval = collection.extent.temporal.intervals[0]
                    temporal = [i.isoformat() if i else None for i in interval]
                if collection.extent.spatial and collection.extent.spatial.bboxes:
                    spatial = list(collection.extent.spatial.bboxes[0])

            description = collection.description or ""
            if len(description) > 200:
                description = description[:200] + "..."

            results.append(
                {
                    "id": collection.id,
                    "title": collection.title,
                    "description": description,
                    "temporal_extent": temporal,
                    "spatial_extent": spatial,
                }
            )

        return json.dumps(
            {"count": len(results), "collections": results},
            indent=2,
            default=str,
        )
    except Exception as e:
        logger.exception("Error listing collections")
        return json.dumps({"error": str(e)})


def get_collection_info(catalog_url, collection_id):
    """Get detailed information about a specific STAC collection.

    Args:
        catalog_url: STAC API endpoint URL.
        collection_id: The collection identifier.

    Returns:
        JSON string with full collection details.
    """
    try:
        client = Client.open(catalog_url)
        collection = client.get_collection(collection_id)

        temporal = None
        spatial = None
        if collection.extent:
            if collection.extent.temporal and collection.extent.temporal.intervals:
                interval = collection.extent.temporal.intervals[0]
                temporal = [i.isoformat() if i else None for i in interval]
            if collection.extent.spatial and collection.extent.spatial.bboxes:
                spatial = list(collection.extent.spatial.bboxes[0])

        summaries = {}
        if collection.summaries:
            for key, summary in collection.summaries.lists.items():
                summaries[key] = summary

        item_assets = {}
        extra_fields = collection.extra_fields or {}
        if "item_assets" in extra_fields:
            for key, asset_def in extra_fields["item_assets"].items():
                item_assets[key] = {
                    "title": asset_def.get("title", key),
                    "type": asset_def.get("type"),
                    "description": asset_def.get("description", ""),
                }

        result = {
            "id": collection.id,
            "title": collection.title,
            "description": collection.description,
            "license": collection.license,
            "temporal_extent": temporal,
            "spatial_extent": spatial,
            "keywords": collection.keywords or [],
            "providers": [
                {"name": p.name, "roles": p.roles} for p in (collection.providers or [])
            ],
            "summaries": summaries,
            "item_assets": item_assets,
        }

        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.exception("Error getting collection info")
        return json.dumps({"error": str(e)})


def geocode_location(location_name):
    """Geocode a location name to coordinates using OpenStreetMap Nominatim.

    Args:
        location_name: Place name to geocode, e.g. "San Francisco" or
            "Amazon rainforest".

    Returns:
        JSON string with name, bbox [west, south, east, north], and
        center [lon, lat].
    """
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location_name,
                "format": "json",
                "limit": 1,
            },
            headers={"User-Agent": "agentic-stac/0.1"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return json.dumps({"error": f"Location not found: {location_name}"})

        place = data[0]
        bbox = place.get("boundingbox", [])
        if bbox:
            # Nominatim returns [south, north, west, east] as strings
            south, north, west, east = [float(x) for x in bbox]
            bbox = [west, south, east, north]
        else:
            bbox = None

        return json.dumps(
            {
                "name": place.get("display_name", location_name),
                "bbox": bbox,
                "center": [float(place["lon"]), float(place["lat"])],
            },
            indent=2,
        )
    except Exception as e:
        logger.exception("Error geocoding location")
        return json.dumps({"error": str(e)})


def _parse_list(value):
    """Parse a value that may be a list or a JSON string representation of a list.

    Args:
        value: A list, a JSON string of a list, or None.

    Returns:
        A list, or None if the input is None or empty.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    if isinstance(value, list) and len(value) == 0:
        return None
    return value


# ---------------------------------------------------------------------------
# Tool schemas in OpenAI format for LiteLLM
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_stac_items",
            "description": (
                "Search for satellite imagery and geospatial data items in a "
                "STAC catalog. Use this to find specific imagery based on "
                "location, time range, collection, and property filters like "
                "cloud cover."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC API endpoint URL.",
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Collection IDs to search, e.g. "
                            "['sentinel-2-l2a', 'landsat-c2-l2']."
                        ),
                    },
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": (
                            "Bounding box as [west, south, east, north] "
                            "in WGS84 decimal degrees."
                        ),
                    },
                    "datetime_range": {
                        "type": "string",
                        "description": (
                            "ISO 8601 date or range, e.g. "
                            "'2024-01-01/2024-01-31' or '2024-06-15'."
                        ),
                    },
                    "query": {
                        "type": "object",
                        "description": (
                            "Property filters, e.g. " "{'eo:cloud_cover': {'lt': 20}}."
                        ),
                    },
                    "max_items": {
                        "type": "integer",
                        "description": (
                            "Maximum number of items to return (default 10)."
                        ),
                    },
                },
                "required": ["catalog_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_collections",
            "description": (
                "List available data collections in a STAC catalog. "
                "Optionally filter by a keyword. Use this to discover what "
                "datasets are available before searching for specific items."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC API endpoint URL.",
                    },
                    "keyword": {
                        "type": "string",
                        "description": (
                            "Optional keyword to filter collections by name "
                            "or description (case-insensitive)."
                        ),
                    },
                },
                "required": ["catalog_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_collection_info",
            "description": (
                "Get detailed information about a specific STAC collection, "
                "including its description, temporal and spatial extent, "
                "available bands, and item assets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC API endpoint URL.",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "The collection identifier.",
                    },
                },
                "required": ["catalog_url", "collection_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": (
                "Convert a location name (city, region, landmark) to "
                "geographic coordinates and bounding box. Use this when "
                "the user mentions a place by name instead of coordinates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": (
                            "Place name to geocode, e.g. 'San Francisco', "
                            "'Amazon rainforest', 'Mount Everest'."
                        ),
                    },
                },
                "required": ["location_name"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "search_stac_items": search_stac_items,
    "list_collections": list_collections,
    "get_collection_info": get_collection_info,
    "geocode_location": geocode_location,
}
