/**
 * Chrome Extension Backup Pro - Compare Versions Controller
 * Visual diff inspector comparing files, sizes, and SHA-256 hashes between two backups.
 */

class CompareController {
  constructor() {
    this.itemAPath = "";
    this.itemBPath = "";
    this.diffResult = null;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const runBtn = document.getElementById("btn-run-comparison");
    if (runBtn) runBtn.addEventListener("click", () => this.runComparison());
  }

  async initCompareView() {
    this.init();
    await this.populateDropdowns();
  }

  async populateDropdowns() {
    const selA = document.getElementById("compare-item-a");
    const selB = document.getElementById("compare-item-b");
    if (!selA || !selB) return;

    try {
      const res = await window.bridge.listBackups();
      const backups = res.backups || [];

      const opts = backups
        .map((b) => `<option value="${b.path}">${b.extension_name} (v${b.version}) - ${b.backup_date}</option>`)
        .join("");

      selA.innerHTML = opts;
      selB.innerHTML = opts;

      if (this.itemAPath) selA.value = this.itemAPath;
      if (backups.length > 1) {
        selB.selectedIndex = 1;
      }
    } catch (e) {
      console.error("Erro ao carregar lista de comparação:", e);
    }
  }

  setItemA(path) {
    this.itemAPath = path;
    const selA = document.getElementById("compare-item-a");
    if (selA) selA.value = path;
  }

  async runComparison() {
    const selA = document.getElementById("compare-item-a");
    const selB = document.getElementById("compare-item-b");
    const pathA = selA ? selA.value : "";
    const pathB = selB ? selB.value : "";

    if (!pathA || !pathB) {
      window.app.showToast("Selecione duas versões para comparar.", "warning");
      return;
    }

    if (pathA === pathB) {
      window.app.showToast("Selecione duas versões ou backups diferentes.", "warning");
      return;
    }

    window.app.showToast("A comparar ficheiros e hashes criptográficos...", "info");

    try {
      const res = await window.bridge.compareBackups(pathA, pathB);
      if (res.success) {
        this.diffResult = res;
        this.renderDiffSummary(res);
        this.renderDiffTable(res);
      } else {
        window.app.showToast("Falha na comparação de versões.", "error");
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }

  renderDiffSummary(res) {
    const summaryBox = document.getElementById("compare-summary");
    if (!summaryBox) return;

    summaryBox.style.display = "grid";
    document.getElementById("diff-added-count").textContent = res.counts.added;
    document.getElementById("diff-removed-count").textContent = res.counts.removed;
    document.getElementById("diff-modified-count").textContent = res.counts.modified;
    document.getElementById("diff-identical-count").textContent = res.counts.identical;
  }

  renderDiffTable(res) {
    const tbody = document.getElementById("compare-diff-tbody");
    if (!tbody) return;

    const rows = [];
    const details = res.details;

    // Added files
    details.added.forEach((f) => {
      rows.push(`
        <tr style="background: rgba(16, 185, 129, 0.08);">
          <td><span class="badge badge-success">+ Adicionado</span></td>
          <td style="font-family: monospace; font-size: 12px;">${f.path}</td>
          <td>${f.size_b_formatted}</td>
          <td style="font-family: monospace; font-size: 11px;">${f.hash_b.slice(0, 16)}...</td>
        </tr>
      `);
    });

    // Modified files
    details.modified.forEach((f) => {
      rows.push(`
        <tr style="background: rgba(245, 158, 11, 0.08);">
          <td><span class="badge badge-warning">~ Alterado</span></td>
          <td style="font-family: monospace; font-size: 12px;">${f.path}</td>
          <td>${f.size_a_formatted} → ${f.size_b_formatted} (${f.diff_formatted})</td>
          <td style="font-family: monospace; font-size: 11px;">${f.hash_a.slice(0, 8)}... → ${f.hash_b.slice(0, 8)}...</td>
        </tr>
      `);
    });

    // Removed files
    details.removed.forEach((f) => {
      rows.push(`
        <tr style="background: rgba(239, 68, 68, 0.08);">
          <td><span class="badge badge-danger">- Removido</span></td>
          <td style="font-family: monospace; font-size: 12px;">${f.path}</td>
          <td>${f.size_a_formatted}</td>
          <td style="font-family: monospace; font-size: 11px;">${f.hash_a.slice(0, 16)}...</td>
        </tr>
      `);
    });

    // Identical files
    details.identical.slice(0, 10).forEach((f) => {
      rows.push(`
        <tr>
          <td><span class="badge badge-gray">= Igual</span></td>
          <td style="font-family: monospace; font-size: 12px; color: var(--text-muted);">${f.path}</td>
          <td>${f.size_formatted}</td>
          <td style="font-family: monospace; font-size: 11px; color: var(--text-muted);">${f.hash.slice(0, 16)}...</td>
        </tr>
      `);
    });

    if (details.identical.length > 10) {
      rows.push(`
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-muted); font-size: 12px; padding: 10px;">
            ... e mais ${details.identical.length - 10} ficheiros idênticos.
          </td>
        </tr>
      `);
    }

    tbody.innerHTML = rows.join("");
  }
}

window.compareController = new CompareController();
