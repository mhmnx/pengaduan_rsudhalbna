from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import psycopg2
from psycopg2.extras import RealDictCursor # Agar cursor mengembalikan dictionary seperti sebelumnya
from config import Config
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import functools

app = Flask(__name__)
# PENTING: Ganti dengan secret key yang kuat dan unik!
# Contoh: app.secret_key = os.urandom(24)
app.secret_key = '1234'
app.config.from_object(Config)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'mp4','zip','rar','7z'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Koneksi Database
try:
    conn = psycopg2.connect(
        host=Config.HOST, # Ganti nama variabel di config jika perlu
        database=Config.DATABASE, # Ganti nama variabel di config jika perlu
        user=Config.USER, # Ganti nama variabel di config jika perlu
        password=Config.PASSWORD # Ganti nama variabel di config jika perlu
    )
    # Menggunakan RealDictCursor agar hasil fetch sama seperti sebelumnya (dictionary)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    print("Koneksi ke PostgreSQL berhasil!")
except Exception as e:
    print(f"Koneksi ke PostgreSQL GAGAL: {e}")
    
cursor = conn.cursor(cursor_factory=RealDictCursor)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # --- DEBUGGING LOGIN ---
        print(f"Percobaan login untuk username: {username}")
        print(f"Password yang dimasukkan: {password}") # Hati-hati dengan ini di produksi!

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            print(f"Pengguna ditemukan: {user['username']}")
            print(f"Password ter-hash di DB: {user['password']}")
            is_password_correct = check_password_hash(user['password'], password)
            print(f"Hasil check_password_hash: {is_password_correct}")

            if is_password_correct:
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role'] # Simpan peran pengguna di sesi
                flash(f"Selamat datang, {user['username']}! Login berhasil.", "success")
                print("Login berhasil, mengarahkan ke dashboard.")
                return redirect(url_for('dashboard'))
            else:
                flash("Username atau password salah!", "danger")
                print("Password salah.")
        else:
            flash("Username atau password salah!", "danger")
            print("Pengguna tidak ditemukan.")
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash("Anda telah logout.", "info")
    return redirect(url_for('login'))

# Middleware untuk memeriksa login
# PASTIKAN DECORATOR INI ADA DI FILE ANDA!
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            flash("Anda harus login untuk mengakses halaman ini.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Middleware untuk memeriksa peran admin
# PASTIKAN DECORATOR INI ADA DI FILE ANDA!
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash("Anda tidak memiliki izin untuk mengakses halaman ini.", "danger")
            return redirect(url_for('dashboard')) # Atau redirect ke halaman login
        return f(*args, **kwargs)
    return decorated_function

# Rute Kelola Pengguna (Hanya untuk Admin)
@app.route('/manage_users')
@login_required
@admin_required
def manage_users():
    cursor.execute("SELECT id, username, role FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    return render_template('manage_users.html', users=users)

# Rute Tambah Pengguna Baru (Hanya untuk Admin)
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user') # Default role adalah 'user'

        # Cek apakah username sudah ada
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username sudah digunakan. Silakan pilih username lain.", "danger")
            return render_template('add_user.html')

        hashed_password = generate_password_hash(password)
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                        (username, hashed_password, role))
            conn.commit()
            flash("Pengguna baru berhasil ditambahkan!", "success")
            return redirect(url_for('manage_users'))
        except psycopg2.connect.Error as err:
            flash(f"Terjadi kesalahan saat menambahkan pengguna: {err}", "danger")
            conn.rollback()
    return render_template('add_user.html')

# Rute Edit Pengguna (Hanya untuk Admin)
@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()

    if not user:
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form.get('password') # Password bisa kosong jika tidak diubah
        role = request.form.get('role', 'user')

        update_query_parts = []
        update_values = []

        # Cek apakah username diubah dan sudah ada
        if username != user['username']:
            cursor.execute("SELECT * FROM users WHERE username = %s AND id != %s", (username, id))
            existing_user_with_new_username = cursor.fetchone()
            if existing_user_with_new_username:
                flash("Username sudah digunakan oleh pengguna lain. Silakan pilih username lain.", "danger")
                return render_template('edit_user.html', user=user)
            update_query_parts.append("username=%s")
            update_values.append(username)
        
        if password: # Jika password diisi, hash dan update
            hashed_password = generate_password_hash(password)
            update_query_parts.append("password=%s")
            update_values.append(hashed_password)
        
        update_query_parts.append("role=%s")
        update_values.append(role)

        if update_query_parts: # Hanya jalankan query jika ada yang perlu diupdate
            final_update_query = "UPDATE users SET " + ", ".join(update_query_parts) + " WHERE id=%s"
            update_values.append(id)
            try:
                cursor.execute(final_update_query, tuple(update_values))
                conn.commit()
                flash("Pengguna berhasil diperbarui!", "success")
                return redirect(url_for('manage_users'))
            except psycopg2.connect.Error as err:
                flash(f"Terjadi kesalahan saat memperbarui pengguna: {err}", "danger")
                conn.rollback()
        else:
            flash("Tidak ada perubahan yang dilakukan.", "info")
            return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user=user)

# Rute Hapus Pengguna (Hanya untuk Admin)
@app.route('/delete_user/<int:id>', methods=['GET'])
@login_required
@admin_required
def delete_user(id):
    # Tidak bisa menghapus akun sendiri
    if session.get('user_id') == id:
        flash("Anda tidak dapat menghapus akun Anda sendiri!", "danger")
        return redirect(url_for('manage_users'))

    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        conn.commit()
        flash("Pengguna berhasil dihapus!", "success")
    except psycopg2.connect.Error as err:
        flash(f"Terjadi kesalahan saat menghapus pengguna: {err}", "danger")
        conn.rollback()
    return redirect(url_for('manage_users'))


# Dashboard dengan chart
@app.route('/dashboard')
@login_required # Terapkan dekorator login_required
def dashboard():
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT COUNT(*) as total FROM aduan")
    total = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM aduan WHERE status = 'Diproses'")
    diproses = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM aduan WHERE status = 'Selesai'")
    selesai = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM aduan WHERE jenis = 'Merah'")
    merah = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM aduan WHERE jenis = 'Kuning'")
    kuning = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM aduan WHERE jenis = 'Hijau'")
    hijau = cursor.fetchone()['total']

    chart_data = {
        'Total': total,
        'Diproses': diproses,
        'Selesai': selesai,
        'Merah': merah,
        'Kuning': kuning,
        'Hijau': hijau
    }

    return render_template('dashboard.html', chart_data=chart_data)

# Lihat & Tambah Aduan
@app.route('/aduan', methods=['GET', 'POST'])
@login_required
def aduan():

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        jenis = request.form['jenis']
        tujuan = request.form['tujuan']
        sumber = request.form['sumber']
        isi = request.form['isi']
        status = request.form['status']
        tindak_lanjut = request.form['tindak_lanjut'] # Pastikan ini ada di form aduan.html
        waktu_respon = request.form['waktu_respon']
        penyelesaian = request.form['penyelesaian']
        
        # --- Penanganan Upload Bukti Awal ---
        file_bukti = request.files.get('bukti')
        filename_bukti = None
        if file_bukti and allowed_file(file_bukti.filename):
            filename_bukti = secure_filename(file_bukti.filename)
            # Simpan sementara sebelum mendapatkan last_id
            file_bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_bukti))
        
        # --- Penanganan Upload Dokumentasi Tindak Lanjut ---
        file_dokumentasi = request.files.get('dokumentasi')
        filename_dokumentasi = None
        if file_dokumentasi and allowed_file(file_dokumentasi.filename):
            filename_dokumentasi = secure_filename(file_dokumentasi.filename)
            # Simpan sementara sebelum mendapatkan last_id
            file_dokumentasi.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_dokumentasi))

        # Simpan data awal ke database, termasuk bukti dan dokumentasi
        cursor.execute(
            "INSERT INTO aduan (tanggal, jenis, tujuan, sumber, isi, status, tindak_lanjut, bukti, dokumentasi, waktu_respon, penyelesaian) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (tanggal, jenis, tujuan, sumber, isi, status, tindak_lanjut, filename_bukti, filename_dokumentasi, waktu_respon, penyelesaian)
        )
        conn.commit() # Commit setelah insert untuk mendapatkan last_id yang benar
        last_id = cursor.lastrowid

        # --- Rename dan Update Bukti Awal dengan ID Aduan ---
        if filename_bukti:
            old_filepath_bukti = os.path.join(app.config['UPLOAD_FOLDER'], filename_bukti)
            new_filename_bukti = f"Bukti_{last_id}{os.path.splitext(filename_bukti)[1]}"
            new_filepath_bukti = os.path.join(app.config['UPLOAD_FOLDER'], new_filename_bukti)
            if os.path.exists(old_filepath_bukti):
                os.rename(old_filepath_bukti, new_filepath_bukti)
                cursor.execute("UPDATE aduan SET bukti=%s WHERE id=%s", (new_filename_bukti, last_id))
                conn.commit() # Commit update bukti

        # --- Rename dan Update Dokumentasi dengan ID Aduan ---
        if filename_dokumentasi:
            old_filepath_doc = os.path.join(app.config['UPLOAD_FOLDER'], filename_dokumentasi)
            new_filename_doc = f"Dokumentasi_{last_id}{os.path.splitext(filename_dokumentasi)[1]}"
            new_filepath_doc = os.path.join(app.config['UPLOAD_FOLDER'], new_filename_doc)
            if os.path.exists(old_filepath_doc):
                os.rename(old_filepath_doc, new_filepath_doc)
                cursor.execute("UPDATE aduan SET dokumentasi=%s WHERE id=%s", (new_filename_doc, last_id))
                conn.commit() # Commit update dokumentasi

        flash("Aduan berhasil ditambahkan!", "success")
        return redirect(url_for('aduan'))

    cursor.execute("SELECT * FROM aduan ORDER BY id DESC")
    data = cursor.fetchall()
    return render_template('aduan.html', aduan=data)


# Edit Aduan
@app.route('/edit_aduan/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_aduan(id):

    cursor.execute("SELECT * FROM aduan WHERE id = %s", (id,))
    data = cursor.fetchone()

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        jenis = request.form['jenis']
        tujuan = request.form['tujuan']
        sumber = request.form['sumber']
        isi = request.form['isi']
        status = request.form['status']
        tindak_lanjut = request.form['tindak_lanjut']
        waktu_respon = request.form['waktu_respon']
        penyelesaian = request.form['penyelesaian']

        update_query_parts = []
        update_values = []

        # Tambahkan field teks yang selalu diupdate
        update_query_parts.append("tanggal=%s")
        update_values.append(tanggal)
        update_query_parts.append("jenis=%s")
        update_values.append(jenis)
        update_query_parts.append("tujuan=%s")
        update_values.append(tujuan)
        update_query_parts.append("sumber=%s")
        update_values.append(sumber)
        update_query_parts.append("isi=%s")
        update_values.append(isi)
        update_query_parts.append("status=%s")
        update_values.append(status)
        update_query_parts.append("tindak_lanjut=%s")
        update_values.append(tindak_lanjut)
        update_query_parts.append("waktu_respon=%s")
        update_values.append(waktu_respon)
        update_query_parts.append("penyelesaian=%s")
        update_values.append(penyelesaian)
        
        # --- Penanganan Update Bukti Awal ---
        file_bukti = request.files.get('bukti')
        if file_bukti and allowed_file(file_bukti.filename):
            # Hapus file lama jika ada
            if data and data['bukti']:
                old_file_path_bukti = os.path.join(app.config['UPLOAD_FOLDER'], data['bukti'])
                if os.path.exists(old_file_path_bukti):
                    os.remove(old_file_path_bukti)
            
            # Simpan file baru
            new_filename_bukti = f"Bukti_{id}{os.path.splitext(secure_filename(file_bukti.filename))[1]}"
            file_bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename_bukti))
            
            update_query_parts.append("bukti=%s")
            update_values.append(new_filename_bukti)
        
        # --- Penanganan Update Dokumentasi Tindak Lanjut ---
        file_dokumentasi = request.files.get('dokumentasi')
        if file_dokumentasi and allowed_file(file_dokumentasi.filename):
            # Hapus file lama jika ada
            if data and data['dokumentasi']: # Memeriksa kolom 'dokumentasi'
                old_file_path_doc = os.path.join(app.config['UPLOAD_FOLDER'], data['dokumentasi'])
                if os.path.exists(old_file_path_doc):
                    os.remove(old_file_path_doc)
            
            # Simpan file baru
            new_filename_doc = f"Dokumentasi_{id}{os.path.splitext(secure_filename(file_dokumentasi.filename))[1]}"
            file_dokumentasi.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename_doc))
            
            update_query_parts.append("dokumentasi=%s")
            update_values.append(new_filename_doc)

        final_update_query = "UPDATE aduan SET " + ", ".join(update_query_parts) + " WHERE id=%s"
        update_values.append(id)

        cursor.execute(final_update_query, tuple(update_values))
        conn.commit()
        flash("Aduan berhasil diedit!", "success")
        return redirect(url_for('reports'))

    return render_template('edit_aduan.html', data=data)


# Hapus Aduan
@app.route('/delete/<int:id>', methods=['GET'])
@login_required
def delete_aduan(id):

    # Ambil nama file bukti dan dokumentasi sebelum hapus
    cursor.execute("SELECT bukti, dokumentasi FROM aduan WHERE id = %s", (id,))
    result = cursor.fetchone()

    if result:
        # Hapus file bukti
        if result['bukti']:
            file_path_bukti = os.path.join(app.config['UPLOAD_FOLDER'], result['bukti'])
            if os.path.exists(file_path_bukti):
                os.remove(file_path_bukti)
        
        # Hapus file dokumentasi
        if result['dokumentasi']:
            file_path_doc = os.path.join(app.config['UPLOAD_FOLDER'], result['dokumentasi'])
            if os.path.exists(file_path_doc):
                os.remove(file_path_doc)

    # Hapus aduan dari database
    cursor.execute("DELETE FROM aduan WHERE id = %s", (id,))
    conn.commit()

    flash("Aduan dan semua file terkait berhasil dihapus!", "success")
    return redirect(url_for('reports'))


# Menu Reports + Filter
@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():

    status = request.args.get('status_aduan', '')
    jenis = request.args.get('jenis_aduan', '')
    tanggal_mulai = request.args.get('tanggal_mulai', '')
    tanggal_akhir = request.args.get('tanggal_akhir', '')
    tujuan = request.args.get('tujuan_aduan', '')
    sumber = request.args.get('sumber_aduan', '')

    query = "SELECT * FROM aduan WHERE 1=1"
    values = []

    if status:
        query += " AND status = %s"
        values.append(status)
    if jenis:
        query += " AND jenis = %s"
        values.append(jenis)
    if sumber:
        query += " AND sumber = %s"
        values.append(sumber)
    if tujuan:
        query += " AND tujuan LIKE %s"
        values.append(f"%{tujuan}%")

    tanggal_mulai = tanggal_mulai if tanggal_mulai else ''
    tanggal_akhir = tanggal_akhir if tanggal_akhir else ''

    if tanggal_mulai and tanggal_akhir:
        query += " AND tanggal BETWEEN %s AND %s"
        values.append(tanggal_mulai)
        values.append(tanggal_akhir)
    elif tanggal_mulai:
        query += " AND tanggal >= %s"
        values.append(tanggal_mulai)
    elif tanggal_akhir:
        query += " AND tanggal <= %s"
        values.append(tanggal_akhir)

    query += " ORDER BY id DESC"

    cursor.execute(query, tuple(values))
    data = cursor.fetchall()

    return render_template('report.html', aduan=data, status_aduan=status, jenis_aduan=jenis, tanggal_mulai=tanggal_mulai, tanggal_akhir=tanggal_akhir, tujuan_aduan=tujuan, sumber_aduan=sumber)


# Cetak PDF
@app.route('/print_pdf')
@login_required
def print_pdf():
    
    status = request.args.get('status', '')
    jenis = request.args.get('jenis', '')
    tujuan = request.args.get('tujuan', '')
    sumber = request.args.get('sumber', '')
    tanggal_mulai = request.args.get('tanggal_mulai', '')
    tanggal_akhir = request.args.get('tanggal_akhir', '')

    query = "SELECT * FROM aduan WHERE 1=1"
    values = []
    
    if status:
        query += " AND status = %s"
        values.append(status)
    if jenis:
        query += " AND jenis = %s"
        values.append(jenis)
    if tujuan:
        query += " AND tujuan LIKE %s"
        values.append(f"%{tujuan}%")
    if sumber:
        query += " AND sumber = %s"
        values.append(sumber)
    
    tanggal_mulai = tanggal_mulai if tanggal_mulai else ''
    tanggal_akhir = tanggal_akhir if tanggal_akhir else ''

    if tanggal_mulai and tanggal_akhir:
        query += " AND tanggal BETWEEN %s AND %s"
        values.extend([tanggal_mulai, tanggal_akhir])
    elif tanggal_mulai:
        query += " AND tanggal >= %s"
        values.append(tanggal_mulai)
    elif tanggal_akhir:
        query += " AND tanggal <= %s"
        values.append(tanggal_akhir)

    query += " ORDER BY id DESC"

    # print("Query:", query) # Baris debug, bisa dihapus setelah testing
    # print("Values:", tuple(values)) # Baris debug, bisa dihapus setelah testing
    cursor.execute(query, tuple(values))
    data = cursor.fetchall()

    return render_template('print.html', aduan_list=data)


if __name__ == '__main__':
    # Pastikan untuk membuat folder 'static/uploads' jika belum ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)