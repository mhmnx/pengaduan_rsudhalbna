# app.py
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import mysql.connector
from config import Config
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = ''
app.config.from_object(Config)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# Koneksi Database
conn = mysql.connector.connect(
    host='MHMNX.mysql.pythonanywhere-services.com',
    user='MHMNX',
    password='Mamangganteng13@',
    database='MHMNX$db'
)
cursor = conn.cursor(dictionary=True)

# Login Admin
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# Dashboard dengan chart
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    cursor = conn.cursor(dictionary=True)

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
def aduan():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        jenis = request.form['jenis']
        tujuan = request.form['tujuan']
        sumber = request.form['sumber']
        isi = request.form['isi']
        status = request.form['status']

        file = request.files['bukti']
        filename = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Simpan data awal
        cursor.execute(
        "INSERT INTO aduan (tanggal, jenis, tujuan, sumber, isi, status, bukti) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (tanggal, jenis, tujuan, sumber, isi, status, filename)
    )
        last_id = cursor.lastrowid

        # Rename file setelah tahu ID-nya
        if filename:
            new_filename = f"Bukti_{last_id}" + os.path.splitext(filename)[1]
            os.rename(
                os.path.join(app.config['UPLOAD_FOLDER'], filename),
                os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            )
            cursor.execute("UPDATE aduan SET bukti=%s WHERE id=%s", (new_filename, last_id))

        conn.commit()
        flash("Aduan berhasil ditambahkan!", "success")
        return redirect(url_for('aduan'))

    cursor.execute("SELECT * FROM aduan ORDER BY id DESC")
    data = cursor.fetchall()
    return render_template('aduan.html', aduan=data)


# Edit Aduan
@app.route('/edit_aduan/<int:id>', methods=['GET', 'POST'])
def edit_aduan(id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        jenis = request.form['jenis']
        tujuan = request.form['tujuan']
        isi = request.form['isi']
        status = request.form['status']
        cursor.execute("UPDATE aduan SET tanggal=%s, jenis=%s, tujuan=%s, isi=%s, status=%s WHERE id=%s",
                       (tanggal, jenis, tujuan, isi, status, id))
        conn.commit()
        flash("Aduan berhasil diedit!", "success")
        return redirect(url_for('reports'))

    cursor.execute("SELECT * FROM aduan WHERE id = %s", (id,))
    data = cursor.fetchone()
    return render_template('edit_aduan.html', data=data)

# Hapus Aduan
@app.route('/delete/<int:id>', methods=['GET'])
def delete_aduan(id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    # Ambil nama file bukti sebelum hapus
    cursor.execute("SELECT bukti FROM aduan WHERE id = %s", (id,))
    result = cursor.fetchone()

    if result and result['bukti']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], result['bukti'])
        if os.path.exists(file_path):
            os.remove(file_path)

    # Hapus aduan dari database
    cursor.execute("DELETE FROM aduan WHERE id = %s", (id,))
    conn.commit()

    flash("Aduan dan file bukti berhasil dihapus!", "success")
    return redirect(url_for('reports'))



# Menu Reports + Filter
from datetime import datetime, timedelta

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    if 'admin' not in session:
        return redirect(url_for('login'))

    status = request.args.get('status_aduan')
    jenis = request.args.get('jenis_aduan')
    tanggal_mulai = request.args.get('tanggal_mulai')
    tanggal_akhir = request.args.get('tanggal_akhir')
    tujuan = request.args.get('tujuan_aduan')
    sumber = request.args.get('sumber_aduan')

    # Mulai dengan query dasar
    query = "SELECT * FROM aduan WHERE 1=1"
    values = []

    # Menambahkan kondisi filter sesuai dengan parameter
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

    # Menambahkan kondisi filter berdasarkan rentang tanggal
    if tanggal_mulai and tanggal_akhir:
        query += " AND tanggal BETWEEN %s AND %s"
        values.append(tanggal_mulai)
        values.append(tanggal_akhir)

    # Eksekusi query dan ambil data
    cursor.execute(query, tuple(values))
    data = cursor.fetchall()

    return render_template('report.html', aduan=data, status_aduan=status, jenis_aduan=jenis, tanggal_mulai=tanggal_mulai, tanggal_akhir=tanggal_akhir, tujuan_aduan=tujuan, sumber_aduan=sumber)


# Cetak PDF
@app.route('/print_pdf')
def print_pdf():
    if 'admin' not in session:
        return redirect(url_for('login'))

    # Mengambil parameter filter dari URL
    status = request.args.get('status')
    jenis = request.args.get('jenis')
    tujuan = request.args.get('tujuan')
    sumber = request.args.get('sumber')
    tanggal_mulai = request.args.get('tanggal_mulai')
    tanggal_akhir = request.args.get('tanggal_akhir')

    query = "SELECT * FROM aduan WHERE 1=1"
    values = []

    if status:
        query += " AND status = %s"
        values.append(status)
    if jenis:
        query += " AND jenis = %s"
        values.append(jenis)
    if tujuan:
        query += " AND tujuan = %s"
        values.append(tujuan)
    if sumber:
        query += " AND sumber = %s"
        values.append(sumber)
    if tanggal_mulai and tanggal_akhir:
        query += " AND tanggal BETWEEN %s AND %s"
        values.extend([tanggal_mulai, tanggal_akhir])
    elif tanggal_mulai:
        query += " AND tanggal >= %s"
        values.append(tanggal_mulai)
    elif tanggal_akhir:
        query += " AND tanggal <= %s"
        values.append(tanggal_akhir)

    cursor.execute(query, tuple(values))
    data = cursor.fetchall()

    # Kirim data ke halaman print.html
    return render_template('print.html', aduan_list=data)
