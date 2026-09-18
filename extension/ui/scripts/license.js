/**
 * Chrome Extension Backup Pro - License Controller
 * Manages commercial licensing tiers, key validation, and feature gating display.
 */

class LicenseController {
  constructor() {
    this.licenseInfo = {};
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const actBtn = document.getElementById("btn-activate-license");
    if (actBtn) actBtn.addEventListener("click", () => this.activateKey());

    const deactBtn = document.getElementById("btn-deactivate-license");
    if (deactBtn) deactBtn.addEventListener("click", () => this.deactivateLicense());
  }

  async loadLicense() {
    this.init();
    try {
      const res = await window.bridge.getLicense();
      this.licenseInfo = res.license || {};
      this.renderLicenseUI();
    } catch (e) {
      console.error("Erro ao carregar licença:", e);
    }
  }

  renderLicenseUI() {
    const tierSpan = document.getElementById("license-current-tier");
    const nameSpan = document.getElementById("license-registered-to");
    const keySpan = document.getElementById("license-key-masked");
    const badgeTop = document.getElementById("header-license-badge");

    const tier = this.licenseInfo.tier || "free";
    const tierName = this.licenseInfo.features?.name || "Plano Gratuito";

    if (tierSpan) tierSpan.textContent = tierName;
    if (nameSpan) nameSpan.textContent = this.licenseInfo.registered_to || "Utilizador Não Registado";
    if (keySpan) keySpan.textContent = this.licenseInfo.license_key || "Nenhuma chave ativa";

    if (badgeTop) {
      badgeTop.textContent = tier.toUpperCase();
      badgeTop.className = `badge ${tier === "ultimate" ? "badge-success" : (tier === "premium" ? "badge-info" : "badge-gray")}`;
    }

    const deactBtn = document.getElementById("btn-deactivate-license");
    if (deactBtn) {
      deactBtn.style.display = tier !== "free" ? "inline-flex" : "none";
    }
  }

  async activateKey() {
    const input = document.getElementById("license-key-input");
    const nameInput = document.getElementById("license-name-input");
    const key = input ? input.value.trim() : "";
    const name = nameInput ? nameInput.value.trim() : "Utilizador Registado";

    if (!key) {
      window.app.showToast("Insira uma chave de licença válida.", "warning");
      return;
    }

    window.app.showToast("A validar chave de licença com assinatura criptográfica...", "info");

    try {
      const res = await window.bridge.activateLicense(key, name);
      if (res.success) {
        window.app.showToast(res.message, "success");
        if (input) input.value = "";
        this.loadLicense();
      } else {
        window.app.showErrorModal({
          code: "LC-0002",
          title: "Chave de Licença Inválida",
          description: res.message || "A chave de ativação fornecida não possui uma assinatura ou formato válido.",
          operation: "license_activation",
          solution: "Verifique a chave e certifique-se de que segue a sintaxe XXXX-XXXX-XXXX-XXXX-XXXX."
        });
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }

  async deactivateLicense() {
    if (!confirm("Tem a certeza que deseja desativar a sua licença neste computador?")) {
      return;
    }

    try {
      const res = await window.bridge.deactivateLicense();
      if (res.success) {
        window.app.showToast(res.message, "info");
        this.loadLicense();
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }
}

window.licenseController = new LicenseController();
