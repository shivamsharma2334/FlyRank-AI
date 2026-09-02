# Task API — Week 2 CRUD Assignment

A small FastAPI service that manages an in-memory to-do list. It implements Create, Read, Update, and Delete (CRUD), validates request bodies, exposes interactive Swagger UI, and is designed for Git/GitHub submission.

## Requirements

- Python 3.10+
- pip

## Run locally

```bash
python -m venv .venv
```

Activate the environment:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app:app --reload
```

Open Swagger UI at:

`http://localhost:8000/docs`

## Endpoints

| Method | Endpoint | Purpose | Success |
|---|---|---|---|
| GET | `/` | API description | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List tasks | 200 |
| GET | `/tasks/{id}` | Get one task | 200 |
| POST | `/tasks` | Create task | 201 |
| PUT | `/tasks/{id}` | Update task | 200 |
| DELETE | `/tasks/{id}` | Delete task | 204 |

Invalid request bodies return `400`. Unknown task IDs return `404`.

## curl examples

List tasks:

```bash
curl -i http://localhost:8000/tasks
```

Get task 1:

```bash
curl -i http://localhost:8000/tasks/1
```

Create:

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

Invalid create:

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
```

Update:

```bash
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

Delete:

```bash
curl -i -X DELETE http://localhost:8000/tasks/2
```

## Tests

Run:

```bash
pytest -q
```

## Important note about storage

The task list is stored only in memory. Restarting the server resets the sample data. This is intentional for Week 2; a database is introduced later in the track.

## Swagger evidence

After starting the server, open `/docs`, expand each endpoint, and use **Try it out** to perform the full CRUD cycle. Add your screenshot to the submission package as `swagger-screenshot.png`.

## Git/GitHub submission

Create a public repository and make at least six meaningful commits, ideally one for each assignment stage:

1. `Stage 0: hello server`
2. `Stage 1: root and health endpoints`
3. `Stage 2: read endpoints with 404`
4. `Stage 3: create with validation`
5. `Stage 4: full CRUD`
6. `Stage 5: Swagger UI`
7. `Stage 6: publish and docs`

For the assignment, the README should contain run instructions, an endpoint table, curl output, and a Swagger screenshot.
