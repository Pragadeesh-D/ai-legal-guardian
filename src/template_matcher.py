"""
Template Compatibility Matcher

Enforces strict contract-template compatibility to prevent legal mismatches.
Only allows downloading templates that match the analyzed contract type.
"""

# Compatibility mapping: contract type -> allowed templates
COMPATIBILITY_MAP = {
    "Service Agreement": ["Service Agreement"],
    "Employment Agreement": ["Employment Agreement"],
    "Employment Contract": ["Employment Agreement"],  # Alias
    "NDA": ["NDA"],
    "Non-Disclosure Agreement": ["NDA"],  # Alias
    "Confidentiality Agreement": ["NDA"],  # Alias
    # Unsupported types (no templates available)
    "Lease Agreement": [],
    "Rental Agreement": [],
    "Partnership Agreement": [],
    "Vendor Agreement": [],
    "Purchase Agreement": [],
    "Other": []
}

# All available template types
ALL_TEMPLATES = ["Service Agreement", "Employment Agreement", "NDA"]

# Supported contract types (have at least one template)
SUPPORTED_TYPES = ["Service Agreement", "Employment Agreement", "Employment Contract", 
                   "NDA", "Non-Disclosure Agreement", "Confidentiality Agreement"]


def normalize_contract_type(contract_type):
    """
    Normalize contract type string for consistent matching.
    
    Args:
        contract_type: Raw contract type from AI analysis
        
    Returns:
        Normalized contract type string
    """
    if not contract_type:
        return "Other"
    
    # Convert to title case and strip whitespace
    normalized = contract_type.strip().title()
    
    # Handle common aliases
    aliases = {
        "Employment Contract": "Employment Agreement",
        "Non-Disclosure Agreement": "NDA",
        "Confidentiality Agreement": "NDA",
        "Service Contract": "Service Agreement",
        "Nda": "NDA"  # Fix for title() conversion of acronym
    }
    
    return aliases.get(normalized, normalized)


def get_compatible_templates(contract_type):
    """
    Get list of template names compatible with the given contract type.
    
    Args:
        contract_type: Contract type from AI analysis
        
    Returns:
        List of compatible template names (may be empty)
    """
    normalized = normalize_contract_type(contract_type)
    return COMPATIBILITY_MAP.get(normalized, [])


def is_template_compatible(contract_type, template_name):
    """
    Check if a specific template is compatible with the contract type.
    
    Args:
        contract_type: Contract type from AI analysis
        template_name: Name of the template to check
        
    Returns:
        True if compatible, False otherwise
    """
    compatible = get_compatible_templates(contract_type)
    return template_name in compatible


def is_supported_contract_type(contract_type):
    """
    Check if the contract type has any templates available.
    
    Args:
        contract_type: Contract type from AI analysis
        
    Returns:
        True if at least one template is available, False otherwise
    """
    normalized = normalize_contract_type(contract_type)
    return normalized in SUPPORTED_TYPES


def get_all_templates():
    """
    Get list of all available template names.
    
    Returns:
        List of all template names
    """
    return ALL_TEMPLATES.copy()
