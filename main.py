#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import (
    Flask, render_template, request, session,
    redirect, url_for, flash, send_file
)
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
    """الاتصال بقاعدة البيانات باستخدام DATABASE_URL أو متغيرات PG*."""
    db_url = os.getenv("DATABASE_URL")

    try:
        if db_url:
            # مثال: postgresql://user:pass@host:port/dbname
            conn = psycopg2.connect(db_url)
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
    """إنشاء الجداول إن لم تكن موجودة."""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ لا يمكن تهيئة القاعدة لأن الاتصال فشل")
            return False

        cur = conn.cursor()

        # جدول الأكواد
        cur.execute("""
            CREATE TABLE IF NOT EXISTS codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # جدول العملاء
        cur.execute("""
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
        """)

        # التأكد من وجود عمود installation_center
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='customers'
                      AND column_name='installation_center'
                ) THEN
                    ALTER TABLE customers
                        ADD COLUMN installation_center VARCHAR(255);
                END IF;
            END $$;
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ تم التأكد من الجداول بنجاح")
        return True

    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False


def add_initial_codes():
    """إضافة أكواد أولية إذا كان جدول الأكواد فارغاً."""
    try:
        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM codes")
        count = cur.fetchone()[0]

        if count == 0:
            initial_codes = [
                '11111', '22222', '33333', '44444', '55555',
                '66666', '77777', '88888', '99999', '12345'
            ]
            for code in initial_codes:
                cur.execute(
                    "INSERT INTO codes (code) VALUES (%s) "
                    "ON CONFLICT (code) DO NOTHING",
                    (code,)
                )
            conn.commit()
            print(f"✅ تم إضافة {len(initial_codes)} كود أولي")
        else:
            print(f"ℹ️ يوجد بالفعل {count} كود في جدول الأكواد")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطأ في إضافة الأكواد الأولية: {e}")
        return False


# =========================
#  دوال مساعدة
# =========================
def get_valid_codes():
    """إرجاع الأكواد غير المستخدمة."""
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

    except Exception as e:
        print(f"❌ خطأ في تحميل الأكواد: {e}")
        return []


def save_customer(name, phone, plate_letters, plate_numbers, installation_center, code):
    """حفظ بيانات عميل جديد."""
    try:
        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO customers (
                name, phone, plate_letters, plate_numbers,
                installation_center, activation_code
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, phone, plate_letters, plate_numbers, installation_center, code))

        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ تم حفظ العميل: {name}")
        return True

    except Exception as e:
        print(f"❌ خطأ في حفظ العميل: {e}")
        return False


def mark_code_used(code):
    """تحديد الكود كمستخدم."""
    try:
        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute("UPDATE codes SET is_used = TRUE WHERE code = %s", (code,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"🗑️ تم تمييز الكود كمستخدم: {code}")
        return True

    except Exception as e:
        print(f"❌ خطأ في تحديث حالة الكود: {e}")
        return False


def get_customers():
    """إرجاع جميع العملاء."""
    try:
        conn = get_db_connection()
        if not conn:
            return []

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, phone, plate_letters, plate_numbers,
                   installation_center, activation_code, activated_at
            FROM customers
            ORDER BY activated_at DESC
        """)
        customers = cur.fetchall()
        cur.close()
        conn.close()
        return customers

    except Exception as e:
        print(f"❌ خطأ في تحميل العملاء: {e}")
        return []


def get_stats():
    """إرجاع عدد العملاء وعدد الأكواد المتاحة."""
    try:
        conn = get_db_connection()
        if not conn:
            return {'customers': 0, 'codes': 0}

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        customers_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM codes WHERE is_used = FALSE")
        codes_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {'customers': customers_count, 'codes': codes_count}

    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {'customers': 0, 'codes': 0}


# =========================
#    صفحة تفعيل الضمان
# =========================
@app.route('/', methods=['GET', 'POST'])
def warranty_activation():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        plate_letters = request.form.get('plate_letters', '').strip()
        plate_numbers = request.form.get('plate_numbers', '').strip()
        installation_center = request.form.get('installation_center', '').strip()
        code = request.form.get('code', '').strip()

        if not all([name, phone, plate_letters, plate_numbers, installation_center, code]):
            return render_template(
                'result.html',
                success=False,
                message="يرجى ملء جميع الحقول المطلوبة",
                name=name,
                phone=phone,
                plate_letters=plate_letters,
                plate_numbers=plate_numbers,
                installation_center=installation_center,
                code=code
            )

        valid_codes = get_valid_codes()
        if code in valid_codes:
            if save_customer(name, phone, plate_letters, plate_numbers, installation_center, code):
                mark_code_used(code)
                activation_date = datetime.now().strftime('%Y-%m-%d %H:%M')
                return render_template(
                    'result.html',
                    success=True,
                    message="تم تفعيل الضمان بنجاح!",
                    name=name,
                    installation_center=installation_center,
                    activation_date=activation_date
                )
            else:
                return render_template(
                    'result.html',
                    success=False,
                    message="حدث خطأ في حفظ البيانات",
                    name=name,
                    phone=phone,
                    plate_letters=plate_letters,
                    plate_numbers=plate_numbers,
                    installation_center=installation_center,
                    code=code
                )
        else:
            return render_template(
                'result.html',
                success=False,
                message="كود التفعيل غير صحيح",
                name=name,
                phone=phone,
                plate_letters=plate_letters,
                plate_numbers=plate_numbers,
                installation_center=installation_center,
                code=code
            )

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
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
        return redirect(url_for('admin_login'))


# =========================
#   لوحة التحكم
# =========================
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    customers = get_customers()
    valid_codes = get_valid_codes()
    stats = get_stats()

    return render_template(
        'admin_dashboard.html',
        customers=customers,
        codes=valid_codes,
        stats=stats
    )


# =========================
#   إضافة أكواد جديدة
# =========================
@app.route('/admin/add_codes', methods=['POST'])
def add_codes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    codes_text = request.form.get('codes', '').strip()
    if not codes_text:
        flash('يرجى إدخال أكواد صحيحة', 'error')
        return redirect(url_for('admin_dashboard'))

    codes = []
    for line in codes_text.replace(',', '\n').split('\n'):
        code = line.strip()
        if code:
            codes.append(code)

    if not codes:
        flash('لم يتم العثور على أكواد صحيحة', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        conn = get_db_connection()
        if not conn:
            flash('خطأ في الاتصال بقاعدة البيانات', 'error')
            return redirect(url_for('admin_dashboard'))

        cur = conn.cursor()
        added_count = 0
        duplicate_count = 0

        for code in codes:
            try:
                cur.execute("INSERT INTO codes (code) VALUES (%s)", (code,))
                added_count += 1
            except IntegrityError:
                duplicate_count += 1
                conn.rollback()
                continue

        conn.commit()
        cur.close()
        conn.close()

        msg = f"تم إضافة {added_count} كود جديد"
        if duplicate_count > 0:
            msg += f" (تم تجاهل {duplicate_count} كود مكرر)"
        flash(msg, 'success')

    except Exception as e:
        print(f"❌ خطأ في إضافة الأكواد: {e}")
        flash('حدث خطأ في إضافة الأكواد', 'error')

    return redirect(url_for('admin_dashboard'))


# =========================
#   تحميل نسخة احتياطية
# =========================
@app.route('/admin/backup')
def admin_backup():
    """تحميل نسخة احتياطية (JSON) للمستخدم على جهازه."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    data = {
        "customers": get_customers(),
        "codes": get_valid_codes()
    }

    backup_json = json.dumps(data, ensure_ascii=False, indent=4)
    buffer = io.BytesIO(backup_json.encode('utf-8'))

    # attachment_filename متوافق مع Flask القديم
    return send_file(
        buffer,
        mimetype='application/json; charset=utf-8',
        as_attachment=True,
        attachment_filename='true_shield_backup.json'
    )


# =========================
#   تسجيل الخروج
# =========================
@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    """تسجيل خروج الأدمن (تعمل مع GET أو POST)."""
    session.clear()
    return redirect(url_for('admin_login'))


# =========================
#   API بسيط
# =========================
@app.route('/api', methods=['GET'])
def api_status():
    return {"status": "ok", "service": "True Shield Warranty System"}


# =========================
#  تهيئة القاعدة عند التشغيل
# =========================
def run_initial_setup():
    print("🔧 بدء التهيئة...")
    if init_database():
        add_initial_codes()
        stats = get_stats()
        print("📊 الإحصائيات بعد التهيئة:")
        print(f"   • الأكواد المتاحة: {stats['codes']}")
        print(f"   • العملاء المسجلين: {stats['customers']}")
        print("✅ النظام جاهز للعمل")
    else:
        print("❌ فشل في تهيئة قاعدة البيانات")


# تشغيل التهيئة عند استيراد الملف
run_initial_setup()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
