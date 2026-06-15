# AI-Powered PDF Quiz Generator with SQLite Persistence

A web application inspired by Google NotebookLM that allows users to upload PDF documents, generate highly customizable quizzes using the Google Gemini API, and persist documents, quiz configurations, and attempts/scores in a local SQLite database.

## Quick Demo

Here is a short screen recording demonstrating the quiz generator flow:

<video src="quick_demo.mov" controls width="100%"></video>

> [!IMPORTANT]
> The Gemini API key shown in this demo video has been deleted and is no longer active.

## Project Structure

```
├── .env                  # Configuration for local environment keys (e.g. GEMINI_API_KEY)
├── app.py                # Main Streamlit web application dashboard and LLM interface
├── database.py           # SQLite database layer containing schema and CRUD query functions
├── pyproject.toml        # uv-managed python environment and dependencies config
├── quiz_app.db           # SQLite database file (auto-generated on startup)
└── README.md             # Project documentation (this file)
```

---

## Core Features

1. **SQLite Local Persistence**:
   - Stores metadata and full text parsed from PDF uploads.
   - Saves generated quiz configurations, response schemas, completeness statuses, user selections, and graded scores.
   - Automatically restores the last active document and quiz state on startup.

2. **Inline Deletions**:
   - Sidebar list provides document selection buttons side-by-side with a delete icon (`🗑️`). Deleting a document enables foreign-key cascade-deletes in SQLite, cleaning up all associated quizzes.
   - Generated quizzes list displays historical quizzes next to a delete icon (`🗑️`), allowing individual session clearing.

3. **Gemini API Selection (Quota Mitigation)**:
   - Integrates the modern Google GenAI SDK (`google-genai`).
   - Allows choosing the specific model for generation dynamically in the UI to manage rate limits/quotas:
     - **Gemini 3.5 Flash** (Default)
     - **Gemini 3.1 Flash Lite**
     - **Gemini 2.5 Flash**
     - **Gemini 2.0 Flash**

4. **Programmatic View Controls**:
   - Interactive navigation (simulated tabs) redirects the user to the "Active Quiz" panel immediately upon generating a new quiz, or when choosing a quiz from the history log.

5. **Interactive Grading Engine**:
   - Supports both single correct answers (radio buttons) and multiple correct answers (checkboxes).
   - Generates live grading metrics, shows highlight cards (green for correct, red for incorrect), and outputs explanations for each question.
   - Offers quiz resets to clear selections and re-take the quiz.

6. **Responsive UI**:
   - Built with a modern design system including font imports, gradient titles, glassmorphism card highlights, and accessible color schemes. The active selected document/quiz and primary control buttons are colored in Streamlit red.

---

## Schema Design

### `documents` Table
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `filename` | TEXT | NOT NULL |
| `uploaded_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| `content` | TEXT | NOT NULL |

### `quizzes` Table
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `document_id` | INTEGER | FOREIGN KEY REFERENCES `documents(id)` ON DELETE CASCADE |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| `instructions` | TEXT | |
| `num_questions` | INTEGER | |
| `num_options` | INTEGER | |
| `allow_multiple` | BOOLEAN | |
| `questions_json` | TEXT | |
| `score` | REAL | |
| `completed` | BOOLEAN | DEFAULT 0 |
| `user_answers_json`| TEXT | |

---

## Getting Started

### Prerequisites
Make sure you have [uv](https://github.com/astral-sh/uv) installed.

### Step 1: Install Dependencies
To install the required dependencies and sync the virtual environment, run:
```bash
uv sync
```

### Step 2: Set Up Environment Keys
Obtain your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/api-keys).

Configure your key by updating the local `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(If the `.env` key is not provided, the application will prompt you to enter the API key in the sidebar Settings panel on startup).*

### Step 3: Run the Application
Start the Streamlit application:
```bash
uv run streamlit run app.py
```

Open `http://localhost:8501` (or the URL printed in your terminal) in your browser to start using the app.
