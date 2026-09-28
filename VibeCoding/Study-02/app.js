const STORAGE_KEY = "todos";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const categorySelect = document.getElementById("category-select");
const filterTabs = document.querySelectorAll(".filter-btn");
const todoList = document.getElementById("todo-list");
const emptyState = document.getElementById("empty-state");
const progressPercent = document.getElementById("progress-percent");
const progressFill = document.getElementById("progress-fill");

let todos = loadTodos();
let currentFilter = "전체";
let editingId = null;

function loadTodos() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.filter(
      (t) =>
        t &&
        typeof t.id === "string" &&
        typeof t.title === "string" &&
        typeof t.category === "string" &&
        typeof t.completed === "boolean" &&
        typeof t.createdAt === "string"
    );
  } catch {
    return [];
  }
}

function saveTodos() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

function createId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function addTodo(title, category) {
  todos.push({
    id: createId(),
    title,
    category,
    completed: false,
    createdAt: new Date().toISOString(),
  });
  saveTodos();
  render();
}

function toggleTodo(id) {
  const todo = todos.find((t) => t.id === id);
  if (todo) {
    todo.completed = !todo.completed;
    saveTodos();
    render();
  }
}

function deleteTodo(id) {
  todos = todos.filter((t) => t.id !== id);
  saveTodos();
  render();
}

function editTodo(id, newTitle) {
  const todo = todos.find((t) => t.id === id);
  const trimmed = newTitle.trim();
  if (todo && trimmed && trimmed !== todo.title) {
    todo.title = trimmed;
    saveTodos();
  }
  editingId = null;
  render();
}

function getFilteredTodos() {
  if (currentFilter === "전체") return todos;
  return todos.filter((t) => t.category === currentFilter);
}

function render() {
  const filtered = getFilteredTodos();

  todoList.innerHTML = "";
  filtered.forEach((todo) => {
    const li = document.createElement("li");
    li.className = "todo-item" + (todo.completed ? " completed" : "");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "todo-checkbox";
    checkbox.checked = todo.completed;
    checkbox.addEventListener("change", () => toggleTodo(todo.id));

    let titleEl;

    if (editingId === todo.id) {
      titleEl = document.createElement("input");
      titleEl.type = "text";
      titleEl.className = "todo-edit-input";
      titleEl.value = todo.title;

      const finishEdit = () => editTodo(todo.id, titleEl.value);

      titleEl.addEventListener("blur", finishEdit);
      titleEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          finishEdit();
        } else if (e.key === "Escape") {
          editingId = null;
          render();
        }
      });
    } else {
      titleEl = document.createElement("span");
      titleEl.className = "todo-title";
      titleEl.textContent = todo.title;
      titleEl.addEventListener("dblclick", () => {
        editingId = todo.id;
        render();
      });
    }

    const category = document.createElement("span");
    category.className = "todo-category " + todo.category;
    category.textContent = todo.category;

    const editBtn = document.createElement("button");
    editBtn.className = "edit-btn";
    editBtn.textContent = "✎";
    editBtn.addEventListener("click", () => {
      editingId = todo.id;
      render();
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "delete-btn";
    deleteBtn.textContent = "✕";
    deleteBtn.addEventListener("click", () => deleteTodo(todo.id));

    li.append(checkbox, titleEl, category, editBtn, deleteBtn);
    todoList.appendChild(li);

    if (editingId === todo.id) {
      titleEl.focus();
      titleEl.select();
    }
  });

  emptyState.classList.toggle("visible", filtered.length === 0);

  updateProgress();
}

function updateProgress() {
  const total = todos.length;
  const doneCount = todos.filter((t) => t.completed).length;
  const percent = total === 0 ? 0 : Math.round((doneCount / total) * 100);

  progressPercent.textContent = percent + "%";
  progressFill.style.width = percent + "%";
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const title = input.value.trim();
  if (!title) return;

  addTodo(title, categorySelect.value);
  input.value = "";
  input.focus();
});

filterTabs.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterTabs.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    render();
  });
});

render();
