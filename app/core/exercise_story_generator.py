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

def generate_exercise_stories(user_prompt: str, story_count: int = 5) -> List[str]:
    """
    Generate exercise requirement stories from a user prompt using Gemini.
    
    Args:
        user_prompt: The user's natural language requirements.
        story_count: Number of stories to generate (default: 5, max: 6).
        
    Returns:
        List of exercise requirement stories (strings).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Use Gemini 2.5 Flash for faster, more cost-effective responses
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
<role>
You are a fitness coach specializing in analyzing user requirements and creating exercise requirement stories for video compilation systems.
</role>

<tone>
Be empathetic, practical, and solution-focused. Understand user pain points and constraints while providing actionable exercise requirements.
</tone>

<context>
User Input: "{user_prompt}"
</context>

<task>
Analyze the user's requirements and create exercise requirement stories that capture:

1. **Pain Points**: What problems they're experiencing (tight hips, weak shoulders, etc.)
2. **Counteractions**: What sedentary habits they're trying to overcome (sitting all day, poor posture, etc.)
3. **Fitness Goals**: What skills they want to achieve (handstand, muscle up, splits, etc.)
4. **Constraints**: Time limitations, equipment availability, environment restrictions
5. **Intensity Needs**: Appropriate difficulty level based on their current fitness
6. **Progression Path**: What they need to work on to achieve their goals

Create {story_count} requirement stories that are descriptive paragraphs (not exercise names).
</task>

<output_format>
Return an array of requirement stories like:
[
    "Tight hip mobility training for someone who sits all day and has lower back soreness",
    "Shoulder strength and flexibility development for handstand progression",
    "Beginner-friendly strength building for someone who hasn't exercised in months",
    "Chest-to-knee compression work for handstand preparation"
]
</output_format>
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Parse the response to extract stories
        stories = []
        
        # Try to parse as JSON array first
        if text.startswith('[') and text.endswith(']'):
            try:
                import json
                stories = json.loads(text)
            except json.JSONDecodeError:
                pass
        
        # If not JSON, parse as numbered/bulleted list
        if not stories:
            for line in text.splitlines():
                line = line.strip()
                # Skip empty lines and markdown formatting
                if not line or line.startswith('#') or line.startswith('```'):
                    continue
                # Skip introductory text
                if line.lower().startswith('here are') or line.lower().startswith('based on'):
                    continue
                if line[0].isdigit() or line.startswith("-") or line.startswith("•"):
                    # Remove leading number/bullet
                    story = line.lstrip("0123456789.-• ")
                    if story:
                        stories.append(story)
                elif line and not line.startswith('<') and not line.startswith('[') and not line.startswith(']'):
                    stories.append(line)
        
        # Clean up stories - remove quotes and extra formatting
        cleaned_stories = []
        for story in stories:
            # Remove surrounding quotes
            story = story.strip('"')
            # Remove trailing commas
            story = story.rstrip(',')
            # Only add non-empty stories
            if story and len(story) > 10:
                cleaned_stories.append(story)
        
        # Limit to requested count
        return cleaned_stories[:story_count]
        
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