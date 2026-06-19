"""
LLM Reviewer Module
Handles the integration with the OpenRouter API. 
Responsible for prompt engineering, schema enforcement, and parsing unpredictable LLM outputs safely.
"""
import os
import json
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from the .env file securely
load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using the specified free model per the project requirements
MODEL_NAME = "openai/gpt-oss-120b:free"

def evaluate_commits(commits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Sends commit messages to the OpenRouter API for evaluation.
    Requires the OPENROUTER_API_KEY environment variable to be set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("The OPENROUTER_API_KEY environment variable is not set.")

    # Prompt Engineering Strategy:
    # 1. Assign a clear persona ("expert software engineer").
    # 2. Define strict evaluation criteria (the "why" behind the "what").
    # 3. Enforce a strict JSON schema to ensure programmatic readability.
    system_prompt = (
        "You are an expert software engineer reviewing git commit messages. "
        "Your task is to evaluate the descriptive clarity of each commit, specifically checking "
        "if the commit message explains the 'why' behind the change, rather than just the 'what'. "
        "You must output a valid JSON array of objects. Each object must contain: "
        "1. 'hash': The exact commit hash provided. "
        "2. 'rating': Strictly one of 'excellent', 'good', or 'bad'. "
        "3. 'reasoning': A brief explanation for your rating. "
        "Do not include any markdown formatting, preamble, or postscript in your response. Output only raw JSON."
    )

    # Format the payload for the LLM context window
    user_content = "Please review the following commits:\n\n"
    for commit in commits:
        user_content += (
            f"Hash: {commit.get('hash')}\n"
            f"Author: {commit.get('author')}\n"
            f"Message: {commit.get('message')}\n"
            f"---\n"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    }

    try:
        # Defensive programming: Enforce a timeout so the CLI doesn't hang indefinitely on API lag
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        
        if "choices" not in response_data or not response_data["choices"]:
            raise ValueError("Unexpected API response format: Missing 'choices' array.")
            
        llm_output = response_data["choices"][0]["message"]["content"]
        
        # Defensive Parsing: 
        # Even with strict system prompts, LLMs often wrap JSON in markdown blocks.
        # This sanitizes the output string before attempting to decode it.
        llm_output = llm_output.strip()
        if llm_output.startswith("```json"):
            llm_output = llm_output[7:]
        if llm_output.endswith("```"):
            llm_output = llm_output[:-3]
            
        parsed_reviews = json.loads(llm_output.strip())
        
        # Type verification to ensure downstream modules (like the report server) don't crash
        if not isinstance(parsed_reviews, list):
            raise ValueError("The LLM did not return a JSON array as requested.")
            
        return parsed_reviews

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error occurred while contacting the OpenRouter API: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse the LLM response as JSON. Error: {e}. Raw output: {llm_output}")