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

    # أولاً نحاول باستخدام DATABASE_URL (Render / غيره)
    db_url = os.getenv("DATABASE_URL")

    try:
        if db_url:
            # مثال: postgresql://user:pass@host:port/dbname
            conn = psycopg2.connect(db_url)
            return conn
        else:
            # في حال ما فيه DATABASE_URL نرجع للمتغيرات القديمة
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
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ لا يمكن تهيئة القاعدة لأن الاتصال فشل")
            return False

        cur = conn.cursor()

        # إنشاء جدول الأكواد
        cur.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # إنشاء جدول العملاء
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

        # التأكد من وجود عمود installation_center في الجداول القديمة
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

        print("✅ تم تهيئة قاعدة البيانات بنجاح")
        return True

    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False


def add_initial_codes():
    """إضافة الأكواد الأولية إذا لم تكن موجودة"""
    try:
        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()

        # التحقق من وجود أكواد
        cur.execute("SELECT COUNT(*) FROM codes")
        result = cur.fetchone()
        count = result[0] if result else 0

        if count == 0:
            # الأكواد الأولية
            initial_codes = [
                '11111', '22222', '33333', '44444', '55555',
                '66666', '77777', '88888', '99999', '12345'
            ]

            for code in initial_codes:
                cur.execute(
                    "INSERT INTO codes (code) VALUES (%s) ON CONFLICT (code) DO NOTHING",
                    (code,)
                )

            conn.commit()
            print(f"✅ تم إضافة {len(initial_codes)} كود أولي")
        else:
            print(f"ℹ️ يوجد بالفعل {count} كود في جدول الأكواد، لن نضيف الأكواد الأولية")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطأ في إضافة الأكواد: {e}")
        return False


# =========================
#  دوال مساعدة
# =========================
def get_valid_codes():
    """الحصول على الأكواد الصالحة (غير المستخدمة)"""
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
    """حفظ بيانات العميل في قاعدة البيانات"""
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

        print(f"✅ تم حفظ العميل: {name}")
        return True

    except Exception as e:
        print(f"❌ خطأ في حفظ العميل: {e}")
        return False


def mark_code_used(code):
    """تمييز الكود كمستخدم في قاعدة البيانات"""
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
        print(f"❌ خطأ في تحديث الكود: {e}")
        return False


def get_customers():
    """الحصول على جميع العملاء"""
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
    """إحصائيات النظام"""
    try:
        conn = get_db_connection()
        if not conn:
            return {'customers': 0, 'codes': 0}

        cur = conn.cursor()

        # عدد العملاء
        cur.execute("SELECT COUNT(*) FROM customers")
        result = cur.fetchone()
        customers_count = result[0] if result else 0

        # عدد الأكواد المتاحة
        cur.execute("SELECT COUNT(*) FROM codes WHERE is_used = FALSE")
        result = cur.fetchone()
        codes_count = result[0] if result else 0

        cur.close()
        conn.close()

        return {'customers': customers_count, 'codes': codes_count}

    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {'customers': 0, 'codes': 0}


# =========================
#    المسارات (Routes)
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

        # التحقق من الحقول
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

        # التحقق من صحة الكود
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


@app.route('/admin/add_codes', methods=['POST'])
def add_codes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    codes_text = request.form.get('codes', '').strip()
    if not codes_text:
        flash('يرجى إدخال أكواد صحيحة', 'error')
        return redirect(url_for('admin_dashboard'))

    # تقسيم الأكواد (فاصلة أو سطر جديد)
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

        message = f"تم إضافة {added_count} كود جديد"
        if duplicate_count > 0:
            message += f" ({duplicate_count} كود مكرر تم تجاهله)"

        flash(message, 'success')

    except Exception as e:
        print(f"خطأ في إضافة الأكواد: {e}")
        flash('حدث خطأ في إضافة الأكواد', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_code/<code>', methods=['POST'])
def delete_code(code):
    """حذف كود من قاعدة البيانات"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        conn = get_db_connection()
        if not conn:
            flash('خطأ في الاتصال بقاعدة البيانات', 'error')
            return redirect(url_for('admin_dashboard'))

        cur = conn.cursor()
        cur.execute("DELETE FROM codes WHERE code = %s AND is_used = FALSE", (code,))

        if cur.rowcount > 0:
            conn.commit()
            flash(f'تم حذف الكود {code} بنجاح', 'success')
        else:
            flash('لا يمكن حذف هذا الكود (قد يكون مستخدماً أو غير موجود)', 'error')

        cur.close()
        conn.close()

    except Exception as e:
        print(f"خطأ في حذف الكود: {e}")
        flash('حدث خطأ في حذف الكود', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/api', methods=['GET', 'HEAD'])
def api_status():
    """API status endpoint"""
    return {"status": "ok", "service": "True Shield Warranty System"}


# =========================
#  تهيئة القاعدة عند استيراد الملف
#  (يعمل مع gunicorn و التشغيل المحلي)
# =========================
def run_initial_setup():
    print("🔧 بدء تهيئة قاعدة البيانات...")
    if init_database():
        add_initial_codes()
        stats = get_stats()
        print("📊 إحصائيات بعد التهيئة:")
        print(f"   • الأكواد المتاحة: {stats['codes']}")
        print(f"   • العملاء المسجلين: {stats['customers']}")
        print("✅ True Shield جاهز للعمل مع قاعدة البيانات!")
    else:
        print("❌ فشل في تهيئة قاعدة البيانات")


# تشغيل التهيئة مرة واحدة عند استيراد الملف
run_initial_setup()


if __name__ == '__main__':
    # تشغيل مباشر (على جهازك مثلاً)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
