// 난이도 표기: 쉬움(E) 3 / 보통(M) 5 / 어려움(H) 2 — 카테고리마다 동일
const QUESTIONS = [
  // ===== 한국사 =====
  { id: "h01", category: "history", // E
    question: "고구려를 세운 인물은?",
    choices: ["온조", "주몽", "박혁거세", "김수로"],
    answerIndex: 1,
    explanation: "주몽(동명성왕)이 기원전 37년 졸본 지역에서 고구려를 세웠습니다." },
  { id: "h02", category: "history", // E
    question: "훈민정음을 창제한 조선의 왕은?",
    choices: ["세종", "태종", "정조", "성종"],
    answerIndex: 0,
    explanation: "세종이 1443년 훈민정음을 창제하고 1446년에 반포했습니다." },
  { id: "h03", category: "history", // E
    question: "임진왜란 때 거북선을 앞세워 활약한 장군은?",
    choices: ["권율", "곽재우", "이순신", "김시민"],
    answerIndex: 2,
    explanation: "이순신은 옥포·한산도 등 여러 해전에서 거북선과 함께 승리를 이끌었습니다." },
  { id: "h04", category: "history", // M
    question: "612년 살수에서 수나라 대군을 크게 물리친 고구려 장군은?",
    choices: ["연개소문", "을지문덕", "양만춘", "계백"],
    answerIndex: 1,
    explanation: "을지문덕은 거짓 후퇴 작전으로 수나라군을 지치게 한 뒤 살수에서 격파했습니다." },
  { id: "h05", category: "history", // M
    question: "698년 발해를 세운 인물은?",
    choices: ["대조영", "왕건", "궁예", "견훤"],
    answerIndex: 0,
    explanation: "대조영이 고구려 유민과 말갈족을 이끌고 동모산에서 발해를 건국했습니다." },
  { id: "h06", category: "history", // M
    question: "고려 시대에 만든 팔만대장경판이 보관되어 있는 사찰은?",
    choices: ["불국사", "통도사", "해인사", "송광사"],
    answerIndex: 2,
    explanation: "팔만대장경판은 합천 해인사 장경판전에 보관되어 있습니다." },
  { id: "h07", category: "history", // M
    question: "이성계가 조선을 건국한 해는?",
    choices: ["1274년", "1446년", "1592년", "1392년"],
    answerIndex: 3,
    explanation: "이성계는 1392년 고려를 무너뜨리고 조선을 건국했습니다." },
  { id: "h08", category: "history", // M
    question: "전국적으로 만세 운동이 일어난 3·1 운동은 몇 년에 일어났을까?",
    choices: ["1894년", "1905년", "1910년", "1919년"],
    answerIndex: 3,
    explanation: "3·1 운동은 1919년 3월 1일에 시작되어 전국으로 퍼졌습니다." },
  { id: "h09", category: "history", // H
    question: "병자호란 때 인조가 청 태종에게 세 번 절하고 아홉 번 머리를 조아리는 항복 의식을 치른 곳은?",
    choices: ["강화도", "삼전도", "남한산성", "행주산성"],
    answerIndex: 1,
    explanation: "인조는 남한산성에서 나와 삼전도에서 청 태종에게 항복했습니다." },
  { id: "h10", category: "history", // H
    question: "인쇄 연대가 확인되는 현존 금속활자본 중 가장 오래된 『직지심체요절』을 인쇄한 사찰은?",
    choices: ["흥덕사", "봉정사", "불국사", "부석사"],
    answerIndex: 0,
    explanation: "『직지심체요절』은 1377년 청주 흥덕사에서 금속활자로 인쇄되었습니다." },
  { id: "h11", category: "history", // M
    question: "660년 황산벌 전투에서 계백이 이끄는 백제군과 맞서 싸운 신라군의 총사령관은?",
    choices: ["김춘추", "관창", "김유신", "장보고"],
    answerIndex: 2,
    explanation: "김유신이 이끄는 신라군이 660년 황산벌에서 계백의 백제군을 격파했고, 같은 해 백제는 멸망했습니다." },

  // ===== 과학 =====
  { id: "s01", category: "science", // E
    question: "물의 화학식은?",
    choices: ["H2O2", "CO2", "H2O", "HCl"],
    answerIndex: 2,
    explanation: "물은 수소 원자 2개와 산소 원자 1개로 이루어진 H2O입니다." },
  { id: "s02", category: "science", // E
    question: "지름 기준으로 태양계에서 가장 큰 행성은?",
    choices: ["목성", "토성", "천왕성", "해왕성"],
    answerIndex: 0,
    explanation: "목성은 지름이 지구의 약 11배로 태양계에서 가장 큰 행성입니다." },
  { id: "s03", category: "science", // E
    question: "식물이 광합성을 할 때 공기 중에서 흡수하는 기체는?",
    choices: ["산소", "이산화탄소", "질소", "수소"],
    answerIndex: 1,
    explanation: "식물은 빛에너지로 이산화탄소와 물을 이용해 포도당과 산소를 만듭니다." },
  { id: "s04", category: "science", // M
    question: "진공에서 빛의 속도는 약 얼마일까?",
    choices: ["약 340 m/s", "약 3,000 km/s", "약 3억 km/s", "약 30만 km/s"],
    answerIndex: 3,
    explanation: "빛은 진공에서 초속 약 30만 km(299,792 km)로 나아갑니다." },
  { id: "s05", category: "science", // M
    question: "혈액에서 산소를 운반하는 단백질은?",
    choices: ["백혈구 속 글로불린", "혈소판 속 피브린", "적혈구 속 헤모글로빈", "혈장 속 알부민"],
    answerIndex: 2,
    explanation: "적혈구의 헤모글로빈은 철을 포함하고 있어 산소와 결합해 운반합니다." },
  { id: "s06", category: "science", // M
    question: "지구 대기(건조 공기)를 이루는 기체 중 부피 비율이 가장 큰 것은?",
    choices: ["산소", "이산화탄소", "아르곤", "질소"],
    answerIndex: 3,
    explanation: "대기의 약 78%가 질소이고 산소는 약 21%입니다." },
  { id: "s07", category: "science", // M
    question: "외부에서 힘이 작용하지 않으면 정지한 물체는 계속 정지하고 움직이는 물체는 등속 직선 운동을 한다는 법칙은?",
    choices: ["작용 반작용의 법칙", "가속도의 법칙", "만유인력의 법칙", "관성의 법칙"],
    answerIndex: 3,
    explanation: "뉴턴의 운동 제1법칙인 관성의 법칙입니다." },
  { id: "s08", category: "science", // M
    question: "25℃에서 pH가 7인 수용액의 성질은?",
    choices: ["중성", "산성", "염기성", "강산성"],
    answerIndex: 0,
    explanation: "pH 7은 산성도 염기성도 아닌 중성이며 순수한 물이 대표적입니다." },
  { id: "s09", category: "science", // H
    question: "지구 내부를 통과하는 지진파(P파, S파) 중 액체를 통과하지 못하는 것은?",
    choices: ["P파", "S파", "P파와 S파 모두", "어느 쪽도 아님"],
    answerIndex: 1,
    explanation: "S파는 횡파라 액체를 통과하지 못해, 액체인 외핵의 존재를 알아내는 단서가 되었습니다." },
  { id: "s10", category: "science", // H
    question: "상온(약 20℃)에서 다음 중 소리가 가장 빠르게 전달되는 매질은?",
    choices: ["진공", "액체(물)", "고체(철)", "기체(공기)"],
    answerIndex: 2,
    explanation: "소리는 입자 사이가 촘촘한 고체에서 가장 빠르고 진공에서는 전달되지 않습니다." },

  // ===== 지리 =====
  { id: "g01", category: "geography", // E
    question: "일본의 수도는?",
    choices: ["도쿄", "오사카", "교토", "요코하마"],
    answerIndex: 0,
    explanation: "일본의 수도는 도쿄입니다." },
  { id: "g02", category: "geography", // E
    question: "면적 기준으로 세계에서 가장 넓은 대양은?",
    choices: ["대서양", "태평양", "인도양", "북극해"],
    answerIndex: 1,
    explanation: "태평양은 지구 표면의 약 3분의 1을 차지하는 가장 큰 대양입니다." },
  { id: "g03", category: "geography", // E
    question: "면적 기준으로 대한민국에서 가장 큰 섬은?",
    choices: ["거제도", "강화도", "제주도", "울릉도"],
    answerIndex: 2,
    explanation: "제주도는 면적 약 1,850㎢로 우리나라에서 가장 큰 섬입니다." },
  { id: "g04", category: "geography", // M
    question: "오스트레일리아(호주)의 수도는?",
    choices: ["시드니", "멜버른", "퍼스", "캔버라"],
    answerIndex: 3,
    explanation: "시드니와 멜버른이 경쟁하다 중간 지점에 새로 만든 도시가 캔버라입니다." },
  { id: "g05", category: "geography", // M
    question: "캐나다의 수도는?",
    choices: ["오타와", "토론토", "밴쿠버", "몬트리올"],
    answerIndex: 0,
    explanation: "캐나다의 수도는 오타와이며, 토론토는 가장 큰 도시입니다." },
  { id: "g06", category: "geography", // M
    question: "길이 기준으로 아프리카 대륙에서 가장 긴 강은?",
    choices: ["콩고강", "니제르강", "나일강", "잠베지강"],
    answerIndex: 2,
    explanation: "나일강은 약 6,650km로 아프리카에서 가장 긴 강입니다." },
  { id: "g07", category: "geography", // M
    question: "2026년 기준 독도의 행정구역(도·군)은?",
    choices: ["강원특별자치도 울릉군", "경상북도 울릉군", "경상남도 울릉군", "경상북도 울진군"],
    answerIndex: 1,
    explanation: "독도는 경상북도 울릉군 울릉읍 독도리에 속합니다." },
  { id: "g08", category: "geography", // M
    question: "7대륙 구분에서 다음 중 면적이 가장 작은 대륙은?",
    choices: ["남극", "유럽", "아시아", "오세아니아"],
    answerIndex: 3,
    explanation: "오세아니아는 약 850만㎢로 7대륙 중 면적이 가장 작습니다." },
  { id: "g09", category: "geography", // H
    question: "튀르키예(터키)의 수도는?",
    choices: ["앙카라", "이스탄불", "이즈미르", "안탈리아"],
    answerIndex: 0,
    explanation: "가장 큰 도시는 이스탄불이지만 수도는 앙카라입니다." },
  { id: "g10", category: "geography", // H
    question: "수심 기준으로 지구에서 가장 깊은 것으로 알려진 해구는?",
    choices: ["푸에르토리코 해구", "자바 해구", "마리아나 해구", "통가 해구"],
    answerIndex: 2,
    explanation: "서태평양의 마리아나 해구에 있는 챌린저 해연이 약 1만 1천 m로 가장 깊습니다." },

  // ===== 일반상식 =====
  { id: "n01", category: "general", // E
    question: "한글날은 매년 며칠일까?",
    choices: ["10월 9일", "10월 3일", "5월 5일", "8월 15일"],
    answerIndex: 0,
    explanation: "훈민정음 반포를 기념하는 한글날은 10월 9일입니다." },
  { id: "n02", category: "general", // E
    question: "우리나라에서 무지개는 보통 몇 가지 색으로 구분할까?",
    choices: ["6가지", "7가지", "8가지", "9가지"],
    answerIndex: 1,
    explanation: "빨강·주황·노랑·초록·파랑·남색·보라의 7가지 색으로 구분합니다." },
  { id: "n03", category: "general", // E
    question: "올림픽 오륜기에 그려진 원의 개수는?",
    choices: ["3개", "4개", "6개", "5개"],
    answerIndex: 3,
    explanation: "오륜기의 5개 원은 다섯 대륙의 화합을 상징합니다." },
  { id: "n04", category: "general", // M
    question: "「모나리자」를 그린 화가는?",
    choices: ["미켈란젤로", "라파엘로", "레오나르도 다 빈치", "보티첼리"],
    answerIndex: 2,
    explanation: "「모나리자」는 레오나르도 다 빈치가 16세기 초에 그린 초상화입니다." },
  { id: "n05", category: "general", // M
    question: "『햄릿』을 쓴 작가는?",
    choices: ["찰스 디킨스", "윌리엄 셰익스피어", "괴테", "빅토르 위고"],
    answerIndex: 1,
    explanation: "『햄릿』은 셰익스피어의 4대 비극 중 하나입니다." },
  { id: "n06", category: "general", // M
    question: "사자성어 '일석이조(一石二鳥)'의 뜻은?",
    choices: ["두 번 실패함", "둘이 서로 다툼", "두 번 생각함", "한 번에 두 가지 이득을 얻음"],
    answerIndex: 3,
    explanation: "돌 하나로 새 두 마리를 잡는다는 뜻으로, 한 가지 일로 두 가지 이득을 얻는 것을 말합니다." },
  { id: "n07", category: "general", // M
    question: "한글의 기본 자음(쌍자음 제외)은 모두 몇 개일까?",
    choices: ["14개", "19개", "21개", "24개"],
    answerIndex: 0,
    explanation: "기본 자음은 ㄱ부터 ㅎ까지 14개이고, 기본 모음은 10개입니다." },
  { id: "n08", category: "general", // M
    question: "로마 숫자 'XIV'가 나타내는 수는?",
    choices: ["6", "16", "14", "24"],
    answerIndex: 2,
    explanation: "X는 10, IV는 4이므로 XIV는 14입니다." },
  { id: "n09", category: "general", // H
    question: "소설 『돈키호테』를 쓴 작가는?",
    choices: ["발자크", "괴테", "단테", "세르반테스"],
    answerIndex: 3,
    explanation: "에스파냐의 미겔 데 세르반테스가 17세기 초에 『돈키호테』를 발표했습니다." },
  { id: "n10", category: "general", // H
    question: "음악 빠르기말 '알레그로(Allegro)'의 뜻은?",
    choices: ["느리게", "빠르게", "점점 세게", "부드럽게"],
    answerIndex: 1,
    explanation: "알레그로는 '빠르게'를 뜻하는 이탈리아어 빠르기말입니다." }
];
