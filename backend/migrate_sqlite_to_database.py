"""Copy the local SQLite database, including reviewed annotations, to DATABASE_URL.

The target database must be empty. Set DATABASE_URL in the environment before
running this script. No source data is modified.

Examples (from the repository root):
    $env:DATABASE_URL = 'mysql+pymysql://user:password@host/building_code?charset=utf8mb4'
    python backend/migrate_sqlite_to_database.py
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, inspect, select, func

from app import create_app
from config import DATABASE_URL, RUNTIME_DIR
from models import db


DEFAULT_SOURCE = RUNTIME_DIR / 'instance' / 'specifications.db'


def parse_datetime(value):
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return value


def copy_database(source_path: Path):
    if not DATABASE_URL or DATABASE_URL.startswith('sqlite:'):
        raise SystemExit('请先将 DATABASE_URL 设置为 MySQL 等外部持久数据库地址。')
    if not source_path.exists():
        raise SystemExit(f'找不到源数据库：{source_path}')

    app = create_app()
    with sqlite3.connect(source_path) as source, app.app_context():
        source.row_factory = sqlite3.Row
        target = db.engine
        inspector = inspect(target)
        tables = [table for table in db.metadata.sorted_tables if table.name in inspector.get_table_names()]

        existing = []
        with target.connect() as connection:
            for table in tables:
                count = connection.execute(select(func.count()).select_from(table)).scalar_one()
                if count:
                    existing.append(f'{table.name}={count}')
        if existing:
            raise SystemExit('目标数据库不是空库，已停止以避免重复导入：' + ', '.join(existing))

        copied = 0
        with target.begin() as connection:
            for table in tables:
                columns = [column.name for column in table.columns]
                quoted = ', '.join(f'"{column}"' for column in columns)
                rows = source.execute(f'SELECT {quoted} FROM "{table.name}"').fetchall()
                if not rows:
                    continue
                values = []
                for row in rows:
                    item = dict(row)
                    for column in table.columns:
                        if isinstance(column.type, DateTime):
                            item[column.name] = parse_datetime(item[column.name])
                    values.append(item)
                connection.execute(table.insert(), values)
                copied += len(values)
                print(f'已迁移 {table.name}: {len(values)} 行')
    print(f'迁移完成，共 {copied} 行；源数据库未修改。')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='迁移本地 SQLite 到 DATABASE_URL')
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE, help='源 SQLite 文件路径')
    args = parser.parse_args()
    copy_database(args.source)
