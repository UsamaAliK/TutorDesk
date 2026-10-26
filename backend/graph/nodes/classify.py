from backend.llm.model import llm
from backend.graph.state import TutorState

CLASSIFY_PROMPT = """\
You are a query classifier for an AI teaching assistant called TutorDesk.

Classify the user's message into exactly ONE category and reply with that
single word only — no explanation, no punctuation.

Categories:

rag
  The user is referring to their own uploaded material. Signals:
  - Words like "my notes", "my document", "my material", "the PDF",
    "the slides", "the file I uploaded", "the handout", "the course".
  - A filename, "chapter X", "page Y".
  - Phrases like "based on my notes", "using my material",
    "from what I uploaded", "teach me from my file".

web
  Any substantive educational request that is NOT about the user's own
  uploaded material. This includes:
  - General topic questions, lesson plan requests, quiz generation,
    MCQs, summaries, explanations about a subject.
  - Requests mentioning "latest", "current", "search", "find sources",
    "research online".
  - Anything where the user does NOT reference their own documents.

greeting
  Pure greetings, thanks, or small talk with no educational request.
  Examples: "hi", "hello", "thanks", "good morning", "how are you".

If you are unsure between rag and web, choose rag.
If you are unsure between web and greeting, choose web.

User's message:
{query}
"""


def classify_query(state: TutorState) -> dict:
    """Classify the user query into rag / web / greeting."""

    message = llm.invoke(CLASSIFY_PROMPT.format(query=state["query"]))
    raw = message.content.strip().lower()

    if "rag" in raw:
        query_type = "rag"
    elif "greeting" in raw:
        query_type = "greeting"
    else:
        query_type = "web"

    return {"query_type": query_type}

