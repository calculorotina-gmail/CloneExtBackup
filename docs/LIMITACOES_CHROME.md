# Limitações Técnicas do Google Chrome e Políticas de Segurança (Requisito 41)

O **Chrome Extension Backup Pro** baseia-se na transparência técnica e na precisão científica. Este documento detalha as restrições impostas pelo Google Chrome e pelo sistema operativo Windows, explicando como o nosso motor opera e quais os limites intransponíveis da arquitetura do navegador.

---

## 1. Classificação Técnica dos Ficheiros e Dados

| Categoria | O que Inclui | Suporte no Backup Pro | Comportamento Técnico |
| :--- | :--- | :--- | :--- |
| **Código e Recursos Locais** | Ficheiros `.js`, `.html`, `.css`, `manifest.json`, pastas `_locales/`, imagens, assets visuais, bibliotecas locais. | ✅ **100% Suportado** | Copiados diretamente preservando a árvore de diretórios e hashes SHA-256 intactos. |
| **Metadados da Instalação** | Versão, ID da extensão, data de modificação, estado ativo/desativado, permissões declaradas. | ✅ **100% Suportado** | Extraídos de `manifest.json`, `Preferences`, `Secure Preferences` e `Local State`. |
| **Armazenamento de Sessão / IndexedDB / LevelDB** | Dados voláteis de navegação, tokens de autenticação da sessão web da extensão. | ⚠️ **Protegido pelo Chrome** | Quando o Chrome está aberto, estes ficheiros possuem lock exclusivo no Windows (`FILE_SHARE_READ=0`). Não devem ser restaurados a quente para evitar corrupção de base de dados SQLite/LevelDB. |
| **Chaves de Encriptação DPAPI do Windows** | Chaves criptográficas de passwords guardadas no cofre do Chrome (`OS Crypt`). | 🔒 **Excluído por Segurança** | O Chrome utiliza a API `CryptProtectData` vinculada ao utilizador Windows logado. Por respeito absoluto às normas de privacidade e segurança (Requisito 31), o Backup Pro **não recolhe nem extrai credenciais**. |

---

## 2. A Proteção de Assinatura da Chrome Web Store

Quando uma extensão é descarregada da Chrome Web Store oficial, o navegador grava uma assinatura criptográfica nos ficheiros internos do perfil:
1. `_metadata/computed_hashes.json` (calculado e assinado pelos servidores da Google).
2. O ficheiro `Preferences` / `Secure Preferences` do perfil, que contém um hash HMAC protegido contra adulteração local da lista de extensões.

### O Desafio Técnico:
Se ficheiros forem substituídos ou restaurados diretamente na pasta `Extensions` enquanto o Chrome estiver em execução, ou se o Chrome detetar que o hash HMAC de `Secure Preferences` diverge:
- O Chrome pode desativar a extensão e exibir o aviso:
  > *"Esta extensão pode ter sido corrompida."*

### A Solução Técnica Robusta do Backup Pro:
Para garantir que o utilizador nunca fica impedido de aceder às suas extensões locais, o Backup Pro disponibiliza duas vias de restauro:

1. **Restauro Direto com Chrome Fechado:**
   - O Chrome deve ser terminado de forma controlada.
   - É criado um snapshot prévio de rollback.
   - Os ficheiros são colocados na pasta do perfil. Se a extensão pertencer ao perfil original e os hashes coincidirem, o Chrome aceita a inicialização.

2. **Exportação como Extensão Descompactada (Developer Mode / Load Unpacked) - RECOMENDADO:**
   - O Backup Pro descompacta a extensão para uma pasta permanente (ex: `Documents\ChromeExtensionsRestored\<Nome>`).
   - O utilizador acede a `chrome://extensions`, ativa o **Modo de Programador** e clica em **Carregar expandida**.
   - **Garantia Técnica:** O Chrome executa extensões descompactadas sem exigir validação de assinatura da Chrome Web Store. A extensão funciona imediatamente a 100%, com todo o código fonte e recursos preservados localmente!

---

## 3. Extensões que Dependem de Componentes Externos

Determinadas extensões dependem de arquiteturas externas que ultrapassam os ficheiros locais:
- **Extensões de Autenticação OAuth/Google Sync:** extensões que sincronizam definições na nuvem do fornecedor (ex: Google Drive, Notion Web Clipper) dependem de ligação à conta após o restauro.
- **Extensões com Native Messaging próprio:** extensões que comunicam com aplicações de desktop instaladas à parte (ex: leitores de cartões de cidadão, 1Password Desktop, gestores de downloads). O Backup Pro salvaguarda o código da extensão Chrome, mas a aplicação desktop companheira deve estar instalada no Windows.

O Backup Pro informa o utilizador sobre todas estas especificidades de forma transparente e antecipada, garantindo conformidade integral com as melhores práticas de integridade de dados.
