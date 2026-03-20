import aiohttp
import json
import os
import re

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

async def synthesize_report(molecule, clinical, patents, market, regulatory, cross_domain_context="") -> dict:
    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key:
        return _mock_report(molecule)

    prompt = f"""You are an expert pharmaceutical researcher specializing in drug repurposing.
Analyze the following real data collected about the molecule: {molecule}

--- CLINICAL TRIALS DATA ---
Total trials found: {clinical.get('total_found', 0) or len(clinical.get('trials', []))}
Trials: {json.dumps(clinical.get('trials', [])[:5], indent=2)}

--- PATENT DATA ---
Compound info: {json.dumps(patents.get('compound_info', {}), indent=2)}
Total patents: {patents.get('total_patents', 0)}
Sample patents: {json.dumps(patents.get('patents', [])[:3], indent=2)}

--- MARKET DATA ---
Products found: {market.get('products_found', 0)}
Products: {json.dumps(market.get('products', [])[:3], indent=2)}
Adverse event reports (usage proxy): {market.get('adverse_event_reports', 0):,}
Market insight: {market.get('market_insight', '')}

--- REGULATORY DATA ---
Approvals: {json.dumps(regulatory.get('approvals', [])[:3], indent=2)}
Current indications: {json.dumps(regulatory.get('current_indications', [])[:2], indent=2)}
Warnings: {json.dumps(regulatory.get('warnings', [])[:1], indent=2)}

--- CROSS-DOMAIN CONTEXT ---
{cross_domain_context}

CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, no code blocks.
Start with {{ and end with }}.

Generate this exact JSON structure:
{{
  "executive_summary": "2-3 sentences. Be specific about what was found.",
  "repurposing_opportunities": [
    {{
      "disease": "Exact disease or condition name",
      "description": "1-2 sentences explaining why this drug could treat this disease based on the data",
      "confidence": "HIGH",
      "confidence_score": 82,
      "trial_id": "NCT12345678",
      "trial_phase": "Phase 3",
      "market_gap": "1 sentence on unmet need or commercial opportunity",
      "patent_status": "Free to use",
      "source": "ClinicalTrials.gov"
    }}
  ],
  "unmet_needs": {{
    "finding": "Specific unmet needs identified from the data",
    "evidence": "Cite specific trial IDs or data points",
    "source": "ClinicalTrials.gov"
  }},
  "pipeline_status": {{
    "finding": "Current clinical pipeline status with phases",
    "evidence": "Specific trial numbers and phases",
    "source": "ClinicalTrials.gov"
  }},
  "patent_landscape": {{
    "finding": "Patent situation and freedom to operate assessment",
    "evidence": "Based on {patents.get('total_patents', 0)} patents found",
    "source": "PubChem"
  }},
  "market_potential": {{
    "finding": "Commercial opportunity based on usage data",
    "evidence": "Based on {market.get('adverse_event_reports', 0):,} adverse event reports",
    "source": "OpenFDA"
  }},
  "strategic_recommendation": {{
    "verdict": "PURSUE",
    "reasoning": "Specific reasoning combining all 4 domains",
    "next_steps": ["Step 1", "Step 2", "Step 3"]
  }},
  "confidence_score": 70,
  "key_risks": ["Risk 1", "Risk 2"],
  "cross_domain_insight": "One insight combining all data sources"
}}

RESPOND WITH ONLY THE JSON OBJECT. START WITH {{ and END WITH }}.
"""

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta/llama-3.1-70b-instruct",
                "max_tokens": 3000,
                "temperature": 0.5,  # Lower for more consistent JSON
                "top_p": 0.9,
                "messages": [
                    {"role": "system", "content": "You are a JSON API. You only output valid JSON. Never use markdown or explanations."},
                    {"role": "user", "content": prompt}
                ]
            }
            async with session.post(NVIDIA_API_URL, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    
                    # Debug: Print raw response
                    print(f"[Synthesizer] Raw AI response (first 500 chars):\n{text[:500]}")
                    
                    # Clean the response
                    text = _extract_json(text)
                    
                    # Debug: Print cleaned response
                    print(f"[Synthesizer] Cleaned JSON (first 300 chars):\n{text[:300]}")
                    
                    return json.loads(text)
                else:
                    body = await resp.text()
                    print(f"[Synthesizer] API error {resp.status}: {body[:200]}")
                    return _mock_report(molecule, error=f"API error {resp.status}")
    except json.JSONDecodeError as e:
        print(f"[Synthesizer] JSON parse error: {e}")
        print(f"[Synthesizer] Failed text:\n{text[:500]}")
        return _mock_report(molecule, error="AI returned invalid JSON. Check logs.")
    except Exception as e:
        print(f"[Synthesizer] Error: {e}")
        return _mock_report(molecule, error=str(e))


def _extract_json(text: str) -> str:
    """Extract JSON from various formats AI might return"""
    # Remove markdown code blocks
    if "```json" in text:
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
    if "```" in text:
        match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
    
    # Find JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    
    # Return as-is if no patterns match
    return text.strip()


def _mock_report(molecule, error=None):
    note = error or "Set NVIDIA_API_KEY in your .env file."
    return {
        "executive_summary": f"Demo mode for {molecule}. {note}",
        "repurposing_opportunities": [
            {
                "disease": "Demo — add API key to see real opportunities",
                "description": "Real repurposing opportunities will appear here once NVIDIA_API_KEY is configured.",
                "confidence": "INVESTIGATE",
                "confidence_score": 0,
                "trial_id": None,
                "trial_phase": None,
                "market_gap": "Configure API key to unlock real market gap analysis.",
                "patent_status": "Unknown",
                "source": "Demo"
            }
        ],
        "unmet_needs":      {"finding": "Demo mode", "evidence": note, "source": "Demo"},
        "pipeline_status":  {"finding": "Live data fetched from ClinicalTrials.gov", "evidence": "See raw tabs", "source": "ClinicalTrials.gov"},
        "patent_landscape": {"finding": "Live data fetched from PubChem", "evidence": "See raw tabs", "source": "PubChem"},
        "market_potential": {"finding": "Live data fetched from OpenFDA", "evidence": "See raw tabs", "source": "OpenFDA"},
        "strategic_recommendation": {
            "verdict": "INVESTIGATE FURTHER",
            "reasoning": note,
            "next_steps": ["Add NVIDIA_API_KEY to .env", "Re-run analysis", "Check raw data tabs"]
        },
        "confidence_score": 0,
        "key_risks": ["API key not configured"],
        "cross_domain_insight": note
    }
