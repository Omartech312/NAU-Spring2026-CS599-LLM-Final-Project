import os
import time
import json
from typing import List, Dict, Any, Optional
import openai
import anthropic
import google.generativeai as genai
from app.services.codex_service import query_codex as _query_codex
from app.services.claude_service import query_claude


# System prompt for citation-grounded Q&A
QA_SYSTEM_PROMPT = """You are a research assistant helping answer questions about academic papers.
Your task:
1. Answer the user's question based ONLY on the provided context (retrieved chunks from the paper).
2. Context is formatted with numbered references: [1] [Page 3] first sentence... [2] [Page 7] first sentence...
3. Use [1], [2], etc. to cite specific chunks in your answer, e.g. "According to [1], ..."
4. If the answer is NOT in the context, explicitly say "I cannot find this information in the provided text."
5. Be precise, concise, and factual. Do not make up information not present in the context.
"""

SUMMARY_SYSTEM_PROMPT = """You are a research assistant summarizing academic papers.
Your task:
1. Provide a comprehensive summary of the provided text.
2. Highlight key findings, methodology, and contributions.
3. Support key claims with citation references.
4. Be clear, well-structured, and academic in tone.
"""


def query_openai(
    context: str,
    question: str,
    model: str = "gpt-4o",
    system_prompt: str = QA_SYSTEM_PROMPT,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    """Query OpenAI GPT model."""
    start_time = time.time()

    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context from the paper:\n\n{context}\n\n---\n\nQuestion: {question}",
                },
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )

        latency_ms = (time.time() - start_time) * 1000
        answer_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        return {
            "model_name": f"openai/{model}",
            "answer_text": answer_text,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "success": True,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"openai/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }


def query_anthropic(
    context: str,
    question: str,
    model: str = "claude-3-5-sonnet-20240620",
    system_prompt: str = QA_SYSTEM_PROMPT,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    """Query Anthropic Claude model."""
    start_time = time.time()

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Context from the paper:\n\n{context}\n\n---\n\nQuestion: {question}",
                }
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )

        latency_ms = (time.time() - start_time) * 1000
        answer_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return {
            "model_name": f"anthropic/{model}",
            "answer_text": answer_text,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "success": True,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"anthropic/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }


def query_google(
    context: str,
    question: str,
    model: str = "gemini-1.5-flash",
    system_instruction: str = None,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    """Query Google Gemini model."""
    start_time = time.time()

    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        model_instance = genai.GenerativeModel(
            model,
            system_instruction=system_instruction or QA_SYSTEM_PROMPT,
        )
        response = model_instance.generate_content(
            f"Context from the paper:\n\n{context}\n\n---\n\nQuestion: {question}",
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.2,
            },
        )

        latency_ms = (time.time() - start_time) * 1000
        answer_text = response.text

        return {
            "model_name": f"google/{model}",
            "answer_text": answer_text,
            "latency_ms": latency_ms,
            "tokens_used": 0,  # Gemini doesn't easily expose this
            "success": True,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"google/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }


def query_codex(
    context: str,
    question: str,
    model: str = "gpt-5.2",
    system_prompt: str = QA_SYSTEM_PROMPT,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    """Query Codex CLI as an LLM."""
    start_time = time.time()
    try:
        result = _query_codex(
            context=context,
            question=question,
            model=model,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )
        return result
    except Exception as e:
        return {
            "model_name": f"codex/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": (time.time() - start_time) * 1000,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }


def query_single_model(
    model_provider: str,
    context: str,
    question: str,
    query_type: str = "qa",
    model_name: Optional[str] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Query a single model by provider.
    Providers: 'openai', 'anthropic', 'google', 'codex'
    """
    config = config or {}

    if query_type == "summary":
        system_prompt = SUMMARY_SYSTEM_PROMPT
    else:
        system_prompt = QA_SYSTEM_PROMPT

    if model_provider == "openai":
        model = model_name or config.get("OPENAI_MODEL", "gpt-4o")
        return query_openai(context, question, model, system_prompt)
    elif model_provider == "anthropic":
        model = model_name or config.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
        return query_anthropic(context, question, model, system_prompt)
    elif model_provider == "google":
        model = model_name or config.get("GOOGLE_MODEL", "gemini-1.5-flash")
        return query_google(context, question, model, system_prompt)
    elif model_provider == "codex":
        model = model_name or config.get("CODEX_MODEL", "gpt-5.2")
        return query_codex(context, question, model, system_prompt)
    elif model_provider == "claude":
        model = model_name or config.get("CLAUDE_MODEL", "claude-opus-4-6")
        return query_claude(context, question, model, system_prompt)
    else:
        return {
            "model_name": f"{model_provider}/unknown",
            "answer_text": f"Unknown provider: {model_provider}",
            "latency_ms": 0,
            "tokens_used": 0,
            "success": False,
            "error": f"Unknown provider: {model_provider}",
        }


def query_all_models(
    context: str,
    question: str,
    query_type: str = "qa",
    config: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Query all three LLM models and return their results.
    Returns a list of result dicts.
    """
    config = config or {}

    results = []

    # Try OpenAI
    if config.get("OPENAI_API_KEY"):
        result = query_single_model("openai", context, question, query_type, config=config)
        results.append(result)
    else:
        results.append({
            "model_name": "openai/gpt-4o",
            "answer_text": "OpenAI API key not configured",
            "latency_ms": 0,
            "tokens_used": 0,
            "success": False,
            "error": "API key missing",
        })

    # Try Anthropic
    if config.get("ANTHROPIC_API_KEY"):
        result = query_single_model("anthropic", context, question, query_type, config=config)
        results.append(result)
    else:
        results.append({
            "model_name": "anthropic/claude-3-5-sonnet",
            "answer_text": "Anthropic API key not configured",
            "latency_ms": 0,
            "tokens_used": 0,
            "success": False,
            "error": "API key missing",
        })

    # Try Google
    if config.get("GOOGLE_API_KEY"):
        result = query_single_model("google", context, question, query_type, config=config)
        results.append(result)
    else:
        results.append({
            "model_name": "google/gemini-1.5-flash",
            "answer_text": "Google API key not configured",
            "latency_ms": 0,
            "tokens_used": 0,
            "success": False,
            "error": "API key missing",
        })

    # Always try Codex (no API key needed, uses local CLI)
    model = config.get("CODEX_MODEL", "gpt-5.2")
    result = query_single_model("codex", context, question, query_type, model_name=model, config=config)
    results.append(result)

    # Always try Claude (no API key needed, uses local CLI)
    model = config.get("CLAUDE_MODEL", "claude-opus-4-6")
    result = query_single_model("claude", context, question, query_type, model_name=model, config=config)
    results.append(result)

    return results
