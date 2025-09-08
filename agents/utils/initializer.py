"""
RCM Agent initialization utilities
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_dotenv_value(val: str):
    return os.getenv(val)


# LLM Initialization
llm_instance = None


def get_llm():
    global llm_instance
    if llm_instance is None:
        llm_instance = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=2,
            api_key=get_dotenv_value("GROQ_API_KEY"),
        )
    return llm_instance


def get_coding_llm():
    return get_llm()
    # """Specialized LLM for medical coding tasks with higher precision"""
    # api_key = get_dotenv_value("OPENAI_API_KEY")
    # if not api_key:
    #     raise ValueError("OPENAI_API_KEY not found in environment variables")

    # return ChatOpenAI(
    #     model="gpt-4-1106-preview",
    #     temperature=0.0,  # Zero temperature for deterministic coding
    #     api_key=api_key,
    #     max_tokens=1500,
    # )


def get_structuring_llm():
    return get_llm()
    # """Specialized LLM for data structuring tasks"""
    # api_key = get_dotenv_value("OPENAI_API_KEY")
    # if not api_key:
    #     raise ValueError("OPENAI_API_KEY not found in environment variables")

    # return ChatOpenAI(
    #     model="gpt-4-1106-preview",
    #     temperature=0.2,  # Slightly higher for creative structuring
    #     api_key=api_key,
    #     max_tokens=2500,
    # )
