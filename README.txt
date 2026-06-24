# 📊 Prediksi Wisatawan

 🔗[Prediksi Wisatawan](https://wisatawan.pythonanywhere.com/)

Projek ini dibangun untuk memprediksi volume kunjungan wisatawan dengan menggunakan pendekatan **Regresi Linear**. Proyek ini menganalisis tren dari data historis untuk mengestimasi jumlah kunjungan, yang berfungsi sebagai instrumen pendukung perencanaan strategis sektor pariwisata.

## 📈 Sumber Data

* **Data:** Statistik kunjungan wisatawan dari **Badan Pusat Statistik (BPS)**.
* **Rentang Waktu:** 2022 – 2026.
* **Karakteristik:** Data mencakup pola kunjungan tahunan yang digunakan untuk melatih model regresi dalam memproyeksikan tren ke depan.
* **Link:** [Data Kunjungan Wisatawan - BPS](https://www.bps.go.id/id/statistics-table/2/MTQ3MCMy/jumlah-kunjungan-wisatawan-mancanegara-per-bulan-menurut-paspor-yang-dipegang-.html)

## 🛠 Tech Stack

* **Bahasa:** Python
* **Library:** `pandas`, `numpy`, `scikit-learn` (implementasi regresi), `matplotlib`/`seaborn` (visualisasi).

## 🧠 Pendekatan Teknis

1. **Data Preprocessing:** Pembersihan data BPS, penanganan *outliers*, dan normalisasi format data untuk rentang 2022-2026.
2. **EDA:** Identifikasi pola musiman dan tren pertumbuhan wisatawan dari data BPS.
3. **Modeling:** Implementasi **Regresi Linear** untuk memetakan hubungan antara variabel waktu dan volume kunjungan.
4. **Evaluation:** Validasi model menggunakan MSE dan R-squared ($R^2$) untuk mengukur akurasi garis tren prediksi.

## ⚙️ Cara Menjalankan

1. Clone repositori:
```bash
git clone https://github.com/MochZidann/prediksi-wisatawan.git

```


2. Install dependensi:
```bash
pip install -r requirements.txt

```

3. Eksekusi script/notebook untuk melihat hasil prediksi berbasis data BPS 2022-2026.

---
