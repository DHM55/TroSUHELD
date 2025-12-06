#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import psycopg2
from datetime import datetime

# اسم مجلد الباك أب داخل المشروع
BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), "backup_20251203_194325")

CODES_FILE = os.path.join(BACKUP_FOLDER, "codes_backup.json")
CUSTOMERS_FILE = os.path.join(BACKUP_FOLDER, "customers_backup.json")


def get_db_connection():
    """الاتصال بقاعدة بيانات Render عبر DATABASE_URL"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL غير موجود في Environment Variables.")
    return psycopg2.connect(db_url)


def restore_codes(cur):
    """استرجاع وتركيب الأكواد القديمة (مع تحديث حالة is_used)"""
    if not os.path.exists(CODES_FILE):
        print("⚠️ لم يتم العثور على ملف الأكواد:", CODES_FILE)
        return

    with open(CODES_FILE, "r", encoding="utf-8") as f:
        codes = json.load(f)

    added = 0
    for row in codes:
        code = row.get("code")
        if not code:
            continue

        is_used = row.get("is_used", False)
        created_at = row.get("created_at")
        if created_at:
            created_at = datetime.fromisoformat(created_at)

        # لو الكود موجود من قبل → نحدث حالة is_used
        cur.execute(
            """
            INSERT INTO codes (code, is_used, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (code) DO UPDATE
                SET is_used = EXCLUDED.is_used
            """,
            (code, is_used, created_at),
        )
        added += 1

    print(f"✅ تم استرجاع / تحديث {added} كوداً من الباك أب.")


def restore_customers(cur):
    """استرجاع وتركيب العملاء القدامى بدون تكرار مع الجدد"""
    if not os.path.exists(CUSTOMERS_FILE):
        print("⚠️ لم يتم العثور على ملف العملاء:", CUSTOMERS_FILE)
        return

    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
        customers = json.load(f)

    added = 0
    skipped = 0

    for row in customers:
        phone = row.get("phone")
        activation_code = row.get("activation_code")

        if not phone or not activation_code:
            continue

        # نتأكد ما نكرر نفس العميل (نفس الجوال + نفس الكود)
        cur.execute(
            "SELECT 1 FROM customers WHERE phone = %s AND activation_code = %s",
            (phone, activation_code),
        )
        if cur.fetchone():
            skipped += 1
            continue

        name = row.get("name")
        plate_letters = row.get("plate_letters")
        plate_numbers = row.get("plate_numbers")
        installation_center = row.get("installation_center")
        activated_at = row.get("activated_at")

        if activated_at:
            activated_at = datetime.fromisoformat(activated_at)

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
        added += 1

    print(f"✅ تم استرجاع {added} عميل من النسخة الاحتياطية. (تخطي {skipped} عميل مكرر)")


def main():
    print("🚀 بدء عملية استرجاع البيانات من النسخة الاحتياطية (Replit)...")
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                restore_codes(cur)
                restore_customers(cur)
        print("🎉 تم استرجاع البيانات بنجاح.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
