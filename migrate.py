import psycopg2
from config import Config

# SQL untuk membuat skema database di PostgreSQL.
# Perintah ini akan menghapus tabel lama (jika ada) dan membuatnya kembali.
MIGRATION_SQL = """
-- Menghapus tabel jika sudah ada agar migrasi bisa diulang
DROP TABLE IF EXISTS aduan;
DROP TABLE IF EXISTS users;


-- 1. Membuat tabel 'users'
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user'
);

COMMENT ON TABLE users IS 'Menyimpan data kredensial dan peran pengguna.';


-- 2. Membuat tabel 'aduan'
CREATE TABLE aduan (
    id SERIAL PRIMARY KEY,
    tanggal DATE NOT NULL,
    jenis VARCHAR(50),
    tujuan VARCHAR(255),
    sumber VARCHAR(255),
    isi TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    tindak_lanjut TEXT,
    bukti VARCHAR(255),
    dokumentasi VARCHAR(255),
    waktu_respon DATE,
    penyelesaian DATE
);

COMMENT ON TABLE aduan IS 'Menyimpan semua data terkait pengaduan.';


-- 3. (PENTING) Menambahkan satu pengguna admin default
-- Hash ini adalah untuk password 'admin'
INSERT INTO users (username, password, role) VALUES
('admin', 'scrypt:32768:8:1$DowKJ1xrmVinO3S2$df24e519fc8b9ccc0a0a5399cb2b0c56e6773d6038ed6483b98c645ee11117beb72d6c6ece518939b75a1be03132b392949bcc1341c28ac164770b0dc97ddca0', 'admin');

"""

def run_migration():
    """
    Menjalankan proses migrasi dengan menghubungkan ke DB PostgreSQL
    dan mengeksekusi perintah SQL.
    """
    conn = None
    try:
        # Menggunakan kredensial dari file config.py
        print("Mencoba terhubung ke database PostgreSQL...")
        conn = psycopg2.connect(
            host=Config.HOST,      # Pastikan nama variabel di config.py sesuai
            database=Config.DATABASE, # atau ganti dengan kredensial Postgres Anda
            user=Config.USER,
            password=Config.PASSWORD
        )
        cursor = conn.cursor()
        print("✅ Koneksi berhasil.")

        # Menjalankan skrip migrasi SQL
        print("⚙️  Menjalankan skrip migrasi...")
        cursor.execute(MIGRATION_SQL)

        # Menyimpan perubahan ke database
        conn.commit()
        print("🎉 Migrasi berhasil! Tabel 'users' dan 'aduan' telah dibuat di PostgreSQL.")

    except psycopg2.Error as e:
        print(f"❌ Terjadi kesalahan saat migrasi: {e}")
        if conn:
            # Membatalkan semua perubahan jika terjadi error
            conn.rollback()

    finally:
        # Selalu tutup koneksi setelah selesai
        if conn:
            cursor.close()
            conn.close()
            print("🔌 Koneksi ke database ditutup.")

if __name__ == '__main__':
    run_migration()