import aiohttp
import json
import os

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def answer_followup(question: str, report_context: dict) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "API key not configured. Add OPENROUTER_API_KEY to your .env file."

    molecule = report_context.get("molecule", "the drug")
    report  = report_context.get("report", {})

    system_prompt = f"""You are a pharmaceutical research assistant. 
The user is asking a follow-up question about a drug repurposing report for {molecule}.

Here is the full report context:
{json.dumps(report, indent=2)}

Answer concisely and specifically based on this data. 
If the answer isn't in the data, say so honestly.
Keep answers under 150 words. Be direct."""

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "RepurposeAI"
            }
            payload = {
                "model": "anthropic/claude-3-haiku",
                "max_tokens": 300,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            }
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return f"Could not get answer (API error {resp.status})."
    except Exception as e:
        return f"Error: {str(e)}"
