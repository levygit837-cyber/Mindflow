"""Research-domain worker consumers."""

from .browser_consumer import BrowserTaskConsumer
from .content_consumer import ContentTaskConsumer

__all__ = [
    "BrowserTaskConsumer",
    "ContentTaskConsumer",
]
