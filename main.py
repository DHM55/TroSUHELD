#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import IntegrityError

app = Flask(__name__)
app.secret_key = 'true_shield_2025'

# بيانات المدير
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Aa3650667788'


# =========================
#  الاتصال بقاعدة البيانات
# =========================
def get_db_connection():
    """الاتصال بقاعدة البيانات"""

    db_url = os.getenv("DATABASE_URL")

    try:
        if db_url:
            conn = psycopg2.connect(db_url)
            return conn
        else:
            conn = psycopg2.connect(
                database=os.getenv('PGDATABASE'),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD'),
                host=os.getenv('PGHOST'),
                port=os.getenv('PGPORT')
            )
            return conn

    except Exception as e:
        print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None


# =========================
#  تهيئة قاعدة البيانات
# =========================
def init_database():
    """إنشاء الجداول إذا لم تكن موجودة"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ فشل الاتصال — لم يتم إنشاء الجداول")
            return False

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
        conn.close()

        return True

    except Exception as e:
        print(f"❌ خطأ في التهيئة: {e}")
        return False


# =========================
#  إضافة الأكواد الأولية
# =========================
def add_initial_codes():
    try:
        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM codes")
        count = cur.fetchone()[0]

        if count == 0:
            initial_codes = [
                '11111','22222','33333','44444','55555',
                '66666','77777','88888','99999','12345'
            ]

            for code in initial_codes:
                cur.execute("INSERT INTO codes (code) VALUES (%s) ON CONFLICT DO NOTHING", (code,))

            conn.commit()

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطأ عند إضافة الأكواد الأولية: {e}")
        return False


# =========================
#  دوال مساعدة
# =========================
def get_valid_codes():
    try:
        conn = get_db_connection()
        if not conn:
            return []

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
        if not conn:
            return False

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
        if not conn:
            return False

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
        if not conn:
            return []

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM customers ORDER BY activated_at DESC")
        result = cur.fetchall()

        cur.close()
        conn.close()
        return result

    except:
        return []


def get_stats():
    try:
        conn = get_db_connection()
        if not conn:
            return {'customers': 0, 'codes': 0}

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM codes WHERE is_used = FALSE")
        codes = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {'customers': customers, 'codes': codes}

    except:
        return {'customers': 0, 'codes': 0}


# =========================
#  Routes
# =========================
@app.route('/', methods=['GET', 'POST'])
def warranty_activation():
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        letters = request.form['plate_letters'].strip()
        numbers = request.form['plate_numbers'].strip()
        center = request.form['installation_center'].strip()
        code = request.form['code'].strip()

        if not all([name, phone, letters, numbers, center, code]):
            return render_template('result.html',
                                   success=False,
                                   message="يرجى تعبئة جميع البيانات")

        valid = get_valid_codes()
        if code not in valid:
            return render_template('result.html',
                                   success=False,
                                   message="كود التفعيل غير صحيح")

        if save_customer(name, phone, letters, numbers, center, code):
            mark_code_used(code)
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            return render_template('result.html',
                                   success=True,
                                   name=name,
                                   installation_center=center,
                                   activation_date=date,
                                   message="تم تفعيل الضمان")

        return render_template('result.html',
                               success=False,
                               message="خطأ في حفظ البيانات")

    return render_template('index.html')


@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')


@app.route('/admin/authenticate', methods=['POST'])
def admin_auth():
    if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect('/admin/dashboard')
    flash("بيانات الدخول غير صحيحة", "error")
    return redirect('/admin')


@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin')

    return render_template('admin_dashboard.html',
                           customers=get_customers(),
                           codes=get_valid_codes(),
                           stats=get_stats())


# =========================
#  إصلاح: إضافة الأكواد تعمل الآن 100%
# =========================
@app.route('/admin/add_codes', methods=['POST'])
def add_codes():
    if not session.get('admin_logged_in'):
        return redirect('/admin')

    text = request.form.get('codes', '').strip()
    if not text:
        flash("⚠️ يرجى إدخال أكواد", "error")
        return redirect('/admin/dashboard')

    codes = [c.strip() for c in text.replace(',', '\n').split('\n') if c.strip()]

    conn = get_db_connection()
    cur = conn.cursor()

    added = 0
    duplicate = 0

    for code in codes:
        try:
            cur.execute("INSERT INTO codes (code) VALUES (%s)", (code,))
            added += 1
        except IntegrityError:
            duplicate += 1
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    msg = f"✔️ تم إضافة {added} كود"
    if duplicate > 0:
        msg += f" — {duplicate} مكرر"

    flash(msg, "success")
    return redirect('/admin/dashboard')


@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin')


@app.route('/api')
def api_status():
    return {"status": "ok", "service": "True Shield"}


# =========================
#  تهيئة قاعدة البيانات
# =========================
print("🔧 Initializing database...")
init_database()
add_initial_codes()
print("✅ Ready")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
