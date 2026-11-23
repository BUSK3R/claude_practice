"""PRD 3단계: 프로필과 저장 레시피 API. 인증 없음 -> 로컬(127.0.0.1) 전용."""
import json
import re
import sqlite3
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from app.db import connect
from app.recipes import Ingredient

router = APIRouter(prefix="/api")

# 항목별 길이 제한: recipes.py 파서가 만드는 최대 길이와 같다(exclude는 저장 시 40자로 자르므로 입력만 느슨하게).
Short = Annotated[str, StringConstraints(max_length=40)]
Step = Annotated[str, StringConstraints(max_length=400)]
RawShort = Annotated[str, StringConstraints(max_length=200)]


class Prefs(BaseModel):
    exclude: list[RawShort] = Field(default_factory=list, max_length=20)
    servings: int = Field(default=2, ge=1, le=10)


class ProfileIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    prefs: Prefs = Field(default_factory=Prefs)


class RecipeIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(default="", max_length=200)
    servings: int = Field(ge=1, le=20)
    time_minutes: int = Field(ge=0, le=1000)
    difficulty: Literal["easy", "medium", "hard"]
    uses: list[Short] = Field(max_length=30)
    missing: list[Short] = Field(max_length=30)
    steps: list[Step] = Field(min_length=1, max_length=20)


class SaveRequest(BaseModel):
    recipe: RecipeIn
    ingredients: list[Ingredient] = Field(min_length=1, max_length=30)


def _profile(row) -> dict:
    prefs = json.loads(row["prefs_json"])
    return {"nickname": row["nickname"], "prefs": prefs}


@router.get("/profile")
def get_profile():
    with connect() as db:
        row = db.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return _profile(row) if row else {"nickname": None, "prefs": Prefs().model_dump()}


@router.put("/profile")
def put_profile(p: ProfileIn):
    nickname = p.nickname.strip()
    if not nickname:
        raise HTTPException(422, "닉네임을 입력하세요.")
    prefs = Prefs(exclude=[e.strip()[:40] for e in p.prefs.exclude if e.strip()], servings=p.prefs.servings)
    with connect() as db:
        db.execute(
            "INSERT INTO profile (id, nickname, prefs_json) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET nickname = excluded.nickname, prefs_json = excluded.prefs_json",
            (nickname, prefs.model_dump_json()),
        )
    return {"nickname": nickname, "prefs": prefs.model_dump()}


def _dedupe_key(title: str, ingredients: list[Ingredient]) -> str:
    norm = lambda s: re.sub(r"\s+", "", s).lower()
    return norm(title) + "|" + ",".join(sorted(norm(i.name) for i in ingredients))


def _row_out(r) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "created_at": r["created_at"],
        "recipe": json.loads(r["data_json"]),
        "ingredients": json.loads(r["ingredients_json"]),
    }


@router.post("/saved", status_code=201)
def save_recipe(req: SaveRequest):
    with connect() as db:
        if not db.execute("SELECT 1 FROM profile WHERE id = 1").fetchone():
            raise HTTPException(409, "먼저 프로필을 만들어야 저장할 수 있습니다.")
        key = _dedupe_key(req.recipe.title, req.ingredients)
        try:
            cur = db.execute(
                "INSERT INTO recipes (title, data_json, ingredients_json, dedupe_key) VALUES (?, ?, ?, ?)",
                (
                    req.recipe.title,
                    req.recipe.model_dump_json(),
                    json.dumps([i.model_dump() for i in req.ingredients], ensure_ascii=False),
                    key,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "이미 저장된 레시피입니다(같은 제목, 같은 재료 구성).")
        row = db.execute("SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_out(row)


@router.get("/saved")
def list_saved(q: Optional[str] = None):
    with connect() as db:
        rows = db.execute("SELECT * FROM recipes ORDER BY created_at DESC, id DESC").fetchall()
    out = [_row_out(r) for r in rows]
    if q and q.strip():
        needle = q.strip().lower()
        out = [
            r for r in out
            if needle in r["title"].lower() or any(needle in i["name"].lower() for i in r["ingredients"])
        ]
    return {"recipes": out}


@router.delete("/saved/{recipe_id}", status_code=204)
def delete_saved(recipe_id: int):
    with connect() as db:
        cur = db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "저장된 레시피를 찾을 수 없습니다.")
