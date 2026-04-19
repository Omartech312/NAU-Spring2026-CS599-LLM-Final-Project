"""
Claude Code CLI integration for citation-grounded Q&A.

Uses the Claude CLI as a subprocess with:
  - --print (-p): non-interactive mode
  - --no-session-persistence: stateless, no disk writes
  - --output-format json: parseable JSON output
  - --dangerously-skip-permissions: no interactive prompts
  - --append-system-prompt: inject research assistant instructions
"""
import os
import time
import json
import subprocess
import threading
from typing import Dict, Any


# System prompt for citation-grounded Q&A
CLAUDE_QA_PROMPT = """You are a research assistant helping answer questions about academic papers.
Your task:
1. Answer the user's question based ONLY on the provided context (retrieved chunks from the paper).
2. Context is formatted with numbered references: [1] [Page 3] first sentence... [2] [Page 7] first sentence...
3. Use [1], [2], etc. to cite specific chunks in your answer, e.g. "According to [1], ..."
4. If the answer is NOT in the context, explicitly say "I cannot find this information in the provided text."
5. Be precise, concise, and factual. Do not make up information not present in the context.
Start your response immediately with the answer - do not prepend any preamble."""

CLAUDE_SUMMARY_PROMPT = """You are a research assistant summarizing academic papers.
Your task:
1. Provide a comprehensive summary of the provided text.
2. Highlight key findings, methodology, and contributions.
3. Support key claims with citation references.
4. Be clear, well-structured, and academic in tone.
Start your response immediately - do not prepend any preamble."""


def _stream_stdout(proc: subprocess.Popen, out: dict) -> None:
    """Read stdout in a thread, collecting JSONL lines."""
    try:
        for line in proc.stdout:
            if line.strip():
                out["lines"].append(line.strip())
    except Exception:
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def query_claude(
    context: str,
    question: str,
    model: str = "claude-opus-4-6",
    system_prompt: str = CLAUDE_QA_PROMPT,
    max_tokens: int = 1000,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Query Claude Code CLI as an LLM.

    Args:
        context: Retrieved text chunks from the paper.
        question: The user's question.
        model: Claude model (passed via --model flag).
        system_prompt: Appended system instructions.
        max_tokens: Soft token limit.
        timeout: Seconds before killing the process.

    Returns:
        Dict with model_name, answer_text, latency_ms, tokens_used, success.
    """
    start_time = time.time()

    prompt = f"""{system_prompt}

---

Context from the paper:

{context}

---

Question: {question}"""

    cmd = [
        "claude",
        "-p",
        "--print",
        "--no-session-persistence",
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--model", model,
        "--append-system-prompt", system_prompt,
        prompt,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            env=os.environ.copy(),
            text=True,
        )

        out = {"lines": []}
        t = threading.Thread(target=_stream_stdout, args=(proc, out), daemon=True)
        t.start()

        proc.wait(timeout=timeout)
        t.join(timeout=2)

        stderr = proc.stderr.read() if proc.stderr else ""
        if proc.returncode != 0 and stderr:
            print(f"Claude stderr: {stderr[:300]}")

        answer_text = ""
        input_tokens = 0
        output_tokens = 0
        total_cost = 0.0
        model_used = model

        for line in out["lines"]:
            try:
                event = json.loads(line)
                subtype = event.get("subtype", "")

                if subtype == "success" and not event.get("is_error", False):
                    answer_text = event.get("result", "")
                    usage = event.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    total_cost = event.get("total_cost_usd", 0.0)

                    # Get actual model used
                    mu = event.get("modelUsage", {})
                    if mu:
                        model_used = list(mu.keys())[0] if mu else model

            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: join raw lines if no result found
        if not answer_text and out["lines"]:
            answer_text = out["lines"][-1]

        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"claude/{model_used}",
            "answer_text": answer_text,
            "latency_ms": latency_ms,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "api_cost_usd": total_cost,
            "success": bool(answer_text),
        }

    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"claude/{model}",
            "answer_text": "Error: Claude request timed out",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": "timeout",
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "model_name": f"claude/{model}",
            "answer_text": f"Error: {str(e)}",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "success": False,
            "error": str(e),
        }
