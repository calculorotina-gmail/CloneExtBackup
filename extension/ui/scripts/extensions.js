/**
 * Chrome Extension Backup Pro - Extensions View Controller
 * Lists installed extensions with rich metadata, search, filtering, and bulk actions.
 * Complies 100% with Manifest V3 CSP (zero inline event handlers).
 */

class ExtensionsController {
  constructor() {
    this.extensions = [];
    this.filteredExtensions = [];
    this.selectedIds = new Set();
    this.currentFilter = "all";
    this.searchQuery = "";
    this._initialized = false;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    // Filter buttons
    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const filter = e.target.dataset.filter;
        if (filter) this.setFilter(filter);
      });
    });

    // Search input
    const searchInput = document.getElementById("ext-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.setSearch(e.target.value);
      });
    }

    // Select all checkbox
    const selectAllCheckbox = document.getElementById("ext-select-all");
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", (e) => {
        this.toggleSelectAll(e.target.checked);
      });
    }

    // Bulk backup button
    const bulkBtn = document.getElementById("btn-bulk-backup");
    if (bulkBtn) {
      bulkBtn.addEventListener("click", () => {
        this.runBulkBackup();
      });
    }

    // Table body event delegation for action buttons & row checkboxes
    const tbody = document.getElementById("extensions-tbody");
    if (tbody) {
      tbody.addEventListener("click", (e) => {
        const target = e.target.closest("button");
        if (!target) return;

        const action = target.dataset.action;
        const extId = target.dataset.id;
        if (!extId) return;

        if (action === "backup") {
          this.triggerBackup(extId);
        } else if (action === "validate") {
          this.triggerValidate(extId);
        } else if (action === "restore") {
          this.triggerRestore(extId);
        }
      });

      tbody.addEventListener("change", (e) => {
        if (e.target.classList.contains("row-select")) {
          this.toggleSelectRow(e.target.dataset.id, e.target.checked);
        }
      });
    }
  }

  async loadExtensions(profileId = "Default") {
    this.init();
    try {
      const tbody = document.getElementById("extensions-tbody");
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 28px; color: var(--text-muted);"><span style="font-size: 18px;">⏳</span> A carregar extensões instaladas no perfil ${profileId}...</td></tr>`;
      }

      let res = null;
      try {
        res = await window.bridge.getExtensions(profileId);
      } catch (bridgeErr) {
        console.warn("[Extensions] Native bridge indisponível, tentando chrome.management:", bridgeErr);
        if (typeof chrome !== "undefined" && chrome.management && typeof chrome.management.getAll === "function") {
          try {
            const mgmtList = await new Promise((resolve) => chrome.management.getAll(resolve));
            const filtered = (mgmtList || []).filter((e) => e.type !== "theme" && e.id !== chrome.runtime.id);
            res = {
              extensions: filtered.map((e) => ({
                extension_id: e.id,
                name: e.name,
                version: e.version,
                profile_id: profileId,
                status: e.enabled ? "Ativa" : "Desativada",
                is_enabled: e.enabled,
                local_path: e.installType === "development" ? "Pasta local (Modo Programador)" : "Chrome Web Store / Cache",
                size_formatted: "Modo leitura",
                file_count: 0,
                modified_date: "Instalada no Chrome",
                description: e.description || "",
                manifest_version: 3,
                has_backup: false,
                last_backup_date: "Nenhum backup",
                last_backup_status: "Sem backup",
                icon_url: (e.icons && e.icons.length > 0) ? e.icons[e.icons.length - 1].url : null,
                is_unpacked: e.installType === "development"
              }))
            };
            window.app.showToast("Host nativo desconectado. As extensões foram carregadas via Chrome API (modo de leitura).", "warning");
          } catch (mgmtErr) {
            throw bridgeErr;
          }
        } else {
          throw bridgeErr;
        }
      }

      this.extensions = (res && res.extensions) ? res.extensions : [];
      this.selectedIds.clear();

      // Update sidebar badge
      const navBadge = document.getElementById("nav-ext-count");
      if (navBadge) navBadge.textContent = this.extensions.length;

      this.applyFilters();
    } catch (err) {
      console.error("[Extensions] Erro ao carregar extensões:", err);
      window.app.showToast(`Falha ao carregar extensões: ${err.message}`, "error");
    }
  }

  setFilter(filterName) {
    this.currentFilter = filterName;
    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.filter === filterName);
    });
    this.applyFilters();
  }

  setSearch(query) {
    this.searchQuery = (query || "").toLowerCase().trim();
    this.applyFilters();
  }

  applyFilters() {
    let list = [...this.extensions];

    // Filter type
    if (this.currentFilter === "with_backup") {
      list = list.filter((e) => e.has_backup);
    } else if (this.currentFilter === "without_backup") {
      list = list.filter((e) => !e.has_backup);
    } else if (this.currentFilter === "active") {
      list = list.filter((e) => e.is_enabled);
    } else if (this.currentFilter === "disabled") {
      list = list.filter((e) => !e.is_enabled);
    }

    // Search query
    if (this.searchQuery) {
      list = list.filter((e) => {
        return (
          e.name.toLowerCase().includes(this.searchQuery) ||
          e.extension_id.toLowerCase().includes(this.searchQuery) ||
          e.version.toLowerCase().includes(this.searchQuery) ||
          (e.profile_id && e.profile_id.toLowerCase().includes(this.searchQuery)) ||
          (e.last_backup_date && e.last_backup_date.toLowerCase().includes(this.searchQuery))
        );
      });
    }

    this.filteredExtensions = list;
    this.updateSelectionUI();
    this.renderTable();
  }

  toggleSelectAll(checked) {
    if (checked) {
      this.filteredExtensions.forEach((e) => this.selectedIds.add(e.extension_id));
    } else {
      this.selectedIds.clear();
    }
    this.updateSelectionUI();
    this.renderTable();
  }

  toggleSelectRow(extId, checked) {
    if (checked) {
      this.selectedIds.add(extId);
    } else {
      this.selectedIds.delete(extId);
    }
    this.updateSelectionUI();
  }

  updateSelectionUI() {
    const count = this.selectedIds.size;
    const btn = document.getElementById("btn-bulk-backup");
    if (btn) {
      btn.style.display = count > 0 ? "inline-flex" : "none";
      btn.textContent = `Fazer Backup Selecionadas (${count})`;
    }
    const selectAllCheckbox = document.getElementById("ext-select-all");
    if (selectAllCheckbox) {
      selectAllCheckbox.checked = count > 0 && count === this.filteredExtensions.length;
    }
  }

  renderTable() {
    const tbody = document.getElementById("extensions-tbody");
    if (!tbody) return;

    if (this.filteredExtensions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-muted);">Nenhuma extensão encontrada com os filtros selecionados.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.filteredExtensions
      .map((ext) => {
        const isSelected = this.selectedIds.has(ext.extension_id);
        const iconSrc = ext.icon_url || "icons/icon48.png";
        const statusBadge = ext.is_enabled
          ? `<span class="badge badge-success">Ativa</span>`
          : `<span class="badge badge-warning">Desativada</span>`;

        let integrityBadge = `<span class="badge badge-gray">Sem backup</span>`;
        if (ext.has_backup) {
          integrityBadge = `<span class="badge badge-success">Válido (${ext.backup_count})</span>`;
        }

        return `
        <tr>
          <td style="width: 38px;">
            <input type="checkbox" class="row-select" data-id="${ext.extension_id}" ${isSelected ? "checked" : ""}>
          </td>
          <td>
            <div class="ext-cell">
              <img class="ext-icon" src="${iconSrc}" alt="icon" onerror="this.src='icons/icon48.png'">
              <div class="ext-details">
                <span class="ext-name" title="${ext.name}">${ext.name}</span>
                <span class="ext-id">${ext.extension_id}</span>
              </div>
            </div>
          </td>
          <td><span class="badge badge-gray">v${ext.version}</span></td>
          <td>${ext.profile_id}</td>
          <td>${statusBadge}</td>
          <td style="font-size: 12px; color: var(--text-secondary);">${ext.last_backup_date}</td>
          <td style="font-weight: 500;">${ext.size_formatted}</td>
          <td>${integrityBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-primary btn-sm" data-action="backup" data-id="${ext.extension_id}" title="Criar Backup Local">Backup</button>
              <button class="btn btn-secondary btn-sm" data-action="validate" data-id="${ext.extension_id}" title="Validar Integridade">Validar</button>
              <button class="btn btn-secondary btn-sm" data-action="restore" data-id="${ext.extension_id}" title="Restaurar Extensão">Restaurar</button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");
  }

  async triggerBackup(extId) {
    const ext = this.extensions.find((e) => e.extension_id === extId);
    if (!ext) return;

    const btn = document.querySelector(`button[data-action="backup"][data-id="${extId}"]`);
    if (btn) {
      btn.disabled = true;
      btn.textContent = "⏳...";
    }

    window.app.showToast(`A iniciar cópia física de '${ext.name}'...`, "info");
    try {
      const res = await window.bridge.backupExtension({
        extension_id: ext.extension_id,
        extension_name: ext.name,
        version: ext.version,
        source_dir: ext.local_path,
        profile_id: ext.profile_id
      });

      if (res.success) {
        window.app.showToast(`Backup concluído: ${res.final_size_formatted} gravados com SHA-256!`, "success");
        this.loadExtensions(ext.profile_id);
      } else {
        window.app.showErrorModal(res.error);
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Backup";
        }
      }
    } catch (e) {
      window.app.showToast(`Erro ao criar backup: ${e.message}`, "error");
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Backup";
      }
    }
  }

  async triggerValidate(extId) {
    const ext = this.extensions.find((e) => e.extension_id === extId);
    if (!ext) return;
    if (!ext.has_backup) {
      window.app.showToast("Esta extensão ainda não possui um backup criado.", "warning");
      return;
    }
    window.app.navigate("backups");
  }

  async triggerRestore(extId) {
    window.app.navigate("restore");
  }

  async runBulkBackup() {
    const ids = Array.from(this.selectedIds);
    if (ids.length === 0) {
      window.app.showToast("Nenhuma extensão selecionada. Marque as caixas de seleção primeiro.", "warning");
      return;
    }

    const bulkBtn = document.getElementById("btn-bulk-backup");
    if (bulkBtn) {
      bulkBtn.disabled = true;
    }

    window.app.showToast(`A iniciar backup em lote de ${ids.length} extensões...`, "info");
    let ok = 0;
    let err = 0;

    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const ext = this.extensions.find((e) => e.extension_id === id);
      if (ext) {
        if (bulkBtn) {
          bulkBtn.textContent = `⏳ [${i + 1}/${ids.length}] ${ext.name.substring(0, 16)}...`;
        }
        window.app.showToast(`[${i + 1}/${ids.length}] A processar ${ext.name}...`, "info");
        try {
          const res = await window.bridge.backupExtension({
            extension_id: ext.extension_id,
            extension_name: ext.name,
            version: ext.version,
            source_dir: ext.local_path,
            profile_id: ext.profile_id
          });
          if (res && res.success) {
            ok++;
          } else {
            err++;
            console.error("Erro no backup de", ext.name, res ? res.error : "sem resposta");
          }
        } catch (ex) {
          err++;
          console.error("Exceção no backup de", ext.name, ex);
        }
      }
    }

    window.app.showToast(`Backup em lote finalizado: ${ok} com sucesso, ${err} erros.`, ok > 0 ? "success" : "error");
    this.selectedIds.clear();
    this.updateSelectionUI();
    if (bulkBtn) {
      bulkBtn.disabled = false;
    }
    this.loadExtensions(window.app.currentProfileId);
  }
}

window.extensionsController = new ExtensionsController();
