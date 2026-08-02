from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# ----- Pydantic Models (same as before) -----
class TaskCreate(BaseModel):
    title: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

# ----- Database connection helper -----
def get_db_connection():
    """Returns a connection with dict_row factory."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# ----- Database initialization (table + seed) -----
def init_db():
    """Creates the tasks table and seeds examples if empty."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Create table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN DEFAULT FALSE
                )
            """)
            # 2. Check if empty (prevents duplicate seeding)
            cur.execute("SELECT COUNT(*) FROM tasks")
            count = cur.fetchone()["count"]
            if count == 0:
                # 3. Seed examples
                example_tasks = [
                    ("Learn FastAPI", False),
                    ("Build CRUD API", False),
                    ("Write README", True)
                ]
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    example_tasks
                )
                conn.commit()

# ----- Lifespan (modern replacement for on_event) -----
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    init_db()
    yield
    # Runs on shutdown (cleanup if needed)

# ----- FastAPI app -----
app = FastAPI(lifespan=lifespan)

# ----- Root & Health (unchanged) -----
@app.get("/", description="Root endpoint with API information")
def read_root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health", description="Health check for monitoring")
def health_check():
    return {"status": "ok"}

# ----- READ -----
@app.get("/tasks", description="List all tasks")
def list_tasks():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks")
            return cur.fetchall()

@app.get("/tasks/{task_id}", description="Get a single task by ID")
def get_task(task_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            return row

# ----- CREATE -----
@app.post("/tasks", status_code=201, description="Create a new task")
def create_task(task_data: TaskCreate):
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
                (task_data.title.strip(), False)
            )
            new_task = cur.fetchone()
            conn.commit()
            return new_task

# ----- UPDATE -----
@app.put("/tasks/{task_id}", description="Update an existing task")
def update_task(task_id: int, update_data: TaskUpdate):
    if update_data.title is None and update_data.done is None:
        raise HTTPException(status_code=400, detail="Request body cannot be empty")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if exists
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            existing = cur.fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            # Build update fields
            new_title = existing["title"]
            new_done = existing["done"]
            if update_data.title is not None:
                if not update_data.title.strip():
                    raise HTTPException(status_code=400, detail="Title cannot be empty")
                new_title = update_data.title.strip()
            if update_data.done is not None:
                new_done = update_data.done
            
            # Update and return the new row
            cur.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
                (new_title, new_done, task_id)
            )
            updated = cur.fetchone()
            conn.commit()
            return updated

# ----- DELETE -----
@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task")
def delete_task(task_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            conn.commit()
            # Returns 204 No Content automatically