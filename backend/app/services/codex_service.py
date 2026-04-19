"""
Codex CLI LLM integration for citation-grounded Q&A.

Uses the Codex CLI as a subprocess that reads prompts from stdin
and outputs JSONL responses. Supports both QA and summary modes.
"""
import os
import time
import json
import subprocess
import threading
from typing import List, Dict, Any, Optional, IO


CODEX_SYSTEM_PROMPT_QA = """You are a research assistant helping answer questions about academic papers.
Your task:
1. Answer the user's question based ONLY on the provided context (retrieved chunks from the paper).
2. Context is formatted with numbered references: [1] [Page 3] first sentence... [2] [Page 7] first sentence...
3. Use [1], [2], etc. to cite specific chunks in your answer, e.g. "According to [1], ..."
4. If the answer is NOT in the context, explicitly say "I cannot find this information in the provided text."
5. Be precise, concise, and factual. Do not make up information not present in the context.
Start your response immediately with the answer - do not prepend any preamble like "Here is the answer:" or similar."""

CODEX_SYSTEM_PROMPT_SUMMARY = """You are a research assistant summarizing academic papers.
Your task:
1. Provide a comprehensive summary of the provided text.
2. Highlight key findings, methodology, and contributions.
3. Support key claims with citation references.
4. Be clear, well-structured, and academic in tone.
Start your response immediately - do not prepend any preamble."""


def _stream_codex_output(proc: subprocess.Popen, output_buffer: dict) -> None:
    """Read stdout from Codex process in a thread, collecting output."""
    try:
        for line in proc.stdout:
            if line.strip():
                output_buffer["lines"].append(line.strip())
    except Exception:
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def _build_prompt(context: str, question: str, system_prompt: str) -> str:
    """Build the full prompt for Codex from context and question."""
    return f"""{system_prompt}

---

Context from the paper:

{context}

---

Question: {question}"""


def query_codex(
    context: str,
    question: str,
    model: str = "gpt-5.2",
    system_prompt: str = CODEX_SYSTEM_PROMPT_QA,
    max_tokens: int = 1000,
    timeout: int = 120,
    working_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query Codex CLI as an LLM.

    Args:
        context: Retrieved text chunks from the paper.
        question: The user's question.
        model: Codex model to use (default: gpt-5.2 from config).
        system_prompt: System instructions.
        max_tokens: Token budget (used as soft limit).
        timeout: Seconds before killing the process.
        working_dir: Directory to run Codex from (default: project root).

    Returns:
        Dict with model_name, answer_text, latency_ms, tokens_used, success.
    """
    start_time = time.time()

    if working_dir is None:
        working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    prompt = _build_prompt(context, question, system_prompt)

    try:
        proc = subprocess.Popen(
            ["codex", "exec", "--full-auto", "--json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            env=os.environ.copy(),
            text=True,
        )

        output_buffer: Dict[str, List[str]] = {"lines": []}
        reader_thread = threading.Thread(
            target=_stream_codex_output,
            args=(proc, output_buffer),
            daemon=True,
        )
        reader_thread.start()

        proc.stdin.write(prompt)
        proc.stdin.close()

        proc.wait(timeout=timeout)

        reader_thread.join(timeout=2)

        stderr = proc.stderr.read() if proc.stderr else ""
        if proc.returncode != 0 and stderr:
            print(f"Codex stderr: {stderr[:500]}")

        answer_text = ""
        input_tokens = 0
        output_tokens = 0

        for line in output_buffer["lines"]:
            try:
                event = json.loads(line)
                event_type = event.get("type", "")
                if event_type == "agent_message":
                    answer_text = event.get("text", "")
                elif event_type == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        answer_text = item.get("text", "")
                elif event_type == "turn.completed":
                    usage = event.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
            except (json.JSONDecodeError, TypeError):
                continue

        if not answer_text:
            answer_text = "\n".join(output_buffer["lines"][-3:]) if output_buffer["lines"] else ""

        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"codex/{model}",
            "answer_text": answer_text,
            "latency_ms": latency_ms,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "success": bool(answer_text),
        }

    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"codex/{model}",
            "answer_text": "Error: Codex request timed out",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": "timeout",
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"codex/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }
