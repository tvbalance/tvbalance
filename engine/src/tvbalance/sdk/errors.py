"""Typed failures shared by the engine and every adapter."""


class TVError(Exception):
    """The TV is unreachable or a command failed."""


class TVPairingError(TVError):
    """The TV is reachable but pairing is required, refused or expired."""


class TVTimeoutError(TVError):
    """A TV call exceeded its hard timeout (raised by the engine, never by adapters)."""


class UnsupportedCapabilityError(TVError):
    """The adapter does not declare the capability needed for this call."""
