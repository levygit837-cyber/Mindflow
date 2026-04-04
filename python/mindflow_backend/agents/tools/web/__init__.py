"""Web tools for MindFlow agents."""

from __future__ import annotations

import warnings
from importlib import import_module

from .api_client import ApiClientTool
from .browser_search import BrowserSearchTool
from .http_client import HttpClientTool
from .pinchtab_browser import PinchTabBrowserTool
from .pinchtab_fleet import PinchTabFleetTool
from .web_scraper import WebScraperTool

_COMPAT_EXPORTS = {
    "HttpClientToolV3": (".http_client_v3", "HttpClientToolV3"),
    "WebScraperToolV3": (".web_scraper_v3", "WebScraperToolV3"),
    "ApiClientToolV3": (".api_client_v3", "ApiClientToolV3"),
}

__all__ = [
    "WebScraperTool",
    "HttpClientTool",
    "ApiClientTool",
    "PinchTabFleetTool",
    "PinchTabBrowserTool",
    "BrowserSearchTool",
]


def __getattr__(name: str):
    if name not in _COMPAT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _COMPAT_EXPORTS[name]
    warnings.warn(
        (
            f"{__name__}.{name} is a deprecated compatibility export. "
            f"Import {attr_name} from {__name__}{module_name} instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
