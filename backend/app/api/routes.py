"""Compatibility import for deployments that referenced the earlier route path."""

from backend.app.api.router import router

__all__ = ["router"]
