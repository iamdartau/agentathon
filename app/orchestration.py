import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.agents import discovery, sentiment, journey, pain_detector, recommender, evaluator


class CXState(TypedDict):
    run_id: str
    reviews: list[dict]
    sample_mode: bool
    business_context: dict
    sentiments: list[dict]
    journey_mapped: list[dict]
    pain_clusters: list[dict]
    recommendations: list[dict]
    evaluation: dict
    revision_count: int


MAX_REVISIONS = int(os.environ.get("MAX_REVISIONS", "2"))


def _discovery(state: CXState) -> dict:
    return discovery.run(state)


def _sentiment(state: CXState) -> dict:
    return sentiment.run(state)


def _journey(state: CXState) -> dict:
    return journey.run(state)


def _pain(state: CXState) -> dict:
    return pain_detector.run(state)


def _recommend(state: CXState) -> dict:
    return recommender.run(state)


def _evaluate(state: CXState) -> dict:
    return evaluator.run(state)


def _route_after_eval(state: CXState) -> str:
    decision = state.get("evaluation", {}).get("decision", "approved")
    if decision == "revision_needed" and state.get("revision_count", 0) < MAX_REVISIONS:
        return "recommend"
    return END


def build_graph():
    g = StateGraph(CXState)
    g.add_node("discovery", _discovery)
    g.add_node("sentiment", _sentiment)
    g.add_node("journey", _journey)
    g.add_node("pain", _pain)
    g.add_node("recommend", _recommend)
    g.add_node("evaluate", _evaluate)

    g.set_entry_point("discovery")
    g.add_edge("discovery", "sentiment")
    g.add_edge("sentiment", "journey")
    g.add_edge("journey", "pain")
    g.add_edge("pain", "recommend")
    g.add_edge("recommend", "evaluate")
    g.add_conditional_edges("evaluate", _route_after_eval, {"recommend": "recommend", END: END})

    return g.compile()


workflow = build_graph()
