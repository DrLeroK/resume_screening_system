# 🤖 AI-Powered Resume & Applicant Screening System

An intelligent resume screening system that uses Natural Language Processing (NLP) to parse resumes, extract key information, and match candidates to job descriptions with high accuracy.

## ✨ Features

- 📄 **Resume Parsing** - Extract text from PDF/DOCX files
- 🔍 **Information Extraction** - Skills, experience, education using spaCy
- 🧠 **Semantic Embeddings** - Convert text to vectors using Sentence Transformers
- ⚡ **Fast Similarity Search** - FAISS for real-time candidate matching
- 🎯 **Smart Matching** - Weighted scoring (Skills 35%, Experience 25%, Education 15%, Semantic 25%)
- 📊 **Bias Detection** - Fairness metrics (Statistical Parity, Demographic Parity, Equal Opportunity, Disparate Impact)
- 🖥️ **Interactive Dashboard** - Streamlit frontend with bulk upload, search, and analytics
- 🔄 **Async Processing** - Background task queue for large volumes


## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- LibreOffice (for PDF conversion)

### Installation

```bash
# Clone repository
git clone https://github.com/DrLeroK/resume_screening_system.git
cd resume_screening_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_lg



# Running the system

# Terminal 1: Start Backend
python run.py
# Runs on http://localhost:8000

# Terminal 2: Start Frontend
streamlit run streamlit_app.py
# Runs on http://localhost:8501



# API Endpoints
Method	Endpoint	Description
POST	/resumes/upload	Upload resume (PDF/DOCX)
GET	/resumes/	List all resumes
GET	/resumes/{id}	Get resume details
DELETE	/resumes/{id}	Delete resume
POST	/jobs/create	Create job description
GET	/jobs/	List all jobs
POST	/matches/for-job/{id}	Get candidate matches
POST	/search/	Semantic search
GET	/health	System health check


# Example usage

# Create a job
curl -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"title":"Python Developer","description":"...","required_skills":["Python","FastAPI"]}'

# Upload a resume
curl -X POST http://localhost:8000/resumes/upload \
  -F "file=@resume.pdf"

# Get matches
curl -X POST "http://localhost:8000/matches/for-job/{job_id}?top_k=10"


# 🛠️ Tech Stack
Category	   Technology
Backend	       FastAPI, Python 3.12
NLP	           spaCy, Sentence-Transformers
ML	           PyTorch, Transformers, FAISS
Database	   SQLite, SQLAlchemy
Frontend	   Streamlit, Plotly
Async	       asyncio, BackgroundTasks


# Project Structure

resume_screening_system/
├── app/
│   ├── api/routes/     # API endpoints
│   ├── services/       # Core logic (parser, extractor, embedder, matcher)
│   ├── models/         # Database & Pydantic models
│   └── core/           # Task manager, cache, exceptions
├── data/               # SQLite, uploads, FAISS index
├── test_data/          # Sample resumes
├── run.py              # Server entry point
├── streamlit_app.py    # Frontend application
└── requirements.txt    # Dependencies


# 📈 Performance
Resume Processing: ~5-10 seconds per resume

Real-time Matching: <500ms for 100 resumes

Semantic Search: <200ms with FAISS

# 🤝 Contributing
Fork the repository

Create a feature branch

Commit your changes

Push to the branch

Open a Pull Request

# 📄 License
MIT License - see LICENSE file for details.

# 🙏 Acknowledgments
spaCy - Industrial-strength NLP
Sentence-Transformers - State-of-the-art embeddings
FAISS - Efficient similarity search
FastAPI - Modern Python web framework

Made with ❤️ for HR and Recruitment Teams
