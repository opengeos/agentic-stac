"""Tests for the catalog registry."""

import pytest

from agentic_stac.catalogs import CATALOGS, resolve_catalog


def test_resolve_known_alias():
    """Resolve a known alias to its URL."""
    assert resolve_catalog("pc") == CATALOGS["pc"]
    assert resolve_catalog("planetary-computer") == CATALOGS["planetary-computer"]


def test_resolve_earth_search():
    """Resolve earth-search aliases."""
    url = "https://earth-search.aws.element84.com/v1"
    assert resolve_catalog("earth-search") == url
    assert resolve_catalog("es") == url


def test_resolve_nasa_cmr():
    """Resolve NASA CMR aliases."""
    url = "https://cmr.earthdata.nasa.gov/stac/"
    assert resolve_catalog("nasa-cmr") == url
    assert resolve_catalog("cmr") == url


def test_resolve_custom_url():
    """Pass through a custom STAC API URL."""
    url = "https://my-stac.example.com/api/v1"
    assert resolve_catalog(url) == url


def test_resolve_http_url():
    """Pass through an http URL."""
    url = "http://localhost:8080/stac"
    assert resolve_catalog(url) == url


def test_resolve_unknown_alias_raises():
    """Raise ValueError for an unknown alias that is not a URL."""
    with pytest.raises(ValueError, match="Unknown catalog"):
        resolve_catalog("nonexistent-catalog")


def test_aliases_point_to_same_urls():
    """Short and long aliases resolve to the same URL."""
    assert CATALOGS["pc"] == CATALOGS["planetary-computer"]
    assert CATALOGS["es"] == CATALOGS["earth-search"]
    assert CATALOGS["cmr"] == CATALOGS["nasa-cmr"]
