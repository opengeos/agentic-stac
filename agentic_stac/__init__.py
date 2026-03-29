"""AI Agents for SpatioTemporal Asset Catalogs (STAC)."""

__author__ = "Qiusheng Wu"
__email__ = "giswqs@gmail.com"
__version__ = "0.1.0"

from agentic_stac.agent import STACAgent
from agentic_stac.catalogs import CATALOGS, resolve_catalog

__all__ = ["STACAgent", "CATALOGS", "resolve_catalog"]
