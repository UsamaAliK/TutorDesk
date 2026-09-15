from langchain_core.prompts import ChatPromptTemplate


lessonprompt=ChatPromptTemplate([
        (
        "system",
        """
        You are TutorDesk, an AI teaching assistant.

        Create clear and practical lesson plans for teachers.

        Consider the student's level, prerequisites, learning
        objectives, activities, and assessments.
        """
    ),
    (
        "human",
        "{request}"
    )
])