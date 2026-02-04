
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


load_dotenv()

# Prompts
SYSTEM_PROMPT = """You are an expert legal assistant for Indian Small and Medium Enterprises (SMEs). 
Your goal is to analyze contracts, identify risks under Indian Law, and explain terms in simple business language.
Output purely valid JSON without markdown formatting."""

ANALYSIS_PROMPT_TEMPLATE = """
Analyze the following contract text. 
Context: {context_str}

Perform the following tasks:
1. **Classify**: Determine the type of contract (e.g., Employment, Lease, Service, NDA).
2. **Risk Assessment**: 
   - Assign a "Risk Score" (Low, Medium, High) for the whole contract.
   - Assign a numeric score (0-100, where 100 is extremely risky).
   - Identify "Unfavorable Terms" specifically for an SME context (e.g., one-sided termination, heavy indemnity, non-compete).
   - Flag "Compliance Issues" relative to common Indian laws (e.g., Notice period norms, Payment terms).
3. **Ambiguity Detection**:
   - Identify clauses that are vague, unclear, or open to interpretation (e.g., "reasonable time", "mutual agreement").
4. **Clause Analysis**:
   - For key clauses, provide a "Plain Language Explanation".
   - If a clause is risky, suggest a "Negotiation Tip" or "Alternative Clause".
5. **Summary**: Provide a 3-sentence summary of the contract.

**Output Format (JSON)**:
{{
  "contract_type": "string",
  "summary": "string",
  "overall_risk_score": "Low/Medium/High",
  "numeric_risk_score": 0-100,
  "key_risks": [
    {{ "clause": "excerpt...", "risk": "explanation...", "severity": "High/Medium/Low" }}
  ],
  "ambiguous_clauses": [
    {{ "clause": "text snippet...", "reason": "why it is vague" }}
  ],
  "clauses_analysis": [
    {{ "title": "clause topic", "text": "original text snippet", "explanation": "simple english", "risk_level": "Low/Med/High", "recommendation": "tip" }}
  ],
  "missing_clauses": ["list of important clauses missing"]
}}

Contract Text:
{contract_text}
"""

def get_client(provider):
    if provider == "groq":
        return OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
    else:
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_contract_with_llm(text, entities, provider="openai"):
    """
    Sends text to LLM for comprehensive analysis.
    provider: "openai" or "groq"
    """
    context_str = f"Dimensions found: {json.dumps(entities)}"
    
    # Select Model
    if provider == "groq":
        model_name = "llama-3.3-70b-versatile" # Free, high performance
    else:
        model_name = "gpt-4o"

    client = get_client(provider)
    
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(context_str=context_str, contract_text=text)
    
    try:
        response = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}

def chat_with_assistant(history, user_question, contract_context, provider="openai"):
    """
    Simple Q&A interface.
    """
    client = get_client(provider)
    if provider == "groq":
        model_name = "llama-3.3-70b-versatile"
    else:
        model_name = "gpt-4o"

    messages = [{"role": "system", "content": "You are a helpful legal assistant for Indian SMEs. Answer based on the contract provided."}]
    # Add context
    messages.append({"role": "system", "content": f"Contract Context: {contract_context[:20000]}..."}) # succinct context
    
    # Add history
    for msg in history:
        messages.append(msg)
        
    messages.append({"role": "user", "content": user_question})
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


def extract_template_data(contract_text, contract_type, provider="openai"):
    """
    Extract structured data from contract for template population.
    
    Args:
        contract_text: Full contract text
        contract_type: Detected contract type (Service/Employment/NDA)
        provider: AI provider (openai/groq)
        
    Returns:
        Dictionary with extracted fields in strict JSON format
    """
    EXTRACTION_PROMPT = """Extract the following fields from the contract text. 
Return ONLY valid JSON. Do NOT hallucinate or infer missing information.

If a field is not explicitly stated in the contract, return: "Not specified in the provided contract"

Required fields:
- contract_type: Type of contract (Service Agreement/Employment Agreement/NDA/Other)
- services: Description of services/work/responsibilities
- amount: Payment amount or compensation
- termination_notice: Termination notice period
- confidentiality: Confidentiality clause text
- provider: Provider/Employer/Disclosing party name
- client: Client/Employee/Receiving party name
- start_date: Start date
- end_date: End date or duration
- payment_terms: Payment terms (e.g., "Net 30 days", "50% upfront")
- jurisdiction: Governing law jurisdiction

Contract Text:
{contract_text}

Return ONLY the JSON object, no markdown formatting."""

    client = get_client(provider)
    if provider == "groq":
        model_name = "llama-3.3-70b-versatile"
    else:
        model_name = "gpt-4o"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(contract_text=contract_text[:15000])}
            ],
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        # Parse JSON
        extracted_data = json.loads(result_text)
        
        # Ensure contract_type is set
        if "contract_type" not in extracted_data or not extracted_data["contract_type"]:
            extracted_data["contract_type"] = contract_type
        
        return extracted_data
        
    except Exception as e:
        # Return fallback structure if extraction fails
        return {
            "contract_type": contract_type,
            "services": "Not specified in the provided contract",
            "amount": "Not specified in the provided contract",
            "termination_notice": "Not specified in the provided contract",
            "confidentiality": "Not specified in the provided contract",
            "provider": "Not specified in the provided contract",
            "client": "Not specified in the provided contract",
            "start_date": "Not specified in the provided contract",
            "end_date": "Not specified in the provided contract",
            "payment_terms": "Not specified in the provided contract",
            "jurisdiction": "Not specified in the provided contract"
        }

