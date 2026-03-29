"""Integration tests for STAC tools.

These tests hit real STAC APIs and the Nominatim geocoding service.
They require network access.
"""

import json

import pytest

from agentic_stac.tools import (
    TOOL_DISPATCH,
    TOOLS,
    geocode_location,
    get_collection_info,
    list_collections,
    search_stac_items,
)

EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1"


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------


class TestGeocodeLocation:
    """Tests for the geocode_location tool."""

    def test_geocode_known_city(self):
        """Geocode a well-known city and check bbox format."""
        result = json.loads(geocode_location("San Francisco"))
        assert "bbox" in result
        assert "center" in result
        assert len(result["bbox"]) == 4
        west, south, east, north = result["bbox"]
        assert west < east
        assert south < north

    def test_geocode_returns_name(self):
        """The result includes a display name."""
        result = json.loads(geocode_location("Paris, France"))
        assert "name" in result
        assert "Paris" in result["name"]

    def test_geocode_unknown_location(self):
        """An unrecognizable location returns an error."""
        result = json.loads(geocode_location("xyznonexistentplace12345"))
        assert "error" in result


# ---------------------------------------------------------------------------
# list_collections
# ---------------------------------------------------------------------------


class TestListCollections:
    """Tests for the list_collections tool."""

    def test_list_all_collections(self):
        """List all collections from Earth Search."""
        result = json.loads(list_collections(EARTH_SEARCH_URL))
        assert "count" in result
        assert result["count"] > 0
        assert "collections" in result

        collection = result["collections"][0]
        assert "id" in collection
        assert "title" in collection

    def test_filter_by_keyword(self):
        """Filter collections by keyword."""
        result = json.loads(list_collections(EARTH_SEARCH_URL, keyword="sentinel"))
        assert result["count"] > 0
        for c in result["collections"]:
            searchable = f"{c['id']} {c['title']} {c['description']}".lower()
            assert "sentinel" in searchable

    def test_filter_no_match(self):
        """A keyword that matches nothing returns zero collections."""
        result = json.loads(
            list_collections(EARTH_SEARCH_URL, keyword="xyznonexistent")
        )
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# get_collection_info
# ---------------------------------------------------------------------------


class TestGetCollectionInfo:
    """Tests for the get_collection_info tool."""

    def test_get_sentinel2_info(self):
        """Get info for sentinel-2-l2a collection."""
        result = json.loads(get_collection_info(EARTH_SEARCH_URL, "sentinel-2-l2a"))
        assert result["id"] == "sentinel-2-l2a"
        assert result["title"] is not None
        assert result["temporal_extent"] is not None
        assert result["spatial_extent"] is not None

    def test_get_nonexistent_collection(self):
        """A nonexistent collection returns an error."""
        result = json.loads(
            get_collection_info(EARTH_SEARCH_URL, "nonexistent-collection")
        )
        assert "error" in result


# ---------------------------------------------------------------------------
# search_stac_items
# ---------------------------------------------------------------------------


class TestSearchStacItems:
    """Tests for the search_stac_items tool."""

    def test_search_with_bbox_and_datetime(self):
        """Search Sentinel-2 with bbox and datetime range."""
        result = json.loads(
            search_stac_items(
                catalog_url=EARTH_SEARCH_URL,
                collections=["sentinel-2-l2a"],
                bbox=[-122.5, 37.7, -122.3, 37.8],
                datetime_range="2024-01-01/2024-06-30",
                max_items=3,
            )
        )
        assert "count" in result
        assert result["count"] > 0
        assert result["count"] <= 3

        item = result["items"][0]
        assert "id" in item
        assert "collection" in item
        assert "datetime" in item
        assert "bbox" in item
        assert "assets" in item
        assert "properties" in item

    def test_search_with_cloud_cover_query(self):
        """Search with cloud cover filter."""
        result = json.loads(
            search_stac_items(
                catalog_url=EARTH_SEARCH_URL,
                collections=["sentinel-2-l2a"],
                bbox=[-122.5, 37.7, -122.3, 37.8],
                datetime_range="2024-01-01/2024-12-31",
                query={"eo:cloud_cover": {"lt": 5}},
                max_items=5,
            )
        )
        assert result["count"] > 0
        for item in result["items"]:
            cloud_cover = item["properties"].get("eo:cloud_cover")
            if cloud_cover is not None:
                assert cloud_cover < 5

    def test_search_no_results(self):
        """A very restrictive search returns zero items."""
        result = json.loads(
            search_stac_items(
                catalog_url=EARTH_SEARCH_URL,
                collections=["sentinel-2-l2a"],
                bbox=[0.0, 0.0, 0.001, 0.001],
                datetime_range="2000-01-01/2000-01-02",
                max_items=1,
            )
        )
        assert result["count"] == 0

    def test_search_string_bbox(self):
        """Handle bbox passed as a JSON string (LLM sometimes does this)."""
        result = json.loads(
            search_stac_items(
                catalog_url=EARTH_SEARCH_URL,
                collections=["sentinel-2-l2a"],
                bbox="[-122.5, 37.7, -122.3, 37.8]",
                datetime_range="2024-01-01/2024-01-31",
                max_items=2,
            )
        )
        assert "count" in result
        assert "error" not in result

    def test_search_catalog_only(self):
        """Search with only catalog_url (no filters) returns items."""
        result = json.loads(
            search_stac_items(
                catalog_url=EARTH_SEARCH_URL,
                max_items=2,
            )
        )
        assert result["count"] > 0


# ---------------------------------------------------------------------------
# Tool schema validation
# ---------------------------------------------------------------------------


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_all_tools_have_schemas(self):
        """Every dispatched tool has a corresponding schema."""
        schema_names = {t["function"]["name"] for t in TOOLS}
        dispatch_names = set(TOOL_DISPATCH.keys())
        assert schema_names == dispatch_names

    def test_tools_have_required_fields(self):
        """Each tool schema has name, description, and parameters."""
        for tool in TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_dispatch_functions_are_callable(self):
        """All dispatch entries are callable."""
        for name, fn in TOOL_DISPATCH.items():
            assert callable(fn), f"{name} is not callable"
