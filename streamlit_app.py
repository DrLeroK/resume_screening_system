"""
AI-Powered Resume Screening System - Streamlit Frontend
COMPLETE VISIBILITY & UX FIXES
"""

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import time

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# COMPLETE CSS FIX - ALL TEXT VISIBLE EVERYWHERE
# ============================================================
st.markdown("""
<style>
    /* ===== GLOBAL TEXT COLOR ===== */
    * {
        color: #1a1a1a !important;
    }
    
    /* ===== MAIN APP ===== */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* ===== HEADINGS ===== */
    h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
        font-weight: 700 !important;
    }
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #1a1a1a !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #1a1a1a !important;
    }
    
    /* ===== DROPDOWNS / SELECT BOXES ===== */
    .stSelectbox > div > div {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #4CAF50 !important;
    }
    
    .stSelectbox > div > div > div {
        color: #1a1a1a !important;
    }
    
    /* Dropdown options when expanded */
    .stSelectbox > div > div ul {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
    
    .stSelectbox > div > div ul li {
        color: #1a1a1a !important;
        background-color: #ffffff !important;
    }
    
    .stSelectbox > div > div ul li:hover {
        background-color: #e9ecef !important;
        color: #1a1a1a !important;
    }
    
    /* ===== FILE UPLOADER ===== */
    .stFileUploader {
        background-color: #ffffff !important;
        border: 2px dashed #ced4da !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }
    
    .stFileUploader > div {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
    
    .stFileUploader label {
        color: #1a1a1a !important;
        font-weight: 600 !important;
    }
    
    .stFileUploader p, .stFileUploader span {
        color: #1a1a1a !important;
    }
    
    /* File uploader drag area */
    .stFileUploader > div > div {
        background-color: #f8f9fa !important;
        border: 2px dashed #ced4da !important;
        border-radius: 8px !important;
        color: #1a1a1a !important;
    }
    
    .stFileUploader > div > div:hover {
        background-color: #e9ecef !important;
        border-color: #4CAF50 !important;
    }
    
    /* ===== TEXT INPUTS ===== */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #6c757d !important;
    }
    
    .stTextInput label {
        color: #1a1a1a !important;
        font-weight: 500 !important;
    }
    
    /* ===== TEXT AREAS ===== */
    .stTextArea > div > div > textarea {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: #6c757d !important;
    }
    
    .stTextArea label {
        color: #1a1a1a !important;
        font-weight: 500 !important;
    }
    
    /* ===== NUMBER INPUTS ===== */
    .stNumberInput > div > div > input {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
    }
    
    .stNumberInput label {
        color: #1a1a1a !important;
        font-weight: 500 !important;
    }
    
    /* ===== SLIDERS ===== */
    .stSlider label {
        color: #1a1a1a !important;
        font-weight: 500 !important;
    }
    
    .stSlider > div > div > div {
        color: #1a1a1a !important;
    }
    
    /* ===== METRICS ===== */
    .stMetric {
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
        padding: 15px !important;
        border: 1px solid #dee2e6 !important;
    }
    
    .stMetric label, .stMetric div {
        color: #1a1a1a !important;
    }
    
    .stMetric .stMetricValue, .stMetric .stMetricDelta {
        color: #1a1a1a !important;
    }
    
    /* ===== MATCH CARDS ===== */
    .match-card {
        background-color: #f8f9fa !important;
        padding: 20px !important;
        border-radius: 10px !important;
        margin-bottom: 10px !important;
        border: 1px solid #e9ecef !important;
    }
    
    .match-card * {
        color: #1a1a1a !important;
    }
    
    .match-card b, .match-card strong {
        color: #1a1a1a !important;
    }
    
    .match-card table, .match-card td, .match-card tr {
        color: #1a1a1a !important;
    }
    
    .match-card details, .match-card summary {
        color: #1a1a1a !important;
    }
    
    .match-card summary {
        font-weight: bold !important;
        cursor: pointer !important;
        color: #1a1a1a !important;
    }
    
    .match-card summary:hover {
        color: #4CAF50 !important;
    }
    
    /* ===== SCORE COLORS ===== */
    .score-high {
        color: #2e7d32 !important;
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    .score-medium {
        color: #e65100 !important;
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    .score-low {
        color: #c62828 !important;
        font-size: 24px !important;
        font-weight: bold !important;
    }
    
    /* ===== BUTTONS ===== */
    .stButton > button {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #43a047 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        color: white !important;
    }
    
    .stButton > button * {
        color: white !important;
    }
    
    /* Delete button */
    .delete-btn > button {
        background-color: #dc3545 !important;
    }
    
    .delete-btn > button:hover {
        background-color: #c82333 !important;
    }
    
    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        color: #1a1a1a !important;
    }
    
    .streamlit-expanderHeader * {
        color: #1a1a1a !important;
    }
    
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
    
    .streamlit-expanderContent * {
        color: #1a1a1a !important;
    }
    
    /* ===== DATAFRAMES ===== */
    .stDataFrame {
        color: #1a1a1a !important;
    }
    
    .stDataFrame table {
        color: #1a1a1a !important;
    }
    
    .stDataFrame td, .stDataFrame th {
        color: #1a1a1a !important;
    }
    
    .stDataFrame thead tr th {
        color: #1a1a1a !important;
        background-color: #f8f9fa !important;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #e9ecef !important;
    }
    
    /* ===== HOVER TOOLTIPS ===== */
    .stTooltipContent {
        color: #1a1a1a !important;
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
        padding: 8px 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    
    .stTooltipContent * {
        color: #1a1a1a !important;
    }
    
    /* ===== HOVER EFFECTS ON ELEMENTS ===== */
    .stSelectbox > div > div:hover {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1) !important;
    }
    
    .stTextInput > div > div > input:hover {
        border-color: #4CAF50 !important;
    }
    
    .stTextArea > div > div > textarea:hover {
        border-color: #4CAF50 !important;
    }
    
    /* ===== ALERTS ===== */
    .stAlert {
        border-radius: 8px !important;
    }
    
    .stAlert * {
        color: #1a1a1a !important;
    }
    
    .stAlert .stAlertContent {
        color: #1a1a1a !important;
    }
    
    /* ===== CHECKBOX ===== */
    .stCheckbox label {
        color: #1a1a1a !important;
    }
    
    /* ===== RADIO BUTTONS ===== */
    .stRadio > div > label {
        color: #1a1a1a !important;
    }
    
    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div {
        background-color: #4CAF50 !important;
    }
    
    /* ===== PLOTLY CHARTS ===== */
    .js-plotly-plot .plotly .main-svg text {
        fill: #1a1a1a !important;
    }
    
    /* ===== DIALOG/TOAST OVERLAY ===== */
    .stToast {
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    .stToast * {
        color: #1a1a1a !important;
    }
    
    /* ===== SUCCESS TOAST ===== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .success-toast {
        animation: fadeInUp 0.5s ease !important;
        background-color: #d4edda !important;
        border: 1px solid #c3e6cb !important;
        border-radius: 8px !important;
        padding: 15px !important;
        margin: 10px 0 !important;
    }
    
    /* ===== FORCE DARK TEXT ON ALL HOVER STATES ===== */
    *:hover {
        color: #1a1a1a !important;
    }
    
    [data-testid="stSidebar"] *:hover {
        color: #1a1a1a !important;
    }
    
    /* Override any white text on dark backgrounds */
    .st-emotion-cache-1v0mbdj, .st-emotion-cache-1y4p8pa {
        color: #1a1a1a !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State Initialization
# ============================================================
if 'selected_job_id' not in st.session_state:
    st.session_state.selected_job_id = None
if 'uploaded_resumes' not in st.session_state:
    st.session_state.uploaded_resumes = []
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'job_created' not in st.session_state:
    st.session_state.job_created = False
if 'deleted_resume' not in st.session_state:
    st.session_state.deleted_resume = False
if 'delete_target' not in st.session_state:
    st.session_state.delete_target = None
if 'show_delete_dialog' not in st.session_state:
    st.session_state.show_delete_dialog = False

# ============================================================
# Helper Functions
# ============================================================

def api_call(method, endpoint, data=None, files=None, params=None):
    """Make API calls to FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        elif method == "PUT":
            response = requests.put(url, json=data)
        
        if response.status_code in [200, 201, 202]:
            return response.json()
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.error(f"Details: {response.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Make sure the server is running.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def get_jobs():
    return api_call("GET", "/jobs/")

def create_job(job_data):
    return api_call("POST", "/jobs/create", data=job_data)

def delete_job(job_id):
    return api_call("DELETE", f"/jobs/{job_id}")

def get_matches(job_id, top_k=10, min_score=0.3):
    return api_call("POST", f"/matches/for-job/{job_id}?top_k={top_k}&min_score_threshold={min_score}")

def upload_resume(file):
    files = {"file": (file.name, file.getvalue(), file.type)}
    return api_call("POST", "/resumes/upload", files=files)

def get_resumes(limit=50):
    return api_call("GET", f"/resumes/?limit={limit}")

def delete_resume(resume_id):
    return api_call("DELETE", f"/resumes/{resume_id}")

def search_resumes(query, top_k=10):
    return api_call("POST", "/search/", data={"query": query, "top_k": top_k})

def get_system_health():
    return api_call("GET", "/health")

# ============================================================
# Delete Confirmation Dialog
# ============================================================
def show_delete_confirmation(target_type, target_id, target_name):
    """Show a confirmation dialog before deletion"""
    st.session_state.delete_target = {
        "type": target_type,
        "id": target_id,
        "name": target_name
    }
    st.session_state.show_delete_dialog = True

def handle_delete_confirmation():
    """Handle the delete confirmation"""
    if st.session_state.show_delete_dialog and st.session_state.delete_target:
        target = st.session_state.delete_target
        
        st.warning(f"⚠️ Are you sure you want to delete '{target['name']}'?")
        st.caption("This action cannot be undone.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete", type="primary"):
                with st.spinner("Deleting..."):
                    if target['type'] == "resume":
                        result = delete_resume(target['id'])
                    else:  # job
                        result = delete_job(target['id'])
                    
                    if result:
                        st.success(f"✅ {target['type'].title()} deleted successfully!")
                        st.session_state.show_delete_dialog = False
                        st.session_state.delete_target = None
                        time.sleep(1)
                        st.rerun()
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_delete_dialog = False
                st.session_state.delete_target = None
                st.rerun()

# ============================================================
# Sidebar - Navigation
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/resume.png", width=80)
    st.title("AI Resume Screener")
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📋 Job Management", "📄 Resume Upload", 
         "🎯 Candidate Matching", "🔍 Semantic Search", "📊 Analytics"]
    )
    
    st.markdown("---")
    
    # System status
    st.subheader("System Status")
    health = get_system_health()
    if health:
        st.success(f"✅ API: {health.get('status', 'unknown')}")
        st.info(f"🔍 {health.get('components', {}).get('search_index', 'N/A')}")
    else:
        st.error("❌ API Offline")
    
    st.markdown("---")
    st.caption(f"Version: 1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
# Check for delete dialog
# ============================================================
if st.session_state.show_delete_dialog:
    handle_delete_confirmation()

# ============================================================
# Page: Dashboard
# ============================================================
if page == "🏠 Dashboard":
    st.title("🏠 AI Resume Screening Dashboard")
    st.markdown("---")
    
    resumes = get_resumes()
    jobs = get_jobs()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Resumes", len(resumes) if resumes else 0)
    with col2:
        st.metric("Open Positions", len(jobs) if jobs else 0)
    with col3:
        completed = sum(1 for r in resumes if r.get('status') == 'completed') if resumes else 0
        st.metric("Processed Resumes", completed)
    with col4:
        total_skills = 0
        if resumes:
            for r in resumes:
                total_skills += r.get('total_skills', 0)
        st.metric("Skills Extracted", total_skills)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Recent Resumes")
        if resumes:
            recent = resumes[:5]
            for r in recent:
                name = r.get('personal_info', {}).get('name', 'Unknown')
                exp = r.get('total_experience_years', 0)
                skills = r.get('total_skills', 0)
                status = r.get('status', 'pending')
                status_icon = "✅" if status == "completed" else "⏳"
                st.markdown(f"""
                <div class="match-card">
                    <b>{name}</b><br>
                    📅 Experience: {exp} years | 🎯 Skills: {skills} | {status_icon} {status}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No resumes uploaded yet.")
    
    with col2:
        st.subheader("📋 Current Openings")
        if jobs:
            for j in jobs[:5]:
                st.markdown(f"""
                <div class="match-card">
                    <b>{j.get('title', 'Unknown')}</b><br>
                    🏢 {j.get('company', 'N/A')} | 📍 {j.get('required_skills_count', 0)} required skills
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No job descriptions created yet.")

# ============================================================
# Page: Job Management
# ============================================================
elif page == "📋 Job Management":
    st.title("📋 Job Description Management")
    st.markdown("---")
    
    with st.expander("➕ Create New Job Description", expanded=not st.session_state.job_created):
        with st.form("create_job_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Job Title*", placeholder="e.g., Senior Python Developer")
                company = st.text_input("Company Name", placeholder="e.g., TechCorp Inc.")
                min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, step=0.5)
            
            with col2:
                education = st.selectbox("Education Requirement", ["None", "bachelors", "masters", "phd"])
                location = st.text_input("Location", placeholder="e.g., Remote, New York, etc.")
                employment_type = st.selectbox("Employment Type", ["full-time", "part-time", "contract", "internship"])
            
            description = st.text_area("Job Description*", height=150)
            required_skills = st.text_input("Required Skills (comma-separated)*", 
                                           placeholder="e.g., Python, FastAPI, PostgreSQL, Docker, AWS")
            preferred_skills = st.text_input("Preferred Skills (comma-separated)", 
                                            placeholder="e.g., Kubernetes, Redis, GraphQL")
            
            submitted = st.form_submit_button("🚀 Create Job")
            
            if submitted:
                if not title or not description or not required_skills:
                    st.error("❌ Please fill in all required fields (*)")
                else:
                    job_data = {
                        "title": title,
                        "company": company if company else None,
                        "description": description,
                        "required_skills": [s.strip() for s in required_skills.split(",")],
                        "preferred_skills": [s.strip() for s in preferred_skills.split(",")] if preferred_skills else [],
                        "min_experience_years": min_experience,
                        "education_requirement": education if education != "None" else None,
                        "location": location if location else None,
                        "employment_type": employment_type if employment_type else None
                    }
                    
                    with st.spinner("Creating job..."):
                        result = create_job(job_data)
                        if result:
                            st.session_state.job_created = True
                            st.success("✅ Job created successfully!")
                            st.balloons()
                            st.json({
                                "Job ID": result.get('job_id'),
                                "Title": result.get('title'),
                                "Requirements": result.get('requirements', {})
                            })
                            time.sleep(1)
                            st.rerun()
    
    st.subheader("📋 Existing Job Descriptions")
    jobs = get_jobs()
    
    if jobs:
        jobs_df = pd.DataFrame(jobs)
        st.dataframe(
            jobs_df[['title', 'company', 'required_skills_count', 'min_experience', 'created_at']],
            width='stretch',
            column_config={
                "title": "Job Title",
                "company": "Company",
                "required_skills_count": "Required Skills",
                "min_experience": "Min Experience (yrs)",
                "created_at": "Created"
            }
        )
        
        st.subheader("🎯 Select Job for Matching")
        job_options = {f"{j['title']} - {j['company']}": j['job_id'] for j in jobs}
        selected_job_label = st.selectbox("Choose a job:", list(job_options.keys()))
        
        if selected_job_label:
            selected_id = job_options[selected_job_label]
            st.session_state.selected_job_id = selected_id
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🎯 Match Candidates", type="primary"):
                    st.session_state.page = "🎯 Candidate Matching"
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Delete This Job", type="secondary"):
                    show_delete_confirmation("job", selected_id, selected_job_label)
                    st.rerun()
    else:
        st.info("No job descriptions created yet. Use the form above to create one.")

# ============================================================
# Page: Resume Upload
# ============================================================
elif page == "📄 Resume Upload":
    st.title("📄 Resume Management")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Resumes")
        st.markdown("""
        **Supported formats:** PDF, DOCX  
        **You can upload multiple files at once!**
        """)
        
        uploaded_files = st.file_uploader(
            "Choose PDF or DOCX files",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Select multiple resumes to upload at once"
        )
        
        if uploaded_files:
            st.info(f"📎 {len(uploaded_files)} file(s) selected")
            
            if st.button("📤 Upload All Resumes", type="primary"):
                with st.spinner(f"Uploading {len(uploaded_files)} resumes..."):
                    progress_bar = st.progress(0)
                    results = []
                    
                    for i, file in enumerate(uploaded_files):
                        result = upload_resume(file)
                        if result:
                            results.append(result)
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    if results:
                        st.success(f"✅ Successfully uploaded {len(results)} resumes!")
                        st.balloons()
                        
                        for r in results:
                            st.info(f"📄 {r.get('filename')} → ID: {r.get('resume_id')[:8]}...")
                        
                        st.session_state.upload_success = True
                        time.sleep(2)
                        st.rerun()
    
    with col2:
        st.subheader("Quick Stats")
        resumes = get_resumes()
        if resumes:
            completed = sum(1 for r in resumes if r.get('status') == 'completed')
            pending = sum(1 for r in resumes if r.get('status') == 'pending')
            failed = sum(1 for r in resumes if r.get('status') == 'failed')
            
            st.metric("Total Uploads", len(resumes))
            st.metric("✅ Processed", completed)
            st.metric("⏳ Pending", pending)
            if failed > 0:
                st.metric("❌ Failed", failed)
    
    st.markdown("---")
    
    st.subheader("📄 Uploaded Resumes")
    resumes = get_resumes()
    
    if resumes:
        for idx, r in enumerate(resumes):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                
                name = r.get('personal_info', {}).get('name', 'Unknown')
                email = r.get('personal_info', {}).get('email', 'N/A')
                exp = r.get('total_experience_years', 0)
                skills = r.get('total_skills', 0)
                status = r.get('status', 'unknown')
                resume_id = r.get('id')
                
                with col1:
                    st.write(f"**{name}**")
                with col2:
                    st.write(email)
                with col3:
                    st.write(f"{exp} years")
                with col4:
                    if status == "completed":
                        st.write("✅ completed")
                    elif status == "processing":
                        st.write("⏳ processing")
                    elif status == "failed":
                        st.write("❌ failed")
                    else:
                        st.write("⏳ pending")
                with col5:
                    if st.button("🗑️", key=f"del_{resume_id}", help="Delete this resume"):
                        show_delete_confirmation("resume", resume_id, name)
                        st.rerun()
                
                if skills > 0 and r.get('skills'):
                    top_skills = [s.get('name') for s in r.get('skills', [])[:5]]
                    st.caption(f"🎯 Skills: {', '.join(top_skills)}")
                st.markdown("---")
    else:
        st.info("No resumes uploaded yet. Upload your first resume above!")

# ============================================================
# Page: Candidate Matching
# ============================================================
elif page == "🎯 Candidate Matching":
    st.title("🎯 Candidate Matching")
    st.markdown("---")
    
    jobs = get_jobs()
    if not jobs:
        st.warning("⚠️ No job descriptions found. Please create a job first in the Job Management page.")
        st.stop()
    
    job_options = {f"{j['title']} - {j['company']}": j['job_id'] for j in jobs}
    selected_job = st.selectbox("Select Job Description", list(job_options.keys()))
    selected_job_id = job_options[selected_job]
    st.session_state.selected_job_id = selected_job_id
    
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Number of candidates to show", min_value=5, max_value=50, value=10)
    with col2:
        min_score = st.slider("Minimum score threshold", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    
    if st.button("🔍 Find Matches", type="primary"):
        with st.spinner("🔍 Matching candidates..."):
            matches = get_matches(selected_job_id, top_k, min_score)
            
            if matches and matches.get('results'):
                st.success(f"✅ Found {matches.get('total_matches')} matching candidates")
                
                for idx, candidate in enumerate(matches.get('results', []), 1):
                    score = candidate.get('overall_score', 0) * 100
                    name = candidate.get('resume_summary', {}).get('personal_info', {}).get('name', 'Unknown')
                    exp = candidate.get('resume_summary', {}).get('total_experience_years', 0)
                    recommendation = candidate.get('recommendation', 'N/A')
                    matched_skills = candidate.get('matched_skills', [])
                    missing_skills = candidate.get('missing_skills', [])
                    explanation = candidate.get('explanation', '')
                    
                    if score >= 70:
                        score_class = "score-high"
                    elif score >= 50:
                        score_class = "score-medium"
                    else:
                        score_class = "score-low"
                    
                    st.markdown(f"""
                    <div class="match-card">
                        <table width="100%">
                            <tr>
                                <td width="8%"><h2>#{idx}</h2></td>
                                <td width="32%">
                                    <b>{name}</b><br>
                                    📅 {exp} years experience
                                </td>
                                <td width="20%" class="{score_class}">
                                    {score:.1f}%
                                </td>
                                <td width="20%">
                                    🏷️ {recommendation}
                                </td>
                                <td width="20%">
                                    <span style="color:#2e7d32;">✅ {len(matched_skills)} matched</span>
                                    <span style="color:#c62828;"> | ❌ {len(missing_skills)} missing</span>
                                </td>
                            </tr>
                        </table>
                        <details>
                            <summary style="color:#1a1a1a; cursor:pointer; font-weight:bold;">📋 View Details</summary>
                            <div style="padding:10px 0; color:#1a1a1a;">
                                <b style="color:#1a1a1a;">✅ Matched Skills:</b> 
                                <span style="color:#1a1a1a;">{', '.join(matched_skills[:10]) if matched_skills else 'None'}</span><br>
                                <b style="color:#1a1a1a;">❌ Missing Skills:</b> 
                                <span style="color:#1a1a1a;">{', '.join(missing_skills[:5]) if missing_skills else 'None'}</span><br>
                                <b style="color:#1a1a1a;">💡 Recommendation:</b> 
                                <span style="color:#1a1a1a;">{explanation[:200] if explanation else 'N/A'}</span>
                            </div>
                        </details>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No matches found. Try adjusting the score threshold or upload more resumes.")

# ============================================================
# Page: Semantic Search
# ============================================================
elif page == "🔍 Semantic Search":
    st.title("🔍 Semantic Resume Search")
    st.markdown("---")
    
    st.markdown("""
    Search for resumes using natural language queries. 
    The system will find semantically similar resumes based on skills, experience, and context.
    """)
    
    query = st.text_input("Enter your search query", placeholder="e.g., python developer with aws experience")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        top_k = st.number_input("Number of results", min_value=1, max_value=50, value=10)
    
    if st.button("🔍 Search", type="primary"):
        if query:
            with st.spinner("Searching..."):
                results = search_resumes(query, top_k)
                
                if results and results.get('total_results', 0) > 0:
                    st.success(f"✅ Found {results.get('total_results')} matching resumes")
                    
                    for result in results.get('results', []):
                        name = result.get('resume_summary', {}).get('personal_info', {}).get('name', 'Unknown')
                        exp = result.get('resume_summary', {}).get('total_experience_years', 0)
                        similarity = result.get('similarity_score', 0) * 100
                        explanation = result.get('relevance_explanation', '')
                        
                        if similarity >= 70:
                            score_class = "score-high"
                        elif similarity >= 50:
                            score_class = "score-medium"
                        else:
                            score_class = "score-low"
                        
                        st.markdown(f"""
                        <div class="match-card">
                            <table width="100%">
                                <tr>
                                    <td width="60%">
                                        <b>{name}</b><br>
                                        📅 {exp} years experience
                                    </td>
                                    <td width="20%" class="{score_class}">
                                        {similarity:.1f}% match
                                    </td>
                                </tr>
                            </table>
                            <small style="color:#555;">{explanation}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No results found. Try a different query.")
        else:
            st.warning("Please enter a search query")

# ============================================================
# Page: Analytics
# ============================================================
elif page == "📊 Analytics":
    st.title("📊 Analytics Dashboard")
    st.markdown("---")
    
    st.subheader("🏥 System Health")
    health = get_system_health()
    if health:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("API Status", health.get('status', 'unknown'))
        with col2:
            st.metric("Database", health.get('components', {}).get('database', 'unknown'))
        with col3:
            st.metric("Task Manager", health.get('components', {}).get('task_manager', 'unknown'))
    
    st.subheader("📄 Resume Statistics")
    resumes = get_resumes()
    
    if resumes:
        df = pd.DataFrame([
            {
                'name': r.get('personal_info', {}).get('name', 'Unknown'),
                'experience': r.get('total_experience_years', 0),
                'skills_count': r.get('total_skills', 0),
                'status': r.get('status', 'unknown')
            }
            for r in resumes
        ])
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_exp = px.histogram(df, x='experience', title='Experience Distribution (years)',
                                   labels={'experience': 'Years', 'count': 'Number of Candidates'})
            fig_exp.update_layout(template='plotly_white')
            st.plotly_chart(fig_exp, width='stretch')
        
        with col2:
            df_sorted = df.sort_values('skills_count', ascending=True)
            fig_skills = px.bar(df_sorted, x='name', y='skills_count', 
                               title='Skills per Candidate',
                               labels={'name': 'Candidate', 'skills_count': 'Number of Skills'})
            fig_skills.update_layout(template='plotly_white')
            st.plotly_chart(fig_skills, width='stretch')
        
        status_counts = df['status'].value_counts()
        fig_status = px.pie(values=status_counts.values, names=status_counts.index, 
                           title='Processing Status')
        fig_status.update_layout(template='plotly_white')
        st.plotly_chart(fig_status, width='stretch')
        
        st.subheader("📋 Candidate Summary")
        st.dataframe(df, width='stretch')
    
    st.subheader("📋 Job Statistics")
    jobs = get_jobs()
    if jobs:
        jobs_df = pd.DataFrame(jobs)
        st.dataframe(jobs_df[['title', 'company', 'required_skills_count', 'min_experience']], 
                    width='stretch')
    
    st.subheader("⚖️ Bias Detection")
    st.info("Bias detection metrics will appear here once more data is available")

