from backend.models.llm import lessonmodel
from backend.prompts.lesson import lessonprompt
from backend.content.generator import generate_content


def ask_with_source(question: str, source: str = "auto"):

    return generate_content(question, lessonprompt, lessonmodel, source)