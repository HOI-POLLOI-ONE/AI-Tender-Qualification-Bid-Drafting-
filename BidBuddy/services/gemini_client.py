# ai_copilot.py
from dotenv import load_dotenv
import os
import json
import re
from typing import Dict, List, Optional

# Load environment variables from .env
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("REGION", "us-central1")
CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

from google.cloud import aiplatform

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)

def _call_vertex(prompt: str, temperature: float = 0.3, max_output_tokens: int = 2048) -> str:
    """
    Call Vertex AI Text Generation (Gemini) model.
    """
    try:
        model = aiplatform.TextGenerationModel.from_prebuilt("text-bison@001")  # Replace with Gemini model if available
        response = model.predict(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        return response.text
    except Exception as e:
        return f"Vertex AI call failed: {str(e)}"


def _parse_json(raw: str) -> Optional[Dict]:
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract first { … } block
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Fix common trailing comma issues
    try:
        fixed = re.sub(r',\s*([}\]])', r'\1', text[start:end+1] if start != -1 else text)
        return json.loads(fixed)
    except Exception:
        pass

    return None


def extract_tender_structure(raw_text: str, sections: Optional[Dict] = None) -> Dict:
    if sections:
        relevant = ""
        for key in ["eligibility criteria", "eligibility requirement", "pre-qualification",
                    "financial requirement", "documents required", "scope of work"]:
            if key in sections:
                relevant += f"\n\n=== {key.upper()} ===\n{sections[key]}"
        text_to_send = relevant[:6000] if len(relevant) > 500 else raw_text[:6000]
    else:
        text_to_send = raw_text[:6000]

    prompt = f"""You are a government tender analyst. Extract structured data from the tender text below.

CRITICAL INSTRUCTIONS:
- Return ONLY JSON
- Start with {{ and end with }}
- Do NOT include text or markdown fences

Use this schema:
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

TENDER TEXT:
{text_to_send}"""

    raw_response = _call_vertex(prompt, temperature=0.0, max_output_tokens=2048)
    parsed = _parse_json(raw_response)
    if parsed is None:
        print(f"WARNING: Could not parse JSON. Preview: {raw_response[:200]}")
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
            "_note": "AI extraction failed — check raw_text"
        }
    return parsed


def generate_bid_draft(tender_data: Dict, company_data: Dict, additional_context: Optional[str] = None) -> str:
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

Use formal language and reference actual values from above.
"""

    return _call_vertex(prompt, temperature=0.4, max_output_tokens=4096)


def copilot_answer(tender_data: Dict, question: str, conversation_history: List[Dict]) -> str:
    history_text = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are an Indian government procurement consultant helping an MSME understand a tender.

TENDER CONTEXT:
{json.dumps(tender_data, indent=2)}

{f'PREVIOUS CONVERSATION:\n{history_text}' if history_text else ''}

USER QUESTION: {question}

Answer clearly and specifically based on the tender context.
Reference data directly. Be concise and actionable.
"""
    return _call_vertex(prompt, temperature=0.3, max_output_tokens=1024)


def analyze_compliance_gaps(tender_data: Dict, company_data: Dict, gaps: List[Dict]) -> str:
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
    return _call_vertex(prompt, temperature=0.5, max_output_tokens=1024)