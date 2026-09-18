/**
 * Chrome Extension Backup Pro - History Controller
 * Audit trail of all operations: Backup, Restore, Rollback, Validation, and Delete.
 */

class HistoryController {
  constructor() {
    this.entries = [];
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const exportBtn = document.getElementById("btn-export-history");
    if (exportBtn) exportBtn.addEventListener("click", () => this.exportHistoryJSON());
  }

  async loadHistory() {
    this.init();
    try {
      const tbody = document.getElementById("history-tbody");
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">A carregar histórico de operações...</td></tr>`;
      }

      const res = await window.bridge.getHistory();
      this.entries = res.history || [];
      this.renderTable();
    } catch (e) {
      console.error("Erro ao carregar histórico:", e);
    }
  }

  renderTable() {
    const tbody = document.getElementById("history-tbody");
    if (!tbody) return;

    if (this.entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 32px; color: var(--text-muted);">Nenhuma operação registada no histórico.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.entries
      .map((entry) => {
        let opBadge = `<span class="badge badge-info">${entry.action}</span>`;
        if (entry.action === "Backup") opBadge = `<span class="badge badge-primary">${entry.action}</span>`;
        else if (entry.action === "Restore") opBadge = `<span class="badge badge-success">${entry.action}</span>`;
        else if (entry.action === "Rollback") opBadge = `<span class="badge badge-warning">${entry.action}</span>`;
        else if (entry.action === "Delete") opBadge = `<span class="badge badge-danger">${entry.action}</span>`;

        const resBadge = entry.result === "Sucesso"
          ? `<span class="badge badge-success">Sucesso</span>`
          : `<span class="badge badge-danger">Falha</span>`;

        return `
        <tr>
          <td style="font-size: 12px; color: var(--text-secondary); white-space: nowrap;">${entry.timestamp}</td>
          <td>${opBadge}</td>
          <td style="font-weight: 600;">${entry.extension_name || "-"}</td>
          <td>${entry.profile_id || "Default"}</td>
          <td>${entry.version ? "v" + entry.version : "-"}</td>
          <td>${resBadge}</td>
          <td style="font-size: 12px; color: var(--danger); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${entry.errors || ''}">${entry.errors || "-"}</td>
        </tr>
      `;
      })
      .join("");
  }

  exportHistoryJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.entries, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `historico_backups_${new Date().toISOString().slice(0, 10)}.json`);
    dlAnchor.click();
  }
}

window.historyController = new HistoryController();
