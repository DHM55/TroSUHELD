#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, session, redirect, url_for, flash, send_file
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import IntegrityError
import json
import io

app = Flask(__name__)
app.secret_key = 'true_shield_2025'

# بيانات المدير
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Aa3650667788'


# =========================
#  الاتصال بقاعدة البيانات
# =========================
def get_db_connection():
    db_url = os.getenv("DATABASE_URL")

    try:
        if db_url:
            return psycopg2.connect(db_url)
        else:
            return psycopg2.connect(
                database=os.getenv('PGDATABASE'),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD'),
                host=os.getenv('PGHOST'),
                port=os.getenv('PGPORT')
            )
    except Exception as e:
        print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None


# =========================
#  تهيئة قاعدة البيانات
# =========================
def init_database():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ الاتصال فشل")
            return False

        cur = conn.cursor()

        # جدول الأكواد
        cur.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # جدول العملاء
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

        # إضافة العمود لو غير موجود
        cur.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='customers' AND column_name='installation_center'
                ) THEN
                    ALTER TABLE customers ADD COLUMN installation_center VARCHAR(255);
                END IF;
            END $$;
        ''')

        conn.commit()
        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطأ التهيئة: {e}")
        return False


# =========================
#  دوال مساعدة
# =========================
def get_valid_codes():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code FROM codes WHERE is_used = FALSE ORDER BY code")
        codes = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return codes
    except:
        return []


def save_customer(name, phone, plate_letters, plate_numbers, installation_center, code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
            INSERT INTO customers (name, phone, plate_letters, plate_numbers, installation_center, activation_code)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, phone, plate_letters, plate_numbers, installation_center, code))

        conn.commit()
        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطأ في حفظ العميل: {e}")
        return False


def mark_code_used(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE codes SET is_used = TRUE WHERE code = %s", (code,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False


def get_customers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, phone, plate_letters, plate_numbers,
                   installation_center, activation_code, activated_at
            FROM customers ORDER BY activated_at DESC
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except:
        return []


def get_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        customers_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM codes WHERE is_used = FALSE")
        codes_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {'customers': customers_count, 'codes': codes_count}

    except:
        return {'customers': 0, 'codes': 0}


# =========================
#    المسارات
# =========================

@app.route('/', methods=['GET', 'POST'])
def warranty_activation():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        plate_letters = request.form.get('plate_letters')
        plate_numbers = request.form.get('plate_numbers')
        installation_center = request.form.get('installation_center')
        code = request.form.get('code')

        if not all([name, phone, plate_letters, plate_numbers, installation_center, code]):
            return render_template('result.html', success=False, message="يرجى ملء جميع الحقول")

        valid_codes = get_valid_codes()
        if code in valid_codes:
            if save_customer(name, phone, plate_letters, plate_numbers, installation_center, code):
                mark_code_used(code)
                return render_template('result.html', success=True, name=name,
                    installation_center=installation_center,
                    activation_date=datetime.now().strftime('%Y-%m-%d %H:%M'))
            else:
                return render_template('result.html', success=False, message="خطأ في حفظ البيانات")
        else:
            return render_template('result.html', success=False, message="الكود غير صحيح")

    return render_template('index.html')


# =========================
#  تسجيل دخول الأدمن
# =========================

@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')


@app.route('/admin/authenticate', methods=['POST'])
def admin_authenticate():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    else:
        flash('بيانات الدخول غير صحيحة', 'error')
        return redirect(url_for('admin_login'))


# =========================
#   لوحة التحكم
# =========================

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html',
                           customers=get_customers(),
                           codes=get_valid_codes(),
                           stats=get_stats())


# =========================
#   إضافة أكواد جديدة
# =========================

@app.route('/admin/add_codes', methods=['POST'])
def add_codes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    codes_text = request.form.get('codes', '')
    codes_list = [c.strip() for c in codes_text.replace(",", "\n").split("\n") if c.strip()]

    conn = get_db_connection()
    cur = conn.cursor()

    added = 0
    skipped = 0

    for code in codes_list:
        try:
            cur.execute("INSERT INTO codes (code) VALUES (%s)", (code,))
            added += 1
        except IntegrityError:
            conn.rollback()
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    flash(f"تمت إضافة {added} كود — المكرر {skipped}", "success")
    return redirect(url_for('admin_dashboard'))


# =========================
#   النسخة الاحتياطية (تحميل)
# =========================

@app.route('/admin/backup')
def admin_backup():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    data = {
        "customers": get_customers(),
        "codes": get_valid_codes()
    }

    backup_json = json.dumps(data, ensure_ascii=False, indent=4)

    return send_file(
        io.BytesIO(backup_json.encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name='true_shield_backup.json'
    )


# =========================
# تسجيل الخروج
# =========================

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# =========================
# API
# =========================

@app.route('/api', methods=['GET'])
def api_status():
    return {"status": "ok", "service": "True Shield Warranty System"}


# =========================
# تهيئة القاعدة عند بدء التشغيل
# =========================

def run_initial_setup():
    if init_database():
        print("✓ قاعدة البيانات جاهزة")


run_initial_setup()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
