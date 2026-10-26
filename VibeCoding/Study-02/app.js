const STORAGE_KEY = "todos";

const CATEGORY_LABELS = {
  work: "업무",
  personal: "개인",
  study: "공부",
};

// 자동 분류용 키워드. 텍스트에 포함된 키워드가 가장 많은 카테고리로 분류한다.
const CATEGORY_KEYWORDS = {
  work: ["회의", "미팅", "보고서", "업무", "프로젝트", "발표", "출장", "메일", "견적", "계약", "거래처", "고객", "납품", "기획", "결재", "회사", "마감", "meeting", "report"],
  study: ["공부", "시험", "과제", "강의", "수업", "복습", "예습", "독서", "문제집", "자격증", "영어", "토익", "퀴즈", "논문", "숙제", "학습", "암기", "study", "exam"],
  personal: ["장보기", "운동", "병원", "약속", "청소", "빨래", "친구", "가족", "여행", "쇼핑", "요리", "은행", "생일", "산책", "헬스", "미용실", "영화"],
};
const DEFAULT_CATEGORY = "personal"; // 일치하는 키워드가 없을 때

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const categorySelect = document.getElementById("category-select");
const todoList = document.getElementById("todo-list");
const emptyState = document.getElementById("empty-state");
const clearCompletedBtn = document.getElementById("clear-completed");
const storageWarning = document.getElementById("storage-warning");
const filterBtns = document.querySelectorAll(".filter-btn");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");
const todayEl = document.getElementById("today");

// ---------- 저장소 (localStorage는 이 두 함수에서만 접근) ----------

// 저장된 todos를 읽는다. 값이 없거나 깨졌으면 빈 배열을 돌려준다.
function loadTodos() {
  let raw;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
  } catch {
    storageWarning.hidden = false;
    return [];
  }
  if (raw === null) return [];

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (t) =>
        t &&
        typeof t.id === "string" &&
        typeof t.text === "string" &&
        typeof t.category === "string" &&
        typeof t.done === "boolean" &&
        typeof t.createdAt === "string"
    );
  } catch {
    return [];
  }
}

// todos를 즉시 저장하고, 저장할 수 없으면 상단 안내를 보여 준다.
function saveTodos() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
    storageWarning.hidden = true;
  } catch {
    storageWarning.hidden = false;
  }
}

// ---------- 상태 ----------

let todos = loadTodos();
let currentFilter = "all"; // 'all' | 'work' | 'personal' | 'study' (저장하지 않음)
let editingId = null; // 수정 중인 항목의 id

// ---------- 상태 변경 (배열 수정 → 저장 → render) ----------

// 현재 필터를 바꾼다.
function setFilter(filter) {
  currentFilter = filter;
  render();
}

// 텍스트의 키워드로 카테고리를 추정한다. 동점이면 work, study, personal 순으로 우선한다.
function classifyText(text) {
  const lower = text.toLowerCase();
  let best = DEFAULT_CATEGORY;
  let bestScore = 0;
  Object.entries(CATEGORY_KEYWORDS).forEach(([category, keywords]) => {
    const score = keywords.filter((k) => lower.includes(k)).length;
    if (score > bestScore) {
      best = category;
      bestScore = score;
    }
  });
  return best;
}

// 공백을 제거한 텍스트로 새 항목을 추가한다. 빈 값이면 등록하지 않고, 'auto'면 키워드로 분류한다.
function addTodo(text, category) {
  const trimmed = text.trim();
  if (!trimmed) {
    input.focus();
    return;
  }
  if (category === "auto") category = classifyText(trimmed);

  todos.push({
    id: Date.now().toString() + Math.random().toString(36).slice(2, 6), // 같은 ms에 추가돼도 겹치지 않게
    text: trimmed,
    category,
    done: false,
    createdAt: new Date().toISOString(),
  });
  saveTodos();
  render();

  input.value = "";
  input.focus();
}

// 항목의 완료 상태를 뒤집는다.
function toggleTodo(id) {
  const todo = todos.find((t) => t.id === id);
  if (!todo) return;
  todo.done = !todo.done;
  saveTodos();
  render();
}

// 확인 후 항목 하나를 삭제한다.
function deleteTodo(id) {
  if (!confirm("이 항목을 삭제할까요?")) return;
  todos = todos.filter((t) => t.id !== id);
  if (editingId === id) editingId = null;
  saveTodos();
  render();
}

// 완료된 항목을 모두 삭제한다.
function deleteCompleted() {
  todos = todos.filter((t) => !t.done);
  if (!todos.some((t) => t.id === editingId)) editingId = null;
  saveTodos();
  render();
}

// 항목을 수정 모드로 전환한다.
function startEdit(id) {
  editingId = id;
  render();
}

// 수정 내용을 저장한다. 텍스트가 비어 있으면 수정을 취소한다.
function commitEdit(id, text, category) {
  if (editingId !== id) return; // 이미 저장/취소된 수정
  editingId = null;

  const todo = todos.find((t) => t.id === id);
  const trimmed = text.trim();
  if (todo && trimmed) {
    todo.text = trimmed;
    todo.category = category;
    saveTodos();
  }
  render();
}

// 수정을 취소하고 원래 내용으로 되돌린다.
function cancelEdit() {
  editingId = null;
  render();
}

// ---------- 렌더링 ----------

// 현재 필터에 해당하는 항목만 돌려준다.
function getFilteredTodos() {
  if (currentFilter === "all") return todos;
  return todos.filter((t) => t.category === currentFilter);
}

// 텍스트 입력과 카테고리 선택으로 이루어진 수정용 영역을 만든다.
function createEditFields(todo, li) {
  const textInput = document.createElement("input");
  textInput.type = "text";
  textInput.className = "todo-edit-input";
  textInput.maxLength = 100;
  textInput.value = todo.text;
  textInput.setAttribute("aria-label", "할 일 수정");

  const select = document.createElement("select");
  select.className = "category-select";
  select.setAttribute("aria-label", "카테고리");
  Object.entries(CATEGORY_LABELS).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  select.value = todo.category;

  const commit = () => commitEdit(todo.id, textInput.value, select.value);

  li.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  });
  // 입력창과 선택창 사이로 포커스가 옮겨갈 때는 저장하지 않는다.
  li.addEventListener("focusout", (e) => {
    if (!li.contains(e.relatedTarget)) commit();
  });

  return [textInput, select];
}

// 항목 하나의 <li>를 만든다. 사용자 텍스트는 textContent로만 넣는다.
function createTodoItem(todo) {
  const li = document.createElement("li");
  li.className = "todo-item" + (todo.done ? " done" : "");

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "todo-checkbox";
  checkbox.checked = todo.done;
  checkbox.setAttribute("aria-label", "완료");
  checkbox.addEventListener("change", () => toggleTodo(todo.id));
  li.appendChild(checkbox);

  if (editingId === todo.id) {
    li.append(...createEditFields(todo, li));
    return li;
  }

  const title = document.createElement("span");
  title.className = "todo-title";
  title.textContent = todo.text;
  title.title = "더블클릭하여 수정";
  title.addEventListener("dblclick", () => startEdit(todo.id));

  const badge = document.createElement("span");
  badge.className = "badge badge-" + todo.category;
  badge.textContent = CATEGORY_LABELS[todo.category] || todo.category;

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "icon-btn";
  editBtn.setAttribute("aria-label", "수정");
  editBtn.textContent = "✎";
  editBtn.addEventListener("click", () => startEdit(todo.id));

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "icon-btn delete-btn";
  deleteBtn.setAttribute("aria-label", "삭제");
  deleteBtn.textContent = "✕";
  deleteBtn.addEventListener("click", () => deleteTodo(todo.id));

  li.append(title, badge, editBtn, deleteBtn);
  return li;
}

// todos 상태를 기준으로 목록, 필터 탭, 진행률을 모두 다시 그린다.
function render() {
  const visible = getFilteredTodos();

  todoList.innerHTML = "";
  visible.forEach((todo) => todoList.appendChild(createTodoItem(todo)));

  emptyState.hidden = visible.length > 0;

  filterBtns.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.filter === currentFilter);
  });

  const total = visible.length;
  const doneCount = visible.filter((t) => t.done).length;
  const percent = total === 0 ? 0 : Math.round((doneCount / total) * 100);
  progressText.textContent = `${doneCount} / ${total} 완료 (${percent}%)`;
  progressFill.style.width = percent + "%";

  if (editingId !== null) {
    const editInput = todoList.querySelector(".todo-edit-input");
    if (editInput) {
      editInput.focus();
      editInput.select();
    }
  }
}

// 헤더에 오늘 날짜를 채운다.
function showToday() {
  todayEl.textContent = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });
}

// ---------- 이벤트 연결 및 시작 ----------

// 추가 버튼 클릭과 Enter 키 모두 form submit으로 처리된다.
form.addEventListener("submit", (e) => {
  e.preventDefault();
  addTodo(input.value, categorySelect.value);
});

filterBtns.forEach((btn) => {
  btn.addEventListener("click", () => setFilter(btn.dataset.filter));
});

clearCompletedBtn.addEventListener("click", deleteCompleted);

showToday();
input.focus();
render();
