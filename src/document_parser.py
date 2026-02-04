
import PyPDF2
from docx import Document
import io

def extract_text_from_pdf(file_stream):
    """Result: str"""
    try:
        # Reset file pointer to beginning
        file_stream.seek(0)
        
        reader = PyPDF2.PdfReader(file_stream)
        text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_stream):
    """Result: str"""
    try:
        # Reset file pointer to beginning
        file_stream.seek(0)
        
        doc = Document(file_stream)
        text = [para.text for para in doc.paragraphs]
        return "\n".join(text)
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_stream):
    """Result: str"""
    try:
        # CRITICAL: Reset file pointer to beginning before reading
        file_stream.seek(0)
        
        # file_stream might be bytesIO from streamlit
        content = file_stream.read()
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return content
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

def parse_document(uploaded_file):
    """
    Dispatcher based on file type.
    uploaded_file: Streamlit UploadedFile object or similar
    """
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    elif filename.endswith(".txt"):
        return extract_text_from_txt(uploaded_file)
    else:
        return "Unsupported file format."
