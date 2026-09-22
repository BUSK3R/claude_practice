"""Defines the set of Hangul syllables the model will learn to recognize."""

import re

# 일상에서 자주 쓰이는 한글 단어 모음 (여기서 음절을 추출해 클래스 집합을 만든다)
_SAMPLE_WORDS = """
안녕하세요 감사합니다 사랑해요 죄송합니다 반갑습니다
학교 친구 가족 선생님 학생 회사 직장 병원 약국 은행 시장 식당 카페 도서관 공원
지하철 버스 택시 비행기 자동차
아버지 어머니 형제 자매 동생 오빠 언니 누나 삼촌 이모 할머니 할아버지
사과 바나나 딸기 포도 수박 김치 라면 국밥 비빔밥 불고기 떡볶이 삼겹살 냉면
하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열
월요일 화요일 수요일 목요일 금요일 토요일 일요일
봄 여름 가을 겨울 날씨 오늘 내일 어제 지금 시간 아침 점심 저녁 밤
사랑 행복 슬픔 기쁨 걱정 희망 꿈 마음 생각 기분
컴퓨터 전화 인터넷 음악 영화 사진 그림 책 공부 운동 여행 요리
"""

_HANGUL_SYLLABLE_RE = re.compile(r"[가-힣]")


def build_charset():
    """샘플 단어에서 중복 없는 한글 음절 리스트를 순서대로 추출한다."""
    seen = dict.fromkeys(_HANGUL_SYLLABLE_RE.findall(_SAMPLE_WORDS))
    return sorted(seen.keys())


CHARSET = build_charset()
NUM_CLASSES = len(CHARSET)

if __name__ == "__main__":
    # 클래스 개수와 일부 샘플을 확인하기 위한 용도
    print(f"num classes: {NUM_CLASSES}")
    print("".join(CHARSET))
