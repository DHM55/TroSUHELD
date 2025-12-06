import os
import json
import psycopg2
from datetime import datetime

# مجلد النسخة الاحتياطية داخل المشروع
BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), "backup_20251203_194325")
CODES_FILE = os.path.join(BACKUP_FOLDER, "codes_backup.json")
CUSTOMERS_FILE = os.path.join(BACKUP_FOLDER, "customers_backup.json")


def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL غير موجود في المتغيرات البيئية")
    return psycopg2.connect(db_url)


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def restore_from_backup():
    print("🚀 بدء عملية استرجاع البيانات من النسخة الاحتياطية...")
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # استرجاع الأكواد
                if os.path.exists(CODES_FILE):
                    with open(CODES_FILE, "r", encoding="utf-8") as f:
                        codes = json.load(f)
                    added_codes = 0
                    for row in codes:
                        code = row.get("code")
                        if not code:
                            continue
                        is_used = bool(row.get("is_used", False))
                        created_at = _parse_dt(row.get("created_at"))
                        cur.execute(
                            """
                            INSERT INTO codes (code, is_used, created_at)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (code) DO UPDATE
                                SET is_used = EXCLUDED.is_used
                            """,
                            (code, is_used, created_at),
                        )
                        added_codes += 1
                    print(f"✅ تم استرجاع / تحديث {added_codes} كوداً.")
                else:
                    print(f"⚠️ ملف الأكواد غير موجود: {CODES_FILE}")

                # استرجاع العملاء
                if os.path.exists(CUSTOMERS_FILE):
                    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
                        customers = json.load(f)
                    added_customers = 0
                    skipped_customers = 0
                    for row in customers:
                        phone = row.get("phone")
                        activation_code = row.get("activation_code")
                        if not phone or not activation_code:
                            continue

                        # منع التكرار (نفس الجوال + نفس الكود)
                        cur.execute(
                            "SELECT 1 FROM customers WHERE phone = %s AND activation_code = %s",
                            (phone, activation_code),
                        )
                        if cur.fetchone():
                            skipped_customers += 1
                            continue

                        name = row.get("name")
                        plate_letters = row.get("plate_letters")
                        plate_numbers = row.get("plate_numbers")
                        installation_center = row.get("installation_center")
                        activated_at = _parse_dt(row.get("activated_at"))

                        cur.execute(
                            """
                            INSERT INTO customers
                                (name, phone, plate_letters, plate_numbers,
                                 installation_center, activation_code, activated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                name,
                                phone,
                                plate_letters,
                                plate_numbers,
                                installation_center,
                                activation_code,
                                activated_at,
                            ),
                        )
                        added_customers += 1
                    print(
                        f"✅ تم استرجاع {added_customers} عميل. "
                        f"(تم تخطي {skipped_customers} عميل مكرر)"
                    )
                else:
                    print(f"⚠️ ملف العملاء غير موجود: {CUSTOMERS_FILE}")

        print("🎉 تم استرجاع البيانات بنجاح.")
    finally:
        conn.close()


if __name__ == "__main__":
    restore_from_backup()
