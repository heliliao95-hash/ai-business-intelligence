import sqlite3
from pathlib import Path

import pandas as pd


# 数据库文件路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "business.db"


def get_connection():
	"""创建 SQLite 数据库连接。"""
	DATA_DIR.mkdir(parents=True, exist_ok=True)
	return sqlite3.connect(DB_PATH)


def save_data(df, table_name="sales"):
	"""将 Pandas DataFrame 保存到 SQLite 数据库。"""
	if df is None or df.empty:
		raise ValueError("不能保存空数据！")

	with get_connection() as conn:
		df.to_sql(table_name, conn, if_exists="replace", index=False)

	return len(df)


def load_data(table_name="sales"):
	"""从 SQLite 数据库读取数据。"""
	with get_connection() as conn:
		return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)


def execute_query(sql, params=None):
	"""执行 SQL 查询并返回 DataFrame。"""
	with get_connection() as conn:
		return pd.read_sql_query(sql, conn, params=params or ())


def get_table_info(table_name="sales"):
	"""获取数据表结构和记录数量。"""
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute(f'PRAGMA table_info("{table_name}")')
		columns = cursor.fetchall()
		cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
		count = cursor.fetchone()[0]

	return {"columns": columns, "row_count": count}


if __name__ == "__main__":
	print("数据库模块加载成功！")
	print(f"数据库路径：{DB_PATH}")
