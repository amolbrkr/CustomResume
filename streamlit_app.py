import streamlit as st
import pdfplumber
import openai
import re
from weasyprint import HTML
from bs4 import BeautifulSoup
import tempfile
import os

# Set up OpenAI and Streamlit
client = openai.Client(api_key=st.secrets["OPENAI_API_KEY"])
st.title("AI-Powered Resume Customizer")

def extract_text_from_pdf(uploaded_file):
    with pdfplumber.open(uploaded_file) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)

def convert_to_html(text):
    # Basic conversion to HTML with preserved structure
    html_content = """<html><head><style>
        body { font-family: 'Times New Roman'; margin: 40px; padding: 20px; }
        h2 { color: #2E4053; border-bottom: 2px solid #2E4053; font-weight: bold; }
        ul { margin-top: 5px; margin-bottom: 15px; padding-left: 20px; }
        li { margin-bottom: 5px; }
    </style></head><body>"""
    
    sections = re.split(r'\n\s*\n', text)
    for section in sections:
        if re.match(r'^[A-Z][a-zA-Z ]+$', section.strip()):
            html_content += f"<h2>{section.strip()}</h2>"
        else:
            # Convert bullet points to list items
            lines = section.split('\n')
            html_content += "<ul>"
            for line in lines:
                if line.strip().startswith(('•', '-', '*')):
                    html_content += f"<li>{line.strip()[1:].strip()}</li>"
                else:
                    html_content += f"<p>{line.strip()}</p>"
            html_content += "</ul>"
    
    html_content += "</body></html>"
    return html_content

def modify_resume_html(html_content, job_desc, notes):
    prompt = f"""
    Modify ONLY THE TEXT CONTENT WITHIN <li> TAGS in this HTML resume to better match the job description. 
    PRESERVE ALL HTML TAGS AND STRUCTURE EXACTLY. Follow these rules:

    1. Only modify text between <li> and </li> tags
    2. Keep the same number of list items in each section
    3. Replace technologies from job description where appropriate
    4. Use concrete achievements: "Accomplished [X] by doing [Y], resulting in [Z]"
    5. Maintain original capitalization and punctuation style
    6. Never add or remove any HTML tags

    Job Description: {job_desc}
    User Notes: {notes}

    HTML Resume:
    {html_content}
    """
    
    response = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are an expert resume customization AI."},
            {"role": "user", "content": prompt}
        ]
    )
    
    # Get and clean the response content
    modified_content = response.choices[0].message.content.strip()
    if modified_content.startswith("```") and modified_content.endswith("```"):
        lines = modified_content.splitlines()
        if len(lines) >= 3:
            modified_content = "\n".join(lines[1:-1]).strip()
    
    # Sanitize HTML output
    soup = BeautifulSoup(modified_content, 'html.parser')
    return soup.prettify()

def html_to_pdf(html_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        # Create a proper HTML document if it doesn't already have the structure
        if not html_content.strip().startswith("<html"):
            html_content = f"<html><body>{html_content}</body></html>"
        
        # Use the correct WeasyPrint syntax
        HTML(string=html_content).write_pdf(tmpfile.name)
        return tmpfile.name

# Sidebar inputs
with st.sidebar:
    st.header("Inputs")
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    job_desc = st.text_area("Job Description", height=300)
    user_notes = st.text_input("Custom Instructions")
    process_btn = st.button("Generate Custom Resume")

# Main content
if process_btn and resume_file and job_desc:
    with st.spinner("Analyzing and customizing..."):
        try:
            # Extract and convert to HTML
            raw_text = extract_text_from_pdf(resume_file)
            original_html = convert_to_html(raw_text)
            
            # Generate modified HTML
            modified_html = modify_resume_html(original_html, job_desc, user_notes)
            
            # Display preview
            st.subheader("HTML Preview")
            st.components.v1.html(modified_html, height=800, scrolling=True)
            
            # Add edit capabilities
            with st.expander("Edit HTML Content"):
                edited_html = st.text_area("Modify HTML", modified_html, height=400)
                
            # Generate PDF
            pdf_path = html_to_pdf(edited_html)
            
            # Download button
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download Custom Resume",
                    data=f,
                    file_name="custom_resume.pdf",
                    mime="application/pdf"
                )
            
            # Cleanup
            os.unlink(pdf_path)
            
        except Exception as e:
            st.error(f"Error processing resume: {str(e)}")
else:
    st.info("Upload resume and enter job description to get started")

st.sidebar.markdown("---")