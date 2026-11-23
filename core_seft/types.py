"""Result objects returned by core_seft.analyse."""
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


def _dict(o):
    return asdict(o) if hasattr(o, '__dataclass_fields__') else o


@dataclass
class AnalyseResult:
    kind: str
    state: str
    district: str
    library_version: str
    knowledge_version: str
    tehsil: Optional[str] = None
    uid: Optional[str] = None
    identity: dict = field(default_factory=dict)
    context: Any = None
    mix: Any = None
    mix_before: Any = None
    notes: list = field(default_factory=list)
    observed_stresses: list = field(default_factory=list)
    pathways: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    schemes: list = field(default_factory=list)
    interventions: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    commons_connect: list = field(default_factory=list)
    villages: list = field(default_factory=list)
    production_systems: list = field(default_factory=list)
    must_ask_summary: dict = field(default_factory=dict)
    answers_applied: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    diff: Optional[dict] = None
    # waterbody
    type: Optional[str] = None
    status: Optional[str] = None
    roles: dict = field(default_factory=dict)
    # district / tehsil
    tehsils: list = field(default_factory=list)
    waterbodies: Optional[dict] = None

    def to_dict(self):
        keep_empty = {
            'kind', 'state', 'district', 'library_version', 'knowledge_version',
            'questions', 'answers_applied', 'notes', 'interventions', 'schemes',
        }
        return {k: v for k, v in asdict(self).items() if k in keep_empty or v not in (None, [], {})}
