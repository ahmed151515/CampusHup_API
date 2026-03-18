import os
from google import genai


def Chat_bot(first_request):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    client = genai.Client(api_key=GEMINI_API_KEY)

    current_request = first_request
    running = True
    SYSTEM_PROMPT = """
    You are Campus Hub AI, an academic assistant designed to help university students
    with academic planning and faculty-related guidance.

    Scope:
    You can help with:
    - Course recommendations
    - Academic roadmaps
    - Study planning
    - Understanding course prerequisites
    - Time management for studying
    - Faculty announcements and academic resources

    Restrictions:
    You must NOT answer questions about politics, religion, personal life advice,
    medical advice, legal advice, or any topic unrelated to university academics.

    If a question is outside your scope, politely respond with:
    "I'm sorry, but this question is outside my academic support scope.
    Please consult a faculty member or the administration for assistance."

    Behavior rules:
    - Provide clear and helpful explanations.
    - When recommending courses, Study Plans explain the reasoning.
    - Mention prerequisites when relevant.
    - Use bullet points when giving suggestions.
    - Keep answers concise and professional.
    - If you are unsure about something, say you do not have enough information.
    Do NOT invent information.
    """

    while running:

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=SYSTEM_PROMPT + "\n\nStudent question:\n" + current_request
        )

        print("\nAI:", response.text)

        answer = input("\nDo you need help with anything else? (Y/N): ")

        if answer.lower() == "n":
            running = False
        else:
            current_request = input("\nEnter your next question: ")


Chat_bot(input("Enter your first question: "))