/**
 * Chrome Extension Backup Pro - Reports Controller
 * Generates and exports detailed diagnostic and operation reports.
 */

class ReportsController {
  constructor() {
    this.currentReport = null;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const refBtn = document.getElementById("btn-refresh-report");
    if (refBtn) refBtn.addEventListener("click", () => this.generateLatestReport());

    const txtBtn = document.getElementById("btn-export-report-txt");
    if (txtBtn) txtBtn.addEventListener("click", () => this.exportTXT());

    const jsonBtn = document.getElementById("btn-export-report-json");
    if (jsonBtn) jsonBtn.addEventListener("click", () => this.exportJSON());
  }

  async generateLatestReport() {
    this.init();
    try {
      const hist = await window.bridge.getHistory();
      const backups = await window.bridge.listBackups();
      const sys = await window.bridge.getSystemInfo();

      const latestBackup = (backups.backups || [])[0] || {};
      const latestOp = (hist.history || [])[0] || {};

      this.currentReport = {
        title: "CHROME EXTENSION BACKUP PRO - RELATÓRIO TÉCNICO",
        generated_at: new Date().toLocaleString("pt-PT"),
        system: {
          os: sys.os,
          arch: sys.arch,
          chrome_version: sys.chrome_version,
          free_space: sys.disk?.free_formatted || "Desconhecido"
        },
        latest_operation: {
          action: latestOp.action || "N/A",
          target: latestOp.extension_name || "N/A",
          version: latestOp.version || "N/A",
          profile: latestOp.profile_id || "Default",
          result: latestOp.result || "N/A",
          timestamp: latestOp.timestamp || "N/A"
        },
        latest_backup: {
          extension: latestBackup.extension_name || "Nenhum",
          version: latestBackup.version || "1.0",
          profile: latestBackup.chrome_profile || "Default",
          files: latestBackup.file_count || 0,
          size: latestBackup.size_formatted || "0 B",
          integrity: latestBackup.integrity_status || "Válido",
          path: latestBackup.path || "N/A"
        }
      };

      this.renderReport();
    } catch (e) {
      console.error("Erro ao gerar relatório:", e);
    }
  }

  renderReport() {
    const pre = document.getElementById("report-preview");
    if (!pre || !this.currentReport) return;

    const r = this.currentReport;
    const text = `================================================================
          CHROME EXTENSION BACKUP PRO - RELATÓRIO
================================================================
Data de Emissão:    ${r.generated_at}
Sistema Operativo:  ${r.system.os} (${r.system.arch})
Versão do Chrome:   ${r.system.chrome_version}
Espaço Livre Disco: ${r.system.free_space}

--- ÚLTIMA OPERAÇÃO REGISTADA ---
Ação:               ${r.latest_operation.action}
Extensão Alvo:      ${r.latest_operation.target} (v${r.latest_operation.version})
Perfil Chrome:      ${r.latest_operation.profile}
Resultado:          ${r.latest_operation.result}
Data/Hora:          ${r.latest_operation.timestamp}

--- ÚLTIMO BACKUP NO CATÁLOGO ---
Extensão:           ${r.latest_backup.extension} (v${r.latest_backup.version})
Perfil de Origem:   ${r.latest_backup.profile}
Ficheiros Gravados: ${r.latest_backup.files}
Tamanho do Arquivo: ${r.latest_backup.size}
Integridade SHA256: ${r.latest_backup.integrity}
Caminho no Disco:   ${r.latest_backup.path}

================================================================
Relatório gerado com sucesso por Chrome Extension Backup Pro v2.0
`;
    pre.textContent = text;
  }

  exportTXT() {
    if (!this.currentReport) return;
    const pre = document.getElementById("report-preview");
    const content = pre ? pre.textContent : "";
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_backup_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
  }

  exportJSON() {
    if (!this.currentReport) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.currentReport, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = `relatorio_backup_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  }
}

window.reportsController = new ReportsController();
