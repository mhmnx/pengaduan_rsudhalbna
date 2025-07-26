from werkzeug.security import generate_password_hash

# Ganti 'password_admin_baru' dengan password yang Anda inginkan
password_polos = 'admin'

# Buat hash dengan metode yang sama seperti di app.py
hash_password = generate_password_hash(password_polos)

print("--- HASH PASSWORD ---")
print(hash_password)
