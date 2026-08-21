(function () {
    const widget = document.querySelector(".land-registry-widget");
    if (!widget) return;

    fetch(widget.dataset.jsonUrl)
        .then((r) => r.json())
        .then((data) => {
            renderTable(data.transactions);
            renderChart(data.transactions);
            renderVolumeChart(data.transactions);
            renderTypeChart(data.transactions);
            renderHistogram(data.transactions);
        })
        .catch((err) => console.error("Land registry data load failed:", err));

    function formatPrice(amount) {
        return "£" + amount.toLocaleString("en-GB");
    }

    function renderTable(transactions) {
        const tbody = document.querySelector("#land-registry-table tbody");
        tbody.innerHTML = "";
        transactions.forEach((t) => {
            if (!t.amount) return;
            const address =
                [t.saon, t.paon, t.street].filter(Boolean).join(" ") || "—";
            const row = document.createElement("tr");
            row.innerHTML = `
        <td data-value="${t.date || ""}">${(t.date || "—").slice(0, 10)}</td>
        <td data-value="${address}">${address}</td>
        <td data-value="${t.postcode || ""}">${t.postcode || "—"}</td>
        <td data-value="${t.property_type || ""}">${t.property_type || "—"}</td>
        <td data-value="${t.amount}">${formatPrice(t.amount)}</td>
      `;
            tbody.appendChild(row);
        });
        enableSorting();
    }

    function enableSorting() {
        document
            .querySelectorAll("#land-registry-table th[data-sort]")
            .forEach((th, index) => {
                th.style.cursor = "pointer";
                th.addEventListener("click", () => {
                    const tbody = document.querySelector(
                        "#land-registry-table tbody",
                    );
                    const rows = Array.from(tbody.querySelectorAll("tr"));
                    const ascending = th.dataset.sortDir !== "asc";
                    document
                        .querySelectorAll("#land-registry-table th")
                        .forEach((h) => delete h.dataset.sortDir);
                    th.dataset.sortDir = ascending ? "asc" : "desc";

                    rows.sort((a, b) => {
                        const aVal = a.children[index].dataset.value;
                        const bVal = b.children[index].dataset.value;
                        const aNum = parseFloat(aVal);
                        const bNum = parseFloat(bVal);
                        const cmp =
                            !isNaN(aNum) && !isNaN(bNum)
                                ? aNum - bNum
                                : aVal.localeCompare(bVal);
                        return ascending ? cmp : -cmp;
                    });

                    rows.forEach((row) => tbody.appendChild(row));
                });
            });
    }

    function renderChart(transactions) {
        const byMonth = {};
        transactions.forEach((t) => {
            if (!t.amount || !t.date) return;
            const month = t.date.slice(0, 7);
            if (!byMonth[month]) byMonth[month] = [];
            byMonth[month].push(t.amount);
        });

        const months = Object.keys(byMonth).sort();
        const medians = months.map((m) => {
            const vals = byMonth[m].slice().sort((a, b) => a - b);
            const mid = Math.floor(vals.length / 2);
            return vals.length % 2 !== 0
                ? vals[mid]
                : (vals[mid - 1] + vals[mid]) / 2;
        });

        new Chart(document.getElementById("land-registry-chart"), {
            type: "line",
            data: {
                labels: months,
                datasets: [
                    {
                        label: "Median sale price",
                        data: medians,
                        borderWidth: 2,
                        tension: 0.2,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { ticks: { callback: (v) => formatPrice(v) } } },
            },
        });
    }

    function renderVolumeChart(transactions) {
        const byMonth = {};
        transactions.forEach((t) => {
            if (!t.amount || !t.date) return;
            const month = t.date.slice(0, 7);
            byMonth[month] = (byMonth[month] || 0) + 1;
        });

        const months = Object.keys(byMonth).sort();
        const counts = months.map((m) => byMonth[m]);

        new Chart(document.getElementById("land-registry-volume-chart"), {
            type: "bar",
            data: {
                labels: months,
                datasets: [
                    {
                        label: "Sales",
                        data: counts,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            },
        });
    }

    function renderTypeChart(transactions) {
        const typeLabels = {
            D: "Detached",
            S: "Semi-detached",
            T: "Terraced",
            F: "Flat/Maisonette",
            O: "Other",
        };
        const byType = {};
        transactions.forEach((t) => {
            if (!t.amount) return;
            const key = t.property_type || "O";
            if (!byType[key]) byType[key] = [];
            byType[key].push(t.amount);
        });

        const types = Object.keys(byType);
        const labels = types.map((t) => typeLabels[t] || t);
        const medians = types.map((t) => {
            const vals = byType[t].slice().sort((a, b) => a - b);
            const mid = Math.floor(vals.length / 2);
            return vals.length % 2 !== 0
                ? vals[mid]
                : (vals[mid - 1] + vals[mid]) / 2;
        });

        new Chart(document.getElementById("land-registry-type-chart"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Median price",
                        data: medians,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { ticks: { callback: (v) => formatPrice(v) } } },
            },
        });
    }

    function renderHistogram(transactions) {
        const prices = transactions
            .map((t) => t.amount)
            .filter(Boolean)
            .sort((a, b) => a - b);
        if (prices.length === 0) return;

        // Use 5th-95th percentile to size buckets, so a handful of outliers
        // (very cheap leasehold/partial sales, very expensive properties)
        // don't stretch the range and collapse everything into one bucket.
        const p05 = prices[Math.floor(prices.length * 0.05)];
        const p95 = prices[Math.floor(prices.length * 0.95)];

        const bucketCount = 10;
        const rawBucketSize = (p95 - p05) / bucketCount;
        const bucketSize = Math.ceil(rawBucketSize / 5000) * 5000 || 5000;

        const buckets = {};
        let overflowCount = 0;

        prices.forEach((p) => {
            if (p > p95) {
                overflowCount++;
                return;
            }
            const bucketStart =
                p05 + Math.floor((p - p05) / bucketSize) * bucketSize;
            buckets[bucketStart] = (buckets[bucketStart] || 0) + 1;
        });

        const bucketKeys = Object.keys(buckets)
            .map(Number)
            .sort((a, b) => a - b);
        const labels = bucketKeys.map((k) => formatPrice(k));
        const counts = bucketKeys.map((k) => buckets[k]);

        if (overflowCount > 0) {
            labels.push(`${formatPrice(p95)}+`);
            counts.push(overflowCount);
        }

        new Chart(document.getElementById("land-registry-histogram"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Sales",
                        data: counts,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: "Price distribution" },
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                    x: { ticks: { maxRotation: 45, minRotation: 45 } },
                },
            },
        });
    }
})();
