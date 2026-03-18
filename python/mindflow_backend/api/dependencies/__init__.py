"""Shared FastAPI dependencies for the API layer."""

from .security import protected_route_dependencies

__all__ = ["protected_route_dependencies"]
