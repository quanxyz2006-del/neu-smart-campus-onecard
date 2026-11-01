import unicodedata
from urllib.parse import quote


def generate_password_from_name(full_name: str) -> str:
    if not full_name:
        return ""
    normalized = full_name.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ASCII", "ignore").decode("utf-8")
    return "".join(normalized.split()).lower()


def vietqr_link(amount: int, username: str) -> str:
    memo = quote(f"NAPTHE {username}")
    return f"https://img.vietqr.io/image/MB-0966618840-compact2.png?amount={int(amount)}&addInfo={memo}&accountName=HOANG%20MINH%20QUAN"
