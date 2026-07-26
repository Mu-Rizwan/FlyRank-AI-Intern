from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from contextlib import asynccontextmanager

# ----- Database Setup Functions -----
def init_db():
    """Creates the table and seeds example tasks if the table is empty."""
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    
    # 1. Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0
        )
    """)
    
    # 2. Check if table is empty (prevents duplicate seeding on restart)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    
    # 3. Seed only if empty
    if count == 0:
        example_tasks = [
            ("Learn FastAPI", 0),
            ("Build CRUD API", 0),
            ("Write README", 1)
        ]
        cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", example_tasks)
        conn.commit()
    
    conn.close()

def get_db():
    """Returns a connection to the SQLite database with row factory for dict-like access."""
    conn = sqlite3.connect("tasks.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs BEFORE the server starts accepting requests
    init_db()
    yield
    # This runs AFTER the server shuts down (cleanup goes here, if needed)

# ----- Initialize FastAPI with the lifespan -----
app = FastAPI(lifespan=lifespan)

# ----- Models (unchanged) -----
class TaskCreate(BaseModel):
    title: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None
    
# ----- In‑memory “database” -----
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build CRUD API", "done": False},
    {"id": 3, "title": "Write README", "done": True}
]

# Root – describe the API
@app.get("/", description="Root endpoint with API information")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

# Health check – used by monitoring tools
@app.get("/health", description="Health check for monitoring")
def health_check():
    return {"status": "ok"}

# ----- READ endpoints -----
@app.get("/tasks", description="List all tasks")
def list_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    # Convert rows to list of dicts
    return [dict(row) for row in rows]

@app.get("/tasks/{task_id}", description="Get a single task by ID")
def get_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return dict(row)

# ----- CREATE -----
@app.post("/tasks", status_code=201, description="Create a new task")
def create_task(task_data: TaskCreate):
    # Validation (same as Week 2)
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")
    
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task_data.title.strip(), 0)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    # Fetch the newly created task to return it
    conn = get_db()
    new_task = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    
    return dict(new_task)

# ----- UPDATE -----
@app.put("/tasks/{task_id}", description="Update an existing task")
def update_task(task_id: int, update_data: TaskUpdate):
    # Check if body is empty
    if update_data.title is None and update_data.done is None:
        raise HTTPException(status_code=400, detail="Request body cannot be empty")
    
    conn = get_db()
    
    # First, check if the task exists
    existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Build update dynamically
    current = dict(existing)
    if update_data.title is not None:
        if not update_data.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        current["title"] = update_data.title.strip()
    if update_data.done is not None:
        current["done"] = 1 if update_data.done else 0
    
    # Perform UPDATE
    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (current["title"], current["done"], task_id)
    )
    conn.commit()
    conn.close()
    
    # Return updated task
    conn = get_db()
    updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(updated)

# ----- DELETE -----
@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task")
def delete_task(task_id: int):
    conn = get_db()
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    
    if rows_deleted == 0:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    # Returns 204 No Content automatically