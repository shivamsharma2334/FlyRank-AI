# Week 2 Bonus — AI Rematch Prompt

Build a small **Python FastAPI** API called `Task API`.

Requirements:
- Store tasks in an in-memory list; do not use a database or files.
- Each task has `id` (number), `title` (text), and `done` (boolean).
- Start with three example tasks.
- `GET /` returns the API name, version, and `/tasks`.
- `GET /health` returns `{"status":"ok"}`.
- `GET /tasks` lists all tasks.
- `GET /tasks/{id}` returns one task; unknown IDs return 404 with a JSON error.
- `POST /tasks` accepts `{"title":"..."}`, assigns the next free ID, sets `done` to false, and returns 201.
- Missing or empty titles return 400 with a JSON error.
- `PUT /tasks/{id}` updates title and/or done; unknown IDs return 404; invalid or empty bodies return 400.
- `DELETE /tasks/{id}` removes the task and returns 204 with an empty body; unknown IDs return 404.
- Swagger UI must be available at `/docs`.
- Include clear setup/run instructions and endpoint documentation.
- Keep the implementation small and readable.

Generate the code in a separate `ai-version/` folder or branch. Do not replace the hand-built version.
