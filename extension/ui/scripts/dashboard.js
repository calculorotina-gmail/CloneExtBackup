/**
 * Chrome Extension Backup Pro - Dashboard Controller
 * Calculates and updates KPIs, recent activities, and quick batch actions.
 */

class DashboardController {
  constructor() {
    this.stats = {
      installed: 0,
      validBackups: 0,
      withoutBackup: 0,
      usedSpaceFormatted: "0 B",
      lastBackupDate: "Nenhum",
      integrityPct: 100
    };
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const bkpActBtn = document.getElementById("btn-quick-backup-active");
    if (bkpActBtn) bkpActBtn.addEventListener("click", () => this.runBatchBackupActive());

    const valBtn = document.getElementById("btn-quick-validate");
    if (valBtn) valBtn.addEventListener("click", () => window.app.navigate("backups"));

    const schedBtn = document.getElementById("btn-quick-scheduler");
    if (schedBtn) schedBtn.addEventListener("click", () => window.app.navigate("scheduler"));

    const findBtn = document.getElementById("btn-quick-find-backups");
    if (findBtn) findBtn.addEventListener("click", () => window.backupsController.scanCustomFolderPrompt());
  }

  async loadDashboardData() {
    this.init();
    try {
      const activeProfile = window.app.currentProfileId || "Default";
      
      // Fetch extensions, backups, and system info concurrently with fault-tolerance
      const [extResult, backupResult, sysResult] = await Promise.allSettled([
        window.bridge.getExtensions(activeProfile),
        window.bridge.listBackups(),
        window.bridge.getSystemInfo()
      ]);

      let exts = [];
      if (extResult.status === "fulfilled" && extResult.value && extResult.value.extensions) {
        exts = extResult.value.extensions;
      } else if (typeof chrome !== "undefined" && chrome.management && typeof chrome.management.getAll === "function") {
        try {
          const mgmtExts = await new Promise((resolve) => chrome.management.getAll(resolve));
          exts = (mgmtExts || []).filter((e) => e.type !== "theme" && e.id !== chrome.runtime.id);
        } catch (e) {
          console.warn("[Dashboard] Fallback chrome.management falhou:", e);
        }
      }

      let backups = [];
      if (backupResult.status === "fulfilled" && backupResult.value && backupResult.value.backups) {
        backups = backupResult.value.backups;
      }

      // Calculate KPIs
      this.stats.installed = exts.length;
      
      const extsWithBackup = exts.filter((e) => e.has_backup);
      this.stats.withoutBackup = Math.max(0, exts.length - extsWithBackup.length);

      // Backups stats
      this.stats.validBackups = backups.filter((b) => b.integrity_status === "Válido").length;

      let totalBackupBytes = backups.reduce((acc, b) => acc + (b.size_bytes || 0), 0);
      this.stats.usedSpaceFormatted = this.formatBytes(totalBackupBytes);

      if (backups.length > 0) {
        this.stats.lastBackupDate = backups[0].backup_date || "Hoje";
      } else {
        this.stats.lastBackupDate = "Nenhum";
      }

      const totalVerifiable = backups.length;
      this.stats.integrityPct = totalVerifiable > 0 
        ? Math.round((this.stats.validBackups / totalVerifiable) * 100) 
        : 100;

      this.renderKpis();
      this.renderRecentBackups(backups.slice(0, 5));
    } catch (err) {
      console.error("[Dashboard] Erro ao carregar dados:", err);
    }
  }

  renderKpis() {
    document.getElementById("kpi-installed").textContent = this.stats.installed;
    document.getElementById("kpi-valid-backups").textContent = this.stats.validBackups;
    document.getElementById("kpi-without-backup").textContent = this.stats.withoutBackup;
    document.getElementById("kpi-used-space").textContent = this.stats.usedSpaceFormatted;
    document.getElementById("kpi-last-backup").textContent = this.stats.lastBackupDate;
    document.getElementById("kpi-integrity").textContent = `${this.stats.integrityPct}%`;
  }

  renderRecentBackups(recentList) {
    const tbody = document.getElementById("dashboard-recent-tbody");
    if (!tbody) return;

    if (recentList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum backup realizado ainda. Vá a 'Extensões' para criar a sua primeira cópia de segurança local.</td></tr>`;
      return;
    }

    tbody.innerHTML = recentList
      .map(
        (b) => `
      <tr>
        <td style="font-weight: 600;">${b.extension_name}</td>
        <td><span class="badge badge-gray">v${b.version}</span></td>
        <td>${b.chrome_profile || "Default"}</td>
        <td>${b.size_formatted}</td>
        <td><span class="badge ${b.integrity_status === "Válido" ? "badge-success" : "badge-danger"}">${b.integrity_status}</span></td>
      </tr>
    `
      )
      .join("");
  }

  formatBytes(bytes) {
    if (bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    let v = bytes;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(2)} ${units[i]}`;
  }

  async runBatchBackupActive() {
    const activeProfile = window.app.currentProfileId || "Default";
    const resp = await window.bridge.getExtensions(activeProfile);
    const activeExts = (resp.extensions || []).filter((e) => e.is_enabled);

    if (activeExts.length === 0) {
      window.app.showToast("Nenhuma extensão ativa encontrada para backup.", "warning");
      return;
    }

    window.app.showToast(`Iniciando backup em lote de ${activeExts.length} extensões ativas...`, "info");
    let success = 0;
    let errors = 0;

    for (const ext of activeExts) {
      try {
        const res = await window.bridge.backupExtension({
          extension_id: ext.extension_id,
          extension_name: ext.name,
          version: ext.version,
          source_dir: ext.local_path,
          profile_id: activeProfile
        });
        if (res.success) {
          success++;
        } else {
          errors++;
        }
      } catch (e) {
        errors++;
      }
    }

    window.app.showToast(`Backup concluído: ${success} com sucesso, ${errors} com erro.`, success > 0 ? "success" : "error");
    this.loadDashboardData();
  }
}

window.dashboardController = new DashboardController();
