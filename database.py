import sqlite3
import json
import os

DB_PATH = "quiz_app.db"

def get_connection(db_path=DB_PATH):
    return sqlite3.connect(db_path)

def init_db(db_path=DB_PATH):
    """Initializes the SQLite database tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content TEXT NOT NULL
        )
    """)
    
    # Create quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            instructions TEXT,
            num_questions INTEGER,
            num_options INTEGER,
            allow_multiple BOOLEAN,
            questions_json TEXT,
            score REAL,
            completed BOOLEAN DEFAULT 0,
            user_answers_json TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def add_document(filename, content, db_path=DB_PATH):
    """Inserts a new document and returns its ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (filename, content) VALUES (?, ?)",
        (filename, content)
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def get_all_documents(db_path=DB_PATH):
    """Retrieves metadata of all documents."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at FROM documents ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "filename": r[1], "uploaded_at": r[2]} for r in rows]

def get_document_by_id(doc_id, db_path=DB_PATH):
    """Retrieves complete details of a single document."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at, content FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "filename": row[1], "uploaded_at": row[2], "content": row[3]}
    return None

def add_quiz(doc_id, instructions, num_questions, num_options, allow_multiple, questions_json, db_path=DB_PATH):
    """Creates a new quiz configuration and returns its ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO quizzes 
           (document_id, instructions, num_questions, num_options, allow_multiple, questions_json) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (doc_id, instructions, num_questions, num_options, int(allow_multiple), questions_json)
    )
    quiz_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return quiz_id

def get_quizzes_for_document(doc_id, db_path=DB_PATH):
    """Retrieves all quizzes generated for a specific document."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, document_id, created_at, instructions, num_questions, num_options, 
                  allow_multiple, questions_json, score, completed, user_answers_json 
           FROM quizzes WHERE document_id = ? ORDER BY created_at DESC""",
        (doc_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    quizzes = []
    for r in rows:
        quizzes.append({
            "id": r[0],
            "document_id": r[1],
            "created_at": r[2],
            "instructions": r[3],
            "num_questions": r[4],
            "num_options": r[5],
            "allow_multiple": bool(r[6]),
            "questions_json": r[7],
            "score": r[8],
            "completed": bool(r[9]),
            "user_answers_json": r[10]
        })
    return quizzes

def get_quiz_by_id(quiz_id, db_path=DB_PATH):
    """Retrieves details of a single quiz by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, document_id, created_at, instructions, num_questions, num_options, 
                  allow_multiple, questions_json, score, completed, user_answers_json 
           FROM quizzes WHERE id = ?""",
        (quiz_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "document_id": row[1],
            "created_at": row[2],
            "instructions": row[3],
            "num_questions": row[4],
            "num_options": row[5],
            "allow_multiple": bool(row[6]),
            "questions_json": row[7],
            "score": row[8],
            "completed": bool(row[9]),
            "user_answers_json": row[10]
        }
    return None

def update_quiz_status(quiz_id, score, user_answers_json, completed, db_path=DB_PATH):
    """Updates the status and score of a quiz session."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE quizzes SET score = ?, user_answers_json = ?, completed = ? WHERE id = ?",
        (score, user_answers_json, int(completed), quiz_id)
    )
    conn.commit()
    conn.close()

def get_latest_quiz_session(db_path=DB_PATH):
    """Fetches the ID of the most recently generated or updated quiz."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM quizzes ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def delete_document(doc_id, db_path=DB_PATH):
    """Deletes a document and all cascading quizzes associated with it."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

def delete_quiz(quiz_id, db_path=DB_PATH):
    """Deletes a quiz configuration from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    conn.commit()
    conn.close()

