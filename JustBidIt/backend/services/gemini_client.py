from groq import Groq
import json
import os
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PROMPT_DIR   = os.path.join(os.path.dirname(__file__), "..", "prompts")

client = None
if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
    client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq API configured successfully")
else:
    print("⚠️  GROQ_API_KEY not set. Add it to .env file.")


def _load_prompt(filename: str) -> str:
    try:
        with open(os.path.join(PROMPT_DIR, filename)) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _call_groq(prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    if not client:
        raise Exception("Groq API key not configured. Add GROQ_API_KEY to .env")
    response = client.chat.completions.create(
        model       = "llama-3.3-70b-versatile",
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
        max_tokens  = max_tokens,
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> Optional[Dict]:
    """
    Aggressively try to extract valid JSON from LLM response.
    Handles markdown fences, leading text, trailing text, etc.
    """
    text = raw.strip()

    # Remove markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the FIRST { and LAST } and extract everything between
    start = text.find('{')
    end   = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try fixing common issues: trailing commas before } or ]
    try:
        fixed = re.sub(r',\s*([}\]])', r'\1', text[start:end+1] if start != -1 else text)
        return json.loads(fixed)
    except Exception:
        pass

    return None


def extract_tender_structure(raw_text: str, sections: Optional[Dict] = None) -> Dict:
    if not client:
        return {"error": "Groq API key not configured. Add GROQ_API_KEY to .env"}

    if sections:
        relevant = ""
        for key in ["eligibility criteria", "eligibility requirement", "pre-qualification",
                    "financial requirement", "documents required", "scope of work"]:
            if key in sections:
                relevant += f"\n\n=== {key.upper()} ===\n{sections[key]}"
        text_to_send = relevant[:6000] if len(relevant) > 500 else raw_text[:6000]
    else:
        text_to_send = raw_text[:6000]

    # Very explicit prompt — forces JSON only
    prompt = f"""You are a government tender analyst. Extract structured data from the tender text below.

CRITICAL INSTRUCTIONS:
- Your response must start with {{ and end with }}
- Do NOT write any text before or after the JSON
- Do NOT use markdown code fences
- Return ONLY the raw JSON object

Use this exact schema:
{{
  "tender_id": null,
  "title": "string",
  "issuing_authority": "string",
  "deadline": "DD-MM-YYYY or null",
  "estimated_value": null,
  "eligibility": {{
    "min_turnover": null,
    "years_experience": null,
    "required_certifications": [],
    "msme_preference": false,
    "past_project_requirement": null,
    "min_single_project_value": null,
    "other_requirements": []
  }},
  "documents_required": [],
  "key_clauses": [],
  "sector": "string",
  "bid_security": null,
  "contract_duration": null
}}

Rules:
- Use null for missing values, [] for empty lists
- All money values in INR Lakhs (1 Crore = 100 Lakhs)
- Do NOT guess values not explicitly in the document

TENDER TEXT:
{text_to_send}"""

    try:
        raw_response = _call_groq(prompt, temperature=0.0, max_tokens=2048)
        parsed = _parse_json(raw_response)

        if parsed is None:
            # Last resort: return a minimal valid structure so the upload doesn't fail
            print(f"WARNING: Could not parse JSON. Raw response preview: {raw_response[:200]}")
            return {
                "tender_id": None,
                "title": "Tender (manual review needed)",
                "issuing_authority": "Unknown",
                "deadline": None,
                "estimated_value": None,
                "eligibility": {
                    "min_turnover": None,
                    "years_experience": None,
                    "required_certifications": [],
                    "msme_preference": False,
                    "past_project_requirement": None,
                    "min_single_project_value": None,
                    "other_requirements": []
                },
                "documents_required": [],
                "key_clauses": [],
                "sector": "Unknown",
                "bid_security": None,
                "contract_duration": None,
                "_note": "AI extraction failed — please check raw_text and retry"
            }

        return parsed

    except Exception as e:
        return {"error": f"Groq API error: {str(e)}"}


def generate_bid_draft(tender_data: Dict, company_data: Dict, additional_context: Optional[str] = None) -> str:
    if not client:
        return "Error: Groq API key not configured."

    projects = company_data.get("past_projects", [])
    projects_text = "\n".join([
        f"  - {p.get('name')}: Rs.{p.get('value')}L, Client: {p.get('client')}, Year: {p.get('year')}"
        for p in projects[:5]
    ]) or "  - No past projects listed"

    prompt = f"""You are a senior procurement consultant in India. Generate a professional bid proposal.

TENDER:
- Title: {tender_data.get('title', 'N/A')}
- Authority: {tender_data.get('issuing_authority', 'N/A')}
- Sector: {tender_data.get('sector', 'N/A')}
- Value: Rs.{tender_data.get('estimated_value', 'N/A')} Lakhs
- Requirements: {json.dumps(tender_data.get('eligibility', {}), indent=2)}
- Documents Required: {', '.join(tender_data.get('documents_required', []))}

COMPANY:
- Name: {company_data.get('name')}
- MSME Category: {company_data.get('msme_category', 'MSME')}
- Annual Turnover: Rs.{company_data.get('annual_turnover', 0)} Lakhs
- Years in Operation: {company_data.get('years_in_operation', 0)}
- Certifications: {', '.join(company_data.get('certifications', []))}
- Past Projects:
{projects_text}

{f'Additional Instructions: {additional_context}' if additional_context else ''}

Write a complete bid proposal in Markdown with these sections:
1. Cover Letter
2. Company Overview
3. Technical Compliance Statement
4. Scope Understanding & Approach
5. Relevant Past Experience
6. Team & Resource Plan
7. Quality Assurance
8. Compliance Declarations
9. Document Index

Use formal language. Be specific. Reference actual values from above.
"""
    try:
        return _call_groq(prompt, temperature=0.4, max_tokens=4096)
    except Exception as e:
        return f"Error generating draft: {str(e)}"


def copilot_answer(tender_data: Dict, question: str, conversation_history: List[Dict]) -> str:
    if not client:
        return "Error: Groq API key not configured."

    history_text = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are an Indian government procurement consultant helping an MSME understand a tender.

TENDER CONTEXT:
{json.dumps(tender_data, indent=2)}

{f'PREVIOUS CONVERSATION:{chr(10)}{history_text}' if history_text else ''}

USER QUESTION: {question}

Answer clearly and specifically based on the tender context.
Reference data directly. Be concise and actionable.
"""
    try:
        return _call_groq(prompt, temperature=0.3, max_tokens=1024)
    except Exception as e:
        return f"Error: {str(e)}"


def analyze_compliance_gaps(tender_data: Dict, company_data: Dict, gaps: List[Dict]) -> str:
    if not client:
        return "AI analysis unavailable — add GROQ_API_KEY to .env"

    prompt = f"""You are a senior procurement consultant analyzing an MSME's eligibility for a government tender.

TENDER: {tender_data.get('title')} | Authority: {tender_data.get('issuing_authority')}
REQUIREMENTS: {json.dumps(tender_data.get('eligibility', {}), indent=2)}

COMPANY:
- Name: {company_data.get('name')}
- Turnover: Rs.{company_data.get('annual_turnover', 0)} Lakhs
- Experience: {company_data.get('years_in_operation', 0)} years
- Certifications: {', '.join(company_data.get('certifications', []))}
- MSME: {company_data.get('msme_category', 'Not specified')}

IDENTIFIED GAPS: {json.dumps(gaps, indent=2) if gaps else 'None'}

Write a 3-4 paragraph strategic analysis:
1. Overall assessment
2. Critical gaps and why they matter
3. Specific actionable steps to address gaps
4. Alternative strategies (consortium, sub-contracting, etc.)

Be encouraging but realistic. Use Indian procurement context.
"""
    try:
        return _call_groq(prompt, temperature=0.5, max_tokens=1024)
    except Exception as e:
        return f"AI analysis failed: {str(e)}"
