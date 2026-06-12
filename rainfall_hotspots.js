// ===============================
// 🌧️ Rainfall Hotspot Monitor JS
// ===============================

// Kaart opzetten
const map = L.map("map").setView([4.8, -55.2], 7);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
}).addTo(map);

// ===============================
// HELPERS
// ===============================
function formatRain(rain) {
  if (rain === null || rain === undefined || rain === "" || isNaN(rain)) {
    return "NA";
  }
  return Number(rain).toFixed(1);
}

// ===============================
// CATEGORIE + NEON KLEUREN
// ===============================
function getCategory(rain) {
  if (rain === null || rain === undefined || rain === "" || isNaN(rain))
    return "Geen data";

  if (rain <= 10) return "Licht";
  if (rain <= 30) return "Matig";
  if (rain <= 60) return "Zwaar";
  return "Zeer Zwaar";
}

function getColor(category) {
  if (category === "Zeer Zwaar") return "#ff1a1a";   // neon rood
  if (category === "Zwaar") return "#ff7b00";        // neon oranje
  if (category === "Matig") return "#fff000";        // neon geel
  if (category === "Licht") return "#00ffd5";        // neon aqua
  return "#00c3ff";                                   // default
}

// Globale variabelen
let stationsLast10 = [];
let allDays = {};
let daysList = [];
let stationChart = null;
let dayChart = null;
let currentStation = null;

// ===============================
// DATA LADEN
// ===============================
fetch("https://klima2025.pythonanywhere.com/api/hotspots10days")
  .then((res) => res.json())
  .then((data) => {
    stationsLast10 = data.stations_last10 || [];
    allDays = data.all_days || {};
    daysList = data.days || [];

    plotStationsOnMap(stationsLast10);
    initRangeTable();
    initDayPicker(daysList);
  })
  .catch((err) => console.error("API FOUT:", err));

// ===============================
// VAKJE 1 – STATION DETAILS
// ===============================
function plotStationsOnMap(stations) {
  stations.forEach((station) => {
    if (!station.Last10Days || station.Last10Days.length === 0) return;

    const hasSignificant = station.Last10Days.some((d) => d.rain > 10);
    if (!hasSignificant) return;

    const last = station.Last10Days[station.Last10Days.length - 1];
    const cat = getCategory(last.rain);
    const color = getColor(cat);

    const radius =
      cat === "Zeer Zwaar" ? 16 :
      cat === "Zwaar" ? 13 :
      cat === "Matig" ? 11 :
      9;

    const marker = L.circleMarker([station.Latitude, station.Longitude], {
      radius: radius,
      color: color,
      fillColor: color,
      fillOpacity: 0.85,
    }).addTo(map);

    marker.on("click", () => showStationDetails(station));
  });
}

function showStationDetails(station) {
  currentStation = station;

  const tableDiv = document.getElementById("station_table");
  tableDiv.innerHTML = "";

  let html = `
    <h3 style="text-align:center; margin-bottom:10px;">
      Station: ${station.StationID}
    </h3>
    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
      <tr>
        <th>Datum</th>
        <th>Regen (mm)</th>
        <th>Categorie</th>
      </tr>
  `;

  station.Last10Days.forEach((d) => {
    const cat = getCategory(d.rain);

    html += `
      <tr>
        <td>${d.date}</td>
        <td>${formatRain(d.rain)}</td>
        <td>${cat}</td>
      </tr>
    `;
  });

  html += "</table>";
  tableDiv.innerHTML = html;

  buildStationChart(station);
}

function buildStationChart(station) {
  const ctx = document.getElementById("station_chart");

  if (stationChart) stationChart.destroy();

  const days = station.Last10Days;

  const labels = days.map(d => d.date);

  const values = days.map(d => {
    if (d.rain === null || d.rain === undefined || d.rain === "" || isNaN(d.rain)) {
      return 0;
    }
    return Number(d.rain);
  });

  const colors = days.map(d => {
    if (d.rain === null || d.rain === undefined || d.rain === "" || isNaN(d.rain)) {
      return "#888888"; // NA = grijs
    }
    return getColor(getCategory(d.rain));
  });

  const labelsAboveBars = days.map(d => {
    if (d.rain === null || d.rain === undefined || d.rain === "" || isNaN(d.rain)) {
      return "NA";
    }
    return Number(d.rain).toFixed(1);
  });

  stationChart = new Chart(ctx, {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: labels,
      datasets: [
        {
          label: `Regenval (mm) - ${station.StationID}`,
          data: values,
          backgroundColor: colors,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        datalabels: {
          anchor: "end",
          align: "top",
          color: "white",
          font: { weight: "bold", size: 12 },
          formatter: (value, context) => labelsAboveBars[context.dataIndex]
        },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

// DOWNLOADS VAKJE 1
document.getElementById("download_station_png").addEventListener("click", () => {
  if (!stationChart || !currentStation) return;
  const link = document.createElement("a");
  link.href = stationChart.toBase64Image();
  link.download = `station_${currentStation.StationID}.png`;
  link.click();
});

document.getElementById("download_station_csv").addEventListener("click", () => {
  if (!currentStation) return;

  let csv = "Datum,Regen(mm),Categorie\n";
  currentStation.Last10Days.forEach((d) => {
    csv += `${d.date},${formatRain(d.rain)},${getCategory(d.rain)}\n`;
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `station_${currentStation.StationID}.csv`;
  link.click();
});

// ===============================
// VAKJE 2 – DATUMRANGE TABEL
// ===============================
function initRangeTable() {
  const startInput = document.getElementById("range_start");
  const endInput = document.getElementById("range_end");
  const btn = document.getElementById("range_apply");

  document.getElementById("all_stations_table").innerHTML = "";

  btn.addEventListener("click", () => {
    const start = startInput.value;
    const end = endInput.value;
    buildRangeTable(start, end);
  });
}

function buildRangeTable(start, end) {
  const div = document.getElementById("all_stations_table");
  let html = `
    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
      <tr>
        <th>Datum</th>
        <th>Station</th>
        <th>Regen (mm)</th>
        <th>Categorie</th>
      </tr>
  `;

  daysList.forEach((day) => {
    if (day < start || day > end) return;

    const entries = allDays[day] || [];
    entries.forEach((e) => {
      if (e.rain <= 10) return;

      const cat = getCategory(e.rain);
      html += `
        <tr>
          <td>${day}</td>
          <td>${e.StationID}</td>
          <td>${e.rain}</td>
          <td>${cat}</td>
        </tr>
      `;
    });
  });

  html += "</table>";
  div.innerHTML = html;
}

// DOWNLOAD CSV VAKJE 2
document.getElementById("download_range_csv").addEventListener("click", () => {
  const start = document.getElementById("range_start").value;
  const end = document.getElementById("range_end").value;

  let csv = "Datum,Station,Regen(mm),Categorie\n";

  daysList.forEach((day) => {
    if (day < start || day > end) return;

    const entries = allDays[day] || [];
    entries.forEach((e) => {
      if (e.rain <= 10) return;
      csv += `${day},${e.StationID},${e.rain},${getCategory(e.rain)}\n`;
    });
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `regenval_${start}_tot_${end}.csv`;
  link.click();
});

// ===============================
// VAKJE 3 – DAGSELECTIE + GRAFIEK
// ===============================
function initDayPicker(days) {
  const picker = document.getElementById("day_picker");

  picker.min = days[0];
  picker.max = days[days.length - 1];
  picker.value = days[0];

  buildDayChart(days[0]);

  picker.addEventListener("change", () => {
    buildDayChart(picker.value);
  });
}

function buildDayChart(day) {
  const ctx = document.getElementById("day_chart");
  const entries = (allDays[day] || []).filter((e) => e.rain > 10);

  const labels = entries.map((e) => e.StationID);
  const values = entries.map((e) => e.rain);
  const colors = entries.map((e) => getColor(getCategory(e.rain)));

  if (dayChart) dayChart.destroy();

  dayChart = new Chart(ctx, {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: labels,
      datasets: [
        {
          label: `Regenval (mm) op ${day}`,
          data: values,
          backgroundColor: colors,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        datalabels: {
          anchor: "end",
          align: "top",
          color: "white",
          font: { weight: "bold", size: 12 },
          formatter: (value) => value,
        },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

function downloadDayCsv(day) {
  const entries = (allDays[day] || []).filter((e) => e.rain > 10);
  let csv = "Station,Datum,Regen(mm),Categorie\n";

  entries.forEach((e) => {
    const cat = getCategory(e.rain);
    csv += `${e.StationID},${day},${e.rain},${cat}\n`;
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `regenval_${day}.csv`;
  link.click();
}

// DOWNLOADS VAKJE 3
document.getElementById("download_day_png").addEventListener("click", () => {
  if (!dayChart) return;
  const link = document.createElement("a");
  link.href = dayChart.toBase64Image();
  link.download = "regenval_dag.png";
  link.click();
});

document.getElementById("download_day_csv").addEventListener("click", () => {
  const day = document.getElementById("day_picker").value;
  downloadDayCsv(day);
});
