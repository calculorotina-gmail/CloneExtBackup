# Master Task Prompt: Chrome Extension Backup Pro (Windows)

> Este documento consolida todos os requisitos, arquitetura técnica, lições aprendidas e especificações desenvolvidas ao longo do projeto num **Master Prompt de Engenharia** reutilizável para Antigravity ou outros agentes de IA.

---

## 📋 Como Usar este Master Prompt

Para recriar este projeto de raiz ou pedir a um agente de IA para criar uma extensão idêntica com componente nativo Windows, copie o bloco abaixo e use o comando **/goal** ou **/plan** no Antigravity:

```markdown
/goal Crie uma extensão Google Chrome Premium profissional para Windows (Manifest V3) acompanhada de um Native Messaging Host local em Python para salvaguardar e repor ficheiros físicos reais das extensões do Google Chrome, de forma 100% offline e independente da Chrome Web Store.
```

---

## 📜 Master Prompt de Especificação Técnica Completa

```markdown
Você é um Engenheiro de Software Sénior e Arquiteto de Sistemas especialista em extensões Google Chrome (Manifest V3) e aplicações nativas para Windows. 

Construa um sistema comercial completo, profissional e pronto para produção com a seguinte especificação:

### 1. Requisitos Principais & Filosofia Local-First
- A extensão NÃO deve utilizar a Chrome Web Store como mecanismo principal de backup ou restauro. O objetivo é preservar localmente os ficheiros reais (código-fonte JS, HTML, CSS, manifest.json, ficheiros de localização _locales/, imagens, ícones e metadados) instalados em `%LOCALAPPDATA%\Google\Chrome\User Data\<Perfil>\Extensions\<ID>\<Versão>\`.
- Sistema 100% offline: sem telemetria, sem envio de credenciais, cookies ou dados sensíveis para servidores externos.
- Conformidade estrita com o Content Security Policy (CSP) do Manifest V3: zero manipuladores inline (sem onclick, onchange, oninput em tags HTML). Todos os eventos devem ser registados via `addEventListener` ou delegação no DOM.

### 2. Arquitetura em Duas Camadas
1. **Extensão Chrome (Manifest V3)**:
   - `manifest.json`: com permissões `nativeMessaging`, `storage`, `management`, `alarms`, `notifications`. Chave pública RSA fixa para ID permanente.
   - `background/service_worker.js`: serviço em segundo plano para gestão de alarmes de monitorização periódica e ponte com o Native Host.
   - `ui/index.html`: SPA moderna responsiva com tema Dark/Light e 12 vistas:
     1. Dashboard (6 KPIs em tempo real e ações rápidas)
     2. Extensões Instaladas (tabela com busca, filtros, seleção individual e em lote)
     3. Catálogo de Backups (.crxbackup guardados, status de integridade, bloqueio contra eliminação)
     4. Restauro & Rollback (assistente de restauro, ponto prévio de rollback)
     5. Comparador de Versões (visual diff de ficheiros, hashes e tamanhos)
     6. Agendador de Tarefas (integração com o Windows Task Scheduler)
     7. Histórico de Operações (auditoria local de eventos)
     8. Relatórios Técnicos (diagnóstico do sistema, exportação JSON/TXT)
     9. Definições (pastas primária e secundária, compressão, encriptação AES-256)
     10. Licença (planos Free, Premium Pro, Ultimate Enterprise)
     11. Sobre o Sistema (versões, dados do SO)
     12. Privacidade & Segurança

2. **Native Messaging Host (Windows / Python)**:
   - Protocolo padrão do Chrome: mensagens JSON com prefixo de tamanho de 32 bits little-endian unsigned integer via stdin/stdout.
   - Launcher `ext_backup_host.bat` executando `python -u` (unbuffered I/O obrigatório para evitar timeouts).
   - Manifesto nativo `com.extbackup.pro.json` registado em `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro`.
   - Scripts de instalação e desinstalação automática no registo do Windows (`install_host.bat`, `install_host.ps1`, `uninstall_host.bat`).

### 3. Motores do Componente Nativo (`native_host/core/`)
- `chrome_detector.py`: Deteção automática do caminho `User Data`, leitura de múltiplos perfis (`Default`, `Profile 1`, etc.) a partir de `Local State` e `Secure Preferences`, resolução de nomes internacionalizados `_locales/messages.json` (case-insensitive) e extração de ícones em Data URL base64.
- `backup_engine.py`: Cópia integral da árvore de pastas para container `.crxbackup` (formato ZIP estruturado com pasta `extension/`, `metadata/metadata.json`, `hashes/hashes.json` e `manifest.json` na raiz).
- `restore_engine.py`: Dois modos de restauro:
  1. *Modo Descompactado*: Exporta para pasta pronta a carregar em `chrome://extensions` via "Carregar extensão descompactada" (Developer Mode), 100% imune a rejeições de assinatura da Web Store.
  2. *Modo Direto*: Cria automaticamente um snapshot prévio de Rollback (`pre_restore_rollback`) antes de repor ficheiros no perfil ativo.
- `integrity.py`: Validação SHA-256 ficheiro a ficheiro, discriminando: Idênticos, Alterados, Em Falta e Adicionados.
- `encryption.py`: Encriptação militar AES-256-GCM com derivação de chave PBKDF2-HMAC-SHA256 (100.000 iterações), salt aleatório de 16 bytes e nonce de 12 bytes.
- `comparator.py`: Motor de comparação visual de diferenças estruturais e criptográficas entre duas versões de backup ou entre o backup e a versão instalada.
- `process_manager.py`: Deteção de processos `chrome.exe` ativos via Windows API (`tasklist`) e fecho suave/controlado com confirmação do utilizador.
- `disk_space.py`: Verificação de capacidade livre em disco via `ctypes.windll.kernel32.GetDiskFreeSpaceExW`.
- `scheduler.py`: Integração com o Agendador de Tarefas do Windows (`schtasks.exe`) para tarefas automatizadas sem necessidade do Chrome aberto.
- `license_manager.py`: Sistema comercial offline com planos *Free* (até 3 backups), *Premium Pro* (ilimitado, multi-perfil, encriptação, agendamento) e *Ultimate Enterprise*. Chaves no formato `PREM-XXXX-XXXX-XXXX-YYYY` com checksum criptográfico SHA-256 validado localmente.
- `logger.py` e `error_codes.py`: Logs rotativos diários com códigos padronizados (`BK-xxxx`, `RS-xxxx`, `VL-xxxx`, `NT-xxxx`, `LC-xxxx`).

### 4. Suíte de Testes Automatizada (`tests/test_runner.py`)
Implementar 20 casos de teste de integração abrangendo:
1. Perfil único
2. Múltiplos perfis
3. Extensão pequena
4. Extensão grande
5. Extensão ativa
6. Extensão desativada
7. Múltiplas versões
8. Backup incremental
9. Backup corrompido
10. Ficheiro em falta
11. Restauro
12. Rollback
13. Deteção do Chrome aberto
14. Monitorização de estado do Chrome
15. Espaço em disco insuficiente
16. Unidade externa desligada
17. Encriptação AES-256
18. Importação/Exportação
19. Reconstrução após desinstalação
20. Sistema de licenciamento
```
