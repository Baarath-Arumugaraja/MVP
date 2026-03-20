import aiohttp
import json
import os
import asyncio

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def sanitize(text: str) -> str:
    """Remove newline/carriage return to prevent header issues"""
    if not isinstance(text, str):
        return str(text)
    return text.replace("\n", " ").replace("\r", " ").strip()


async def answer_followup(question: str, report_context: dict) -> str:
    # 🔥 STRIP KEY (fixes your main bug)
    api_key = (
        os.getenv("NVIDIA_API_KEY") or
        os.getenv("OPENROUTER_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY") or
        ""
    ).strip()

    if not api_key:
        return "API key not configured. Add NVIDIA_API_KEY to your .env file."

    # Debug once if needed
    # print("API KEY:", repr(api_key))

    # Extract + sanitize
    molecule = sanitize(report_context.get("molecule", "the drug"))
    report = report_context.get("report", {})

    # Compact JSON (NO newlines)
    try:
        report_str = json.dumps(report, separators=(",", ":"))[:4000]
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
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama3-70b-instruct",  # NVIDIA-supported model
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    }

    # Retry logic
    for attempt in range(2):
        try:
            timeout = aiohttp.ClientTimeout(total=20)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    NVIDIA_API_URL,
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
            await asyncio.sleep(1)
