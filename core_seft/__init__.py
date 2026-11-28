"""core-seft: on-demand analysis of CoRE Stack micro-watersheds, waterbodies, tehsils and districts."""
__version__ = "0.3.0"

from .errors import CacheMiss, CoreSeftError, KnowledgeError, UnknownEntity
from .session import Session, analyse, configure, predict_impact, site_suitability
__all__ = [
    "Session", "analyse", "configure", "predict_impact", "site_suitability",
    "CacheMiss", "CoreSeftError", "KnowledgeError", "UnknownEntity",
    "__version__",
]
