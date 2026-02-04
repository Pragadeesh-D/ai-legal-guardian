import streamlit as st
import os
import json
import pandas as pd
import plotly.graph_objects as go
from src.document_parser import parse_document
from src.nlp_processor import preprocess_text
from src.llm_engine import analyze_contract_with_llm, chat_with_assistant, extract_template_data
from src.risk_engine import process_risk_analysis
from src.exporter import generate_pdf_report
from src.templates import populate_template, generate_docx, get_template_structure
from src.template_matcher import get_compatible_templates, is_template_compatible, get_all_templates, is_supported_contract_type
from dotenv import load_dotenv

# Page Config
st.set_page_config(
    page_title="Contract AI - Risk Assessment Bot",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Environment
load_dotenv()

# CSS for better UI
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .risk-high { color: #dc3545; font-weight: bold; }
    .risk-medium { color: #ffc107; font-weight: bold; }
    .risk-low { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def safe_text(text):
    """Escapes $ to prevent Streamlit from treating it as LaTeX math."""
    if text:
        return text.replace("$", "\\$")
    return ""

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2620/2620436.png", width=80)
    st.title("Contract AI")
    st.markdown("Your intelligent legal assistant for risk assessment.")
    
    # API Keys Logic
    st.write("### 🔑 API Configuration")
    
    # Demo Mode Toggle (moved to top for better UX)
    # Demo Mode Toggle (moved to top for better UX)
    use_demo_mode = st.checkbox("☑️ Enable Demo Mode (Mock Data)", value=False, help="Test the UI without using API credits. Answers only predefined questions.")
    
    if use_demo_mode:
        st.info("🎭 **Demo Mode Active**: AI model selection disabled. Using mock data.")
        provider_code = "demo"
        active_api_key = "demo_key"
    else:
        st.write("### 🤖 Model Configuration")
        # Fixed Model: OpenAI GPT-4o
        st.success("⚡ Powered by **OpenAI GPT-4o**")
        
        active_api_key = None
        provider_code = "openai"
        active_api_key = os.getenv("OPENAI_API_KEY")
        if not active_api_key:
            active_api_key = st.text_input("Enter OpenAI API Key", type="password", help="Requires 'gpt-4o' model access. Credits required.")
            if active_api_key: os.environ["OPENAI_API_KEY"] = active_api_key

    st.divider()
    
    st.write("### 📂 Upload Contract")
    st.caption("Supports PDF, DOCX, and TXT files. Hindi contracts are automatically translated.")
    
    # Initialize uploader key for forcing widget reset
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    
    uploaded_file = st.file_uploader(
        "Upload PDF, DOCX, or TXT", 
        type=["pdf", "docx", "txt"], 
        key=f"file_uploader_{st.session_state.uploader_key}"
    )
    
    # Handle new file upload
    if uploaded_file is not None:
        # Store uploaded file in session state
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = {}
        
        # Add to collection if new
        file_id = uploaded_file.name
        if file_id not in st.session_state.uploaded_files:
            st.session_state.uploaded_files[file_id] = uploaded_file
            
            # Auto-select new upload AND clear analysis
            st.session_state.active_contract = file_id 
            st.session_state.analysis_result = None
            st.session_state.contract_text = ""
            st.session_state.template_data = None
            st.session_state.chat_history = []
            st.rerun()
    
    # Display uploaded files and allow selection
    if "uploaded_files" in st.session_state and st.session_state.uploaded_files:
        st.markdown("---")
        st.write("**📋 Uploaded Contracts**")
        
        # Initialize active contract if not set
        if "active_contract" not in st.session_state or st.session_state.active_contract not in st.session_state.uploaded_files:
            st.session_state.active_contract = list(st.session_state.uploaded_files.keys())[0]
        
        # Create file list
        file_list = list(st.session_state.uploaded_files.keys())
        
        # Radio button for single selection - key includes uploader_key to force reset
        selected_file = st.radio(
            "Select active contract:",
            options=file_list,
            index=file_list.index(st.session_state.active_contract) if st.session_state.active_contract in file_list else 0,
            format_func=lambda x: f"🎯 {x}" if x == st.session_state.active_contract else f"📄 {x}",
            key=f"contract_selector_{st.session_state.uploader_key}",  # Include uploader_key
            help="Only one contract can be active at a time"
        )
        
        # Update active contract when selection changes
        if selected_file != st.session_state.active_contract:
            st.session_state.active_contract = selected_file
            # Clear previous analysis when switching files
            st.session_state.analysis_result = None
            st.session_state.contract_text = ""
            st.session_state.template_data = None
            st.session_state.chat_history = []
            st.rerun()
        
        # Delete buttons - each file gets a delete button
        st.write("**Remove Files:**")
        delete_cols = st.columns(min(len(file_list), 4))  # Max 4 columns
        for idx, file_name in enumerate(file_list):
            with delete_cols[idx % 4]:
                if st.button(f"🗑️ {file_name[:12]}...", key=f"del_{idx}_{st.session_state.uploader_key}", help=f"Remove {file_name}", use_container_width=True):
                    # Remove file
                    del st.session_state.uploaded_files[file_name]
                    
                    # Update active contract if we removed it
                    if st.session_state.active_contract == file_name:
                        if st.session_state.uploaded_files:
                            st.session_state.active_contract = list(st.session_state.uploaded_files.keys())[0]
                        else:
                            st.session_state.active_contract = None
                    
                    # Clear analysis and increment uploader_key to reset all widgets
                    st.session_state.analysis_result = None
                    st.session_state.contract_text = ""
                    st.session_state.template_data = None
                    st.session_state.chat_history = []
                    st.session_state.uploader_key += 1
                    st.rerun()
        
        # Active contract indicator
        st.success(f"✅ **Active Contract**: {st.session_state.active_contract}")

        
        # Clear all button
        st.markdown("")
        if st.button("🗑️ Clear All Contracts", help="Remove all uploaded contracts", type="secondary"):
            st.session_state.uploaded_files = {}
            st.session_state.active_contract = None
            st.session_state.analysis_result = None
            st.session_state.contract_text = ""
            st.session_state.chat_history = []
            st.session_state.uploader_key += 1
            st.rerun()
        
        st.markdown("---")
    
    process_btn = st.button("Analyze Contract", type="primary", help="Click to start AI-powered risk analysis", disabled=("uploaded_files" not in st.session_state or not st.session_state.uploaded_files))

# Session State Initialization
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "contract_text" not in st.session_state:
    st.session_state.contract_text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "active_contract" not in st.session_state:
    st.session_state.active_contract = None

# Mock Data for Demo Mode
MOCK_RESULT = {
    "contract_type": "Service Agreement (DEMO)",
    "summary": "This is a DEMO summary. The Provider agrees to build a mobile app for $50,000. Key risks include a one-sided termination clause and a strict non-compete.",
    "overall_risk_score": "High",
    "numeric_risk_score": 85,
    "key_risks": [
        {"risk": "Unilateral Termination", "severity": "High", "clause": "Provider may terminate... at any time."},
        {"risk": "Strict Non-Compete", "severity": "Medium", "clause": "Client agrees not to hire... for 5 years."}
    ],
    "clauses_analysis": [
        {"title": "Termination", "text": "Provider may terminate... 24 hours notice.", "explanation": "The provider can cancel instantly, but you need to give 6 months notice.", "risk_level": "High", "recommendation": "Negotiate for mutual 30-day notice."},
        {"title": "Liability", "text": "Total liability... limited to $10.00.", "explanation": "If they break the app, they only owe you $10.", "risk_level": "High", "recommendation": "Increase cap to contract value ($50k)."}
    ],
    "missing_clauses": ["Confidentiality / NDA", "Data Privacy"]
}

# Type-specific mock template data for demo mode
# Each contract type has realistic, domain-correct fields
DEMO_TEMPLATE_DATA = {
    "service": {
        "contract_type": "Service Agreement",
        "services": "Development of mobile application for iOS and Android platforms, including UI/UX design, backend API integration, payment gateway integration (Stripe and PayPal), deployment to app stores, and 30 days post-launch support",
        "amount": "$50,000 USD",
        "termination_notice": "Provider: 24 hours notice | Client: 6 months notice",
        "confidentiality": "Both parties acknowledge that they may have access to confidential information during the term of this Agreement and agree to maintain the confidentiality of such information.",
        "provider": "TechCorp Solutions Ltd.",
        "client": "ABC Enterprises Inc.",
        "start_date": "January 15, 2024",
        "end_date": "December 31, 2024",
        "payment_terms": "30% upfront, 40% upon development completion, 30% upon final delivery. All payments within 90 days after invoice.",
        "jurisdiction": "State of California, USA"
    },
    "employment": {
        "contract_type": "Employment Agreement",
        "services": "Software Engineer - Full Stack Development: Develop and maintain web applications using React, Node.js, and MongoDB; participate in code reviews; collaborate with cross-functional teams; mentor junior developers",
        "amount": "₹12,00,000 per annum (CTC)",
        "termination_notice": "60 days written notice after probation period (6 months probation with 15 days notice)",
        "confidentiality": "Employee acknowledges access to Confidential Information including source code, algorithms, business strategies, and customer information. Employee agrees to maintain strict confidentiality and not disclose to third parties. Obligations survive termination for 3 years.",
        "provider": "InnovateTech Private Limited",
        "client": "Mr. Rajesh Kumar",
        "start_date": "March 1, 2024",
        "end_date": "Not specified (permanent employment)",
        "payment_terms": "Monthly salary paid on last working day of each month. Basic: ₹6L, HRA: ₹2.4L, Special Allowance: ₹1.8L, PF: ₹72K",
        "jurisdiction": "Courts of Bangalore, Karnataka, India"
    },
    "nda": {
        "contract_type": "NDA",
        "services": "Exploration of potential business partnership and collaboration opportunities in the technology sector",
        "amount": "Not specified in the provided contract",
        "termination_notice": "Confidentiality obligations survive for 5 years from the date of disclosure",
        "confidentiality": "Both parties agree to protect all Confidential Information disclosed during discussions, including but not limited to: technical specifications, business plans, customer lists, financial data, and proprietary methodologies. Information may not be disclosed to third parties without prior written consent.",
        "provider": "DataSecure Technologies",
        "client": "CloudVault Systems",
        "start_date": "February 10, 2024",
        "end_date": "February 10, 2029 (5-year confidentiality period)",
        "payment_terms": "Not specified in the provided contract",
        "jurisdiction": "Courts of Mumbai, Maharashtra, India"
    }
}

def get_demo_template_data(contract_type):
    """
    Get type-specific mock template data based on detected contract type.
    Returns None for unsupported contract types.
    
    Args:
        contract_type: Detected contract type from analysis
        
    Returns:
        Dictionary of mock template data or None
    """
    # Normalize contract type
    contract_type_lower = contract_type.lower()
    
    # Map contract types to demo data keys
    if "service" in contract_type_lower:
        return DEMO_TEMPLATE_DATA["service"]
    elif "employment" in contract_type_lower:
        return DEMO_TEMPLATE_DATA["employment"]
    elif "nda" in contract_type_lower or "non-disclosure" in contract_type_lower or "confidentiality" in contract_type_lower:
        return DEMO_TEMPLATE_DATA["nda"]
    else:
        # Unsupported contract type - no template data
        return None


# Main Logic
if process_btn:
    # Get active file from session state
    if "active_contract" in st.session_state and st.session_state.active_contract:
        active_file = st.session_state.uploaded_files[st.session_state.active_contract]
        
        if use_demo_mode:
            with st.spinner("🚀 Running in DEMO MODE (Using Mock Data)..."):
                import time
                time.sleep(1.5) # Simulate processing time
                
                # CRITICAL: Detect contract type from filename
                filename_lower = st.session_state.active_contract.lower()
                
                # Determine contract type based on filename
                if "service" in filename_lower:
                    detected_type = "Service Agreement (DEMO)"
                    mock_result = {
                        "contract_type": "Service Agreement (DEMO)",
                        "summary": "This is a DEMO summary. The Provider agrees to build a mobile app for $50,000. Key risks include a one-sided termination clause and a strict non-compete.",
                        "overall_risk_score": "High",
                        "numeric_risk_score": 85,
                        "key_risks": [
                            {"risk": "Unilateral Termination", "severity": "High", "clause": "Provider may terminate with 24 hours notice."},
                            {"risk": "Strict Non-Compete", "severity": "Medium", "clause": "Client agrees not to hire provider's employees for 5 years."}
                        ],
                        "clauses_analysis": [
                            {"title": "Termination", "text": "Provider may terminate with 24 hours notice.", "explanation": "The provider can cancel instantly, but you need to give 6 months notice.", "risk_level": "High", "recommendation": "Negotiate for mutual 30-day notice."},
                            {"title": "Liability", "text": "Total liability limited to fees paid.", "explanation": "If they break the app, they only owe you the amount you paid.", "risk_level": "High", "recommendation": "Increase cap to contract value."}
                        ],
                        "missing_clauses": ["Confidentiality / NDA", "Data Privacy"]
                    }
                elif "employment" in filename_lower:
                    detected_type = "Employment Agreement (DEMO)"
                    mock_result = {
                        "contract_type": "Employment Agreement (DEMO)",
                        "summary": "This is a DEMO employment contract for a Software Engineer position at ₹12L CTC. Key risks include a 12-month non-compete and asymmetric termination notice.",
                        "overall_risk_score": "Medium",
                        "numeric_risk_score": 60,
                        "key_risks": [
                            {"risk": "Non-Compete Clause", "severity": "Medium", "clause": "Employee cannot work for competitors for 12 months after termination."},
                            {"risk": "Confidentiality Obligations", "severity": "Medium", "clause": "Confidentiality obligations survive for 3 years."}
                        ],
                        "clauses_analysis": [
                            {"title": "Notice Period", "text": "60 days notice required after probation.", "explanation": "Both parties must give 60 days notice to terminate.", "risk_level": "Low", "recommendation": "Standard for Indian IT industry."},
                            {"title": "Non-Compete", "text": "Cannot work for competitors for 12 months.", "explanation": "You cannot join competing companies for a year after leaving.", "risk_level": "Medium", "recommendation": "Negotiate to reduce to 6 months or specific geography."}
                        ],
                        "missing_clauses": ["Severance Pay", "Stock Options"]
                    }
                elif "nda" in filename_lower or "non-disclosure" in filename_lower or "confidentiality" in filename_lower:
                    detected_type = "NDA (DEMO)"
                    mock_result = {
                        "contract_type": "NDA (DEMO)",
                        "summary": "This is a DEMO NDA between two technology companies exploring business partnership. Confidentiality obligations survive for 5 years.",
                        "overall_risk_score": "Low",
                        "numeric_risk_score": 30,
                        "key_risks": [
                            {"risk": "Long Confidentiality Period", "severity": "Low", "clause": "Confidentiality obligations survive for 5 years."},
                            {"risk": "Broad Definition", "severity": "Low", "clause": "Confidential Information includes all business and technical data."}
                        ],
                        "clauses_analysis": [
                            {"title": "Confidentiality Period", "text": "Obligations survive for 5 years from disclosure.", "explanation": "You must keep information secret for 5 years.", "risk_level": "Low", "recommendation": "Standard for technology partnerships."},
                            {"title": "Permitted Use", "text": "Information can only be used for evaluating partnership.", "explanation": "You can only use the information to assess collaboration opportunities.", "risk_level": "Low", "recommendation": "Acceptable for business discussions."}
                        ],
                        "missing_clauses": ["Return of Information", "Compelled Disclosure"]
                    }
                elif "lease" in filename_lower or "rental" in filename_lower:
                    detected_type = "Lease Agreement (DEMO)"
                    mock_result = {
                        "contract_type": "Lease Agreement (DEMO)",
                        "summary": "This is a DEMO residential lease agreement for ₹30,000 per month. This is an unsupported contract type for template generation.",
                        "overall_risk_score": "Medium",
                        "numeric_risk_score": 55,
                        "key_risks": [
                            {"risk": "Security Deposit", "severity": "Low", "clause": "Security deposit of ₹90,000 (3 months rent)."},
                            {"risk": "Notice Period", "severity": "Low", "clause": "2 months notice required for termination."}
                        ],
                        "clauses_analysis": [
                            {"title": "Rent Payment", "text": "₹30,000 per month due by 5th of each month.", "explanation": "You must pay rent by the 5th day of every month.", "risk_level": "Low", "recommendation": "Standard payment terms."}
                        ],
                        "missing_clauses": ["Maintenance Responsibilities", "Subletting Terms"]
                    }
                else:
                    detected_type = "Other (DEMO)"
                    mock_result = MOCK_RESULT  # Fallback to default
                
                # Store contract text
                st.session_state.contract_text = f"This is a demo contract text for {detected_type}..."
                
                # Store analysis result
                st.session_state.analysis_result = mock_result
                
                # Get type-specific mock template data
                template_data = get_demo_template_data(detected_type)
                
                if template_data:
                    # Supported contract type - use type-specific mock data
                    st.session_state.template_data = template_data
                    st.toast("✅ Analysis Complete using Demo Data!")
                else:
                    # Unsupported contract type - no template data
                    st.session_state.template_data = None
                    st.toast("✅ Analysis Complete! (No templates available for this contract type)")

                
        elif not active_api_key:
            st.error(f"❌ Please provide an API Key for {provider if 'provider' in locals() else 'the selected model'} to proceed.")
        else:
            try:
                with st.spinner("📄 Parsing document..."):
                    text = parse_document(active_file)
                    st.session_state.contract_text = text
                    
                with st.spinner("🔍 Extracting entities & clauses..."):
                    nlp_data = preprocess_text(text)
                    
                with st.spinner(f"🤖 Analyzing risks with AI ({provider if 'provider' in locals() else 'AI'})..."):
                    llm_raw = analyze_contract_with_llm(text, nlp_data["entities"], provider=provider_code)
                    
                    # Check for API errors expressly
                    if "error" in llm_raw:
                        err_msg = llm_raw['error']
                        st.error(f"⚠️ AI Analysis Failed: {err_msg}")
                        if "429" in str(err_msg) or "quota" in str(err_msg).lower():
                            st.error("🚨 **OUT OF API CREDITS**")
                            st.info("Your OpenAI API Key has exceeded its quota. Please switch to **Demo Mode** in the sidebar to continue testing the application logic with mock data.")
                    else:
                        final_result = process_risk_analysis(llm_raw, text, nlp_data["entities"])
                        st.session_state.analysis_result = final_result
                        
                        # Extract template data for population
                        with st.spinner("📋 Extracting contract data for templates..."):
                            try:
                                template_data = extract_template_data(
                                    text,
                                    final_result.get("contract_type", "Other"),
                                    provider=provider_code
                                )
                                st.session_state.template_data = template_data
                            except Exception as extract_err:
                                st.warning(f"Template extraction failed: {str(extract_err)}")
                                st.session_state.template_data = None
                        
                        st.toast("✅ Analysis Complete!")
                        st.success("Analysis Successfully Completed with Live API!")
                        
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
    else:
        st.warning("⚠️ Please upload a contract file first.")

# Dashboard
if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"📄 Analysis: {result.get('contract_type', 'Contract')}")
        st.info(f"**Summary**: {result.get('summary', 'No summary.')}")
    
    with col2:
        score = result.get('numeric_risk_score', 0)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            title = {'text': "Risk Score"},
            gauge = {'axis': {'range': [None, 100]},
                     'bar': {'color': "darkblue"},
                     'steps' : [
                         {'range': [0, 30], 'color': "lightgreen"},
                         {'range': [30, 70], 'color': "orange"},
                         {'range': [70, 100], 'color': "red"}],
                     'threshold' : {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': score}}))
        fig.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["⚠️ Key Risks", "🔍 Clause Analysis", "💬 Assistant", "📥 Export", "📚 Templates", "📊 Knowledge Base"])
    
    with tab1:
        st.subheader("Critical Risks Identified")
        st.caption("These are clauses that may put you at a disadvantage. Review carefully before signing.")
        risks = result.get("key_risks", [])
        if risks:
            for r in risks:
                with st.expander(f"{r.get('risk', 'Unknown Risk')} ({r.get('severity', 'Medium')})", expanded=True):
                    st.write(r.get("clause", ""))
        else:
            st.success("No critical risks identified.")
            
        st.subheader("Compliance & Missing Items")
        st.caption("Standard clauses that should be present in this type of contract.")
        missing = result.get("missing_clauses", [])
        if missing:
            for m in missing:
                st.warning(f"Missing: {m}")
        else:
            st.success("Standard compliance check passed.")

        # --- New Feature: Ambiguity Detection ---
        st.subheader("🤔 Ambiguous/Vague Clauses")
        st.caption("Clauses with unclear language that could be interpreted in multiple ways.")
        ambiguous = result.get("ambiguous_clauses", [])
        if ambiguous:
            for amb in ambiguous:
                st.info(f"**Clause**: \"{amb.get('clause')}\"\n\n**Issue**: {amb.get('reason')}")
        else:
             st.success("No significant ambiguity detected.")
        # ----------------------------------------

    with tab2:
        st.subheader("Clause-by-Clause Breakdown")
        clauses = result.get("clauses_analysis", [])
        for c in clauses:
            risk_color = "red" if c.get("risk_level") == "High" else "orange" if c.get("risk_level") == "Medium" else "green"
            with st.expander(f"{c.get('title', 'Clause')} - :{risk_color}[{c.get('risk_level')}]"):
                st.markdown(f"**Original Text:**\n> {safe_text(c.get('text', ''))}")
                st.markdown(f"**Explanation:** {safe_text(c.get('explanation', ''))}")
                if c.get("recommendation"):
                    st.info(f"💡 **Suggestion:** {safe_text(c.get('recommendation'))}")

    with tab3:
        st.subheader("Ask about this contract")
        st.caption("Ask specific questions about clauses, risks, or terms. The AI has read the entire contract.")
        
        # Suggested Questions
        suggested_questions = [
            "What are the main risks?",
            "Is the termination clause fair?",
            "Explain the indemnity clause",
            "Are there any missing standard clauses?",
            "Summarize the payment terms"
        ]
        
        # Display suggested questions as pills/buttons
        st.write("💡 **Suggested Questions:**")
        cols = st.columns(len(suggested_questions) if len(suggested_questions) < 4 else 3)
        for i, question in enumerate(suggested_questions):
            col_idx = i % 3
            if cols[col_idx].button(question, key=f"q_{i}", use_container_width=True):
                # We can't directly populate chat_input, so we'll run the query immediately
                st.session_state.chat_history.append({"role": "user", "content": question})
                with st.spinner("Thinking..."):
                    if use_demo_mode:
                        import time
                        time.sleep(1)
                        # Re-use the smart mock logic from below
                        q_lower = question.lower()
                        if "risk" in q_lower:
                            answer = "Based on my analysis, this contract has a **High Risk Score (85/100)**. \\n\\nThe main risks are the **Unilateral Termination** clause (Client needs 6 months notice vs Provider's 24 hours) and the **Strict Non-Compete** (5 years is unusually long)."
                        elif "termination" in q_lower:
                            answer = "The **Termination Clause** is very one-sided. \\n\\n- **Provider**: Can cancel with just 24 hours notice.\\n- **Client (You)**: Must provide 6 months notice and can only terminate for 'material breach'.\\n\\n**Recommendation**: Negotiate for a mutual 30-day notice period."
                        elif "payment" in q_lower:
                            answer = "Payment is due **90 days** after invoice date, which is quite long for an SME. Standard terms are usually Net 30 or Net 15."
                        elif "indemnity" in q_lower:
                            answer = "The indemnity clause is broad, requiring you to cover 'all losses' arising from any breach. It lacks a cap or 'gross negligence' qualifier."
                        elif "compliance" in q_lower or "missing" in q_lower:
                            answer = "The contract is **Missing** key standard clauses for Indian SMEs:\\n\\n1. **Confidentiality / NDA**: No protection for your business data.\\n2. **Data Privacy**: No mention of how user data is handled (critical under DPDP Act)."
                        elif "summary" in q_lower:
                            answer = "This is a Service Agreement where the Provider builds a mobile app for \\\\$50,000. Payment is due 90 days after completion."
                        else:
                             answer = "This is a **Demo Response**. \\n\\nSince I am in 'Mock Mode', I can only answer questions about the *specific risks* I was programmed to detect in this sample (Termination, Liability, Non-Compete). \\n\\n**To get flexible, AI-powered answers for ANY question, please use a live API Key.**"
                    else:
                        answer = chat_with_assistant(st.session_state.chat_history[:-1], question, st.session_state.contract_text, provider=provider_code)
                
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()

        user_input = st.chat_input("Ask a question (e.g., 'Is the termination clause fair?')")
        
        # Display history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)
                
            with st.spinner("Thinking..."):
                if use_demo_mode:
                    import time
                    time.sleep(1)
                    # Smarter Mock Logic
                    q_lower = user_input.lower()
                    if "risk" in q_lower:
                        answer = "Based on my analysis, this contract has a **High Risk Score (85/100)**. \\n\\nThe main risks are the **Unilateral Termination** clause (Client needs 6 months notice vs Provider's 24 hours) and the **Strict Non-Compete** (5 years is unusually long)."
                    elif "termination" in q_lower:
                        answer = "The **Termination Clause** is very one-sided. \\n\\n- **Provider**: Can cancel with just 24 hours notice.\\n- **Client (You)**: Must provide 6 months notice and can only terminate for 'material breach'.\\n\\n**Recommendation**: Negotiate for a mutual 30-day notice period."
                    elif "liability" in q_lower:
                        answer = "The **Liability Clause** is capped at **\\\\$10.00**, which is effectively zero coverage. This puts you at huge risk if the software fails. You should ask to increase this cap to at least the contract value (\\\\$50,000)."
                    elif "compliance" in q_lower or "missing" in q_lower:
                        answer = "The contract is **Missing** key standard clauses for Indian SMEs:\\n\\n1. **Confidentiality / NDA**: No protection for your business data.\\n2. **Data Privacy**: No mention of how user data is handled (critical under DPDP Act)."
                    elif "summary" in q_lower:
                        answer = "This is a Service Agreement where the Provider builds a mobile app for \\\\$50,000. Payment is due 90 days after completion."
                    else:
                        answer = "This is a **Demo Response**. \\n\\nSince I am in 'Mock Mode', I can only answer questions about the *specific risks* I was programmed to detect in this sample (Termination, Liability, Non-Compete). \\n\\n**To get flexible, AI-powered answers for ANY question, please use a live API Key.**"
                else:
                    answer = chat_with_assistant(st.session_state.chat_history[:-1], user_input, st.session_state.contract_text, provider=provider_code)
            
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.write(safe_text(answer))

    with tab4:
        st.subheader("Export Report")
        # Prepare PDF data immediately if analysis is ready
        if 'analysis_result' in st.session_state and st.session_state.analysis_result:
            # We generate the PDF in memory
            from src.exporter import generate_pdf_report
            
            try:
                # generate_pdf_report returns a BytesIO buffer
                pdf_buffer = generate_pdf_report(st.session_state.analysis_result)
                pdf_bytes = pdf_buffer.getvalue()
                    
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name="contract_risk_report.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="download_pdf_report"
                )
                st.success("Report is ready for download.")
                
                # --- Audit Logging (New Feature) ---
                try:
                    import datetime
                    log_entry = {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "contract_type": st.session_state.analysis_result.get("contract_type"),
                        "risk_score": st.session_state.analysis_result.get("numeric_risk_score"),
                        "provider": provider_code if 'provider_code' in locals() else "unknown"
                    }
                    log_file = "data/audit_logs/trail.json"
                    # Load existing logs
                    if os.path.exists(log_file):
                        with open(log_file, "r") as f:
                            logs = json.load(f)
                    else:
                        logs = []
                    
                    logs.append(log_entry)
                    if not os.path.exists("data/audit_logs"):
                        os.makedirs("data/audit_logs")
                    with open(log_file, "w") as f:
                        json.dump(logs, f, indent=2)
                        
                except Exception as log_err:
                    print(f"Logging failed: {log_err}")
                # -----------------------------------
                
            except Exception as e:
                st.error(f"Failed to generate PDF: {str(e)}")

    with tab5:
        st.subheader("📚 AI-Populated Contract Templates")
        st.caption("Download professionally structured templates populated with data extracted from your analyzed contract.")
        
        # Check if template data is available
        # Check if analysis has been performed
        if 'analysis_result' not in st.session_state or not st.session_state.analysis_result:
             st.info("📋 **Upload and analyze a contract first** to generate populated templates.")
             st.markdown("---")
             st.write("**How it works:**")
             st.write("1. Upload a contract")
             st.write("2. Click 'Analyze Contract'")
             st.write("3. AI extracts key data (parties, amounts, terms, etc.)")
             st.write("4. Templates are automatically populated with your contract's data")
             st.write("5. Download in .txt or .docx format")
        else:
            # Analysis done - check if we have template data (Supported) or not (Unsupported)
            template_data = st.session_state.get('template_data')
            
            if template_data:
                # Supported Contract Type
                contract_type = template_data.get("contract_type", "Unknown")
            else:
                # Unsupported Contract Type (e.g. Lease)
                # Get type from analysis result instead
                raw_type = st.session_state.analysis_result.get("contract_type", "Unknown")
                # Remove (DEMO) suffix if present for clean display
                contract_type = raw_type.replace("(DEMO)", "").strip()
            
            # Get compatible templates
            compatible_templates = get_compatible_templates(contract_type)
            all_templates = get_all_templates()
            
            # Display contract type and compatibility info
            if template_data:
                st.success(f"✅ **Detected Contract Type**: {contract_type}")
            else:
                st.warning(f"⚠️ **Detected Contract Type**: {contract_type}")
            
            if compatible_templates:
                st.caption(f"Compatible templates: {', '.join(compatible_templates)}")
            else:
                st.error(f"❌ **No templates available for {contract_type}**")
                st.info("Template generation is currently supported for: Service Agreement, Employment Agreement, and NDA contracts.")
            
            st.markdown("---")
            
            # Display all templates with compatibility status
            for template_name in all_templates:
                is_compatible = is_template_compatible(contract_type, template_name)
                
                # Template header
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if is_compatible:
                        st.write(f"✅ **{template_name}**")
                        st.caption("Compatible with your contract")
                    else:
                        st.write(f"🔒 **{template_name}**")
                        st.caption("Not compatible with this contract type")
                
                with col2:
                    # .txt download
                    if is_compatible:
                        populated_text = populate_template(template_name, template_data)
                        st.download_button(
                            label="📄 .txt",
                            data=populated_text,
                            file_name=f"{template_name.replace(' ', '_')}_populated.txt",
                            mime="text/plain",
                            key=f"download_txt_{template_name}",
                            help="Download as plain text file",
                            use_container_width=True
                        )
                    else:
                        st.button("📄 .txt", disabled=True, key=f"disabled_txt_{template_name}", use_container_width=True)
                
                with col3:
                    # .docx download
                    if is_compatible:
                        try:
                            docx_buffer = generate_docx(template_name, template_data)
                            st.download_button(
                                label="📝 .docx",
                                data=docx_buffer,
                                file_name=f"{template_name.replace(' ', '_')}_populated.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"download_docx_{template_name}",
                                help="Download as Word document",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Error generating DOCX: {str(e)}")
                    else:
                        st.button("📝 .docx", disabled=True, key=f"disabled_docx_{template_name}", use_container_width=True)
            
            # Extracted data viewer (expandable)
            st.markdown("---")
            with st.expander("🔍 View Extracted Contract Data (Advanced)"):
                st.caption("This is the structured data extracted from your contract by AI. It's used to populate the templates above.")
                st.json(template_data)

    with tab6:
        st.subheader("📊 Knowledge Base & Audit History")
        st.caption("Analytics from all contracts analyzed by this system. Helps identify trends and common risks.")
        
        log_file = "data/audit_logs/trail.json"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    logs = json.load(f)
                
                if logs:
                    df = pd.DataFrame(logs)
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Contracts Analyzed", len(df), help="Number of contracts processed through this system")
                    avg_risk = df["risk_score"].mean()
                    col2.metric("Average Risk Score", f"{avg_risk:.1f}", help="Mean risk score across all analyzed contracts (0=Safe, 100=Very Risky)")
                    
                    # Chart
                    st.write("### Risk Distribution")
                    st.caption("Shows which contract types you've analyzed most frequently.")
                    st.bar_chart(df["contract_type"].value_counts())
                    
                    # Table
                    st.write("### Recent Activity")
                    st.caption("Last 10 contracts analyzed, sorted by time.")
                    st.dataframe(df[["timestamp", "contract_type", "risk_score"]].tail(10))
                else:
                    st.info("No logs found yet.")
            except Exception as e:
                st.error("Error reading logs.")
        else:
            st.info("Knowledge Base is empty. Analyze contracts to build data.")

else:
    st.info("Upload a document to begin analysis.")
