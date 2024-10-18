import os
import requests
from flask import Flask, render_template, request, jsonify
from lxml import html
from PyPDF2 import PdfReader  # Importing PdfReader to read PDF files

# Initialize Flask app
app = Flask(__name__)

# Set up your API key for GroqCloud
api_key = os.getenv("GROQ_API_KEY")  # Ensure this is set in Replit Secrets

if not api_key:
    raise ValueError("API key for GroqCloud not found. Please set it in Replit Secrets.")

# Function to read the entire PDF content
def read_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return ' '.join(text).strip()
    except Exception as e:
        raise ValueError(f"Error reading PDF file: {e}")

# Function to scrape the webpage
def scrape_webpage(url: str) -> str:
    try:
        response = requests.get(url)

        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve the page, status code: {response.status_code}")

        tree = html.fromstring(response.content)

        # Extract meaningful text from paragraphs, headings, and divs
        paragraphs = tree.xpath('//p//text()')
        headings = tree.xpath('//h1//text() | //h2//text()')
        divs = tree.xpath('//div//text()')

        content = paragraphs + headings + divs

        if not content:
            raise ValueError("No content found on the page.")

        # Join content to return a single string
        return ' '.join(content).strip()

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error occurred while trying to scrape the webpage: {e}")

# Function to interact with the Llama-3 model using GroqCloud API
def get_model_response(user_message: str, document_content: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Construct the prompt with document content and user query
    prompt = f"Here is some content from a document: '{document_content[:3000]}'\n\nQuestion: {user_message}"

    data = {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "model": "llama3-8b-8192"
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)

    if response.status_code != 200:
        raise ValueError(f"Failed to get response from Groq API, status code: {response.status_code}")

    return response.json()['choices'][0]['message']['content']

# Route for home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for processing user queries and uploading PDF
@app.route('/upload', methods=['POST'])
def upload_pdf_and_answer():
    user_question = request.form.get('question')
    pdf_file = request.files.get('file')

    if not pdf_file or not user_question:
        return jsonify({"error": "PDF file or question not provided"}), 400

    try:
        # Save the uploaded PDF file temporarily
        pdf_file_path = os.path.join('/tmp', pdf_file.filename)
        pdf_file.save(pdf_file_path)

        # Read content from the uploaded PDF file
        document_content = read_pdf(pdf_file_path)

        # Get response from Llama-3 model based on the PDF content and user query
        model_response = get_model_response(user_question, document_content)

        return jsonify({"file_name": pdf_file.filename, "answer": model_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route for processing user queries and scraping webpage
@app.route('/scrape', methods=['POST'])
def scrape_and_answer():
    url = request.json.get('url')
    user_question = request.json.get('question')

    if not url or not user_question:
        return jsonify({"error": "URL or question not provided"}), 400

    try:
        # Scrape content from the provided URL
        scraped_content = scrape_webpage(url)

        # Get response from Llama-3 model based on the scraped content and user query
        model_response = get_model_response(user_question, scraped_content)

        return jsonify({"url": url, "answer": model_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app with Werkzeug
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)