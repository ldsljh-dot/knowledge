#!/usr/bin/env python3
"""
Personal DB - Tasks Manager
할일(tasks)을 SQLite DB에 저장·조회·수정·삭제합니다.
LLM이 직접 읽는 대신 이 스크립트를 통해 정확한 결과를 얻습니다.

DB 위치: $OBSIDIAN_VAULT_PATH/4-Archieve/db/personal.db

Usage:
    # 태스크 추가
    python manage_tasks.py add \
      --title "보고서 작성" --content "3분기 성과 정리" \
      --priority high --due "2026-04-01T18:00" \
      --tags '["work"]' --source "user"

    # 목록 조회 (기본: todo + in_progress)
    python manage_tasks.py list
    python manage_tasks.py list --status todo
    python manage_tasks.py list --priority high
    python manage_tasks.py list --due-before "2026-04-07"

    # 완료 처리 (shortcut)
    python manage_tasks.py done --id "abc-123"

    # 상태/내용 수정
    python manage_tasks.py update --id "abc-123" --status in_progress --priority low

    # 태스크 삭제
    python manage_tasks.py delete --id "abc-123"
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


VALID_STATUSES = ("todo", "in_progress", "done", "cancelled")
VALID_PRIORITIES = ("low", "medium", "high")


# ────────────────────────── DB 초기화 ──────────────────────────

def _get_db_path(db_path_arg: str = None) -> Path:
    if db_path_arg:
        return Path(db_path_arg)
    vault = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault:
        return Path(vault) / "4-Archieve" / "db" / "personal.db"
    raise EnvironmentError(
        "DB 경로를 찾을 수 없습니다. --db-path 또는 OBSIDIAN_VAULT_PATH 환경변수를 설정하세요."
    )


def _ensure_db(db_path: Path) -> sqlite3.Connection:
    """DB와 테이블이 없으면 자동 생성. events + memos + tasks 모두 생성."""
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

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_dt TEXT,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'user',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_due_dt ON tasks(due_dt);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
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


PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_ICON = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}


def _print_tasks(rows, fmt: str = "text"):
    if fmt == "json":
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        return

    count = len(rows)
    print(f"\n=== 태스크 ({count}건) ===\n")
    if count == 0:
        print("  조건에 맞는 태스크가 없습니다.")
        return
    for i, row in enumerate(rows, 1):
        tags = json.loads(row["tags"] or "[]")
        tags_str = ", ".join(tags) if tags else "-"
        p_icon = PRIORITY_ICON.get(row["priority"], "")
        s_icon = STATUS_ICON.get(row["status"], "")
        due_str = f"  마감: {_format_dt(row['due_dt'])}" if row["due_dt"] else ""
        content_preview = (row["content"] or "")[:80].replace("\n", " ")
        if len(row["content"] or "") > 80:
            content_preview += "..."

        print(f"[{i}] {s_icon} {p_icon} {row['title']}")
        if content_preview:
            print(f"    내용: {content_preview}")
        print(f"    상태: {row['status']}  우선순위: {row['priority']}{due_str}")
        print(f"    태그: {tags_str}  출처: {row['source'] or 'user'}")
        print(f"    ID: {row['id']}")
        print()


# ────────────────────────── CRUD 함수 ──────────────────────────

def cmd_add(args):
    if args.status not in VALID_STATUSES:
        print(f"[ERROR] 유효하지 않은 status: {args.status}. 가능한 값: {VALID_STATUSES}", file=sys.stderr)
        sys.exit(1)
    if args.priority not in VALID_PRIORITIES:
        print(f"[ERROR] 유효하지 않은 priority: {args.priority}. 가능한 값: {VALID_PRIORITIES}", file=sys.stderr)
        sys.exit(1)

    tags = args.tags or "[]"
    try:
        json.loads(tags)
    except json.JSONDecodeError:
        print(f"[ERROR] --tags 값이 올바른 JSON 배열이 아닙니다: {tags}", file=sys.stderr)
        sys.exit(1)

    db = _ensure_db(_get_db_path(args.db_path))
    now = datetime.utcnow().isoformat()
    task_id = str(uuid.uuid4())

    db.execute(
        """INSERT INTO tasks (id, title, content, status, priority, due_dt, tags, source, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (task_id, args.title, args.content or "", args.status, args.priority,
         args.due, tags, args.source, now, now)
    )
    db.commit()
    db.close()
    print(f"✅ 태스크 추가 완료")
    print(f"   제목: {args.title}")
    print(f"   상태: {args.status}  우선순위: {args.priority}")
    if args.due:
        print(f"   마감: {_format_dt(args.due)}")
    print(f"   ID: {task_id}")


def cmd_update(args):
    db = _ensure_db(_get_db_path(args.db_path))
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] ID '{args.id}'에 해당하는 태스크를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    fields = {}
    if args.title is not None:
        fields["title"] = args.title
    if args.content is not None:
        fields["content"] = args.content
    if args.status is not None:
        if args.status not in VALID_STATUSES:
            print(f"[ERROR] 유효하지 않은 status: {args.status}", file=sys.stderr)
            sys.exit(1)
        fields["status"] = args.status
    if args.priority is not None:
        if args.priority not in VALID_PRIORITIES:
            print(f"[ERROR] 유효하지 않은 priority: {args.priority}", file=sys.stderr)
            sys.exit(1)
        fields["priority"] = args.priority
    if args.due is not None:
        fields["due_dt"] = args.due
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
    db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    db.commit()
    db.close()
    print(f"✅ 태스크 수정 완료 (ID: {args.id})")


def cmd_done(args):
    db = _ensure_db(_get_db_path(args.db_path))
    row = db.execute("SELECT title FROM tasks WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] ID '{args.id}'에 해당하는 태스크를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    now = datetime.utcnow().isoformat()
    db.execute("UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ?", (now, args.id))
    db.commit()
    db.close()
    print(f"✅ 완료 처리: {row['title']} (ID: {args.id})")


def cmd_delete(args):
    db = _ensure_db(_get_db_path(args.db_path))
    row = db.execute("SELECT title FROM tasks WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] ID '{args.id}'에 해당하는 태스크를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    db.execute("DELETE FROM tasks WHERE id = ?", (args.id,))
    db.commit()
    db.close()
    print(f"✅ 태스크 삭제 완료: {row['title']} (ID: {args.id})")


def cmd_list(args):
    db = _ensure_db(_get_db_path(args.db_path))
    sql = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if args.status:
        sql += " AND status = ?"
        params.append(args.status)
    else:
        # 기본: 완료/취소 제외
        sql += " AND status NOT IN ('done', 'cancelled')"

    if args.priority:
        sql += " AND priority = ?"
        params.append(args.priority)
    if args.due_before:
        sql += " AND due_dt IS NOT NULL AND due_dt <= ?"
        params.append(args.due_before + "T23:59:59")
    if args.keyword:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{args.keyword}%", f"%{args.keyword}%"])
    if args.tag:
        sql += " AND tags LIKE ?"
        params.append(f'%"{args.tag}"%')

    # 정렬: 우선순위(high→low) → 마감일 → 생성일
    sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, due_dt ASC NULLS LAST, created_at ASC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    rows = db.execute(sql, params).fetchall()
    db.close()
    _print_tasks(rows, args.format)


# ────────────────────────── CLI ──────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Personal DB - 태스크(Tasks) 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db-path", help="SQLite DB 파일 경로 (기본: $OBSIDIAN_VAULT_PATH/4-Archieve/db/personal.db)")

    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="태스크 추가")
    p_add.add_argument("--title", required=True, help="태스크 제목")
    p_add.add_argument("--content", default="", help="상세 내용")
    p_add.add_argument("--status", default="todo", choices=VALID_STATUSES, help="상태 (기본: todo)")
    p_add.add_argument("--priority", default="medium", choices=VALID_PRIORITIES, help="우선순위 (기본: medium)")
    p_add.add_argument("--due", help="마감 일시 (ISO 8601, e.g. 2026-04-01T18:00)")
    p_add.add_argument("--tags", default='[]', help='태그 JSON 배열 (e.g. \'["work","urgent"]\')')
    p_add.add_argument("--source", default="user", help="출처 (user/nanoclaw/claude/gemini)")

    # update
    p_upd = sub.add_parser("update", help="태스크 수정")
    p_upd.add_argument("--id", required=True, help="수정할 태스크 ID")
    p_upd.add_argument("--title")
    p_upd.add_argument("--content")
    p_upd.add_argument("--status", choices=VALID_STATUSES)
    p_upd.add_argument("--priority", choices=VALID_PRIORITIES)
    p_upd.add_argument("--due")
    p_upd.add_argument("--tags")

    # done
    p_done = sub.add_parser("done", help="태스크 완료 처리")
    p_done.add_argument("--id", required=True, help="완료할 태스크 ID")

    # delete
    p_del = sub.add_parser("delete", help="태스크 삭제")
    p_del.add_argument("--id", required=True, help="삭제할 태스크 ID")

    # list
    p_list = sub.add_parser("list", help="태스크 목록 조회 (기본: todo + in_progress)")
    p_list.add_argument("--status", choices=VALID_STATUSES + ("all",), help="상태 필터 (기본: todo+in_progress)")
    p_list.add_argument("--priority", choices=VALID_PRIORITIES, help="우선순위 필터")
    p_list.add_argument("--due-before", dest="due_before", help="마감일 필터 (e.g. 2026-04-07)")
    p_list.add_argument("--keyword", help="제목/내용 키워드 검색")
    p_list.add_argument("--tag", help="태그 필터")
    p_list.add_argument("--limit", type=int, default=50, help="최대 결과 수 (기본: 50)")
    p_list.add_argument("--format", choices=["text", "json"], default="text", help="출력 형식")

    args = parser.parse_args()

    try:
        if args.command == "add":
            cmd_add(args)
        elif args.command == "update":
            cmd_update(args)
        elif args.command == "done":
            cmd_done(args)
        elif args.command == "delete":
            cmd_delete(args)
        elif args.command == "list":
            if hasattr(args, "status") and args.status == "all":
                args.status = None
            cmd_list(args)
    except EnvironmentError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 예기치 않은 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
