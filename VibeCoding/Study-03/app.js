const SCREENS = ["start", "quiz", "summary", "result", "ranking"];

const CATEGORY_ORDER = ["history", "science", "geography", "general"];
const CATEGORIES = {
  history:   { name: "한국사" },
  science:   { name: "과학" },
  geography: { name: "지리" },
  general:   { name: "일반상식" }
};

const POINTS_PER_CORRECT = 10;
const PRAISES = ["정답이에요!", "잘했어요!", "훌륭해요!", "척척박사네요!", "완벽해요!"];

const RANKING_KEY = "quizRanking";
const RANKING_LIMIT = 100;   // 보관하는 최대 기록 수
const RANKING_VIEW = 10;     // 순위표에 보여 주는 기록 수

let state = createState();
let screenBeforeRanking = "start";

// 한 판의 모든 진행 상태를 담은 초기 state를 만든다.
function createState() {
  return {
    nickname: "",
    categoryIndex: 0,
    questionIndex: 0,
    questions: [],          // 카테고리 순서대로 섞인 문제 배열의 배열
    correctTotal: 0,
    correctByCategory: {},
    wrongLog: [],
    answered: false,
    selectedIndex: null,
    lastFeedback: null,     // 정답일 때 보여 줄 칭찬 문구
    recorded: false,        // 순위 저장을 이미 했는지
    myEntry: null,          // 이번 판의 순위 기록
    myRank: 0,
    saveFailed: false
  };
}

// ---------- 유틸 ----------
const $ = (id) => document.getElementById(id);

// Fisher-Yates로 섞은 새 배열을 돌려준다.
function shuffle(array) {
  const a = array.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// 보기를 섞고, 섞인 순서에 맞춰 answerIndex를 다시 계산한 사본을 돌려준다.
function shuffleChoices(q) {
  const order = shuffle(q.choices.map((_, i) => i));
  return {
    ...q,
    choices: order.map((i) => q.choices[i]),
    answerIndex: order.indexOf(q.answerIndex)
  };
}

// 카테고리 순서대로, 문제와 보기를 섞은 이번 판 문제 배열을 만든다.
function buildRound() {
  return CATEGORY_ORDER.map((cat) =>
    shuffle(QUESTIONS.filter((q) => q.category === cat)).map(shuffleChoices)
  );
}

// 지금 풀고 있는 문제를 돌려준다.
function currentQuestion() {
  return state.questions[state.categoryIndex][state.questionIndex];
}

// 이번 판의 전체 문제 수를 센다.
function totalQuestions() {
  return state.questions.reduce((sum, list) => sum + list.length, 0);
}

// 전체 기준 현재 문제 번호(1부터)를 돌려준다.
function currentPosition() {
  let n = 0;
  for (let i = 0; i < state.categoryIndex; i++) n += state.questions[i].length;
  return n + state.questionIndex + 1;
}

// 이름에 해당하는 화면만 보이게 한다.
function showScreen(name) {
  if (!SCREENS.includes(name)) return;
  SCREENS.forEach((s) => {
    $("screen-" + s).hidden = s !== name;
  });
}

// 지금 보이는 화면 이름을 돌려준다.
function currentScreen() {
  return SCREENS.find((s) => !$("screen-" + s).hidden);
}

// 타임스탬프를 YYYY-MM-DD 문자열로 바꾼다.
function formatDate(ms) {
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

// ---------- 순위 저장소 (localStorage는 이 영역에서만 사용) ----------
// 순위 기록 한 건이 올바른 형식인지 검사한다.
function isValidEntry(e) {
  return e && typeof e === "object" &&
    typeof e.nickname === "string" &&
    Number.isFinite(e.score) &&
    Number.isFinite(e.playedAt) &&
    e.correctByCategory && typeof e.correctByCategory === "object";
}

// 저장된 순위를 읽는다. 없거나 손상되었거나 사용할 수 없으면 빈 배열.
function loadRanking() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RANKING_KEY));
    return Array.isArray(parsed) ? parsed.filter(isValidEntry) : [];
  } catch (e) {
    return [];
  }
}

// 순위를 저장하고 성공 여부를 돌려준다.
function saveRanking(list) {
  try {
    localStorage.setItem(RANKING_KEY, JSON.stringify(list));
    return true;
  } catch (e) {
    return false;
  }
}

// 총점 높은 순, 같으면 먼저 기록한 쪽이 앞.
function compareEntries(a, b) {
  return b.score - a.score || a.playedAt - b.playedAt;
}

// 이번 판 결과를 순위에 한 번만 기록하고 순위를 계산한다.
function recordResult() {
  if (state.recorded) return;
  state.recorded = true;
  const entry = {
    nickname: state.nickname,
    score: state.correctTotal * POINTS_PER_CORRECT,
    correctByCategory: { ...state.correctByCategory },
    playedAt: Date.now()
  };
  const list = loadRanking();
  list.push(entry);
  list.sort(compareEntries);
  state.myEntry = entry;
  state.myRank = list.indexOf(entry) + 1;
  state.saveFailed = !saveRanking(list.slice(0, RANKING_LIMIT));
}

// ---------- 게임 흐름 ----------
// 상태를 초기화하고 문제를 섞어 첫 문제를 시작한다.
function startGame(nickname) {
  state = createState();
  state.nickname = nickname;
  state.questions = buildRound();
  CATEGORY_ORDER.forEach((cat) => { state.correctByCategory[cat] = 0; });
  showScreen("quiz");
  renderQuiz();
}

// 닉네임을 검사하고 통과하면 게임을 시작한다.
function handleStart() {
  const nickname = $("nickname").value.trim();
  if (!nickname) {
    $("nickname-error").hidden = false;
    $("nickname").focus();
    return;
  }
  $("nickname-error").hidden = true;
  startGame(nickname);
}

// 보기를 선택해 즉시 채점한다. 이미 답했으면 무시한다.
function selectChoice(index) {
  if (state.answered) return;
  const q = currentQuestion();
  const cat = CATEGORY_ORDER[state.categoryIndex];
  state.answered = true;
  state.selectedIndex = index;

  if (index === q.answerIndex) {
    state.correctTotal++;
    state.correctByCategory[cat]++;
    state.lastFeedback = PRAISES[Math.floor(Math.random() * PRAISES.length)];
  } else {
    state.lastFeedback = null;
    state.wrongLog.push({
      category: cat,
      question: q.question,
      chosen: q.choices[index],
      correct: q.choices[q.answerIndex],
      explanation: q.explanation
    });
  }
  renderQuiz();
}

// 다음 문제로 넘어가거나, 카테고리가 끝났으면 요약 화면을 보여 준다.
function nextQuestion() {
  if (!state.answered) return;
  const list = state.questions[state.categoryIndex];
  state.answered = false;
  state.selectedIndex = null;
  if (state.questionIndex < list.length - 1) {
    state.questionIndex++;
    renderQuiz();
  } else {
    renderSummary();
    showScreen("summary");
  }
}

// 다음 카테고리로 가거나, 마지막이면 순위를 기록하고 결과 화면을 연다.
function continueAfterSummary() {
  if (state.categoryIndex < CATEGORY_ORDER.length - 1) {
    state.categoryIndex++;
    state.questionIndex = 0;
    showScreen("quiz");
    renderQuiz();
  } else {
    recordResult();
    renderResult();
    showScreen("result");
  }
}

// ---------- 렌더 ----------
// 퀴즈 화면 전체를 state에 맞게 다시 그린다.
function renderQuiz() {
  const q = currentQuestion();
  const cat = CATEGORY_ORDER[state.categoryIndex];
  const total = totalQuestions();
  const pos = currentPosition();

  const screen = $("screen-quiz");
  CATEGORY_ORDER.forEach((c) => screen.classList.remove("cat-" + c));
  screen.classList.add("cat-" + cat);

  $("quiz-category").textContent = CATEGORIES[cat].name;
  $("quiz-score").textContent = state.correctTotal * POINTS_PER_CORRECT;
  $("quiz-progress-text").textContent = pos + " / " + total;
  // 진행 바는 푼 문제 수 기준 (답을 고르면 현재 문제까지 채운다)
  const done = state.answered ? pos : pos - 1;
  $("quiz-progress-bar").style.width = (done / total) * 100 + "%";
  document.querySelector(".progress").setAttribute("aria-valuenow", done);
  $("quiz-question").textContent = q.question;

  document.querySelectorAll("#quiz-choices .choice").forEach((btn, i) => {
    btn.textContent = q.choices[i];
    btn.classList.remove("correct", "wrong");
    btn.disabled = state.answered;
    if (state.answered) {
      if (i === q.answerIndex) btn.classList.add("correct");
      else if (i === state.selectedIndex) btn.classList.add("wrong");
    }
  });

  renderExplanation(q);
  $("btn-next").disabled = !state.answered;
}

// 답을 고른 뒤 칭찬 또는 정답과 해설을 보여 준다.
function renderExplanation(q) {
  const box = $("quiz-explanation");
  box.replaceChildren();
  if (!state.answered) {
    box.hidden = true;
    return;
  }
  const head = document.createElement("p");
  head.className = "explanation-head";
  head.textContent = state.selectedIndex === q.answerIndex
    ? state.lastFeedback
    : "정답: " + q.choices[q.answerIndex];
  const body = document.createElement("p");
  body.className = "explanation-body";
  body.textContent = q.explanation;
  box.append(head, body);
  box.hidden = false;
}

// 카테고리 요약 화면(예: 한국사 8 / 10)을 그린다.
function renderSummary() {
  const cat = CATEGORY_ORDER[state.categoryIndex];
  const size = state.questions[state.categoryIndex].length;
  $("summary-text").textContent =
    CATEGORIES[cat].name + " " + state.correctByCategory[cat] + " / " + size;
  $("btn-continue").textContent =
    state.categoryIndex < CATEGORY_ORDER.length - 1 ? "계속" : "결과 보기";
}

// 결과 화면(총점, 카테고리별 점수, 순위, 오답 복습)을 그린다.
function renderResult() {
  $("result-total").textContent = state.correctTotal * POINTS_PER_CORRECT;
  $("result-rank").textContent = "이번 판 순위: " + state.myRank + "위";
  $("result-save-warning").hidden = !state.saveFailed;

  const list = $("result-categories");
  list.replaceChildren();
  CATEGORY_ORDER.forEach((cat, i) => {
    const li = document.createElement("li");
    li.className = "cat-" + cat;
    const name = document.createElement("span");
    name.textContent = CATEGORIES[cat].name;
    const score = document.createElement("strong");
    score.textContent = state.correctByCategory[cat] + " / " + state.questions[i].length;
    li.append(name, score);
    list.appendChild(li);
  });

  const review = $("result-review");
  review.replaceChildren();
  if (state.wrongLog.length === 0) {
    const p = document.createElement("p");
    p.textContent = "모두 맞혔어요! 복습할 문제가 없습니다.";
    review.appendChild(p);
    return;
  }
  state.wrongLog.forEach((w) => {
    const item = document.createElement("div");
    item.className = "review-item cat-" + w.category;

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = CATEGORIES[w.category].name;
    const q = document.createElement("p");
    q.className = "review-question";
    q.textContent = w.question;
    const mine = document.createElement("p");
    mine.className = "wrong";
    mine.textContent = "내가 고른 답: " + w.chosen;
    const answer = document.createElement("p");
    answer.className = "correct";
    answer.textContent = "정답: " + w.correct;
    const exp = document.createElement("p");
    exp.textContent = w.explanation;

    item.append(badge, q, mine, answer, exp);
    review.appendChild(item);
  });
}

// 순위표 상위 10개를 그리고, 이번 판 기록을 강조한다.
function renderRanking() {
  const body = $("ranking-body");
  body.replaceChildren();
  const list = loadRanking().sort(compareEntries).slice(0, RANKING_VIEW);

  if (list.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.textContent = "아직 기록이 없어요";
    tr.appendChild(td);
    body.appendChild(tr);
  }

  list.forEach((e, i) => {
    const tr = document.createElement("tr");
    const mine = state.myEntry &&
      e.playedAt === state.myEntry.playedAt && e.nickname === state.myEntry.nickname;
    if (mine) tr.className = "me";
    const cells = [
      i + 1,
      mine ? e.nickname + " (나)" : e.nickname,
      e.score,
      formatDate(e.playedAt)
    ];
    cells.forEach((text, c) => {
      const td = document.createElement("td");
      if (c === 1) td.className = "nick";
      td.textContent = text;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });

  const myRank = $("ranking-my-rank");
  myRank.hidden = !(state.myEntry && state.myRank > RANKING_VIEW);
  myRank.textContent = "내 순위: " + state.myRank + "위";
}

// ---------- 이벤트 ----------
// 순위표 화면을 열고, 돌아갈 화면을 기억해 둔다.
function openRanking() {
  screenBeforeRanking = currentScreen();
  renderRanking();
  showScreen("ranking");
}

$("btn-start").addEventListener("click", handleStart);
$("nickname").addEventListener("input", () => { $("nickname-error").hidden = true; });
$("nickname").addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleStart();
});
$("btn-next").addEventListener("click", nextQuestion);
$("btn-continue").addEventListener("click", continueAfterSummary);
$("btn-retry").addEventListener("click", () => startGame(state.nickname));
$("btn-start-ranking").addEventListener("click", openRanking);
$("btn-result-ranking").addEventListener("click", openRanking);
$("btn-ranking-back").addEventListener("click", () => showScreen(screenBeforeRanking));

document.querySelectorAll("#quiz-choices .choice").forEach((btn, i) => {
  btn.addEventListener("click", () => selectChoice(i));
});

// 퀴즈 화면에서 1~4번 키는 보기 선택, Enter는 다음 문제.
document.addEventListener("keydown", (e) => {
  if (currentScreen() !== "quiz") return;
  if (e.key >= "1" && e.key <= "4") {
    selectChoice(Number(e.key) - 1);
  } else if (e.key === "Enter") {
    e.preventDefault(); // 포커스된 버튼의 기본 클릭과 겹쳐 두 번 넘어가는 것을 방지
    if (!e.repeat) nextQuestion();
  }
});

showScreen("start");
