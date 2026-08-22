/*
 * planning-table.js
 *
 * Loads /assets/data/planning-applications.json and renders rows into
 * #planning-table tbody. Click-to-sort on <th data-sort="..."> headers,
 * matching the land-registry-table pattern.
 */

(function () {
    const DATA_URL = "/assets/data/planning-applications.json";
    const TABLE_ID = "planning-table";

    let records = [];
    let currentSort = { key: "received_date", direction: "desc" };

    function statusClass(status) {
        const s = (status || "").toLowerCase();
        if (s.includes("approv") || s.includes("grant"))
            return "status-approved";
        if (s.includes("refus")) return "status-refused";
        return "status-pending";
    }

    function formatDate(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        return d.toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }

    function renderRows() {
        const table = document.getElementById(TABLE_ID);
        if (!table) return;
        const tbody = table.querySelector("tbody");
        if (!tbody) return;

        tbody.innerHTML = "";

        records.forEach((r) => {
            const tr = document.createElement("tr");
            tr.classList.add(statusClass(r.status));

            tr.innerHTML = `
        <td data-value="${r.received_date || ""}">${formatDate(r.received_date)}</td>
        <td>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">${escapeHtml(r.description || "")}</a>` : escapeHtml(r.description || "")}</td>
        <td>${escapeHtml(r.address || "")}</td>
        <td>${escapeHtml(r.postcode || "")}</td>
        <td data-value="${r.units || 0}">${r.units || "-"}</td>
        <td>${escapeHtml(r.status || "")}</td>
      `;

            tbody.appendChild(tr);
        });
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function sortRecords(key) {
        const direction =
            currentSort.key === key && currentSort.direction === "asc"
                ? "desc"
                : "asc";
        currentSort = { key, direction };

        records.sort((a, b) => {
            let valA = a[key];
            let valB = b[key];

            if (key === "units") {
                valA = valA || 0;
                valB = valB || 0;
            } else {
                valA = (valA || "").toString().toLowerCase();
                valB = (valB || "").toString().toLowerCase();
            }

            if (valA < valB) return direction === "asc" ? -1 : 1;
            if (valA > valB) return direction === "asc" ? 1 : -1;
            return 0;
        });

        renderRows();
        updateSortIndicators();
    }

    function updateSortIndicators() {
        const table = document.getElementById(TABLE_ID);
        if (!table) return;
        table.querySelectorAll("th[data-sort]").forEach((th) => {
            th.classList.remove("sort-asc", "sort-desc");
            if (th.dataset.sort === currentSort.key) {
                th.classList.add(
                    currentSort.direction === "asc" ? "sort-asc" : "sort-desc",
                );
            }
        });
    }

    function attachSortHandlers() {
        const table = document.getElementById(TABLE_ID);
        if (!table) return;
        table.querySelectorAll("th[data-sort]").forEach((th) => {
            th.style.cursor = "pointer";
            th.addEventListener("click", () => sortRecords(th.dataset.sort));
        });
    }

    async function init() {
        const table = document.getElementById(TABLE_ID);
        if (!table) return;

        try {
            const resp = await fetch(DATA_URL);
            if (!resp.ok)
                throw new Error(`Failed to load planning data: ${resp.status}`);
            records = await resp.json();
        } catch (err) {
            const tbody = table.querySelector("tbody");
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="6">Unable to load planning applications right now.</td></tr>`;
            }
            console.error(err);
            return;
        }

        attachSortHandlers();
        sortRecords("received_date"); // initial sort: newest first
    }

    document.addEventListener("DOMContentLoaded", init);
})();
