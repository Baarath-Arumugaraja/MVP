import aiohttp
import json
import os

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def synthesize_report(molecule, clinical, patents, market, regulatory, cross_domain_context="") -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
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

Based on ALL the above data, generate a structured drug repurposing report.
Respond ONLY with valid JSON — no markdown, no extra text:
{{
  "executive_summary": "2-3 sentences. Be specific about what was found.",
  "repurposing_opportunities": [
    {{
      "disease": "Exact disease or condition name",
      "description": "1-2 sentences explaining why this drug could treat this disease based on the data",
      "confidence": "HIGH / MODERATE / INVESTIGATE",
      "confidence_score": 82,
      "trial_id": "NCT number if found in data, else null",
      "trial_phase": "Phase 1/2/3/4 or null",
      "market_gap": "1 sentence on unmet need or commercial opportunity",
      "patent_status": "Free to use / Patent protected / Expired / Unknown",
      "source": "ClinicalTrials.gov / PubMed / OpenFDA"
    }}
  ],
  "unmet_needs": {{
    "finding": "Specific unmet needs identified from the data",
    "evidence": "Cite specific trial IDs or data points",
    "source": "ClinicalTrials.gov / OpenFDA"
  }},
  "pipeline_status": {{
    "finding": "Current clinical pipeline status with phases",
    "evidence": "Specific trial numbers and phases",
    "source": "ClinicalTrials.gov"
  }},
  "patent_landscape": {{
    "finding": "Patent situation and freedom to operate assessment",
    "evidence": "Based on {patents.get('total_patents', 0)} patents found",
    "source": "PubChem / Google Patents"
  }},
  "market_potential": {{
    "finding": "Commercial opportunity based on usage data",
    "evidence": "Based on {market.get('adverse_event_reports', 0):,} adverse event reports and {market.get('products_found', 0)} products",
    "source": "OpenFDA"
  }},
  "strategic_recommendation": {{
    "verdict": "PURSUE / INVESTIGATE FURTHER / LOW PRIORITY",
    "reasoning": "Specific reasoning combining all 4 domains",
    "next_steps": ["Specific step 1", "Specific step 2", "Specific step 3"]
  }},
  "confidence_score": 70,
  "key_risks": ["Specific risk 1", "Specific risk 2"],
  "cross_domain_insight": "One insight ONLY visible when combining all 4 data sources"
}}

IMPORTANT for repurposing_opportunities:
- List 2-4 specific diseases this drug could be repurposed for based on the actual trial and literature data
- Each must be a DIFFERENT disease from the drug's current approved use
- Use real trial IDs from the data where available
- If no strong evidence exists, still list 1-2 potential opportunities with INVESTIGATE confidence
- Be specific — not "pain management" but "postoperative analgesia in paediatric adenotonsillectomy"
"""

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
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=40)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if "```" in text:
                        parts = text.split("```")
                        text = parts[1]
                        if text.startswith("json"):
                            text = text[4:]
                    return json.loads(text.strip())
                else:
                    body = await resp.text()
                    print(f"[Synthesizer] API error {resp.status}: {body[:200]}")
                    return _mock_report(molecule, error=f"API error {resp.status}")
    except json.JSONDecodeError as e:
        print(f"[Synthesizer] JSON parse error: {e}")
        return _mock_report(molecule, error="AI returned invalid JSON.")
    except Exception as e:
        print(f"[Synthesizer] Error: {e}")
        return _mock_report(molecule, error=str(e))


def _mock_report(molecule, error=None):
    note = error or "Set OPENROUTER_API_KEY in your .env file."
    return {
        "executive_summary": f"Demo mode for {molecule}. {note}",
        "repurposing_opportunities": [
            {
                "disease": "Demo — add API key to see real opportunities",
                "description": "Real repurposing opportunities will appear here once OPENROUTER_API_KEY is configured.",
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
            "next_steps": ["Add OPENROUTER_API_KEY to .env", "Re-run analysis", "Check raw data tabs"]
        },
        "confidence_score": 0,
        "key_risks": ["API key not configured"],
        "cross_domain_insight": note
    }
