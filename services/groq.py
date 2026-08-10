"""AI service for create/update tickets."""

import os
from groq import Groq

class GroqAI:
    """AI service for create/update tickets."""

    def __init__(self):
        """Initialize the FlowAIAgenet with the Groq API key."""
        self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def call_ai(self, user_question: str) -> str:
        """Call the Groq AI service with the provided user question.

        Args:
            user_question (str): The question to send to the AI service.

        Returns:
            str: The response from the AI service.
        """
        system_prompt = f""""""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ]
        
        response = self.groq.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=messages,
            max_tokens=512,
            temperature=0.2,
        )
        
        return response.choices[0].message.content.strip()
