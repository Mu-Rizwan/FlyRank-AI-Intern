from fastapi import FastAPI, HTTPException

app = FastAPI()

# ----- In‑memory “database” -----
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build CRUD API", "done": False},
    {"id": 3, "title": "Write README", "done": True}
]

# ----- Existing root & health endpoints -----
# ... (keep them as before)

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