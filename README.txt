VISITOR//PULSE - UAS DATA SCIENCE REGRESI

Isi project:
- app.py                         : Backend Flask dan perhitungan regresi manual OLS
- data/dataset_wisatawan_2022_2026.csv
- templates/index.html           : Tampilan web
- static/css/style.css           : UI bawaan + tambahan navbar/model/kode berwarna
- static/js/dashboard.js         : Interaksi dashboard, dropdown model, chart, forecast, dan syntax highlight
- static/vendor/plotly.min.js    : Library chart offline
- requirements.txt
- pythonanywhere_wsgi.py         : Isi WSGI yang bisa dicopy ke file WSGI PythonAnywhere
- wsgi.py                        : Entry point WSGI cadangan
- setup_and_run_windows.bat      : Setup pertama kali + menjalankan web di Windows
- run_windows.bat                : Menjalankan web di Windows setelah setup selesai

Cara run di Windows:
1. Extract zip ini.
2. Klik 2x setup_and_run_windows.bat.
3. Tunggu install dependency selesai.
4. Buka browser: http://127.0.0.1:5000

Cara deploy ke PythonAnywhere:
1. Upload/extract folder project ke PythonAnywhere, misalnya:
   /home/USERNAME/visitor_pulse_uas_ready
2. Buka Bash Console PythonAnywhere.
3. Masuk ke folder project:
   cd /home/USERNAME/visitor_pulse_uas_ready
4. Buat virtualenv sesuai versi Python yang dipilih pada Web tab:
   mkvirtualenv visitorpulse --python=/usr/bin/python3.10
5. Install dependency:
   pip install -r requirements.txt
6. Buka tab Web > Add a new web app > Manual configuration > pilih Python yang sama.
7. Isi bagian Virtualenv dengan:
   /home/USERNAME/.virtualenvs/visitorpulse
8. Buka file WSGI dari tab Web, lalu isi dengan isi file pythonanywhere_wsgi.py.
9. Sesuaikan baris project_home jika nama folder berbeda:
   project_home = Path('/home/USERNAME/visitor_pulse_uas_ready')
10. Di Static files, tambahkan mapping opsional:
    URL: /static/
    Directory: /home/USERNAME/visitor_pulse_uas_ready/static/
11. Klik Reload pada tab Web.

Fitur yang sudah dimasukkan:
1. Dropdown model regresi:
   - Regresi Linear Sederhana
   - Regresi Polinomial
   - Regresi Linear Berganda
2. Filter periode aktual:
   - Semua tahun
   - 2022, 2023, 2024, 2025, 2026
3. Pilihan tahun prediksi:
   - Minimal 2026
   - Maksimal 2100
4. Prediksi 2026 otomatis Mei-Desember karena data aktual 2026 tersedia sampai April.
5. Jika memilih 2027-2100, grafik dan tabel prediksi dibuat berurutan dari Mei 2026 sampai Desember tahun pilihan.
6. Navbar interaktif dengan scroll halus.
7. Bagian kode di web menampilkan fungsi prediksi tanpa komentar tanda pagar dan tampil berwarna seperti editor kode.
8. File berantakan seperti .venv, notebook, cache, zip lama, dan data lama tidak dimasukkan.

Catatan model:
- Perhitungan regresi memakai rumus manual OLS: beta = (X^T X)^-1 X^T y.
- Evaluasi kronologis: latih 2022-2024, uji 2025.
- Model final memakai data aktual tersedia 2022-April 2026.

Catatan periode prediksi:
- Jika tahun prediksi = 2026, sistem menampilkan prediksi Mei sampai Desember saja.
- Jika tahun prediksi > 2026, misalnya 2027, 2030, atau tahun lain sampai 2100, sistem menampilkan titik prediksi lengkap pada seluruh rentang: Mei-Desember 2026, lalu Januari-Desember untuk setiap tahun sampai tahun pilihan.
