#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت استعادة قاعدة البيانات من النسخة الاحتياطية
استخدم هذا السكريبت لاستيراد البيانات إلى قاعدة بيانات جديدة
"""

import os
import json
import psycopg2
from datetime import datetime

def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    try:
        conn = psycopg2.connect(
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD'),
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT')
        )
        return conn
    except Exception as e:
        print(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

def init_database(conn):
    """تهيئة جداول قاعدة البيانات"""
    try:
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                plate_letters VARCHAR(50) NOT NULL,
                plate_numbers VARCHAR(50) NOT NULL,
                installation_center VARCHAR(255),
                activation_code VARCHAR(50) NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cur.close()
        print("تم إنشاء الجداول بنجاح")
        return True
        
    except Exception as e:
        print(f"خطأ في إنشاء الجداول: {e}")
        return False

def restore_codes(conn, backup_folder):
    """استعادة الأكواد من النسخة الاحتياطية"""
    try:
        codes_file = f"{backup_folder}/codes_backup.json"
        if not os.path.exists(codes_file):
            print(f"ملف الأكواد غير موجود: {codes_file}")
            return False
        
        with open(codes_file, 'r', encoding='utf-8') as f:
            codes_data = json.load(f)
        
        cur = conn.cursor()
        restored = 0
        
        for code in codes_data:
            try:
                cur.execute('''
                    INSERT INTO codes (code, is_used, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                ''', (code['code'], code['is_used'], code.get('created_at')))
                restored += 1
            except Exception as e:
                print(f"خطأ في إضافة الكود {code['code']}: {e}")
        
        conn.commit()
        cur.close()
        print(f"تم استعادة {restored} كود")
        return True
        
    except Exception as e:
        print(f"خطأ في استعادة الأكواد: {e}")
        return False

def restore_customers(conn, backup_folder):
    """استعادة العملاء من النسخة الاحتياطية"""
    try:
        customers_file = f"{backup_folder}/customers_backup.json"
        if not os.path.exists(customers_file):
            print(f"ملف العملاء غير موجود: {customers_file}")
            return False
        
        with open(customers_file, 'r', encoding='utf-8') as f:
            customers_data = json.load(f)
        
        cur = conn.cursor()
        restored = 0
        
        for customer in customers_data:
            try:
                cur.execute('''
                    INSERT INTO customers (name, phone, plate_letters, plate_numbers, installation_center, activation_code, activated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    customer['name'],
                    customer['phone'],
                    customer['plate_letters'],
                    customer['plate_numbers'],
                    customer.get('installation_center'),
                    customer['activation_code'],
                    customer.get('activated_at')
                ))
                restored += 1
            except Exception as e:
                print(f"خطأ في إضافة العميل {customer['name']}: {e}")
        
        conn.commit()
        cur.close()
        print(f"تم استعادة {restored} عميل")
        return True
        
    except Exception as e:
        print(f"خطأ في استعادة العملاء: {e}")
        return False

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("الاستخدام: python restore_database.py <مجلد_النسخة_الاحتياطية>")
        print("مثال: python restore_database.py backup_20251203_194325")
        return
    
    backup_folder = sys.argv[1]
    
    if not os.path.exists(backup_folder):
        print(f"مجلد النسخة الاحتياطية غير موجود: {backup_folder}")
        return
    
    print("بدء عملية الاستعادة...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    if init_database(conn):
        restore_codes(conn, backup_folder)
        restore_customers(conn, backup_folder)
    
    conn.close()
    print("اكتملت عملية الاستعادة!")

if __name__ == "__main__":
    main()
