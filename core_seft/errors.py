"""Errors raised by core_seft.Session.analyse."""


class CoreSeftError(Exception):
    """Base class for library errors."""


class CacheMiss(CoreSeftError):
    """Tehsil (or district) cache is incomplete and fetch was False, or fetch could not fill lulc_vector."""


class UnknownEntity(CoreSeftError):
    """State/district/tehsil/uid not in the CoRE Stack list or not in this district's cache."""


class KnowledgeError(CoreSeftError):
    """Knowledge pack missing, incompatible, or below this library's min_library."""
