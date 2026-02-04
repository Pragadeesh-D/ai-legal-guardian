# AI Legal Guardian ⚖️

**AI Legal Guardian** is an intelligent contract analysis tool aimed at empowering SMEs and freelancers to detect legal risks, missing clauses, and ambiguities in seconds.

## 🚀 Key Features

*   **Risk Analysis Dashboard**: Instant 0-100 risk scoring with visual gauges.
*   **Clause Breakdown**: Explains complex legalese in plain English.
*   **Chat with Contract**: Ask questions like "Is this fair?" and get answers based strictly on the document.
*   **Auto-Redrafting Templates**: Converts analyzed contracts into safer, standard templates (Service, Employment, NDA).
*   **Multilingual Support**: Handling of Indian documents (including Hindi translations).
*   **Dual Mode**: 
    *   **Live Mode**: Uses OpenAI GPT-4o for high-precision analysis.
    *   **Demo Mode**: Simulation mode for testing scenarios without API costs.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/ai-legal-guardian.git
    cd ai-legal-guardian
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    python -m spacy download en_core_web_sm
    ```

3.  **Set up keys**:
    *   Create a `.env` file in the root directory.
    *   Add your API key:
        ```
        OPENAI_API_KEY=sk-your-key-here
        ```

4.  **Run the application**:
    ```bash
    streamlit run app.py
    ```

## 📂 Project Structure

*   `app.py`: Main Streamlit application entry point.
*   `src/`: Core logic modules (LLM engine, Document Parser, Template Matcher).
*   `test_contracts/`: Sample files for testing (PDF, DOCX, TXT).
*   `templates/`: Standard legal templates used for auto-population.

## 🏆 Hackathon Submission
Built for HCL Hackathon 2026. Focuses on **Transparency, Speed, and Accessibility** in legal tech.

---
*Note: This project uses OpenAI GPT-4o. Ensure you have a valid API key or use the built-in Demo Mode.*
