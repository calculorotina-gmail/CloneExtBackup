/**
 * Chrome Extension Backup Pro - Main Application Controller
 * Handles navigation, theme management, profile switching, error modals, and initialization.
 */

class App {
  constructor() {
    this.currentView = "dashboard";
    this.currentProfileId = "Default";
    this.profiles = [];
  }

  async init() {
    console.log("[App] Inicializando Chrome Extension Backup Pro UI...");
    this.initTheme();
    this.initNavigation();
    this.initConnectionMonitor();
    await this.initProfiles();
    this.navigate("dashboard");
  }

  // Theme Management
  initTheme() {
    const savedTheme = localStorage.getItem("theme") || "system";
    this.setTheme(savedTheme);
  }

  setTheme(theme) {
    localStorage.setItem("theme", theme);
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
    } else {
      document.documentElement.setAttribute("data-theme", theme);
    }
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    this.setTheme(next);
  }

  // Navigation
  initNavigation() {
    document.querySelectorAll(".nav-item").forEach((item) => {
      item.addEventListener("click", () => {
        const viewId = item.dataset.view;
        if (viewId) this.navigate(viewId);
      });
    });

    // Theme toggle button
    const themeBtn = document.getElementById("btn-toggle-theme");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this.toggleTheme());
    }

    // Expand to full tab button
    const expandBtn = document.getElementById("btn-expand-tab");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        chrome.runtime.sendMessage({ action: "open_full_tab" });
      });
    }

    // Error modal close buttons
    const closeErrBtn = document.getElementById("btn-close-error-modal");
    if (closeErrBtn) closeErrBtn.addEventListener("click", () => this.closeErrorModal());
    const dismissErrBtn = document.getElementById("btn-dismiss-error-modal");
    if (dismissErrBtn) dismissErrBtn.addEventListener("click", () => this.closeErrorModal());
  }

  navigate(viewId) {
    this.currentView = viewId;

    // Update active class on nav items
    document.querySelectorAll(".nav-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.view === viewId);
    });

    // Update active class on view sections
    document.querySelectorAll(".view-section").forEach((sec) => {
      sec.classList.toggle("active", sec.id === `view-${viewId}`);
    });

    // Update page header
    const titleMap = {
      dashboard: { title: "Painel de Controlo (Dashboard)", desc: "Visão geral e métricas de cópias de segurança locais das extensões Chrome" },
      extensions: { title: "Extensões Instaladas", desc: "Gestão, identificação e backup de ficheiros físicos por perfil Chrome" },
      backups: { title: "Catálogo de Backups", desc: "Ficheiros .crxbackup guardados, verificação de integridade e arquivo" },
      restore: { title: "Restauro & Rollback", desc: "Reposição local segura de extensões com ponto de rollback prévio automático" },
      compare: { title: "Comparador de Versões", desc: "Diferenças detalhadas de ficheiros, hashes e tamanhos entre backups" },
      scheduler: { title: "Agendador de Tarefas", desc: "Automação de backups periódicos integrada com o Windows Task Scheduler" },
      history: { title: "Histórico de Operações", desc: "Registo de auditoria local de todas as operações executadas" },
      reports: { title: "Relatórios Técnicos", desc: "Diagnósticos completos de integridade e exportação de relatórios" },
      settings: { title: "Definições do Sistema", desc: "Configurações de pastas, compressão, encriptação AES-256 e retenção" },
      license: { title: "Licenciamento Comercial", desc: "Planos Gratuito, Premium e Ultimate com ativação criptográfica" },
      about: { title: "Sobre o Sistema", desc: "Compatibilidade do Windows, versão do Chrome e limitações técnicas oficiais" },
      privacy: { title: "Privacidade & Segurança", desc: "Garantia de retenção local estrita sem recolha de credenciais ou telemetria" }
    };

    const header = titleMap[viewId] || { title: "Chrome Extension Backup Pro", desc: "" };
    document.getElementById("page-title").textContent = header.title;
    document.getElementById("page-description").textContent = header.desc;

    // Refresh view data
    this.onViewActivated(viewId);
  }

  onViewActivated(viewId) {
    if (viewId === "dashboard") {
      window.dashboardController.loadDashboardData();
    } else if (viewId === "extensions") {
      window.extensionsController.loadExtensions(this.currentProfileId);
    } else if (viewId === "backups") {
      window.backupsController.loadBackups();
    } else if (viewId === "restore") {
      window.restoreController.initRestoreView();
    } else if (viewId === "compare") {
      window.compareController.initCompareView();
    } else if (viewId === "scheduler") {
      window.schedulerController.loadSchedule();
    } else if (viewId === "history") {
      window.historyController.loadHistory();
    } else if (viewId === "reports") {
      window.reportsController.generateLatestReport();
    } else if (viewId === "settings") {
      window.settingsController.loadSettings();
    } else if (viewId === "license") {
      window.licenseController.loadLicense();
    }
  }

  // Profile Switching
  async initProfiles() {
    const sel = document.getElementById("header-profile-select");
    if (!sel) return;

    try {
      const res = await window.bridge.getProfiles();
      this.profiles = res.profiles || [];

      if (this.profiles.length === 0) {
        sel.innerHTML = `<option value="Default">Perfil Padrão (Default)</option>`;
        return;
      }

      sel.innerHTML = this.profiles
        .map((p) => `<option value="${p.profile_id}">${p.name} (${p.profile_id})</option>`)
        .join("");

      sel.addEventListener("change", (e) => {
        this.currentProfileId = e.target.value;
        this.showToast(`Perfil alterado para: ${e.target.selectedOptions[0].text}`, "info");
        this.onViewActivated(this.currentView);
      });
    } catch (e) {
      console.error("Erro ao inicializar perfis:", e);
    }
  }

  // Native Host Connection Monitoring
  initConnectionMonitor() {
    const dot = document.getElementById("host-status-dot");
    const label = document.getElementById("host-status-label");

    const updateUI = (connected) => {
      if (dot) {
        dot.classList.toggle("connected", connected);
      }
      if (label) {
        label.textContent = connected ? "Host Conectado" : "Host Desconectado";
        label.style.color = connected ? "var(--success)" : "var(--danger)";
      }
    };

    window.bridge.onConnectionChange(updateUI);

    // Initial ping
    window.bridge
      .ping()
      .then((res) => updateUI(res && res.success))
      .catch(() => updateUI(false));
  }

  // Toast Notifications
  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Error Modal
  showErrorModal(errorObj) {
    const modal = document.getElementById("error-modal");
    if (!modal) return;

    const err = errorObj || {
      code: "NT-0000",
      title: "Erro na Operação",
      description: "Ocorreu um erro desconhecido.",
      solution: "Consulte os registos de log locais."
    };

    document.getElementById("error-modal-code").textContent = `CÓDIGO: ${err.code}`;
    document.getElementById("error-modal-title").textContent = err.title;
    document.getElementById("error-modal-desc").textContent = err.description;
    document.getElementById("error-modal-file").textContent = err.affected_file || "Nenhum ficheiro específico";
    document.getElementById("error-modal-solution").textContent = err.solution || "Tente novamente mais tarde.";

    modal.classList.add("open");
  }

  closeErrorModal() {
    const modal = document.getElementById("error-modal");
    if (modal) modal.classList.remove("open");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.app = new App();
  window.app.init();
});
