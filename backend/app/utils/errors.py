class ProviderError(Exception):
    """Raised when an external data provider fails."""


class AgentError(Exception):
    """Raised when an analysis agent cannot produce a valid result."""
