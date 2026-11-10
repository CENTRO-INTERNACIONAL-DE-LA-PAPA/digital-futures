"""Graph state. Plain dicts and lists only, so checkpoints stay portable JSON."""

from operator import add
from typing import Annotated, Literal, NotRequired, TypedDict

Steeple = Literal["social", "technological", "economic", "environmental", "political", "legal", "ethical"]


class Source(TypedDict):
    title: str
    url: str


class Scope(TypedDict):
    theme: str
    geography: str
    current_year: int
    horizon_year: int
    seed_drivers: list[str]  # drivers humans bring in before the run (e.g. from a workshop)
    target_drivers: int


class Driver(TypedDict):
    id: str
    name: str
    description: str
    steeple: Steeple
    sources: list[Source]


class Cluster(TypedDict):
    name: str
    rationale: str
    driver_ids: list[str]


class Score(TypedDict):
    driver_id: str
    impact: int  # 1-5
    uncertainty: int  # 1-5
    policy_attention: NotRequired[int]  # 1-5, added in the second scoring pass
    evidence: str


class Axis(TypedDict):
    driver_id: str
    pole_a: str
    pole_b: str


class AxisSet(TypedDict):
    name: str
    x: Axis
    y: Axis


class Quadrant(TypedDict):
    axis_set: str
    x_pole: str
    y_pole: str
    title: str
    sketch: str


class Narrative(TypedDict):
    quadrant: str
    title: str
    personas: dict[str, str]  # persona -> text


class Review(TypedDict):
    step: str
    action: Literal["approve", "edit", "revise"]
    feedback: str
    at: str  # ISO timestamp, for time-to-scenario metrics


class State(TypedDict, total=False):
    scope: Scope
    hitl: bool  # False: reviews auto-approve (Solo AI arm)
    feedback: str | None  # pending revision request for the step being redone
    drivers: list[Driver]
    clusters: list[Cluster]
    scores: list[Score]
    critical: list[str]  # driver ids
    axis_sets: list[AxisSet]
    quadrants: list[Quadrant]
    narratives: list[Narrative]
    reviews: Annotated[list[Review], add]
