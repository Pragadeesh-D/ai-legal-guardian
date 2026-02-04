
import json

def calculate_composite_risk(llm_response):
    """
    Extracts or re-calculates the overall risk score from the LLM JSON.
    validates the range (0-100).
    """
    try:
        score = llm_response.get("numeric_risk_score", 0)
        # normalize
        if isinstance(score, str):
            score = int(''.join(filter(str.isdigit, score)))
        return min(max(score, 0), 100)
    except:
        return 50 # Default medium risk if parsing fails

def compliance_check_heuristics(text, entities):
    """
    Rule-based checks to supplement LLM.
    Example: Check for missing Jurisdiction clause if not found by LLM (though LLM is better).
    """
    alerts = []
    # logic placeholders
    if "Arbitration" not in text and "Dispute Resolution" not in text:
         alerts.append("Missing Dispute Resolution/Arbitration clause.")
         
    return alerts

def process_risk_analysis(llm_result, raw_text, entities):
    """
    Refines the LLM result with local heuristics.
    """
    # 1. Validate Score
    llm_result["numeric_risk_score"] = calculate_composite_risk(llm_result)
    
    # 2. Add rule-based alerts
    heuristic_alerts = compliance_check_heuristics(raw_text, entities)
    if heuristic_alerts:
        if "missing_clauses" not in llm_result:
            llm_result["missing_clauses"] = []
        llm_result["missing_clauses"].extend(heuristic_alerts)
        
    return llm_result
