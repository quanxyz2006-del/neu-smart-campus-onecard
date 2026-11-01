"""Nạp dữ liệu demo từ data/demo_dataset.json vào SQLite."""

import json
from pathlib import Path

from database import connect, init_db
from utils import generate_password_from_name


DATASET_PATH = Path(__file__).with_name("data") / "demo_dataset.json"
ADMIN_ACCOUNT = {
    "username": "quan2006",
    "password": "123456",
    "full_name": "Hoàng Minh Quân (Admin)",
    "role": "ADMIN",
    "finance_manager": True,
}


def load_dataset():
    """Đọc và kiểm tra cấu trúc bộ dữ liệu demo được quản lý riêng."""
    with DATASET_PATH.open(encoding="utf-8") as dataset_file:
        dataset = json.load(dataset_file)
    students = dataset.get("students")
    lecturers = dataset.get("lecturers")
    if not isinstance(students, list) or not isinstance(lecturers, list):
        raise ValueError("Dataset cần có danh sách students và lecturers.")
    if len(students) != 43 or len(lecturers) != 6:
        raise ValueError("Dataset demo cần đúng 43 sinh viên và 6 giảng viên.")
    return students, lecturers


def seed():
    students, lecturers = load_dataset()
    init_db()
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO users(username,password,full_name,role,department,balance,finance_manager) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                ADMIN_ACCOUNT["username"],
                ADMIN_ACCOUNT["password"],
                ADMIN_ACCOUNT["full_name"],
                ADMIN_ACCOUNT["role"],
                "Ban quản trị",
                50000,
                int(ADMIN_ACCOUNT["finance_manager"]),
            ),
        )
        for student in students:
            username = student["username"]
            name = student["full_name"]
            db.execute(
                "INSERT OR IGNORE INTO users(username,password,full_name,role,dob,department,vehicle,balance) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    username,
                    generate_password_from_name(name),
                    name,
                    "STUDENT",
                    student["date_of_birth"],
                    student["department"],
                    student["vehicle"],
                    50000,
                ),
            )
            db.execute("INSERT OR IGNORE INTO cards(username) VALUES(?)", (username,))
            db.execute(
                "INSERT INTO academic_records(username,course_code,course_name,grade,tuition_status) "
                "SELECT ?, 'TIN1181', 'Nhập môn Công nghệ thông tin', 8.2, 'Đã hoàn thành' "
                "WHERE NOT EXISTS (SELECT 1 FROM academic_records WHERE username=? AND course_code='TIN1181')",
                (username, username),
            )

        for lecturer in lecturers:
            username = lecturer["username"]
            name = lecturer["full_name"]
            finance_manager = int(lecturer["finance_manager"])
            db.execute(
                "INSERT OR IGNORE INTO users(username,password,full_name,role,department,balance,finance_manager) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    username,
                    generate_password_from_name(name),
                    name,
                    "LECTURER",
                    lecturer["department"],
                    50000,
                    finance_manager,
                ),
            )
            db.execute("INSERT OR IGNORE INTO cards(username) VALUES(?)", (username,))
            db.execute(
                "INSERT INTO role_assignments(username,permission,granted_by) "
                "SELECT ?, 'FINANCE_MANAGER', 'quan2006' "
                "WHERE ?=1 AND NOT EXISTS "
                "(SELECT 1 FROM role_assignments WHERE username=? AND permission='FINANCE_MANAGER')",
                (username, finance_manager, username),
            )
            db.execute(
                "INSERT INTO lecture_payments(username,period,teaching_hours,gross_income) "
                "SELECT ?, 'Học kỳ 1 - 2026', 48, 7200000 "
                "WHERE NOT EXISTS "
                "(SELECT 1 FROM lecture_payments WHERE username=? AND period='Học kỳ 1 - 2026')",
                (username, username),
            )


if __name__ == "__main__":
    seed()
    students, lecturers = load_dataset()
    print(f"Đã nạp {len(students)} sinh viên, {len(lecturers)} giảng viên và 1 Admin demo.")
