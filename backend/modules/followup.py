import aiohttp
import json
import os
import asyncio

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def sanitize(text: str) -> str:
    """Remove newline/carriage return to prevent header issues"""
    if not isinstance(text, str):
        return str(text)
    return text.replace("\n", " ").replace("\r", " ").strip()


async def answer_followup(question: str, report_context: dict) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return "API key not configured. Add OPENROUTER_API_KEY to your .env file."

    # Extract context safely
    molecule = sanitize(report_context.get("molecule", "the drug"))
    report = report_context.get("report", {})

    # Convert report to compact string (NO newlines)
    try:
        report_str = json.dumps(report, separators=(",", ":"))[:4000]  # limit size
    except Exception:
        report_str = "{}"

    report_str = sanitize(report_str)
    question = sanitize(question)

    # Strong grounding prompt
    system_prompt = (
        f"You are a pharmaceutical research assistant. "
        f"The user is asking a follow-up question about a drug repurposing report for {molecule}. "
        f"Here is the report context: {report_str} "
        f"Answer concisely based ONLY on this data. "
        f"If the answer is not explicitly present, respond EXACTLY: 'Not found in report.' "
        f"Keep answers under 150 words."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("APP_URL", "http://localhost"),
        "X-Title": "RepurposeAI"
    }

    payload = {
        "model": "anthropic/claude-3.5-haiku",  # upgraded model
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    }

    # Retry logic (2 attempts)
    for attempt in range(2):
        try:
            timeout = aiohttp.ClientTimeout(total=20)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload
                ) as resp:

                    if resp.status == 200:
                        data = await resp.json()

                        return (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )

                    else:
                        error_text = await resp.text()
                        return f"API error {resp.status}: {error_text}"

        except Exception as e:
            if attempt == 1:
                return f"Request failed after retry: {str(e)}"

            await asyncio.sleep(1)  # small delay before retry
