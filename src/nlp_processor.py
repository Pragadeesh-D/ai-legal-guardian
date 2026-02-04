
import spacy
import re

# Load English model
# In a real app, we might handle errors if model isn't downloaded yet, 
# but we are assuming it's part of setup.
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

def load_model():
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return nlp

def extract_entities(text):
    """
    Extracts Parties (ORG, PERSON), Dates, and Money.
    Returns a dict with lists of entities.
    """
    model = load_model()
    if not model:
        return {}
    
    doc = model(text)
    entities = {
        "Parties": [],
        "Dates": [],
        "Money": []
    }
    
    seen = set()

    for ent in doc.ents:
        clean_text = ent.text.strip()
        if clean_text in seen:
            continue
            
        if ent.label_ in ["ORG", "PERSON"]:
            entities["Parties"].append(clean_text)
            seen.add(clean_text)
        elif ent.label_ == "DATE":
            entities["Dates"].append(clean_text)
            seen.add(clean_text)
        elif ent.label_ == "MONEY":
            entities["Money"].append(clean_text)
            seen.add(clean_text)
            
    return entities

def segment_into_clauses(text):
    """
    Heuristic segmentation of contract text into clauses.
    Splits by looking for numbering patterns (1., 1.1, Article I, Section 2, etc.)
    or double newlines as a fallback.
    """
    # Regex for common clause starts: 
    # Starts with a number or roman numeral followed by dot or parenthesis, 
    # OR words like "ARTICLE", "SECTION" followed by number/identifier.
    
    # This is a basic implementation. Contracts vary wildy.
    # We will try to split by Double Newlines first which is safer for plain text.
    
    chunks = text.split('\n\n')
    clauses = []
    
    for chunk in chunks:
        clean_chunk = chunk.strip()
        if len(clean_chunk) > 20: # Filter out page numbers or noise
            clauses.append(clean_chunk)
            
    return clauses

def preprocess_text(text):
    """
    Main pipeline entry.
    """
    return {
        "entities": extract_entities(text),
        "clauses": segment_into_clauses(text) 
    }
