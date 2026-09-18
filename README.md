# Chrome Extension Backup Pro (Windows)

[![Chrome Extension](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-blue.svg)](https://developer.chrome.com/docs/extensions/mv3/)
[![Native Messaging](https://img.shields.io/badge/Windows-Native_Messaging_Host-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Crypto-AES--256--GCM_%2B_SHA--256-blueviolet.svg)]()
[![Tests](https://img.shields.io/badge/Tests-20%2F20_Passed-success.svg)]()

> **Sistema Profissional e Comercial de Backup e Reposição Local dos Ficheiros Reais das Extensões do Google Chrome para Windows.**

O **Chrome Extension Backup Pro** NÃO é um mero sincronizador de IDs ou URLs da Chrome Web Store. É uma solução empresarial concebida para preservar, verificar criptograficamente e restaurar os **ficheiros físicos locais reais** instalados no computador, com suporte a múltiplos perfis do Chrome, deduplicação incremental, salvaguarda prévia (rollback), agendamento automático no Windows e encriptação militar AES-256.

---

## 🌟 Principais Funcionalidades

- **Preservação Real dos Ficheiros Locais:** Cópia integral do código-fonte (JavaScript, HTML, CSS), manifest.json, manifestos de locales em `_locales/`, imagens, ícones e assets.
- **Suporte Robusto a Múltiplos Perfis:** Deteção automática de `Default`, `Profile 1`, `Profile 2`, etc., mapeando nomes amigáveis a partir do `Local State` e `Secure Preferences`.
- **Formato Verificável `.crxbackup`:** Container estruturado com manifesto raiz, árvore `extension/`, metadados de sistema e mapa de hashes `hashes/hashes.json`.
- **Integridade Criptográfica SHA-256:** Recálculo e comparação rigorosa de ficheiros, discriminando ficheiros *Iguais*, *Alterados*, *Em falta* ou *Adicionados*.
- **Restauro Seguro com Rollback Automático:** Criação prévia de snapshot de segurança antes de qualquer substituição de ficheiros, com botão de reversão imediata.
- **Dois Modos de Restauro:**
  1. *Restauro Direto no Perfil* (com verificação de locks e encerramento controlado do Chrome).
  2. *Exportação Descompactada (Developer Mode / Load Unpacked)*: 100% garantido e imune a verificações de assinatura da Chrome Web Store.
- **Backup Incremental Inteligente:** Compara tamanho, mtime e hash SHA-256 para reutilizar ficheiros inalterados e poupar espaço em disco.
- **Múltiplos Destinos de Armazenamento:** Suporte para disco local, discos externos (HDD/SSD), pens USB e pastas de rede (UNC), com espelhamento automático e validação de integridade.
- **Agendamento no Windows:** Integração com o Agendador de Tarefas do Windows (`schtasks.exe`) para rotinas diárias, semanais ou ao iniciar sessão.
- **Encriptação AES-256-GCM:** Proteção por palavra-passe com derivação de chave PBKDF2-HMAC-SHA256 (100.000 iterações) e tag de autenticação.
- **Interface Premium Moderna:** Dashboard com 6 KPIs em tempo real, pesquisa rápida, filtros avançados, comparador visual de versões (Diff), modo escuro/claro e suporte a relatórios exportáveis.
- **Sistema de Licenciamento Comercial:** Arquitetura desacoplada com planos *Free*, *Premium Pro* e *Premium Ultimate Enterprise*.

---

## 🏗️ Estrutura do Projeto

```
C:\antigravity\CloneExtChrome\
├── extension/                        # Extensão Chrome Manifest V3
│   ├── manifest.json                 # Manifesto MV3 com chave RSA fixa e Native Messaging
│   ├── background/
│   │   └── service_worker.js         # Service Worker para ponte de mensagens e alarmes
│   └── ui/
│       ├── index.html                # Aplicação SPA Premium com 12 vistas completas
│       ├── styles/
│       │   └── main.css              # Design System moderno (Dark/Light themes)
│       ├── scripts/
│       │   ├── app.js                # Router principal e gestão de estado
│       │   ├── native_bridge.js      # Ponte assíncrona com o Native Messaging Host
│       │   ├── dashboard.js          # KPIs e métricas do painel
│       │   ├── extensions.js         # Tabela de extensões instaladas, busca e filtros
│       │   ├── backups.js            # Catálogo e validação de ficheiros .crxbackup
│       │   ├── restore.js            # Assistente de restauro e gestão de rollback
│       │   ├── compare.js            # Comparador visual de versões (Diff)
│       │   ├── scheduler.js          # Configuração de tarefas agendadas
│       │   ├── history.js            # Registo de auditoria de operações
│       │   ├── reports.js            # Gerador e exportador de relatórios técnicos
│       │   ├── settings.js           # Gestão de configurações e preferências
│       │   └── license.js            # Ativação e gestão de licenças comerciais
│       └── icons/                    # Ícones de alta resolução (16, 32, 48, 128 px)
│
├── native_host/                      # Componente Local Windows (Native Messaging Host)
│   ├── ext_backup_host.py            # Script principal com protocolo 32-bit little-endian
│   ├── ext_backup_host.bat           # Launcher batch para execução transparente no Windows
│   ├── com.extbackup.pro.json        # Manifesto do Native Host para o Chrome
│   ├── install_host.bat              # Instalador 1-click no Registo do Windows (HKCU)
│   ├── install_host.ps1              # Instalador PowerShell com suporte a argumentos
│   ├── uninstall_host.bat            # Desinstalador automático do Registo do Windows
│   └── core/                         # Módulos centrais do motor
│       ├── chrome_detector.py        # Detetor de caminhos, perfis e extensões reais
│       ├── backup_engine.py          # Motor de cópia física, incremental e metadados
│       ├── restore_engine.py         # Motor de restauro, rollback e exportação
│       ├── integrity.py              # Verificador criptográfico SHA-256 e comparador
│       ├── compressor.py             # Motor de compressão ZIP (níveis 0, 6, 9)
│       ├── encryption.py             # Encriptação e desencriptação AES-256-GCM
│       ├── comparator.py             # Comparador detalhado de diferenças entre versões
│       ├── scheduler.py              # Integrador com Windows Task Scheduler (schtasks)
│       ├── process_manager.py        # Monitor de processos chrome.exe e encerramento
│       ├── disk_space.py             # Verificação de espaço livre via Windows API
│       ├── license_manager.py        # Verificador criptográfico de licenças comerciais
│       ├── logger.py                 # Logs locais diários com sanitização de senhas
│       └── error_codes.py            # Definição padronizada de códigos BK, RS, VL, LC
│
├── tests/                            # Suíte de Testes Automatizada Completa
│   └── test_runner.py                # 20 cenários obrigatórios (100% aprovados)
│
├── docs/                             # Documentação Completa
│   ├── MANUAL_UTILIZADOR.md          # Guia passo a passo de utilização
│   ├── ARQUITETURA_TECNICA.md        # Especificações técnicas e diagramas
│   └── LIMITACOES_CHROME.md          # Transparência sobre restrições do Chrome
└── README.md
```

---

## 🚀 Instalação Rápida

### 1. Registar o Componente Local Windows
Execute o script instalador como utilizador standard:
```cmd
C:\antigravity\CloneExtChrome\native_host\install_host.bat
```
Isto regista a chave `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro` apontando para o manifesto JSON.

### 2. Carregar a Extensão no Chrome
1. Abra o Chrome e aceda a `chrome://extensions`.
2. Ative o **Modo de programador** (canto superior direito).
3. Clique em **Carregar expandida** e selecione a pasta:
   ```
   C:\antigravity\CloneExtChrome\extension
   ```
4. A extensão terá o ID fixo: `mdimfmpnjkfmebafopcfildiicfegmjk`.

---

## 🧪 Execução dos Testes Automatizados

A suíte cobre integralmente todos os 20 cenários exigidos no requisito 42:
```cmd
python tests/test_runner.py
```

Resultados:
```
Ran 20 tests in 3.438s

OK (20/20 Passed)
- 1 perfil Chrome: OK
- Múltiplos perfis: OK
- Extensão pequena: OK
- Extensão grande: OK
- Extensão ativa: OK
- Extensão desativada: OK
- Várias versões da mesma extensão: OK
- Backup incremental: OK
- Backup corrompido: OK
- Ficheiro em falta: OK
- Restauro: OK
- Rollback: OK
- Chrome aberto / fechado: OK
- Destino sem espaço: OK
- Unidade externa desligada: OK
- Backup encriptado AES-256: OK
- Importação / Exportação: OK
- Extensão desinstalada pós-backup: OK
- Licenciamento comercial: OK
```

---

## 🔒 Segurança e Privacidade

- **Local-First:** Todo o processamento decorre 100% no seu computador. Zero telemetria, zero dependência de nuvem.
- **Proteção Anti-Path Traversal:** Todos os nomes de ficheiros e descompactações ZIP são validados contra Zip Slip e travessia de diretório.
- **Sem Recolha de Credenciais:** Cookies, palavras-passe e histórico de navegação são escrupulosamente excluídos dos backups.

---

## 📄 Licença
Produto comercial preparado para distribuição corporativa e individual. Direitos reservados.
