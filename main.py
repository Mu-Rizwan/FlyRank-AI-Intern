from fastapi import FastAPI

app = FastAPI()

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