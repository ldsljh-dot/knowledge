#!/usr/bin/env python3
"""
Personal DB - Memos Manager
메모(memos)를 SQLite DB에 저장·조회·수정·삭제합니다.
LLM이 직접 읽는 대신 이 스크립트를 통해 정확한 결과를 얻습니다.

DB 위치: $OBSIDIAN_VAULT_PATH/Agent/personal.db

Usage:
    # 메모 추가
    python manage_memos.py add \
      --title "회의록 2026-03-28" --content "결정사항: ..." \
      --tags '["work","meeting"]' --source "user"

    # 메모 검색
    python manage_memos.py search --keyword "회의록"
    python manage_memos.py search --tag "work" --format json

    # 메모 수정
    python manage_memos.py update --id "abc-123" --content "새 내용"

    # 메모 삭제
    python manage_memos.py delete --id "abc-123"
"""

import os
import sys
import json
import uuid
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# .env 지원 (프로젝트 루트까지 탐색)
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    _p = _here.parent
    for _ in range(6):
        if (_p / ".env").exists():
            load_dotenv(_p / ".env")
            break
        _p = _p.parent
except ImportError:
    pass


# ────────────────────────── DB 초기화 ──────────────────────────

def _get_db_path(db_path_arg: str = None) -> Path:
    if db_path_arg:
        return Path(db_path_arg)
    vault = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault:
        return Path(vault) / "Agent" / "personal.db"
    raise EnvironmentError(
        "DB 경로를 찾을 수 없습니다. --db-path 또는 OBSIDIAN_VAULT_PATH 환경변수를 설정하세요."
    )


def _ensure_db(db_path: Path) -> sqlite3.Connection:
    """DB와 테이블이 없으면 자동 생성. events + memos 모두 생성."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            start_dt TEXT NOT NULL,
            end_dt TEXT,
            location TEXT,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'user',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_start_dt ON events(start_dt);

        CREATE TABLE IF NOT EXISTS memos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'user',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memos_updated ON memos(updated_at);
    """)
    conn.commit()
    return conn


# ────────────────────────── 포맷 헬퍼 ──────────────────────────

def _format_dt(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return dt_str


def _print_memos(rows, fmt: str = "text"):
    if fmt == "json":
        data = [dict(r) for r in rows]
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    count = len(rows)
    print(f"\n=== 메모 ({count}건) ===\n")
    if count == 0:
        print("  조건에 맞는 메모가 없습니다.")
        return
    for i, row in enumerate(rows, 1):
        tags = json.loads(row["tags"] or "[]")
        tags_str = ", ".join(tags) if tags else "-"
        # 내용 미리보기 (최대 100자)
        content_preview = row["content"][:100].replace("\n", " ")
        if len(row["content"]) > 100:
            content_preview += "..."
        print(f"[{i}] {row['title']}")
        print(f"    내용: {content_preview}")
        print(f"    태그: {tags_str}")
        print(f"    출처: {row['source'] or 'user'}")
        print(f"    수정: {_format_dt(row['updated_at'])}")
        print(f"    ID: {row['id']}")
        print()


# ────────────────────────── CRUD 함수 ──────────────────────────

def cmd_add(args):
    db = _ensure_db(_get_db_path(args.db_path))
    now = datetime.utcnow().isoformat()
    memo_id = str(uuid.uuid4())

    tags = args.tags or "[]"
    try:
        json.loads(tags)
    except json.JSONDecodeError:
        print(f"[ERROR] --tags 값이 올바른 JSON 배열이 아닙니다: {tags}", file=sys.stderr)
        sys.exit(1)

    db.execute(
        """INSERT INTO memos (id, title, content, tags, source, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (memo_id, args.title, args.content, tags, args.source, now, now)
    )
    db.commit()
    db.close()
    print(f"✅ 메모 추가 완료")
    print(f"   제목: {args.title}")
    print(f"   ID: {memo_id}")


def cmd_update(args):
    db = _ensure_db(_get_db_path(args.db_path))
    row = db.execute("SELECT * FROM memos WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] ID '{args.id}'에 해당하는 메모를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    fields = {}
    if args.title is not None:
        fields["title"] = args.title
    if args.content is not None:
        fields["content"] = args.content
    if args.tags is not None:
        try:
            json.loads(args.tags)
        except json.JSONDecodeError:
            print(f"[ERROR] --tags 값이 올바른 JSON 배열이 아닙니다.", file=sys.stderr)
            sys.exit(1)
        fields["tags"] = args.tags

    if not fields:
        print("변경할 항목이 없습니다.")
        return

    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [args.id]
    db.execute(f"UPDATE memos SET {set_clause} WHERE id = ?", values)
    db.commit()
    db.close()
    print(f"✅ 메모 수정 완료 (ID: {args.id})")


def cmd_delete(args):
    db = _ensure_db(_get_db_path(args.db_path))
    row = db.execute("SELECT title FROM memos WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] ID '{args.id}'에 해당하는 메모를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    db.execute("DELETE FROM memos WHERE id = ?", (args.id,))
    db.commit()
    db.close()
    print(f"✅ 메모 삭제 완료: {row['title']} (ID: {args.id})")


def cmd_search(args):
    db = _ensure_db(_get_db_path(args.db_path))
    sql = "SELECT * FROM memos WHERE 1=1"
    params = []

    if args.keyword:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{args.keyword}%", f"%{args.keyword}%"])
    if args.tag:
        sql += " AND tags LIKE ?"
        params.append(f'%"{args.tag}"%')

    sql += " ORDER BY updated_at DESC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    rows = db.execute(sql, params).fetchall()
    db.close()
    _print_memos(rows, args.format)


def cmd_batch_add(args):
    """--input-json 파일에서 메모 배열을 읽어 일괄 추가."""
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)
    with open(input_path, encoding="utf-8") as f:
        memos = json.load(f)
    if not isinstance(memos, list):
        print("[ERROR] JSON 파일은 배열 형식이어야 합니다.", file=sys.stderr)
        sys.exit(1)

    db = _ensure_db(_get_db_path(args.db_path))
    now = datetime.utcnow().isoformat()
    count = 0
    for m in memos:
        memo_id = m.get("id") or str(uuid.uuid4())
        db.execute(
            """INSERT OR REPLACE INTO memos
               (id, title, content, tags, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                memo_id,
                m.get("title", "제목 없음"),
                m.get("content", ""),
                json.dumps(m.get("tags", []), ensure_ascii=False),
                m.get("source", "import"),
                m.get("created_at", now),
                now,
            )
        )
        count += 1
    db.commit()
    db.close()
    print(f"✅ {count}건 일괄 추가 완료")


# ────────────────────────── CLI ──────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Personal DB - 메모(Memos) 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db-path", help="SQLite DB 파일 경로 (기본: $OBSIDIAN_VAULT_PATH/Agent/personal.db)")

    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="메모 추가")
    p_add.add_argument("--title", required=True, help="메모 제목")
    p_add.add_argument("--content", required=True, help="메모 내용")
    p_add.add_argument("--tags", default='[]', help='태그 JSON 배열 (e.g. \'["work","todo"]\')')
    p_add.add_argument("--source", default="user", help="출처 (user/zeroclaw/openclaw)")
    p_add.add_argument("--input-json", help="JSON 파일로 배치 추가")

    # update
    p_upd = sub.add_parser("update", help="메모 수정")
    p_upd.add_argument("--id", required=True, help="수정할 메모 ID")
    p_upd.add_argument("--title")
    p_upd.add_argument("--content")
    p_upd.add_argument("--tags")

    # delete
    p_del = sub.add_parser("delete", help="메모 삭제")
    p_del.add_argument("--id", required=True, help="삭제할 메모 ID")

    # search
    p_s = sub.add_parser("search", help="메모 검색")
    p_s.add_argument("--keyword", help="제목/내용 키워드 검색")
    p_s.add_argument("--tag", help="태그 필터")
    p_s.add_argument("--limit", type=int, default=20, help="최대 결과 수 (기본: 20)")
    p_s.add_argument("--format", choices=["text", "json"], default="text", help="출력 형식")

    args = parser.parse_args()

    try:
        if args.command == "add":
            if hasattr(args, "input_json") and args.input_json:
                cmd_batch_add(args)
            else:
                cmd_add(args)
        elif args.command == "update":
            cmd_update(args)
        elif args.command == "delete":
            cmd_delete(args)
        elif args.command == "search":
            cmd_search(args)
    except EnvironmentError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 예기치 않은 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
