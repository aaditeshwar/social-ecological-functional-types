"""core-seft: on-demand analysis of CoRE Stack micro-watersheds, waterbodies, tehsils and districts."""
__version__ = "0.1.0"

from .errors import CacheMiss, CoreSeftError, KnowledgeError, UnknownEntity
from .session import Session, analyse, configure
__all__ = [
    "Session", "analyse", "configure",
    "CacheMiss", "CoreSeftError", "KnowledgeError", "UnknownEntity",
    "__version__",
]
