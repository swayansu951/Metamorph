import fitz  # PyMuPDF

def extract_load_pdf(file_name):
    """Extract text from a PDF path."""
    text = ""
    with fitz.open(file_name) as doc:
        for page in doc:
            text += page.get_text()

    return text
    
