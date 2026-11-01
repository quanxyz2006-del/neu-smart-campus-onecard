import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("neu_smart_campus.db")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          username TEXT PRIMARY KEY, password TEXT NOT NULL, full_name TEXT NOT NULL,
          role TEXT NOT NULL, dob TEXT DEFAULT '', department TEXT DEFAULT '',
          vehicle TEXT DEFAULT 'Xe máy', balance INTEGER NOT NULL DEFAULT 50000,
          finance_manager INTEGER NOT NULL DEFAULT 0, pass_until TEXT, plate TEXT DEFAULT '',
          status TEXT NOT NULL DEFAULT 'Đang hoạt động');
        CREATE TABLE IF NOT EXISTS cards(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE REFERENCES users(username) ON DELETE CASCADE,
          card_type TEXT NOT NULL DEFAULT 'Thẻ thường xuyên - Theo lượt', status TEXT NOT NULL DEFAULT 'Đang hoạt động');
        CREATE TABLE IF NOT EXISTS transactions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          kind TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
          memo TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          vehicle TEXT, plate TEXT, visibility TEXT, payment_reference TEXT);
        CREATE TABLE IF NOT EXISTS parking_logs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          vehicle TEXT NOT NULL, time_band TEXT NOT NULL, fee INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS accounting_entries(
          id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER NOT NULL REFERENCES transactions(id),
          username TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS donations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          amount INTEGER NOT NULL, purpose TEXT NOT NULL, visibility TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS academic_records(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          course_code TEXT NOT NULL, course_name TEXT NOT NULL, grade REAL NOT NULL,
          tuition_status TEXT NOT NULL DEFAULT 'Đã hoàn thành');
        CREATE TABLE IF NOT EXISTS lecture_payments(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          period TEXT NOT NULL, teaching_hours INTEGER NOT NULL, gross_income INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS parking_tariffs(
          vehicle TEXT NOT NULL, time_band TEXT NOT NULL, member_fee INTEGER NOT NULL,
          visitor_fee INTEGER NOT NULL, PRIMARY KEY(vehicle,time_band));
        CREATE TABLE IF NOT EXISTS role_assignments(
          username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
          permission TEXT NOT NULL, granted_by TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(username,permission));
        """)
        transaction_columns = {row['name'] for row in db.execute('PRAGMA table_info(transactions)')}
        if 'payment_reference' not in transaction_columns:
            db.execute('ALTER TABLE transactions ADD COLUMN payment_reference TEXT')
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_payment_reference ON transactions(payment_reference) WHERE payment_reference IS NOT NULL AND payment_reference != ''")
        db.executemany("INSERT OR IGNORE INTO parking_tariffs(vehicle,time_band,member_fee,visitor_fee) VALUES(?,?,?,?)", [
            ('Xe đạp','Trước 18h',1000,2000), ('Xe đạp','Sau 18h',2000,3000),
            ('Xe máy','Trước 18h',2000,3000), ('Xe máy','Sau 18h',4000,4000)])
        db.execute("INSERT OR IGNORE INTO cards(username) SELECT username FROM users")


if __name__ == "__main__":
    init_db()
    print(f"SQLite database ready: {DB_PATH}")
