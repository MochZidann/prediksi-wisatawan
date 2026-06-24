const COLORS = {
    ink: "#0b1020",
    paper: "#f4f1e8",
    white: "#ffffff",
    acid: "#c8ff3d",
    coral: "#ff6b4a",
    blue: "#5aa9ff",
    yellow: "#ffd84a",
    muted: "#6d7281"
};

const numberFormatter = new Intl.NumberFormat("id-ID");
const compactFormatter = new Intl.NumberFormat("id-ID", {
    notation: "compact",
    maximumFractionDigits: 1
});

const plotConfig = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"]
};

const baseLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {family: "Segoe UI, Arial, sans-serif", color: COLORS.ink, size: 12},
    margin: {l: 65, r: 25, t: 28, b: 58},
    xaxis: {
        gridcolor: "rgba(11,16,32,.10)",
        zerolinecolor: "rgba(11,16,32,.2)",
        linecolor: COLORS.ink,
        tickfont: {size: 11}
    },
    yaxis: {
        gridcolor: "rgba(11,16,32,.10)",
        zerolinecolor: "rgba(11,16,32,.2)",
        linecolor: COLORS.ink,
        tickfont: {size: 11}
    },
    hoverlabel: {bgcolor: COLORS.ink, bordercolor: COLORS.acid, font: {color: COLORS.white}}
};

const el = id => document.getElementById(id);

function formatNumber(value) {
    return value === null || value === undefined ? "—" : numberFormatter.format(value);
}

function formatCompact(value) {
    return value === null || value === undefined ? "—" : compactFormatter.format(value);
}

function formatPercent(value) {
    if (value === null || value === undefined) return "—";
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}


function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function highlightPythonCode(code) {
    const withoutHashComments = String(code)
        .split("\n")
        .filter(line => !line.trim().startsWith("#"))
        .join("\n");

    const stringPattern = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g;
    const tokenPattern = /\b(def|return|from|import|for|in|if|else|elif)\b|\b(sum|zip|range|max|round|sin|cos|pi|len|int|float|str)\b|\b(\d+(?:\.\d+)?)\b|\b([A-Za-z_]\w*)(?=\s*\()/g;

    return withoutHashComments.split(stringPattern).map(part => {
        if (!part) return "";
        if ((part.startsWith('"') && part.endsWith('"')) || (part.startsWith("'") && part.endsWith("'"))) {
            return `<span class="tok-string">${escapeHtml(part)}</span>`;
        }
        return escapeHtml(part).replace(tokenPattern, (match, keyword, builtin, number, fn) => {
            if (keyword) return `<span class="tok-keyword">${keyword}</span>`;
            if (builtin) return `<span class="tok-builtin">${builtin}</span>`;
            if (number) return `<span class="tok-number">${number}</span>`;
            if (fn) return `<span class="tok-function">${fn}</span>`;
            return match;
        });
    }).join("");
}

function renderCodeSnippet(code) {
    el("codeSnippet").innerHTML = highlightPythonCode(code);
}

function setLoading(isLoading) {
    el("loadingOverlay").classList.toggle("hidden", !isLoading);
}

function renderKpis(data) {
    const kpi = data.kpis;
    el("kpiTotal").textContent = formatCompact(kpi.total);
    el("kpiTotal").title = formatNumber(kpi.total);
    el("kpiTotalLabel").textContent =
        data.filters.year === "all"
            ? `${data.filters.entity} • semua tahun`
            : `${data.filters.entity} • ${data.filters.year}`;

    el("kpiAverage").textContent = formatCompact(kpi.average);
    el("kpiAverage").title = formatNumber(kpi.average);

    el("kpiPeak").textContent = formatCompact(kpi.peak_value);
    el("kpiPeak").title = formatNumber(kpi.peak_value);
    el("kpiPeakLabel").textContent = kpi.peak_label;

    el("kpiGrowthTitle").textContent = kpi.growth_label;
    el("kpiGrowth").textContent = formatPercent(kpi.growth);
    el("kpiGrowth").style.color = kpi.growth !== null && kpi.growth < 0 ? COLORS.coral : COLORS.ink;

    el("kpiCoverage").textContent = kpi.coverage === null ? "—" : `${kpi.coverage.toFixed(1)}%`;
    el("kpiCoverageLabel").textContent = `${kpi.available_months}/${kpi.expected_months} bulan tersedia`;
}

function renderTrend(data) {
    const actual = data.trend.filter(row => row.nilai !== null);
    const traces = [{
        x: actual.map(row => row.tanggal),
        y: actual.map(row => row.nilai),
        type: "scatter",
        mode: "lines+markers",
        name: "Aktual",
        line: {color: COLORS.blue, width: 4},
        marker: {color: COLORS.paper, line: {color: COLORS.ink, width: 2}, size: 7},
        hovertemplate: "%{x|%b %Y}<br><b>%{y:,.0f}</b><extra>Aktual</extra>"
    }];

    if (data.forecast_overlay && data.forecast_overlay.length) {
        const lastActual = actual.slice(-1)[0];
        const forecastX = data.forecast_overlay.map(row => row.tanggal);
        const forecastY = data.forecast_overlay.map(row => row.prediksi);

        if (lastActual) {
            forecastX.unshift(lastActual.tanggal);
            forecastY.unshift(lastActual.nilai);
        }

        traces.push({
            x: forecastX,
            y: forecastY,
            type: "scatter",
            mode: "lines+markers",
            name: `Prediksi sampai ${data.filters.prediction_year}`,
            line: {color: COLORS.coral, width: 4, dash: "dot"},
            marker: {symbol: "diamond", color: COLORS.acid, line: {color: COLORS.ink, width: 2}, size: 9},
            hovertemplate: "%{x|%b %Y}<br><b>%{y:,.0f}</b><extra>Prediksi</extra>"
        });
    }

    Plotly.react("trendChart", traces, {
        ...baseLayout,
        margin: {l: 72, r: 28, t: 28, b: 65},
        legend: {orientation: "h", x: 0, y: 1.12, bgcolor: "rgba(0,0,0,0)"},
        xaxis: {
            ...baseLayout.xaxis,
            title: {text: "Periode", standoff: 15},
            rangeslider: {
                visible: data.filters.year === "all",
                thickness: .08,
                bgcolor: COLORS.paper,
                bordercolor: COLORS.ink,
                borderwidth: 1
            }
        },
        yaxis: {...baseLayout.yaxis, title: {text: "Kunjungan", standoff: 13}, tickformat: "~s"}
    }, plotConfig);
}

function renderAnnual(data) {
    const years = data.annual.map(row => row.tahun);
    const values = data.annual.map(row => row.total);
    const colors = data.annual.map(row => row.status === "lengkap" ? COLORS.acid : COLORS.coral);

    Plotly.react("annualChart", [{
        x: years,
        y: values,
        type: "bar",
        marker: {
            color: colors,
            line: {color: COLORS.ink, width: 2},
            pattern: {shape: data.annual.map(row => row.status === "lengkap" ? "" : "/")}
        },
        text: values.map(formatCompact),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{x}<br><b>%{y:,.0f}</b><extra></extra>"
    }], {
        ...baseLayout,
        xaxis: {...baseLayout.xaxis, dtick: 1},
        yaxis: {...baseLayout.yaxis, tickformat: "~s"},
        showlegend: false
    }, plotConfig);
}

function renderGrowth(data) {
    const rows = data.annual_growth;
    if (!rows.length) {
        renderEmptyChart("growthChart", "Pertumbuhan belum tersedia");
        return;
    }

    Plotly.react("growthChart", [{
        x: rows.map(row => row.tahun),
        y: rows.map(row => row.growth),
        type: "bar",
        marker: {color: rows.map(row => row.growth >= 0 ? COLORS.blue : COLORS.coral), line: {color: COLORS.ink, width: 2}},
        text: rows.map(row => `${row.growth >= 0 ? "+" : ""}${row.growth.toFixed(1)}%`),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{x}<br><b>%{y:.2f}%</b><extra></extra>"
    }], {
        ...baseLayout,
        xaxis: {...baseLayout.xaxis, dtick: 1},
        yaxis: {...baseLayout.yaxis, ticksuffix: "%", zeroline: true, zerolinecolor: COLORS.ink, zerolinewidth: 2},
        showlegend: false
    }, plotConfig);
}

function renderHeatmap(data) {
    Plotly.react("heatmapChart", [{
        z: data.heatmap.values,
        x: data.heatmap.months,
        y: data.heatmap.years,
        type: "heatmap",
        hoverongaps: false,
        colorscale: [[0, COLORS.paper], [.25, COLORS.blue], [.6, COLORS.yellow], [1, COLORS.coral]],
        colorbar: {title: "Kunjungan", thickness: 13, outlinecolor: COLORS.ink, outlinewidth: 1, tickformat: "~s"},
        hovertemplate: "%{x} %{y}<br><b>%{z:,.0f}</b><extra></extra>"
    }], {
        ...baseLayout,
        margin: {l: 58, r: 80, t: 22, b: 75},
        xaxis: {...baseLayout.xaxis, tickangle: -35, gridcolor: "rgba(0,0,0,0)"},
        yaxis: {...baseLayout.yaxis, dtick: 1, autorange: "reversed", gridcolor: "rgba(0,0,0,0)"}
    }, plotConfig);
}

function renderPassports(data) {
    const rows = [...data.top_passports].reverse();
    if (!rows.length) {
        renderEmptyChart("passportChart", "Top paspor belum tersedia");
        return;
    }

    Plotly.react("passportChart", [{
        x: rows.map(row => row.value),
        y: rows.map(row => row.label),
        type: "bar",
        orientation: "h",
        marker: {color: rows.map((_, index) => index === rows.length - 1 ? COLORS.coral : COLORS.blue), line: {color: COLORS.ink, width: 1.5}},
        text: rows.map(row => formatCompact(row.value)),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{y}<br><b>%{x:,.0f}</b><extra></extra>"
    }], {
        ...baseLayout,
        margin: {l: 125, r: 55, t: 20, b: 45},
        xaxis: {...baseLayout.xaxis, tickformat: "~s"},
        yaxis: {...baseLayout.yaxis, automargin: true},
        showlegend: false
    }, plotConfig);
}

function renderRegion(data) {
    if (!data.regional.length) {
        renderEmptyChart("regionChart", "Komposisi wilayah belum tersedia");
        return;
    }

    Plotly.react("regionChart", [{
        labels: data.regional.map(row => row.label),
        values: data.regional.map(row => row.value),
        type: "pie",
        hole: .58,
        sort: false,
        marker: {
            colors: [COLORS.acid, COLORS.blue, COLORS.coral, COLORS.yellow, "#987cff", "#26c6a0", "#ff9ac5"],
            line: {color: COLORS.ink, width: 2}
        },
        textinfo: "percent",
        hovertemplate: "%{label}<br><b>%{value:,.0f}</b><br>%{percent}<extra></extra>"
    }], {
        ...baseLayout,
        margin: {l: 20, r: 20, t: 25, b: 75},
        showlegend: true,
        legend: {orientation: "h", y: -.16, x: 0, font: {size: 10}},
        annotations: [{
            text: "ASAL<br>WILAYAH",
            x: .5,
            y: .5,
            showarrow: false,
            font: {size: 13, color: COLORS.ink, family: "Courier New"}
        }]
    }, plotConfig);
}

function renderEmptyChart(id, message) {
    Plotly.react(id, [], {
        ...baseLayout,
        xaxis: {visible: false},
        yaxis: {visible: false},
        annotations: [{
            text: message,
            x: .5,
            y: .5,
            xref: "paper",
            yref: "paper",
            showarrow: false,
            font: {size: 13, color: COLORS.muted}
        }]
    }, plotConfig);
}

function renderCorrelation(data) {
    const model = data.model;
    if (!model.available || !model.correlation) {
        renderEmptyChart("correlationChart", "Korelasi belum tersedia");
        return;
    }

    Plotly.react("correlationChart", [{
        z: model.correlation.values,
        x: model.correlation.labels,
        y: model.correlation.labels,
        type: "heatmap",
        zmin: -1,
        zmax: 1,
        colorscale: [[0, COLORS.coral], [.5, COLORS.paper], [1, COLORS.blue]],
        colorbar: {title: "r", thickness: 12, outlinecolor: COLORS.ink, outlinewidth: 1},
        hovertemplate: "%{y} vs %{x}<br><b>r = %{z:.3f}</b><extra></extra>"
    }], {
        ...baseLayout,
        margin: {l: 105, r: 55, t: 24, b: 105},
        xaxis: {...baseLayout.xaxis, tickangle: -35, gridcolor: "rgba(0,0,0,0)"},
        yaxis: {...baseLayout.yaxis, gridcolor: "rgba(0,0,0,0)"}
    }, plotConfig);
}

function renderCoefficients(data) {
    const model = data.model;
    if (!model.available || !model.coefficients) {
        renderEmptyChart("coefficientChart", "Koefisien belum tersedia");
        return;
    }

    const rows = [...model.coefficients].reverse();
    Plotly.react("coefficientChart", [{
        x: rows.map(row => row.value),
        y: rows.map(row => row.feature),
        type: "bar",
        orientation: "h",
        marker: {color: rows.map(row => row.value >= 0 ? COLORS.blue : COLORS.coral), line: {color: COLORS.ink, width: 1.5}},
        text: rows.map(row => formatCompact(row.value)),
        textposition: "outside",
        cliponaxis: false,
        hovertemplate: "%{y}<br><b>%{x:,.2f}</b><extra></extra>"
    }], {
        ...baseLayout,
        margin: {l: 145, r: 70, t: 22, b: 48},
        xaxis: {...baseLayout.xaxis, zeroline: true, zerolinecolor: COLORS.ink, zerolinewidth: 2, tickformat: "~s"},
        yaxis: {...baseLayout.yaxis, automargin: true},
        showlegend: false
    }, plotConfig);
}

function renderRegressionFit(data) {
    const model = data.model;
    if (!model.available || !model.fit || !model.series) {
        renderEmptyChart("regressionFitChart", "Aktual dan fitted belum tersedia");
        return;
    }

    const seriesRows = model.series;
    const fitRows = model.fit;
    const forecastRows = model.forecast || [];

    Plotly.react("regressionFitChart", [{
        x: seriesRows.map(row => row.tanggal),
        y: seriesRows.map(row => row.aktual),
        type: "scatter",
        mode: "lines+markers",
        name: "Aktual 2022-April 2026",
        line: {color: COLORS.ink, width: 2},
        marker: {color: COLORS.paper, size: 7, line: {color: COLORS.ink, width: 2}},
        hovertemplate: "%{x|%b %Y}<br><b>%{y:,.0f}</b><extra>Aktual</extra>"
    }, {
        x: fitRows.map(row => row.tanggal),
        y: fitRows.map(row => row.fitted),
        type: "scatter",
        mode: "lines+markers",
        name: `Fitted ${model.model_short}`,
        line: {color: COLORS.blue, width: 3},
        marker: {color: COLORS.blue, size: 5},
        hovertemplate: "%{x|%b %Y}<br><b>%{y:,.0f}</b><extra>Fitted</extra>"
    }, {
        x: forecastRows.map(row => row.tanggal),
        y: forecastRows.map(row => row.prediksi),
        type: "scatter",
        mode: "lines+markers",
        name: `Prediksi sampai ${model.prediction_year}`,
        line: {color: COLORS.coral, width: 4, dash: "dot"},
        marker: {color: COLORS.acid, symbol: "diamond", size: 9, line: {color: COLORS.ink, width: 2}},
        hovertemplate: "%{x|%b %Y}<br><b>%{y:,.0f}</b><extra>Prediksi</extra>"
    }], {
        ...baseLayout,
        margin: {l: 72, r: 28, t: 30, b: 65},
        legend: {orientation: "h", x: 0, y: 1.12, bgcolor: "rgba(0,0,0,0)"},
        xaxis: {...baseLayout.xaxis, title: {text: "Periode", standoff: 15}},
        yaxis: {...baseLayout.yaxis, title: {text: "Kunjungan", standoff: 13}, tickformat: "~s"}
    }, plotConfig);
}

function renderInsights(data) {
    const container = el("insightList");
    container.innerHTML = "";

    if (!data.insights.length) {
        container.innerHTML = `
            <div class="insight-item">
                <span>INFO</span>
                <div>
                    <strong>Belum ada data</strong>
                    <p>Ubah filter untuk menampilkan insight.</p>
                </div>
            </div>`;
        return;
    }

    data.insights.forEach(item => {
        const row = document.createElement("div");
        row.className = "insight-item";
        row.innerHTML = `
            <span>${item.tag}</span>
            <div>
                <strong>${item.title}</strong>
                <p>${item.text}</p>
            </div>`;
        container.appendChild(row);
    });
}

function renderCalculationSteps(model) {
    const steps = el("calculationSteps");
    steps.innerHTML = "";

    if (!model.available || !model.example_calculation) {
        steps.innerHTML = `<div>Perhitungan belum tersedia.</div>`;
        return;
    }

    const title = document.createElement("div");
    title.innerHTML = `<b>${model.example_calculation.title}</b><br>Y = Σ(beta × nilai fitur)`;
    steps.appendChild(title);

    model.example_calculation.terms.forEach(term => {
        const row = document.createElement("div");
        row.innerHTML = `${term.feature}: ${Number(term.beta).toFixed(4)} × ${Number(term.x).toFixed(4)} = <b>${formatNumber(Math.round(term.hasil))}</b>`;
        steps.appendChild(row);
    });

    const result = document.createElement("div");
    result.innerHTML = `Hasil akhir dibulatkan dan nilai negatif dikunci menjadi 0: <b>${formatNumber(model.example_calculation.result)}</b>`;
    steps.appendChild(result);
}

function renderModel(data) {
    const model = data.model;
    const tbody = el("forecastTable");
    tbody.innerHTML = "";

    if (!model.available) {
        el("modelR2").textContent = "—";
        el("modelMae").textContent = "—";
        el("modelRmse").textContent = "—";
        el("modelFormula").textContent = model.message;
        el("modelDescription").textContent = model.message;
        el("forecastTitle").textContent = "Forecast belum tersedia";
        el("forecastSubtitle").textContent = "Model aktif: —";
        el("forecastBadge").textContent = "0 BULAN";
        renderCodeSnippet("Kode belum tersedia karena data model tidak cukup.");
        renderCalculationSteps(model);
        tbody.innerHTML = `<tr><td colspan="3">${model.message}</td></tr>`;
        return;
    }

    el("modelDescription").innerHTML =
        `Model <span class="model-name-inline">${model.model_label}</span> untuk ${data.filters.entity} ` +
        `dilatih pada periode ${model.training_period}. Evaluasi: ${model.evaluation_method}. ` +
        `Forecast aktif: ${model.forecast_period}.`;
    el("modelR2").textContent = model.r2.toFixed(4);
    el("modelMae").textContent = formatCompact(model.mae);
    el("modelMae").title = formatNumber(Math.round(model.mae));
    el("modelRmse").textContent = formatCompact(model.rmse);
    el("modelRmse").title = formatNumber(Math.round(model.rmse));
    el("modelFormula").textContent = model.formula;

    el("forecastTitle").textContent = model.forecast_period;
    el("forecastSubtitle").textContent = `Model aktif: ${model.model_label}`;
    el("forecastBadge").textContent = `${model.forecast.length} BULAN`;

    model.forecast.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.bulan} ${row.tahun}</td>
            <td>${formatNumber(row.prediksi)}</td>
            <td>${formatNumber(row.batas_bawah)} — ${formatNumber(row.batas_atas)}</td>`;
        tbody.appendChild(tr);
    });

    renderCodeSnippet(model.code_snippet);
    renderCalculationSteps(model);
}

async function loadDashboard() {
    const year = el("yearFilter").value;
    const entity = el("entityFilter").value.trim() || "GRAND TOTAL";
    const model = el("modelFilter").value;
    let predictionYear = parseInt(el("predictionYear").value || "2026", 10);

    if (Number.isNaN(predictionYear)) predictionYear = 2026;
    predictionYear = Math.min(Math.max(predictionYear, 2026), 2100);
    el("predictionYear").value = predictionYear;

    setLoading(true);

    try {
        const params = new URLSearchParams({year, entity, model, prediction_year: predictionYear});
        const response = await fetch(`/api/dashboard?${params.toString()}`);
        if (!response.ok) throw new Error("Dashboard tidak dapat dimuat.");

        const data = await response.json();

        if (data.filters.entity !== entity) el("entityFilter").value = data.filters.entity;
        if (data.filters.model !== model) el("modelFilter").value = data.filters.model;
        if (data.filters.prediction_year !== predictionYear) el("predictionYear").value = data.filters.prediction_year;

        renderKpis(data);
        renderTrend(data);
        renderAnnual(data);
        renderGrowth(data);
        renderHeatmap(data);
        renderPassports(data);
        renderRegion(data);
        renderCorrelation(data);
        renderCoefficients(data);
        renderRegressionFit(data);
        renderInsights(data);
        renderModel(data);

        el("dataNote").textContent = data.data_note;
        el("lastUpdated").textContent =
            `Diperbarui ${new Date().toLocaleTimeString("id-ID", {hour: "2-digit", minute: "2-digit"})}`;
    } catch (error) {
        console.error(error);
        alert("Gagal memuat dashboard. Pastikan server Flask berjalan dengan benar.");
    } finally {
        setLoading(false);
    }
}

function setupNavbar() {
    const links = [...document.querySelectorAll(".nav-link")];
    const sections = links
        .map(link => document.querySelector(link.getAttribute("href")))
        .filter(Boolean);

    links.forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            const target = document.querySelector(link.getAttribute("href"));
            if (!target) return;
            target.scrollIntoView({behavior: "smooth", block: "start"});
        });
    });

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            links.forEach(link => link.classList.remove("active"));
            const active = links.find(link => link.getAttribute("href") === `#${entry.target.id}`);
            if (active) active.classList.add("active");
        });
    }, {rootMargin: "-35% 0px -55% 0px", threshold: 0});

    sections.forEach(section => observer.observe(section));
}

el("applyFilter").addEventListener("click", loadDashboard);
el("resetFilter").addEventListener("click", () => {
    el("yearFilter").value = "all";
    el("entityFilter").value = "GRAND TOTAL";
    el("modelFilter").value = "linear";
    el("predictionYear").value = "2026";
    loadDashboard();
});

el("yearFilter").addEventListener("change", loadDashboard);
el("modelFilter").addEventListener("change", loadDashboard);
el("predictionYear").addEventListener("change", loadDashboard);
el("entityFilter").addEventListener("keydown", event => {
    if (event.key === "Enter") loadDashboard();
});

window.addEventListener("DOMContentLoaded", () => {
    setupNavbar();
    loadDashboard();
});
