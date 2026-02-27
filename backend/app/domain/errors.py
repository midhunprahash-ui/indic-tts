from __future__ import annotations


class AdapterError(Exception):
    """Base exception for adapter-level failures."""


class NotConfiguredError(AdapterError):
    """Raised when credentials/configuration are missing."""


class ProviderAuthError(AdapterError):
    """Raised when a provider rejects credentials."""


class ModelUnavailableError(AdapterError):
    """Raised when a model or endpoint cannot be used."""


class DependencyMissingError(AdapterError):
    """Raised when an optional runtime dependency is absent."""


class AdapterTimeoutError(AdapterError):
    """Raised when adapter execution exceeds configured timeout."""
