from backend.llm.model import llm
from backend.graph.state import TutorState

ACKNOWLEDGE_PROMPT = """\
You are TutorDesk, a friendly AI teaching assistant.
The user sent a greeting or small-talk message. Respond briefly and warmly.
Do NOT generate any educational content, facts, or lesson material.
Keep it to 1-2 sentences.

User's message:
{query}
"""


def acknowledge(state: TutorState) -> dict:
    """Respond briefly to greetings and small-talk."""

    message = llm.invoke(ACKNOWLEDGE_PROMPT.format(query=state["query"]))

    return {
        "answer": message.content.strip(),
        "all_sources": [],
    }

