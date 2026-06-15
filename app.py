import streamlit as st
import os
import json
import sqlite3
from dotenv import load_dotenv
from pypdf import PdfReader
from google import genai
from google.genai import types
import database as db

# Load env file
load_dotenv()

# Page setup
st.set_page_config(
    page_title="AI PDF Quiz Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    /* Elegant Title Styling */
    .title-gradient {
        background: linear-gradient(135deg, #FF6B6B 0%, #4D96FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #8C8C8C;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }    
    /* Card/Container Styling */
    .card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .card:hover {
        border-color: rgba(77, 150, 255, 0.4);
        transform: translateY(-2px);
    }
    
    /* Custom Question & Answer styles */
    .correct-card {
        border-left: 5px solid #2ecc71 !important;
        background: rgba(46, 204, 113, 0.05) !important;
    }
    
    .incorrect-card {
        border-left: 5px solid #e74c3c !important;
        background: rgba(231, 76, 60, 0.05) !important;
    }
    
    /* Highlight primary/active buttons in red */
    button[kind="primary"], div[data-testid="stButton"] button[kind="primary"] {
        background-color: #FF4B4B !important;
        color: white !important;
        border-color: #FF4B4B !important;
    }
    button[kind="primary"]:hover, div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #E04040 !important;
        border-color: #E04040 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
db.init_db()

# Session State Initialization
if "selected_doc_id" not in st.session_state:
    st.session_state.selected_doc_id = None
if "active_quiz_id" not in st.session_state:
    st.session_state.active_quiz_id = None
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")
if "active_view" not in st.session_state:
    st.session_state.active_view = "Active Quiz"

# Load latest session on startup if state is empty
if st.session_state.selected_doc_id is None:
    latest_quiz_id = db.get_latest_quiz_session()
    if latest_quiz_id:
        quiz_data = db.get_quiz_by_id(latest_quiz_id)
        if quiz_data:
            st.session_state.selected_doc_id = quiz_data["document_id"]
            st.session_state.active_quiz_id = quiz_data["id"]

# Retrieve current document if selected
current_doc = None
if st.session_state.selected_doc_id:
    current_doc = db.get_document_by_id(st.session_state.selected_doc_id)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/gradient/100/parse-from-clipboard.png", width=64)
    st.title("NotebookQuiz AI")
    st.markdown("---")
    
    # 1. API Key & Settings
    with st.expander("🔑 API Settings", expanded=not bool(st.session_state.api_key)):
        user_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            value=st.session_state.api_key,
            help="Get your key from Google AI Studio. Stored only in session."
        )
        if user_key != st.session_state.api_key:
            st.session_state.api_key = user_key
            st.rerun()
            
    # 2. Document Upload Section
    st.subheader("📁 Upload New PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type="pdf", 
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        # Check if already uploaded to prevent duplicates
        all_docs = db.get_all_documents()
        existing_doc = next((d for d in all_docs if d["filename"] == uploaded_file.name), None)
        
        if existing_doc:
            st.session_state.selected_doc_id = existing_doc["id"]
            st.info(f"Loaded existing document: {uploaded_file.name}")
        else:
            with st.spinner("Extracting PDF content..."):
                try:
                    pdf_reader = PdfReader(uploaded_file)
                    raw_text = ""
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            raw_text += page_text + "\n"
                    
                    if raw_text.strip() == "":
                        st.error("Could not extract any text from the PDF. Is it scanned/image-only?")
                    else:
                        doc_id = db.add_document(uploaded_file.name, raw_text)
                        st.session_state.selected_doc_id = doc_id
                        st.session_state.active_quiz_id = None  # Reset active quiz for new doc
                        st.success(f"Successfully uploaded: {uploaded_file.name}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error parsing PDF: {str(e)}")

    # 3. Document Library / History
    st.subheader("📚 Your Documents")
    all_docs = db.get_all_documents()
    if all_docs:
        for doc in all_docs:
            is_selected = doc["id"] == st.session_state.selected_doc_id
            btn_label = f"📄 {doc['filename']}"
            
            col_sel, col_del = st.columns([5, 1])
            with col_sel:
                if st.button(
                    btn_label, 
                    key=f"doc_btn_{doc['id']}", 
                    use_container_width=True, 
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_doc_id = doc["id"]
                    st.session_state.active_quiz_id = None
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"doc_del_{doc['id']}", use_container_width=True, help="Delete Document"):
                    db.delete_document(doc["id"])
                    if is_selected:
                        st.session_state.selected_doc_id = None
                        st.session_state.active_quiz_id = None
                    st.rerun()
    else:
        st.caption("No documents uploaded yet.")

# ----------------- MAIN UI -----------------

# Header / Welcome Area
st.markdown('<div class="title-gradient">NotebookQuiz AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Transform any PDF study document into structured, persistent quizzes. Powered by Gemini.</div>', unsafe_allow_html=True)

if not st.session_state.api_key:
    st.warning("⚠️ Please provide a Gemini API Key in the sidebar Settings panel to unlock quiz generation.")
    st.stop()

if not current_doc:
    st.info("💡 To start, upload a PDF document in the sidebar, or select one from your library.")
    st.stop()

# Layout: Split page into Document Info and Quiz Area
col_doc, col_quiz = st.columns([1, 2], gap="large")

# Left Column: Document Details & History
with col_doc:
    st.subheader("📄 Document Details")
    with st.container():
        st.markdown(f"""
        <div class="card">
            <h4>{current_doc['filename']}</h4>
            <p style="font-size: 0.9rem; color: #888;">Uploaded: {current_doc['uploaded_at']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔍 View Raw Text Content", expanded=False):
            st.text_area("Extracted Text", value=current_doc["content"], height=300, disabled=True)
            
    # Quiz history for this specific document
    st.subheader("📜 Generated Quizzes")
    quizzes = db.get_quizzes_for_document(current_doc["id"])
    if quizzes:
        for idx, q in enumerate(quizzes):
            score_text = f"Score: {q['score']:.1f}%" if q['completed'] else "Not started"
            q_label = f"Quiz #{q['id']} - {q['num_questions']} Qs ({score_text})"
            is_active_quiz = q["id"] == st.session_state.active_quiz_id
            
            col_sel, col_del = st.columns([5, 1])
            with col_sel:
                if st.button(
                    q_label,
                    key=f"quiz_select_{q['id']}",
                    use_container_width=True,
                    type="primary" if is_active_quiz else "secondary"
                ):
                    st.session_state.active_quiz_id = q["id"]
                    st.session_state.active_view = "Active Quiz"
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"quiz_del_{q['id']}", use_container_width=True, help="Delete Quiz"):
                    db.delete_quiz(q["id"])
                    if is_active_quiz:
                        st.session_state.active_quiz_id = None
                    st.rerun()
    else:
        st.caption("No quizzes generated for this document yet.")

# Right Column: Quiz Configuration & Interactive Engine
with col_quiz:
    # Quiz Selector / Config Tabs using State Navigation
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        if st.button("🎮 Active Quiz", type="primary" if st.session_state.active_view == "Active Quiz" else "secondary", use_container_width=True):
            st.session_state.active_view = "Active Quiz"
            st.rerun()
    with col_tab2:
        if st.button("⚙️ Generate New Quiz", type="primary" if st.session_state.active_view == "Generate New Quiz" else "secondary", use_container_width=True):
            st.session_state.active_view = "Generate New Quiz"
            st.rerun()
    
    if st.session_state.active_view == "Generate New Quiz":
        st.subheader("Quiz Parameters")
        
        # UI controls for Quiz Configuration
        col_q, col_opt = st.columns(2)
        with col_q:
            num_questions = st.slider("Number of Questions", min_value=1, max_value=20, value=5)
        with col_opt:
            num_options = st.selectbox("Options per Question", options=[2, 3, 4, 5, 6], index=2) # default 4
            
        allow_multiple = st.checkbox(
            "Allow Multiple Correct Answers", 
            help="If checked, questions can have multiple correct answers (checkbox style). If unchecked, exactly one is correct."
        )
        
        selected_model_name = st.selectbox(
            "Select Gemini Model",
            options=[
                "Gemini 3.5 Flash",
                "Gemini 3.1 Flash Lite",
                "Gemini 2.5 Flash",
                "Gemini 2.0 Flash"
            ],
            index=0,
            help="Choose the model for generation. Flash models are faster and cheaper."
        )
        
        model_id_mapping = {
            "Gemini 3.5 Flash": "gemini-3.5-flash",
            "Gemini 3.1 Flash Lite": "gemini-3.1-flash-lite",
            "Gemini 2.5 Flash": "gemini-2.5-flash",
            "Gemini 2.0 Flash": "gemini-2.0-flash"
        }
        selected_model = model_id_mapping[selected_model_name]
        
        instructions = st.text_area(
            "Custom Instructions (Optional)", 
            placeholder="e.g. Focus on key definitions, make it challenging, target mathematical formulas...",
            height=100
        )
        
        # Generation Trigger
        if st.button("✨ Generate Quiz", type="primary", use_container_width=True):
            with st.spinner("Analyzing document and crafting quiz..."):
                try:
                    # Initialize Gemini client
                    client = genai.Client(api_key=st.session_state.api_key)
                    
                    # Mandate structure
                    system_instruction = (
                        "You are an AI instructor generating educational quizzes. "
                        "Produce clean JSON matching the requested schema strictly. Do not add explanations outside the JSON."
                    )
                    
                    prompt = f"""
                    Generate a quiz of exactly {num_questions} questions based ON THE PROVIDED DOCUMENT ONLY.
                    
                    Each question must have exactly {num_options} options.
                    
                    Guidelines:
                    {"- Questions CAN have multiple correct answers (0, 1, or more). Indicate all valid option indices in 'correct_answers'." if allow_multiple else "- Questions MUST have exactly 1 correct answer in 'correct_answers'."}
                    - Provide short explanations for the answers.
                    
                    Format the output strictly as a JSON object with this key:
                    "questions": A list of questions, where each question has:
                      - "question_text": string
                      - "options": list of strings (exactly {num_options} elements)
                      - "correct_answers": list of integers representing 0-based indices of the correct options.
                      - "explanation": string
                      
                    Custom instructions: {instructions}
                    
                    Document content:
                    {current_doc['content']}
                    """
                    
                    # Generate content using modern Google GenAI Client
                    response = client.models.generate_content(
                        model=selected_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json"
                        )
                    )
                    
                    # Validate JSON structure
                    parsed_quiz = json.loads(response.text)
                    if "questions" not in parsed_quiz or not isinstance(parsed_quiz["questions"], list):
                        raise ValueError("Invalid JSON root schema from LLM")
                    
                    # Store generated quiz in SQLite
                    quiz_id = db.add_quiz(
                        doc_id=current_doc["id"],
                        instructions=instructions,
                        num_questions=num_questions,
                        num_options=num_options,
                        allow_multiple=allow_multiple,
                        questions_json=response.text
                    )
                    
                    st.session_state.active_quiz_id = quiz_id
                    st.session_state.active_view = "Active Quiz"
                    st.success("Quiz generated and saved successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to generate quiz: {str(e)}")
                    st.code(response.text if 'response' in locals() else "No response")
                    
    elif st.session_state.active_view == "Active Quiz":
        if st.session_state.active_quiz_id:
            quiz = db.get_quiz_by_id(st.session_state.active_quiz_id)
            if quiz:
                st.subheader(f"Quiz #{quiz['id']}")
                st.info(f"📋 **Config**: {quiz['num_questions']} questions | {quiz['num_options']} choices | {'Multiple answers' if quiz['allow_multiple'] else 'Single answer'}")
                
                # Parse questions
                questions_data = json.loads(quiz["questions_json"]).get("questions", [])
                
                # Retrieve existing state (completed status and saved answers)
                completed = quiz["completed"]
                saved_answers = {}
                if quiz["user_answers_json"]:
                    saved_answers = json.loads(quiz["user_answers_json"])
                
                # Interactive Quiz Form
                user_selections = {}
                
                for idx, q in enumerate(questions_data):
                    st.markdown("---")
                    st.markdown(f"##### Question {idx + 1}: {q['question_text']}")
                    
                    # Retrieve previous selection from database state, if exists
                    default_sel = saved_answers.get(str(idx), [])
                    
                    # Render response widgets depending on Single vs Multiple answer options
                    if quiz["allow_multiple"]:
                        # Multiple choice: checkboxes
                        selected_indices = []
                        for opt_idx, opt_text in enumerate(q["options"]):
                            # Set default state based on prior completion
                            default_checked = opt_idx in default_sel
                            val = st.checkbox(
                                opt_text, 
                                value=default_checked, 
                                key=f"q_{idx}_opt_{opt_idx}",
                                disabled=completed
                            )
                            if val:
                                selected_indices.append(opt_idx)
                        user_selections[str(idx)] = selected_indices
                    else:
                        # Single choice: radio button
                        default_idx = default_sel[0] if default_sel else None
                        
                        # Use a selectbox or radio. Radio with None value is supported in streamlit
                        # by using index parameter if we match. Let's resolve index
                        selected_option = st.radio(
                            "Choose an option:",
                            options=q["options"],
                            index=q["options"].index(q["options"][default_idx]) if default_idx is not None else None,
                            key=f"q_{idx}",
                            disabled=completed,
                            label_visibility="collapsed"
                        )
                        
                        if selected_option:
                            user_selections[str(idx)] = [q["options"].index(selected_option)]
                        else:
                            user_selections[str(idx)] = []
                            
                    # Display results inline if already completed/graded
                    if completed:
                        is_correct = sorted(user_selections[str(idx)]) == sorted(q["correct_answers"])
                        card_class = "correct-card" if is_correct else "incorrect-card"
                        
                        correct_labels = [q["options"][i] for i in q["correct_answers"]]
                        
                        st.markdown(f"""
                        <div class="card {card_class}">
                            <strong>{"✅ Correct" if is_correct else "❌ Incorrect"}</strong><br>
                            <b>Correct Answer(s):</b> {', '.join(correct_labels)}<br><br>
                            <i>Explanation:</i> {q['explanation']}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Action Buttons
                st.markdown("---")
                if not completed:
                    if st.button("Submit Quiz", type="primary", use_container_width=True):
                        # Grade Quiz
                        correct_count = 0
                        for idx, q in enumerate(questions_data):
                            user_ans = user_selections.get(str(idx), [])
                            correct_ans = q["correct_answers"]
                            if sorted(user_ans) == sorted(correct_ans):
                                correct_count += 1
                        
                        total_questions = len(questions_data)
                        final_score = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
                        
                        # Save state back to SQLite
                        db.update_quiz_status(
                            quiz_id=quiz["id"],
                            score=final_score,
                            user_answers_json=json.dumps(user_selections),
                            completed=True
                        )
                        st.success(f"Quiz Submitted! Final Score: {final_score:.1f}% ({correct_count}/{total_questions})")
                        st.rerun()
                else:
                    st.metric(label="Graded Score", value=f"{quiz['score']:.1f}%")
                    if st.button("🔄 Retake/Reset Quiz", type="secondary", use_container_width=True):
                        db.update_quiz_status(
                            quiz_id=quiz["id"],
                            score=None,
                            user_answers_json=None,
                            completed=False
                        )
                        st.rerun()
                    st.rerun()
            else:
                st.info("Select or generate a quiz to begin.")
        else:
            st.info("No active quiz session. Go to 'Generate New Quiz' or select a quiz from the list on the left.")
