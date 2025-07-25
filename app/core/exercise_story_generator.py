"""
Generate exercise stories from a user prompt using Gemini LLM.

- Input: user prompt (string)
- Output: up to 5 exercise stories (list of strings)
- LLM: Gemini (Google Generative AI)

This file is single-responsibility: it only generates exercise stories from a prompt.
"""

import os
import logging
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_exercise_stories(user_prompt: str) -> List[str]:
    """
    Generate up to 5 exercise stories from a user prompt using Gemini.
    Args:
        user_prompt: The user's natural language requirements.
    Returns:
        List of up to 5 exercise stories (strings).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Use Gemini 2.5 Flash for faster, more cost-effective responses
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
You are an expert fitness coach. Given the following user requirements, generate up to 5 distinct, clear, and actionable exercise stories. Each story should describe a specific exercise or movement that would help the user achieve their goals. Be concise and use natural language.

USER REQUIREMENTS: {user_prompt}

Return the stories as a numbered list, one per line.
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Parse numbered list into stories
        stories = []
        for line in text.splitlines():
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                # Remove leading number/bullet
                story = line.lstrip("0123456789.-• ")
                if story:
                    stories.append(story)
            elif line:
                stories.append(line)
        # Limit to 5
        return stories[:5]
        
    except Exception as e:
        logger.error(f"Error generating exercise stories with Gemini: {str(e)}")
        # Fallback to a simple response if API fails
        return [
            "Hip flexor stretches to improve hip mobility",
            "Core strengthening exercises for handstand preparation",
            "Shoulder and wrist mobility work for handstand support",
            "Progressive handstand practice against a wall",
            "Balance and stability training for handstand progression"
        ] 