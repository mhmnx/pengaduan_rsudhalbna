# Gunakan base image Python resmi
FROM python:3.10-slim



# Set direktori kerja di dalam container
WORKDIR /app

# Salin file requirements dan install dependensi
COPY requirements.txt .
RUN pip install -r requirements.txt

# Salin seluruh kode aplikasi ke dalam direktori kerja
COPY . .

# Set environment variable untuk Flask (opsional, tapi baik)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Jalankan aplikasi menggunakan Gunicorn (server WSGI production)
# Gunicorn akan berjalan di port 5000 di dalam container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]