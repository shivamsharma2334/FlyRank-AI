from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="Task API", version="1.0", description="A small in-memory CRUD API.")

tasks = [
    {"id": 1, "title": "Learn HTTP", "done": False},
    {"id": 2, "title": "Build CRUD API", "done": False},
    {"id": 3, "title": "Test with Swagger", "done": True},
]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @model_validator(mode="after")
    def require_update(self):
        if self.title is None and self.done is None:
            raise ValueError("Provide title and/or done")
        if self.title is not None and not self.title.strip():
            raise ValueError("title must not be empty")
        return self


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    next_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": next_id, "title": task.title.strip(), "done": False}
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if update.title is not None:
        task["title"] = update.title.strip()
    if update.done is not None:
        task["done"] = update.done
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    index = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.pop(index)
    return None
