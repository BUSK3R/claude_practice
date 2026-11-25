"""요청 모델, 모델 응답 검증, 위기 키워드 안전망."""
import re
import unicodedata

from pydantic import BaseModel

from app.prompts import EMOTIONS

MAX_TEXT = 2000
LIMITS = {"summary": 200, "empathy": 700, "comfort": 600}

# 위기 표현 판정. 원칙: 미탐보다 오탐이 낫다. 단, 일상 문장에 위기 박스가 자주 뜨면 신뢰를 잃는다.
# 판정은 세 갈래다.
#  (1) 긴 키워드: 공백·구두점을 모두 지운 텍스트에서 부분 일치 ("죽 고 싶 어"처럼 벌려 써도 잡힌다)
#  (2) 짧은(2음절) 키워드: 공백을 지우면 "그러자 해가"에서 '자해'가 만들어지므로 공백을 살려 판정
#  (3) 영어: 단어 경계(\b)가 있는 정규식
# '끝내고싶'처럼 일상 어구와 겹치는 짧은 표현은 넣지 않는다(오늘 일을 끝내고 싶다 등).

# (1) 긴 키워드 (공백 제거 후 일치)
CRISIS_KEYWORDS = [
    # 죽음 (직접). 구어체 변이(십다/시퍼/구)와 맞춤법 변이(낫/나) 포함
    "죽고싶", "죽고싶", "죽고십", "죽고시퍼", "죽고시프", "죽구싶", "죽구십", "죽구시퍼", "죽고파", "죽고만싶",
    "죽어버리고싶", "죽어버릴", "죽어버리자", "죽을까", "죽을래", "죽어야지", "죽는게나", "죽는게낫",
    "뒤지고싶", "뒤지고시퍼",
    "극단적선택", "뛰어내리고싶",
    # 삶을 끝냄
    "목숨을끊", "목숨끊", "스스로목숨", "생을마감", "삶을마감", "삶을끝내", "삶끝내", "인생을끝내", "인생끝내", "생을끝내",
    "모든걸끝내", "모든것을끝내", "다끝내버리고싶",
    # 사라짐·없어짐
    "사라지고싶", "사라져버리고싶", "없어지고싶", "없어져버리고싶", "나없어졌으면", "내가없어졌으면",
    "세상에서없어", "세상에서사라", "내가없는게나", "내가없는게더",
    # 살기 싫음·살 의미 없음
    "살기싫", "살고싶지않", "살아갈자신이없", "살아가고싶지않", "살이유가없", "살아야할이유가없",
    "더이상못살", "더는못살", "사는게의미가없", "사는게의미없", "살아서뭐하", "살아서뭐해", "그만살고싶",
    # 깨어나지 않음
    "눈을뜨지않았으면", "눈뜨지않았으면", "깨어나고싶지않", "깨어나지않았으면", "깨지않았으면",
    # 방법 암시 (유서·손목·약·번개탄)
    "수면제를한꺼번에", "수면제한꺼번에", "약을한꺼번에먹",
    "유서를쓰", "유서를썼", "유서를남", "유서썼", "유서써", "유서쓰",
    "손목을긋", "손목긋", "손목을그었", "손목그었",
    "번개탄",  # 고깃집·캠핑 맥락이면 아래 _BURNER_CONTEXT로 제외
    # --- 3차 QA 보강(F1): '~었으면/~싶다' 같은 소망형·종결형이 붙은 경우만 넣는다(단독 "죽자"·"투신"·"사라졌으면"은 일상과 겹침) ---
    "죽었으면좋겠", "죽었으면싶", "죽어버렸으면", "차라리죽었으면",
    "없어져버렸으면", "세상에없었으면", "세상에없으면", "내가세상에없",
    "살기가싫", "살기도싫", "사는게싫", "사는건싫", "사는게너무싫",
    "삶을포기", "삶포기", "살기를포기", "인생을포기하고싶",
    "투신하고싶", "투신하고파", "투신할까", "투신해버리고싶", "뛰어내릴까", "뛰어내려버리고싶",
    "목을매고싶", "목매고싶", "목을매달고싶", "목매달고싶", "목을매달아죽",
]

# (2) 짧은 키워드: 이어 붙여 쓴 경우는 그대로 일치, 벌려 쓴 경우("자 살", "자.살")는 아래 규칙으로 판정
SHORT_KEYWORDS = ["자살", "자해", "자결"]
# 벌려 쓴 짧은 키워드의 오탐 방지:
#  - 첫 글자 앞이 한글/영숫자가 아니어야 한다 ("그러자 해가", "이자 살펴", "여자 결승"의 '자'는 앞말에 붙어 있어 제외)
#  - 마지막 글자 뒤가 한글이 아니거나, 흔한 서술어·조사여야 한다 ("자 해보자", "자 살펴보자"는 제외)
_SPACED_END = r"(?:(?![가-힣])|(?=(?:했|하|한|할|를|을|은|는|의|에|로|도|시도|생각)))"
_SPACED_SHORT = [
    re.compile(r"(?<![가-힣a-z0-9])" + k[0] + r"[\W_]{1,3}" + k[1] + _SPACED_END) for k in SHORT_KEYWORDS
]

# (2b) 문맥 정규식(어절 경계·앞뒤 어구 필요). 공백·구두점을 지우지 않은 텍스트에서 판정한다.
#  글자 사이 [\W_]*는 벌려 쓴 표기("그냥 죽 자")를 허용한다. 중첩 수량자가 없어 입력 길이에 선형이다.
_G = r"[\W_]*"
_B = r"(?<![가-힣a-z0-9])"  # 앞이 한글·영숫자가 아님(어절 시작)


def _w(s: str) -> str:
    return _G.join(s)


_DISTRESS = "힘들|괴롭|괴로|우울|외롭|지쳐|지치|버티|아프|무서|두려|막막|서러|불안"
_CONTEXT_KO = [re.compile(p) for p in (
    # "그냥 죽자"(O) / "죽자 살자 공부했다"·"죽자 사자"·"죽자고 덤볐다"(X)
    _B + r"(?:" + _w("그냥") + "|" + _w("차라리") + "|" + _w("이대로") + "|" + _w("같이") + "|" + _w("함께") + r")"
    + _G + _w("죽자") + r"(?![\W_]*(?:살자|사자))(?![가-힣])",
    # "내가/나 사라졌으면·없어졌으면": '아내가', '하나 사라졌으면'처럼 앞말에 붙은 '내가/나'는 제외
    _B + r"(?:내가|나)" + _G + r"(?:그냥" + _G + r")?" + r"(?:" + _w("사라졌으면") + "|" + _w("없어졌으면") + "|"
    + _w("사라져버렸으면") + r")",
    _B + _w("내가") + _G + r"(?:그냥" + _G + r")?" + r"(?:" + _w("사라지면") + "|" + _w("없어지면") + "|" + _w("죽었으면") + r")",
    # "죽을 것 같다 (정말) 힘들어": 바로 뒤에 힘듦 표현이 이어질 때만. "웃겨 죽을 것 같다"는 일상 과장이라 제외
    _w("죽을") + _G + _w("것") + _G + "같" + r"[가-힣]{0,3}" + r"(?:[\W_]{0,3}(?:정말|진짜|너무|많이|엄청|요즘|계속|아주|넘)){0,2}"
    + r"[\W_]{0,3}(?:" + _DISTRESS + ")",
)]

# 일상에서 흔한 어구는 판정 전에 지운다 ("인생 끝내주는 맛집", "유서 깊은 건물")
_SAFE_PHRASES = ["끝내주", "유서깊", "유서가깊"]
# '번개탄'은 고깃집·캠핑 단어와 함께 나오면 일상으로 본다
_BURNER_CONTEXT = ["불판", "고기", "고깃집", "삼겹", "숯불", "구이", "캠핑", "바베큐", "바비큐", "갈비", "식당", "화로", "불멍"]

# (3) 영어 (소문자·아포스트로피 제거 후, 단어 경계 기준)
_SEP = r"[\W_]+"
_ENGLISH = [re.compile(p) for p in (
    r"\bwan(?:t" + _SEP + r"to|na)" + _SEP + r"die\b(?!" + _SEP + r"laugh)",   # "wanna die laughing"은 일상
    r"\bkill(?:ing)?[\W_]*my[\W_]*self\b",
    r"\bhang(?:ing)?[\W_]*my[\W_]*self\b",
    r"\bsuicid(?!e" + _SEP + r"squad)",                                          # "Suicide Squad"는 영화
    r"\bend(?:ing)?" + _SEP + r"my" + _SEP + r"life\b",
    r"\btak(?:e|ing)" + _SEP + r"my" + _SEP + r"own" + _SEP + r"life\b",
    r"\bwish" + _SEP + r"i" + _SEP + r"(?:was|were)" + _SEP + r"(?:dead|never" + _SEP + r"born)\b",
    r"\b(?:dont|do" + _SEP + r"not)" + _SEP + r"want" + _SEP + r"to" + _SEP + r"(?:live(?!" + _SEP + r"(?:in|with|near|at|on|far|alone)\b)|be" + _SEP + r"alive|exist)\b",  # "live in a small apartment"는 일상
    r"\bbetter" + _SEP + r"off" + _SEP + r"dead\b",
    r"\bwan(?:t" + _SEP + r"to|na)" + _SEP + r"(?:just" + _SEP + r")?(?:disappear|vanish|be" + _SEP + r"dead)\b",
    r"\bwish" + _SEP + r"i" + _SEP + r"could" + _SEP + r"(?:just" + _SEP + r")?(?:disappear|vanish)\b",
    r"\bself" + _SEP.replace("+", "*") + r"harm",
    r"\bharm(?:ing)?" + _SEP + r"my" + _SEP.replace("+", "*") + r"self\b",
    # "cut myself" 은 위기 쪽으로 본다. 단, 흔한 일상 어구(요리 중 베임, "cut myself off/some slack")는 제외
    r"\bcut(?:ting)?" + _SEP + r"my" + _SEP.replace("+", "*") + r"self\b(?!" + _SEP
    + r"(?:while|when|shaving|cooking|chopping|slicing|peeling|opening|off|some|on" + _SEP + r"(?:a|the|my|some)\b))",
    r"(?<!\d)(?<!\d\s)\bkms\b",                                               # "10 kms"(킬로미터)는 일상
)]
CRISIS_NOTICE = (
    "지금 많이 힘들다면 혼자 견디지 않아도 돼요. 자살예방 상담전화 109(24시간, 무료)에서 언제든 이야기를 들어줄 거예요. "
    "당장 위험하다고 느껴지면 112나 119에 바로 연락해 주세요."
)


class DiaryIn(BaseModel):
    text: str


# 호환 자모 -> 음절 조합 (ㅈㅏㅅㅏㄹ -> 자살). NFKC/NFC는 종성을 합성하지 못해 직접 한다.
_JAMO_SYLLABLE = re.compile(
    r"([ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ])([ㅏ-ㅣ])"
    r"([ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ](?![ㅏ-ㅣ]))?"
)
_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JONG = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")
_INVISIBLE = re.compile(r"[\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


def _compose_jamo(m: "re.Match") -> str:
    code = 0xAC00 + (_CHO.index(m.group(1)) * 21 + (ord(m.group(2)) - 0x314F)) * 28
    return chr(code + (_JONG.index(m.group(3)) if m.group(3) else 0))


def _prepare(text: str) -> str:
    """보이지 않는 문자 제거 -> 띄어쓴 자모 붙이기 -> 자모 합성 -> 울음 표기 제거 -> NFKC -> NFC -> 소문자.
    공백·구두점은 남긴다(짧은 키워드의 어절 경계 판정에 필요)."""
    t = _INVISIBLE.sub("", text)
    t = re.sub(r"(?<=[ㄱ-ㅣ])[ \t.]+(?=[ㄱ-ㅣ])", "", t)
    t = _JAMO_SYLLABLE.sub(_compose_jamo, t)
    t = re.sub(r"[ㅠㅜ]+", "", t)
    t = unicodedata.normalize("NFC", unicodedata.normalize("NFKC", t))
    return t.lower()


def _normalize(text: str) -> str:
    """_prepare 결과에서 글자·숫자 외 전부 제거."""
    return re.sub(r"[\W_]+", "", _prepare(text))


def has_crisis_keyword(text: str) -> bool:
    t = _prepare(text)
    sq = re.sub(r"[\W_]+", "", t)
    for p in _SAFE_PHRASES:
        sq = sq.replace(p, "")
    if "번개탄" in sq and any(w in sq for w in _BURNER_CONTEXT):
        sq = sq.replace("번개탄", "")
    if any(k in sq for k in CRISIS_KEYWORDS):
        return True
    if any(k in t for k in SHORT_KEYWORDS) or any(r.search(t) for r in _SPACED_SHORT):
        return True
    if any(r.search(t) for r in _CONTEXT_KO):
        return True
    en = re.sub(r"['’`´]", "", t)
    return any(r.search(en) for r in _ENGLISH)


_HANGUL = re.compile(r"[가-힣]")
_SENT_END = ".!?。…"


def _fit(v: str, limit: int) -> str:
    """길이 초과는 오류로 보지 않고 문장 경계 근처에서 자른다(재호출 비용 절약)."""
    if len(v) <= limit:
        return v
    cut = v[:limit]
    idx = max(cut.rfind(c) for c in _SENT_END)
    if idx >= limit // 2:
        return cut[: idx + 1].strip()
    return cut[: limit - 1].rstrip() + "…"


def _text(d: dict, key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise ValueError(f"{key} 문자열 아님")
    v = v.strip()
    if not v:
        raise ValueError(f"{key} 비어 있음")
    return v


_QUOTED = re.compile(
    "\"[^\"]*\"|“[^”]*”|‘[^’]*’|「[^」]*」|『[^』]*』"
    "|(?<![A-Za-z])'[^']*'(?![A-Za-z])"
)
_KO = re.compile(r"[가-힣ㄱ-ㅣ]")
_MIN_KO = 10      # 한글이 이보다 적으면 한국어 응답이 아니라고 본다
_ENOUGH_KO = 40   # 이만큼 있으면 영어 단어가 섞여도 통과
_MIN_KO_RATIO = 0.15


def _check_korean(*parts: str) -> None:
    """summary+empathy+comfort 합산 판정. 인용부호 안의 외국어와 영문·숫자 단어는 세지 않는다.
    한글(호환 자모 포함)이 충분하면 통과, 전부 영어 같은 응답만 거절(재시도)."""
    joined = " ".join(parts)
    ko = len(_KO.findall(joined))
    outside = _QUOTED.sub(" ", joined)
    ascii_n = sum(1 for c in outside if c.isascii() and c.isalpha())
    foreign = sum(1 for c in outside if not c.isascii() and c.isalpha() and not _KO.match(c))
    if ko < _MIN_KO or foreign > ko:
        raise ValueError("한국어 아님")
    if ko < _ENOUGH_KO and ko / (ko + ascii_n) < _MIN_KO_RATIO:
        raise ValueError("한국어 아님")


def _emotion_name(name: str) -> str:
    """한글·공백만 남긴다. 한글 음절이 없으면(영어, 이모지만 등) '기타'로 정규화한다."""
    cleaned = re.sub(r"[^가-힣ㄱ-ㅎㅏ-ㅣ\s]", "", name).strip()
    if not _HANGUL.search(cleaned):
        return "기타"
    if len(cleaned) > 12:
        raise ValueError("감정 이름 오류")
    return cleaned


def validate_analysis(d: dict) -> dict:
    """모델 JSON을 검증·정규화한다. 문제가 있으면 ValueError/KeyError(= 재시도 대상)."""
    model_primary = d["primary_emotion"]
    if not isinstance(model_primary, str):
        raise ValueError("primary_emotion 형식 오류")
    model_primary = model_primary.strip()
    raw = d["emotions"]
    if not isinstance(raw, list) or not raw:
        raise ValueError("emotions 개수 오류")
    emotions = []
    for e in raw:
        name, inten = e["name"], e["intensity"]
        if isinstance(inten, float) and inten.is_integer():
            inten = int(inten)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("감정 이름 오류")
        if isinstance(inten, bool) or not isinstance(inten, int) or not 1 <= inten <= 5:
            raise ValueError("intensity 범위 오류")
        emotions.append({"name": _emotion_name(name), "intensity": inten})
    # 세기 순 정렬. 동점이면 모델이 고른 primary가 앞에 오게 한다(그 외엔 입력 순서 유지).
    emotions.sort(key=lambda x: (-x["intensity"], x["name"] != model_primary))
    # primary는 항상 emotions[0]과 일치시킨다. 허용 목록 밖이면 '기타'.
    primary = emotions[0]["name"]
    if primary not in EMOTIONS:
        primary = "기타"
    crisis = d.get("crisis", False)
    if not isinstance(crisis, bool):
        raise ValueError("crisis 형식 오류")
    texts = {k: _text(d, k) for k in ("summary", "empathy", "comfort")}
    _check_korean(*texts.values())
    return {
        "primary_emotion": primary,
        "emotions": emotions[:4],
        **{k: _fit(v, LIMITS[k]) for k, v in texts.items()},
        "crisis": crisis,
    }


def apply_crisis_safety(result: dict, diary: str) -> dict:
    """키워드가 있거나 모델이 crisis=true면, comfort에 109 안내가 반드시 들어가게 한다."""
    if has_crisis_keyword(diary) or result["crisis"]:
        result["crisis"] = True
        if "109" not in result["comfort"]:
            result["comfort"] = f"{result['comfort']} {CRISIS_NOTICE}".strip()
    return result


# ---------------------------------------------------------------------------
# PDF 요약 응답 검증 (일기 검증과 별개)
# ---------------------------------------------------------------------------
PDF_LIMITS = {"one_line": 100, "key_point": 150, "keyword": 20}
PDF_KEY_POINTS = (3, 7)
PDF_KEYWORDS = (3, 8)
_MD_LEAD = re.compile(r"^\s*(?:[-*•·]+|\d+[.)])\s+")


def _str_list(d: dict, key: str, limit: int, lo: int, hi: int) -> list:
    raw = d[key]
    if not isinstance(raw, list):
        raise ValueError(f"{key} 목록 아님")
    out = []
    for v in raw:
        if not isinstance(v, str):
            raise ValueError(f"{key} 항목이 문자열 아님")
        v = _MD_LEAD.sub("", v.strip()).strip()
        if v and v not in out:  # 빈 항목·중복 제거
            out.append(v)
    if len(out) < lo:
        raise ValueError(f"{key} 개수 부족")
    return [_fit(v, limit) for v in out[:hi]]  # 초과 개수는 앞에서부터 상한까지만


def validate_pdf_summary(d: dict) -> dict:
    """PDF 요약 JSON 검증·정규화. 문제가 있으면 ValueError/KeyError(= 재요청 대상). 길이 초과는 잘라낸다."""
    one_line = _fit(_text(d, "one_line"), PDF_LIMITS["one_line"])
    points = _str_list(d, "key_points", PDF_LIMITS["key_point"], *PDF_KEY_POINTS)
    keywords = _str_list(d, "keywords", PDF_LIMITS["keyword"], *PDF_KEYWORDS)
    _check_korean(one_line, *points)  # 키워드는 영어 전문용어가 많아 제외
    for v in (one_line, *points):  # 실측: 띄어쓰기 없이 붙여 쓴 응답이 나온 적 있음 -> 재요청 대상
        if len(v) >= 20 and v.count(" ") / len(v) < 0.05:
            raise ValueError("띄어쓰기 없음")
    return {"one_line": one_line, "key_points": points, "keywords": keywords}
