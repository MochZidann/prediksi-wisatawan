from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dataset_wisatawan_2022_2026.csv"

app = Flask(__name__)

BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

REGION_LABELS = {
    "A S E A N": "ASEAN",
    "TOTAL ASIA (Excl.ASEAN)": "Asia non-ASEAN",
    "TOTAL MIDDLE EAST": "Timur Tengah",
    "TOTAL EUROPE": "Eropa",
    "TOTAL AMERICA": "Amerika",
    "TOTAL OCEANIA": "Oseania",
    "TOTAL AFRICA": "Afrika",
}

MODEL_OPTIONS = {
    "linear": {
        "label": "Regresi Linear Sederhana",
        "short": "Linear",
        "description": "Menggunakan satu fitur utama, yaitu urutan waktu bulanan, untuk membaca tren naik/turun.",
    },
    "polynomial": {
        "label": "Regresi Polinomial",
        "short": "Polinomial",
        "description": "Menambahkan fitur kuadrat dari tren waktu agar model dapat menangkap pola melengkung.",
    },
    "multiple": {
        "label": "Regresi Linear Berganda",
        "short": "Berganda",
        "description": "Menggunakan tren waktu, nomor bulan, dan fitur musiman sin/cos untuk membaca pola bulanan.",
    },
}

FEATURE_LABELS = {
    "intercept": "Intercept",
    "tren_bulan": "Tren bulanan",
    "tren_bulan_kuadrat": "Tren bulanan kuadrat",
    "nomor_bulan": "Nomor bulan",
    "sin_musiman": "Sin musiman",
    "cos_musiman": "Cos musiman",
    "jumlah_kunjungan": "Jumlah kunjungan",
}


def clean_number(value):
    if value is None or pd.isna(value):
        return None
    return float(value)


def int_or_none(value):
    if value is None or pd.isna(value):
        return None
    return int(round(float(value)))


def clamp_prediction(value):
    if value is None or pd.isna(value) or np.isinf(value):
        return 0.0
    return float(max(0, value))


@lru_cache(maxsize=1)
def load_data():
    data = pd.read_csv(DATA_PATH)
    data.columns = data.columns.str.strip().str.lower()

    for column in ["bulan", "paspor_atau_wilayah", "kategori", "status_data"]:
        data[column] = data[column].astype("string").str.strip()

    data["tanggal"] = pd.to_datetime(data["tanggal"], errors="coerce")
    data["tahun"] = pd.to_numeric(data["tahun"], errors="coerce")
    data["nomor_bulan"] = pd.to_numeric(data["nomor_bulan"], errors="coerce")
    data["jumlah_kunjungan"] = pd.to_numeric(data["jumlah_kunjungan"], errors="coerce")
    data.loc[data["jumlah_kunjungan"] < 0, "jumlah_kunjungan"] = np.nan

    data = data.dropna(subset=["tanggal", "tahun", "nomor_bulan", "paspor_atau_wilayah"])
    data = data[data["tahun"].between(2022, 2026)].copy()
    data = data[data["nomor_bulan"].between(1, 12)].copy()
    data["tahun"] = data["tahun"].astype(int)
    data["nomor_bulan"] = data["nomor_bulan"].astype(int)
    data["status_data"] = data["status_data"].str.lower()

    data = data.drop_duplicates(
        subset=["tanggal", "paspor_atau_wilayah", "kategori"],
        keep="last",
    )
    return data.sort_values(["tanggal", "kategori", "paspor_atau_wilayah"]).reset_index(drop=True)


def month_index(years, months):
    years = np.asarray(years, dtype=float)
    months = np.asarray(months, dtype=float)
    return ((years - 2022) * 12) + months


def build_feature_matrix(model_type, years, months):
    t = month_index(years, months)
    months_array = np.asarray(months, dtype=float)

    features = {"intercept": np.ones_like(t), "tren_bulan": t}

    if model_type == "polynomial":
        features["tren_bulan_kuadrat"] = t ** 2
    elif model_type == "multiple":
        features["nomor_bulan"] = months_array
        features["sin_musiman"] = np.sin(2 * np.pi * months_array / 12)
        features["cos_musiman"] = np.cos(2 * np.pi * months_array / 12)

    feature_names = list(features.keys())
    matrix = np.column_stack([features[name] for name in feature_names])
    return matrix, feature_names


def fit_manual_ols(X, y):
    """Menghitung beta regresi manual: beta = (X^T X)^-1 X^T y."""
    return np.linalg.pinv(X.T @ X) @ X.T @ y


def predict_with_beta(beta, X):
    return X @ beta


def metric_rows(y_true, y_pred):
    residual = y_true - y_pred
    mae = np.mean(np.abs(residual))
    rmse = np.sqrt(np.mean(residual ** 2))
    ss_res = np.sum(residual ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot else 0
    return float(mae), float(rmse), float(r2)


def get_model_data(entity):
    data = load_data()
    model_data = data[
        (data["paspor_atau_wilayah"] == entity)
        & (data["tahun"].between(2022, 2026))
        & (data["status_data"] == "tersedia")
    ].sort_values(["tahun", "nomor_bulan"]).copy()

    missing_before = int(model_data["jumlah_kunjungan"].isna().sum())
    if missing_before:
        month_median = model_data.groupby("nomor_bulan")["jumlah_kunjungan"].transform("median")
        entity_median = model_data["jumlah_kunjungan"].median()
        model_data["jumlah_kunjungan"] = (
            model_data["jumlah_kunjungan"].fillna(month_median).fillna(entity_median)
        )

    model_data = model_data.dropna(subset=["jumlah_kunjungan"]).reset_index(drop=True)
    return model_data, missing_before


def forecast_periods_until_year(prediction_year):
    """
    Membuat titik prediksi berurutan dari bulan pertama setelah data aktual.

    Data aktual 2026 tersedia sampai April, sehingga:
    - Jika tahun prediksi 2026: titik forecast = Mei-Desember 2026.
    - Jika tahun prediksi > 2026: titik forecast = Mei-Desember 2026,
      lalu Januari-Desember untuk semua tahun berikutnya sampai tahun pilihan.

    Contoh tahun 2030:
    Mei-Des 2026 + Jan-Des 2027 + Jan-Des 2028 + Jan-Des 2029 + Jan-Des 2030.
    """
    prediction_year = int(prediction_year)
    years = []
    months = []

    for year in range(2026, prediction_year + 1):
        start_month = 5 if year == 2026 else 1
        for month in range(start_month, 13):
            years.append(year)
            months.append(month)

    return np.asarray(years, dtype=int), np.asarray(months, dtype=int)


def forecast_period_label(prediction_year):
    if int(prediction_year) == 2026:
        return "Mei-Desember 2026"
    return f"Mei 2026-Desember {int(prediction_year)}"


def make_formula(beta, feature_names):
    parts = [f"Y = {beta[0]:,.2f}"]
    for name, value in zip(feature_names[1:], beta[1:]):
        sign = "+" if value >= 0 else "-"
        parts.append(f" {sign} {abs(value):,.4f}×{FEATURE_LABELS.get(name, name)}")
    return "".join(parts)


def make_code_snippet(model_type, beta, feature_names):
    rounded = [round(float(v), 6) for v in beta]
    if model_type == "linear":
        feature_code = "X = [1, t]"
    elif model_type == "polynomial":
        feature_code = "X = [1, t, t**2]"
    else:
        feature_code = (
            "X = [1, t, bulan, "
            "sin(2*pi*bulan/12), cos(2*pi*bulan/12)]"
        )

    model_label = MODEL_OPTIONS[model_type]["label"]
    return f'''judul_model = "{model_label}"
from math import sin, cos, pi

beta = {rounded}
fitur = {feature_names}

def prediksi_kunjungan(tahun, bulan):
    t = ((tahun - 2022) * 12) + bulan
    {feature_code}
    y_pred = sum(b * x for b, x in zip(beta, X))
    return max(0, round(y_pred))

def bulan_forecast_sampai(tahun_tujuan):
    periode = []
    for tahun in range(2026, tahun_tujuan + 1):
        bulan_awal = 5 if tahun == 2026 else 1
        for bulan in range(bulan_awal, 13):
            periode.append((tahun, bulan))
    return periode

def prediksi_rentang(tahun_tujuan):
    return [
        {{
            "tahun": tahun,
            "bulan": bulan,
            "prediksi": prediksi_kunjungan(tahun, bulan)
        }}
        for tahun, bulan in bulan_forecast_sampai(tahun_tujuan)
    ]

hasil_2026 = prediksi_rentang(2026)
hasil_2030 = prediksi_rentang(2030)
'''


def regression_result(entity, model_type="linear", prediction_year=2026):
    model_type = model_type if model_type in MODEL_OPTIONS else "linear"
    prediction_year = int(prediction_year) if str(prediction_year).isdigit() else 2026
    prediction_year = min(max(prediction_year, 2026), 2100)

    model_data, imputed_count = get_model_data(entity)
    if len(model_data) < 18:
        return {
            "available": False,
            "message": "Data tidak cukup untuk membentuk model regresi.",
            "model_type": model_type,
            "model_label": MODEL_OPTIONS[model_type]["label"],
        }

    y_all = model_data["jumlah_kunjungan"].to_numpy(dtype=float)
    if np.allclose(y_all, y_all[0]):
        return {
            "available": False,
            "message": "Variasi data terlalu rendah untuk membentuk model regresi.",
            "model_type": model_type,
            "model_label": MODEL_OPTIONS[model_type]["label"],
        }

    # Evaluasi kronologis: latih 2022-2024, uji 2025.
    train_mask = model_data["tahun"] <= 2024
    test_mask = model_data["tahun"] == 2025
    if train_mask.sum() < 12 or test_mask.sum() < 4:
        return {
            "available": False,
            "message": "Data latih atau data uji kronologis tidak cukup.",
            "model_type": model_type,
            "model_label": MODEL_OPTIONS[model_type]["label"],
        }

    X_train, train_features = build_feature_matrix(
        model_type,
        model_data.loc[train_mask, "tahun"],
        model_data.loc[train_mask, "nomor_bulan"],
    )
    y_train = model_data.loc[train_mask, "jumlah_kunjungan"].to_numpy(dtype=float)
    X_test, _ = build_feature_matrix(
        model_type,
        model_data.loc[test_mask, "tahun"],
        model_data.loc[test_mask, "nomor_bulan"],
    )
    y_test = model_data.loc[test_mask, "jumlah_kunjungan"].to_numpy(dtype=float)

    eval_beta = fit_manual_ols(X_train, y_train)
    y_pred_test = np.maximum(0, predict_with_beta(eval_beta, X_test))
    mae, rmse, r2 = metric_rows(y_test, y_pred_test)

    # Model final menggunakan seluruh aktual tersedia 2022-April 2026.
    X_all, feature_names = build_feature_matrix(
        model_type,
        model_data["tahun"],
        model_data["nomor_bulan"],
    )
    beta = fit_manual_ols(X_all, y_all)
    fitted = np.maximum(0, predict_with_beta(beta, X_all))
    residuals = y_all - fitted
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    margin = 1.28 * residual_std

    forecast_years, forecast_months = forecast_periods_until_year(prediction_year)
    X_forecast, _ = build_feature_matrix(model_type, forecast_years, forecast_months)
    forecast_values = np.maximum(0, predict_with_beta(beta, X_forecast))

    forecast_rows = []
    for year, month, prediction in zip(forecast_years, forecast_months, forecast_values):
        forecast_rows.append({
            "tahun": int(year),
            "nomor_bulan": int(month),
            "bulan": BULAN[int(month) - 1],
            "tanggal": f"{int(year)}-{int(month):02d}-01",
            "prediksi": int(round(clamp_prediction(prediction))),
            "batas_bawah": int(round(max(0, prediction - margin))),
            "batas_atas": int(round(max(0, prediction + margin))),
        })

    fit_rows = []
    for (_, row), fitted_value in zip(model_data.iterrows(), fitted):
        fit_rows.append({
            "tahun": int(row["tahun"]),
            "nomor_bulan": int(row["nomor_bulan"]),
            "bulan": BULAN[int(row["nomor_bulan"]) - 1],
            "tanggal": row["tanggal"].strftime("%Y-%m-%d"),
            "aktual": int(round(row["jumlah_kunjungan"])),
            "fitted": int(round(clamp_prediction(fitted_value))),
        })

    data = load_data()
    series_data = data[
        (data["paspor_atau_wilayah"] == entity)
        & (data["tahun"].between(2022, 2026))
        & (data["status_data"] == "tersedia")
        & data["jumlah_kunjungan"].notna()
    ].sort_values(["tahun", "nomor_bulan"])
    series_rows = []
    for _, row in series_data.iterrows():
        series_rows.append({
            "tahun": int(row["tahun"]),
            "nomor_bulan": int(row["nomor_bulan"]),
            "bulan": BULAN[int(row["nomor_bulan"]) - 1],
            "tanggal": row["tanggal"].strftime("%Y-%m-%d"),
            "aktual": int(round(row["jumlah_kunjungan"])),
        })

    coefficient_rows = []
    for name, value in zip(feature_names, beta):
        coefficient_rows.append({
            "feature": FEATURE_LABELS.get(name, name),
            "value": clean_number(value),
        })

    corr_source = pd.DataFrame({
        name: X_all[:, idx]
        for idx, name in enumerate(feature_names)
        if name != "intercept"
    })
    corr_source["jumlah_kunjungan"] = y_all
    corr = corr_source.corr(numeric_only=True).fillna(0)
    corr_labels = [FEATURE_LABELS.get(column, column) for column in corr.columns]

    first_year = int(forecast_years[0])
    first_month = int(forecast_months[0])
    X_example, _ = build_feature_matrix(model_type, [first_year], [first_month])
    example_terms = []
    for name, beta_value, feature_value in zip(feature_names, beta, X_example[0]):
        example_terms.append({
            "feature": FEATURE_LABELS.get(name, name),
            "beta": clean_number(beta_value),
            "x": clean_number(feature_value),
            "hasil": clean_number(beta_value * feature_value),
        })

    return {
        "available": True,
        "model_type": model_type,
        "model_label": MODEL_OPTIONS[model_type]["label"],
        "model_short": MODEL_OPTIONS[model_type]["short"],
        "model_description": MODEL_OPTIONS[model_type]["description"],
        "training_period": "2022-April 2026",
        "evaluation_method": "latih 2022-2024 dan uji kronologis 2025",
        "forecast_period": (
            forecast_period_label(prediction_year)
        ),
        "prediction_year": int(prediction_year),
        "preprocessing": {
            "imputed_training_values": imputed_count,
            "structural_gaps_excluded": True,
        },
        "mae": clean_number(mae),
        "rmse": clean_number(rmse),
        "r2": clean_number(r2),
        "formula": make_formula(beta, feature_names),
        "coefficients": coefficient_rows,
        "correlation": {
            "labels": corr_labels,
            "values": [[clean_number(value) for value in row] for row in corr.to_numpy()],
        },
        "series": series_rows,
        "fit": fit_rows,
        "forecast": forecast_rows,
        "code_snippet": make_code_snippet(model_type, beta, feature_names),
        "example_calculation": {
            "title": f"Contoh hitung {BULAN[first_month - 1]} {first_year}",
            "terms": example_terms,
            "result": forecast_rows[0]["prediksi"] if forecast_rows else None,
        },
    }


def period_data(entity, selected_year):
    data = load_data()
    series = data[data["paspor_atau_wilayah"] == entity].copy()
    if selected_year != "all":
        series = series[series["tahun"] == int(selected_year)]
    return series.sort_values("tanggal")


def same_period_yoy(entity, selected_year):
    data = load_data()
    entity_data = data[
        (data["paspor_atau_wilayah"] == entity)
        & data["jumlah_kunjungan"].notna()
    ].copy()

    if entity_data.empty:
        return None, "YoY"

    if selected_year == "all":
        current_year = int(entity_data["tahun"].max())
    else:
        current_year = int(selected_year)

    current = entity_data[entity_data["tahun"] == current_year]
    if current.empty:
        return None, f"YoY {current_year}"

    max_month = int(current["nomor_bulan"].max())
    previous = entity_data[
        (entity_data["tahun"] == current_year - 1)
        & (entity_data["nomor_bulan"] <= max_month)
    ]
    current = current[current["nomor_bulan"] <= max_month]

    if previous.empty or previous["jumlah_kunjungan"].sum() == 0:
        return None, f"YoY {current_year}"

    growth = ((current["jumlah_kunjungan"].sum() - previous["jumlah_kunjungan"].sum()) / previous["jumlah_kunjungan"].sum() * 100)
    period_label = f"Jan–{BULAN[max_month - 1]} {current_year}" if max_month < 12 else str(current_year)
    return float(growth), f"YoY {period_label}"


def annual_series(entity):
    data = load_data()
    series = data[
        (data["paspor_atau_wilayah"] == entity)
        & data["jumlah_kunjungan"].notna()
    ]
    annual = (
        series.groupby("tahun", as_index=False)
        .agg(total=("jumlah_kunjungan", "sum"), bulan_tersedia=("nomor_bulan", "nunique"))
        .sort_values("tahun")
    )
    return annual


def build_insights(entity, selected_year, filtered, model, top_passports):
    available = filtered[filtered["jumlah_kunjungan"].notna()]
    annual = annual_series(entity)
    insights = []

    if model.get("available"):
        forecast_values = [row["prediksi"] for row in model["forecast"]]
        avg_forecast = float(np.mean(forecast_values)) if forecast_values else 0
        first_forecast = forecast_values[0] if forecast_values else 0
        last_forecast = forecast_values[-1] if forecast_values else 0
        trend_delta = ((last_forecast - first_forecast) / first_forecast * 100) if first_forecast else 0
        direction = "naik" if trend_delta >= 0 else "turun"
        lower_bound = min(row["batas_bawah"] for row in model["forecast"])
        upper_bound = max(row["batas_atas"] for row in model["forecast"])

        insights.append({
            "tag": model["model_short"].upper(),
            "title": f"{avg_forecast:,.0f}/bulan",
            "text": f"Rata-rata prediksi {model['forecast_period']} memakai {model['model_label']}.",
        })
        insights.append({
            "tag": "ARAH MODEL",
            "title": f"{trend_delta:+.2f}%",
            "text": f"Perubahan bersih {direction} dari awal ke akhir periode prediksi.",
        })
        insights.append({
            "tag": "RENTANG",
            "title": f"{lower_bound:,.0f}-{upper_bound:,.0f}",
            "text": "Rentang estimasi dihitung dari sebaran residual model final.",
        })
        insights.append({
            "tag": "EVALUASI",
            "title": f"R² {model['r2']:.4f}",
            "text": f"Galat uji 2025: MAE {model['mae']:,.0f} dan RMSE {model['rmse']:,.0f} kunjungan.",
        })

        reference = annual[(annual["tahun"] == 2025) & (annual["bulan_tersedia"] == 12)]
        if not reference.empty and float(reference.iloc[0]["total"]) > 0:
            avg_2025 = float(reference.iloc[0]["total"]) / 12
            forecast_growth = (avg_forecast - avg_2025) / avg_2025 * 100
            insights.append({
                "tag": "VS 2025",
                "title": f"{forecast_growth:+.2f}%",
                "text": "Perbandingan rata-rata forecast terhadap rata-rata bulanan 2025.",
            })

    if not available.empty:
        peak = available.loc[available["jumlah_kunjungan"].idxmax()]
        insights.append({
            "tag": "PUNCAK",
            "title": f"{BULAN[int(peak['nomor_bulan']) - 1]} {int(peak['tahun'])}",
            "text": f"Periode tertinggi untuk {entity} mencapai {int(peak['jumlah_kunjungan']):,} kunjungan.",
        })

    complete_annual = annual[annual["bulan_tersedia"] == 12]
    if not complete_annual.empty:
        best = complete_annual.loc[complete_annual["total"].idxmax()]
        insights.append({
            "tag": "TAHUN TERKUAT",
            "title": str(int(best["tahun"])),
            "text": f"Total tahunan tertinggi tercatat {int(best['total']):,} kunjungan.",
        })

    growth, _ = same_period_yoy(entity, selected_year)
    if growth is not None:
        direction = "naik" if growth >= 0 else "turun"
        insights.append({
            "tag": "PERTUMBUHAN",
            "title": f"{growth:+.2f}%",
            "text": f"Kunjungan {direction} dibandingkan periode yang sama tahun sebelumnya.",
        })

    if top_passports:
        top = top_passports[0]
        insights.append({
            "tag": "PASAR UTAMA",
            "title": top["label"],
            "text": f"Paspor dengan kontribusi terbesar pada filter aktif, sebanyak {top['value']:,} kunjungan.",
        })

    return insights[:5]


@app.route("/")
def index():
    data = load_data()
    entities = (
        data[data["kategori"].isin(["grand_total", "paspor"])]
        ["paspor_atau_wilayah"]
        .drop_duplicates()
        .tolist()
    )
    entities = ["GRAND TOTAL"] + sorted([item for item in entities if item != "GRAND TOTAL"])
    models = [{"value": key, **value} for key, value in MODEL_OPTIONS.items()]
    return render_template("index.html", entities=entities, years=list(range(2022, 2027)), models=models)


@app.route("/api/dashboard")
def dashboard_api():
    data = load_data()
    selected_year = request.args.get("year", "all")
    entity = request.args.get("entity", "GRAND TOTAL").strip()
    model_type = request.args.get("model", "linear").strip()
    prediction_year_raw = request.args.get("prediction_year", "2026").strip()

    valid_entities = set(data["paspor_atau_wilayah"].dropna().unique())
    if entity not in valid_entities:
        entity = "GRAND TOTAL"

    if selected_year != "all":
        try:
            year_int = int(selected_year)
            if year_int < 2022 or year_int > 2026:
                selected_year = "all"
        except ValueError:
            selected_year = "all"

    try:
        prediction_year = int(prediction_year_raw)
    except ValueError:
        prediction_year = 2026
    prediction_year = min(max(prediction_year, 2026), 2100)

    if model_type not in MODEL_OPTIONS:
        model_type = "linear"

    filtered = period_data(entity, selected_year)
    available = filtered[filtered["jumlah_kunjungan"].notna()].copy()

    total = available["jumlah_kunjungan"].sum() if not available.empty else None
    average = available["jumlah_kunjungan"].mean() if not available.empty else None
    peak = available.loc[available["jumlah_kunjungan"].idxmax()] if not available.empty else None

    expected_months = 60 if selected_year == "all" else 12
    coverage = len(available) / expected_months * 100 if expected_months else None
    growth, growth_label = same_period_yoy(entity, selected_year)

    trend = [{
        "tanggal": row["tanggal"].strftime("%Y-%m-%d"),
        "tahun": int(row["tahun"]),
        "bulan": row["bulan"],
        "nilai": int_or_none(row["jumlah_kunjungan"]),
    } for _, row in filtered.iterrows()]

    annual = annual_series(entity)
    annual_data = [{
        "tahun": int(row["tahun"]),
        "total": int_or_none(row["total"]),
        "bulan_tersedia": int(row["bulan_tersedia"]),
        "status": "lengkap" if int(row["bulan_tersedia"]) == 12 else "parsial",
    } for _, row in annual.iterrows()]

    period_source = data.copy()
    if selected_year != "all":
        period_source = period_source[period_source["tahun"] == int(selected_year)]

    top = (
        period_source[
            (period_source["kategori"] == "paspor")
            & (period_source["paspor_atau_wilayah"] != "Lain-lain")
            & period_source["jumlah_kunjungan"].notna()
        ]
        .groupby("paspor_atau_wilayah", as_index=False)["jumlah_kunjungan"]
        .sum()
        .sort_values("jumlah_kunjungan", ascending=False)
        .head(10)
    )
    top_passports = [{
        "label": row["paspor_atau_wilayah"],
        "value": int(round(row["jumlah_kunjungan"])),
    } for _, row in top.iterrows()]

    regional = (
        period_source[
            (period_source["kategori"] == "subtotal")
            & period_source["jumlah_kunjungan"].notna()
        ]
        .groupby("paspor_atau_wilayah", as_index=False)["jumlah_kunjungan"]
        .sum()
    )
    regional_data = []
    for _, row in regional.iterrows():
        label = REGION_LABELS.get(row["paspor_atau_wilayah"], row["paspor_atau_wilayah"])
        regional_data.append({"label": label, "value": int(round(row["jumlah_kunjungan"]))})
    regional_data.sort(key=lambda item: item["value"], reverse=True)

    heat_source = data[data["paspor_atau_wilayah"] == entity].copy()
    pivot = heat_source.pivot_table(
        index="tahun",
        columns="nomor_bulan",
        values="jumlah_kunjungan",
        aggfunc="sum",
    ).reindex(index=range(2022, 2027), columns=range(1, 13))
    heatmap = {
        "years": [int(year) for year in pivot.index],
        "months": BULAN,
        "values": [[clean_number(value) for value in row] for row in pivot.to_numpy()],
    }

    annual_growth = []
    for _, row in annual.iterrows():
        year = int(row["tahun"])
        months = int(row["bulan_tersedia"])
        current_total = float(row["total"])
        previous_data = data[
            (data["paspor_atau_wilayah"] == entity)
            & (data["tahun"] == year - 1)
            & (data["nomor_bulan"] <= months)
            & data["jumlah_kunjungan"].notna()
        ]
        if previous_data.empty or previous_data["jumlah_kunjungan"].sum() == 0:
            continue
        previous_total = previous_data["jumlah_kunjungan"].sum()
        growth_value = (current_total - previous_total) / previous_total * 100
        annual_growth.append({
            "tahun": year,
            "growth": clean_number(growth_value),
            "partial": months < 12,
        })

    model = regression_result(entity, model_type, prediction_year)
    forecast_overlay = model["forecast"] if model.get("available") else []

    kpis = {
        "total": int_or_none(total),
        "average": int_or_none(average),
        "peak_value": int_or_none(peak["jumlah_kunjungan"]) if peak is not None else None,
        "peak_label": f"{BULAN[int(peak['nomor_bulan']) - 1]} {int(peak['tahun'])}" if peak is not None else "Tidak tersedia",
        "growth": clean_number(growth),
        "growth_label": growth_label,
        "coverage": clean_number(coverage),
        "available_months": int(len(available)),
        "expected_months": expected_months,
    }

    insights = build_insights(entity, selected_year, filtered, model, top_passports)

    return jsonify({
        "filters": {
            "year": selected_year,
            "entity": entity,
            "model": model_type,
            "prediction_year": prediction_year,
        },
        "kpis": kpis,
        "trend": trend,
        "annual": annual_data,
        "top_passports": top_passports,
        "regional": regional_data,
        "heatmap": heatmap,
        "annual_growth": annual_growth,
        "model": model,
        "forecast_overlay": forecast_overlay,
        "insights": insights,
        "data_note": (
            "Dataset web memakai data 2022-2026. Data 2026 yang tersedia adalah Januari-April; "
            "karena itu prediksi dimulai dari Mei 2026. Jika memilih tahun setelah 2026, "
            "forecast menampilkan semua bulan pada rentang Mei 2026 sampai Desember tahun pilihan, maksimal 2100."
        ),
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "rows": len(load_data()), "dataset": DATA_PATH.name})


if __name__ == "__main__":
    app.run(debug=True)
