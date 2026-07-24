from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ----- Models -----
class TaskCreate(BaseModel):
    title: str   # required; must not be empty (we'll validate later)

class TaskUpdate(BaseModel):
    title: str | None = None   # optional
    done: bool | None = None

# ----- In‑memory “database” -----
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build CRUD API", "done": False},
    {"id": 3, "title": "Write README", "done": True}
]

# Root – describe the API
@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

# Health check – used by monitoring tools
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ----- READ endpoints -----
@app.get("/tasks")
def list_tasks():
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    # If not found, raise 404
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

# ----- CREATE -----
@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    # Validate title
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")
    
    new_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {
        "id": new_id,
        "title": task_data.title.strip(),
        "done": False
    }
    tasks.append(new_task)
    return new_task

# ----- UPDATE -----
@app.put("/tasks/{task_id}")
def update_task(task_id: int, update_data: TaskUpdate):
    # Find the task
    for task in tasks:
        if task["id"] == task_id:
            # Validate title if provided
            if update_data.title is not None:
                if not update_data.title.strip():
                    raise HTTPException(status_code=400, detail="Title cannot be empty")
                task["title"] = update_data.title.strip()
            if update_data.done is not None:
                task["done"] = update_data.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

# ----- DELETE -----
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return   # no content
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")