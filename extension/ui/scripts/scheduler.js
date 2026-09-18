/**
 * Chrome Extension Backup Pro - Scheduler Controller
 * Manages automated backup frequency and integration with Windows Task Scheduler.
 */

class SchedulerController {
  constructor() {
    this.schedule = {};
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const saveBtn = document.getElementById("btn-save-schedule");
    if (saveBtn) saveBtn.addEventListener("click", () => this.saveSchedule());
  }

  async loadSchedule() {
    this.init();
    try {
      const res = await window.bridge.getSchedule();
      this.schedule = res.schedule || {};
      this.populateForm();
    } catch (e) {
      console.error("Erro ao carregar agendamento:", e);
    }
  }

  populateForm() {
    const enableCb = document.getElementById("sched-enabled");
    const freqSel = document.getElementById("sched-freq");
    const timeInput = document.getElementById("sched-time");
    const allProfCb = document.getElementById("sched-all-profiles");
    const incCb = document.getElementById("sched-incremental");
    const lastRunSpan = document.getElementById("sched-last-run");
    const lastStatusSpan = document.getElementById("sched-last-status");

    if (enableCb) enableCb.checked = !!this.schedule.enabled;
    if (freqSel) freqSel.value = this.schedule.frequency || "daily";
    if (timeInput) timeInput.value = this.schedule.time || "03:00";
    if (allProfCb) allProfCb.checked = this.schedule.backup_all_profiles !== false;
    if (incCb) incCb.checked = this.schedule.is_incremental !== false;

    if (lastRunSpan) lastRunSpan.textContent = this.schedule.last_run || "Nunca executado";
    if (lastStatusSpan) lastStatusSpan.textContent = this.schedule.last_status || "Nenhum registo recente";
  }

  async saveSchedule() {
    const enableCb = document.getElementById("sched-enabled");
    const freqSel = document.getElementById("sched-freq");
    const timeInput = document.getElementById("sched-time");
    const allProfCb = document.getElementById("sched-all-profiles");
    const incCb = document.getElementById("sched-incremental");

    const newSchedule = {
      enabled: enableCb.checked,
      frequency: freqSel.value,
      time: timeInput.value || "03:00",
      backup_all_profiles: allProfCb.checked,
      is_incremental: incCb.checked,
      compression_level: 6,
      days: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    };

    window.app.showToast("A registar tarefa no Agendador do Windows (schtasks)...", "info");

    try {
      const res = await window.bridge.saveSchedule(newSchedule);
      if (res.success) {
        window.app.showToast(res.message || "Agendamento guardado com sucesso!", "success");
        this.loadSchedule();
      } else {
        window.app.showToast(res.message || "Erro ao agendar tarefa no Windows.", "error");
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }
}

window.schedulerController = new SchedulerController();
