from langchain.agents import create_agent
from backend.models.llm import model
from backend.agent.tools import(
    rag_tool,
    search_tool
)


tools=[
    rag_tool,
    search_tool
]

agent=create_agent(
    model=model,
    tools=tools,
    system_prompt="""
    You are TutorDesk, an AI teaching assistant.

    You have two tools:

    1. rag_tool:
       Use when the user wants information from material
       uploaded to the workspace.

    2. search_tool:
       Use when information needs to be researched from
       the web.

    Choose the appropriate tool based on the user's request.
    """

)