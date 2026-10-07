const express = require("express");
const swaggerUi = require("swagger-ui-express");
const swaggerDocument = require("./openapi.json");
const Database = require("better-sqlite3");

const app = express();
const PORT = process.env.PORT || 3000;

// ========================================
// SQLite database configuration
// ========================================

const db = new Database("tasks.db");

// Improves reliability and concurrency for SQLite.
db.pragma("journal_mode = WAL");

// Create the tasks table automatically.
db.prepare(`
  CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
      CHECK (done IN (0, 1))
  )
`).run();

// Optional stretch goal:
// Speeds up queries that filter tasks using the done column.
db.prepare(`
  CREATE INDEX IF NOT EXISTS idx_tasks_done
  ON tasks(done)
`).run();

// Seed exactly three tasks only when the table is empty.
const taskCount = db
  .prepare("SELECT COUNT(*) AS count FROM tasks")
  .get();

if (taskCount.count === 0) {
  const insertTask = db.prepare(`
    INSERT INTO tasks (title, done)
    VALUES (?, ?)
  `);

  const seedTasks = db.transaction(() => {
    insertTask.run("Learn Express", 0);
    insertTask.run("Build a CRUD API", 0);
    insertTask.run("Test API endpoints", 1);
  });

  seedTasks();

  console.log("Database seeded with 3 example tasks");
}

// ========================================
// Reusable prepared statements
// ========================================

const getAllTasksStatement = db.prepare(`
  SELECT id, title, done
  FROM tasks
  ORDER BY id ASC
`);

const getTaskByIdStatement = db.prepare(`
  SELECT id, title, done
  FROM tasks
  WHERE id = ?
`);

const createTaskStatement = db.prepare(`
  INSERT INTO tasks (title, done)
  VALUES (?, ?)
`);

const updateTitleStatement = db.prepare(`
  UPDATE tasks
  SET title = ?
  WHERE id = ?
`);

const updateDoneStatement = db.prepare(`
  UPDATE tasks
  SET done = ?
  WHERE id = ?
`);

const updateTaskStatement = db.prepare(`
  UPDATE tasks
  SET title = ?, done = ?
  WHERE id = ?
`);

const deleteTaskStatement = db.prepare(`
  DELETE FROM tasks
  WHERE id = ?
`);

// ========================================
// Helper functions
// ========================================

function formatTask(task) {
  if (!task) {
    return null;
  }

  return {
    id: task.id,
    title: task.title,
    done: Boolean(task.done),
  };
}

function isValidTaskId(value) {
  return Number.isInteger(value) && value > 0;
}

// ========================================
// Middleware
// ========================================

app.use(express.json());

app.use(
  "/docs",
  swaggerUi.serve,
  swaggerUi.setup(swaggerDocument)
);

// ========================================
// General routes
// ========================================

app.get("/", (req, res) => {
  res.status(200).json({
    name: "Task API",
    version: "2.0",
    storage: "SQLite",
    endpoints: [
      "GET /tasks",
      "GET /tasks/:id",
      "POST /tasks",
      "PUT /tasks/:id",
      "DELETE /tasks/:id",
      "GET /stats",
    ],
    documentation: "/docs",
  });
});

app.get("/health", (req, res) => {
  try {
    db.prepare("SELECT 1").get();

    res.status(200).json({
      status: "ok",
      database: "ok",
    });
  } catch (error) {
    console.error("Database health check failed:", error);

    res.status(500).json({
      status: "error",
      database: "unavailable",
    });
  }
});

// ========================================
// Stage 1: Read tasks from SQLite
// ========================================

app.get("/tasks", (req, res) => {
  try {
    const { search, done, sort } = req.query;

    const conditions = [];
    const parameters = [];

    if (search !== undefined) {
      if (
        typeof search !== "string" ||
        search.trim() === ""
      ) {
        return res.status(400).json({
          error: "Search must be a non-empty string",
        });
      }

      conditions.push("title LIKE ?");
      parameters.push(`%${search.trim()}%`);
    }

    if (done !== undefined) {
      if (done !== "true" && done !== "false") {
        return res.status(400).json({
          error: "Done filter must be true or false",
        });
      }

      conditions.push("done = ?");
      parameters.push(done === "true" ? 1 : 0);
    }

    let sql = `
      SELECT id, title, done
      FROM tasks
    `;

    if (conditions.length > 0) {
      sql += ` WHERE ${conditions.join(" AND ")}`;
    }

    if (sort === "title") {
      sql += " ORDER BY title COLLATE NOCASE ASC";
    } else if (sort === undefined || sort === "id") {
      sql += " ORDER BY id ASC";
    } else {
      return res.status(400).json({
        error: "Sort must be id or title",
      });
    }

    const tasks = db
      .prepare(sql)
      .all(...parameters)
      .map(formatTask);

    res.status(200).json(tasks);
  } catch (error) {
    console.error("Failed to fetch tasks:", error);

    res.status(500).json({
      error: "Failed to fetch tasks",
    });
  }
});

app.get("/tasks/:id", (req, res) => {
  try {
    const taskId = Number(req.params.id);

    if (!isValidTaskId(taskId)) {
      return res.status(404).json({
        error: `Task ${req.params.id} not found`,
      });
    }

    const task = getTaskByIdStatement.get(taskId);

    if (!task) {
      return res.status(404).json({
        error: `Task ${taskId} not found`,
      });
    }

    res.status(200).json(formatTask(task));
  } catch (error) {
    console.error("Failed to fetch task:", error);

    res.status(500).json({
      error: "Failed to fetch task",
    });
  }
});

// ========================================
// Stage 2: Create tasks using SQL
// ========================================

app.post("/tasks", (req, res) => {
  try {
    const { title } = req.body;

    if (
      title === undefined ||
      typeof title !== "string" ||
      title.trim() === ""
    ) {
      return res.status(400).json({
        error:
          "Title is required and must be a non-empty string",
      });
    }

    const result = createTaskStatement.run(
      title.trim(),
      0
    );

    const newTask = getTaskByIdStatement.get(
      result.lastInsertRowid
    );

    res.status(201).json(formatTask(newTask));
  } catch (error) {
    console.error("Failed to create task:", error);

    res.status(500).json({
      error: "Failed to create task",
    });
  }
});

// ========================================
// Stage 3: Update and delete using SQL
// ========================================

app.put("/tasks/:id", (req, res) => {
  try {
    const taskId = Number(req.params.id);

    if (!isValidTaskId(taskId)) {
      return res.status(404).json({
        error: `Task ${req.params.id} not found`,
      });
    }

    const existingTask = getTaskByIdStatement.get(taskId);

    if (!existingTask) {
      return res.status(404).json({
        error: `Task ${taskId} not found`,
      });
    }

    const { title, done } = req.body;

    if (title === undefined && done === undefined) {
      return res.status(400).json({
        error: "Request body must contain title or done",
      });
    }

    if (
      title !== undefined &&
      (typeof title !== "string" ||
        title.trim() === "")
    ) {
      return res.status(400).json({
        error: "Title must be a non-empty string",
      });
    }

    if (
      done !== undefined &&
      typeof done !== "boolean"
    ) {
      return res.status(400).json({
        error: "Done must be true or false",
      });
    }

    if (title !== undefined && done !== undefined) {
      updateTaskStatement.run(
        title.trim(),
        done ? 1 : 0,
        taskId
      );
    } else if (title !== undefined) {
      updateTitleStatement.run(title.trim(), taskId);
    } else {
      updateDoneStatement.run(done ? 1 : 0, taskId);
    }

    const updatedTask = getTaskByIdStatement.get(taskId);

    res.status(200).json(formatTask(updatedTask));
  } catch (error) {
    console.error("Failed to update task:", error);

    res.status(500).json({
      error: "Failed to update task",
    });
  }
});

app.delete("/tasks/:id", (req, res) => {
  try {
    const taskId = Number(req.params.id);

    if (!isValidTaskId(taskId)) {
      return res.status(404).json({
        error: `Task ${req.params.id} not found`,
      });
    }

    const result = deleteTaskStatement.run(taskId);

    if (result.changes === 0) {
      return res.status(404).json({
        error: `Task ${taskId} not found`,
      });
    }

    res.status(204).send();
  } catch (error) {
    console.error("Failed to delete task:", error);

    res.status(500).json({
      error: "Failed to delete task",
    });
  }
});

// ========================================
// Optional extra: database statistics
// ========================================

app.get("/stats", (req, res) => {
  try {
    const stats = db
      .prepare(`
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS completed,
          SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS pending
        FROM tasks
      `)
      .get();

    res.status(200).json({
      total: stats.total,
      completed: stats.completed || 0,
      pending: stats.pending || 0,
    });
  } catch (error) {
    console.error("Failed to fetch statistics:", error);

    res.status(500).json({
      error: "Failed to fetch statistics",
    });
  }
});

// ========================================
// 404 handler
// ========================================

app.use((req, res) => {
  res.status(404).json({
    error: "Route not found",
  });
});

// ========================================
// Start server
// ========================================

const server = app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(
    `Swagger UI available at http://localhost:${PORT}/docs`
  );
  console.log("SQLite database: tasks.db");
});

// Close the database safely when the server stops.
function shutdown() {
  console.log("\nShutting down server...");

  server.close(() => {
    db.close();
    console.log("Database connection closed");
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);  