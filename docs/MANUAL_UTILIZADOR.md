# Manual do Utilizador - Chrome Extension Backup Pro (Windows)

Bem-vindo ao **Chrome Extension Backup Pro**, a solução profissional de cópia de segurança e recuperação local das extensões instaladas no Google Chrome para Windows.

---

## 1. Instalação e Configuração Inicial

Para o sistema funcionar, são necessários dois componentes que trabalham em conjunto através da API oficial **Native Messaging** do Google Chrome:
1. **A Extensão Chrome (Manifest V3)**.
2. **O Componente Local Windows (Native Messaging Host)**.

### Passo 1: Registar o Componente Local Windows
1. Abra a pasta `native_host/` do projeto:
   ```
   C:\antigravity\CloneExtChrome\native_host
   ```
2. Dê duplo clique no ficheiro:
   ```
   install_host.bat
   ```
   *(Ou execute `install_host.ps1` no PowerShell como utilizador standard).*
3. O instalador configura automaticamente a chave no Registo do Windows:
   `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro`
4. Surgirá a mensagem: `[SUCESSO] Native Messaging Host registado com sucesso!`.

### Passo 2: Instalar a Extensão no Google Chrome
1. Abra o **Google Chrome**.
2. Na barra de endereço, aceda a:
   ```
   chrome://extensions
   ```
3. No canto superior direito, ative a opção **Modo de programador (Developer mode)**.
4. Clique no botão **Carregar expandida (Load unpacked)**.
5. Selecione a pasta `extension`:
   ```
   C:\antigravity\CloneExtChrome\extension
   ```
6. A extensão surgirá com o nome **Chrome Extension Backup Pro** e o ID fixo:
   `mdimfmpnjkfmebafopcfildiicfegmjk`.
7. Fixe o ícone da extensão na barra de ferramentas do Chrome para acesso rápido.

---

## 2. Como Fazer um Backup Local de uma Extensão

1. Abra a interface clicando no ícone da extensão ou abrindo `ui/index.html`.
2. No menu lateral, clique em **Extensões**.
3. Verá a lista de todas as extensões instaladas no seu perfil atual, com nome real, versão, tamanho e estado (Ativa/Desativada).
4. Na linha da extensão desejada, clique em **Backup**.
5. O sistema realiza:
   - A cópia física de todos os ficheiros (HTML, JavaScript, CSS, imagens, manifest.json, _locales).
   - O cálculo das assinaturas criptográficas **SHA-256** de cada ficheiro.
   - A criação do arquivo verificável `.crxbackup` na sua pasta de documentos (`Documents\ChromeExtensionBackups`).
6. Uma notificação de sucesso será apresentada informando o tamanho e a integridade da cópia.

### Backup em Lote (Múltiplas Extensões)
1. Marque as caixas de seleção `[✓]` das extensões que pretende salvaguardar.
2. Clique no botão azul **Fazer Backup Selecionadas (N)** que surge no topo da tabela.
3. O sistema processará as extensões sequencialmente gerando relatórios individuais.

---

## 3. Gestão de Perfis Múltiplos do Chrome

Se utiliza mais de um perfil no Chrome (ex: *Pessoal*, *Trabalho*, *Convidado*):
1. No cabeçalho superior da aplicação, localize o seletor **Perfil**.
2. Selecione o perfil desejado (`Pessoa 1`, `Trabalho`, `Profile 1`, etc.).
3. A lista de extensões, tamanhos e estado é atualizada instantaneamente para refletir esse perfil.

---

## 4. Verificação de Integridade dos Backups

Para garantir que nenhum backup foi corrompido por falha de disco ou vírus:
1. No menu lateral, aceda a **Backups**.
2. Clique em **Validar** na linha do backup pretendido.
3. O motor lê o arquivo `.crxbackup`, recalcula o SHA-256 de todos os ficheiros e compara com o manifesto original.
4. O resultado discrimina:
   - **Iguais:** ficheiros 100% idênticos.
   - **Alterados:** ficheiros modificados após a cópia.
   - **Em falta:** ficheiros apagados ou truncados.

---

## 5. Como Restaurar uma Extensão

Existem dois métodos de restauro no separador **Restaurar**:

### Método A: Exportar como Extensão Descompactada (Recomendado)
- **Vantagem:** Não requer que feche o Chrome e contorna 100% qualquer bloqueio da Chrome Web Store.
- **Passos:**
  1. Selecione o arquivo `.crxbackup`.
  2. Escolha o método: *Exportar como Extensão Descompactada*.
  3. Clique em **Iniciar Restauro**.
  4. O sistema valida os ficheiros e descompacta a extensão para `Documents\ChromeExtensionsRestored`.
  5. No Chrome, aceda a `chrome://extensions` e clique em **Carregar expandida** selecionando essa pasta. A extensão fica imediatamente operacional!

### Método B: Restauro Direto no Perfil Chrome
- **Requisito Obrigatório:** O Google Chrome deve estar **fechado**. Se estiver aberto, utilize o botão *Fechar Chrome de Forma Controlada*.
- O sistema cria automaticamente um **Ponto de Rollback (Salvaguarda Prévia)** da versão atual antes de substituir qualquer ficheiro.
- Substitui os ficheiros físicos no diretório `<Perfil>\Extensions\<ID>\<Versão>`.

---

## 6. Reversão de Restauro (Rollback)

Se restaurou uma extensão e deseja voltar exatamente ao estado anterior:
1. O sistema mantém o histórico de pontos de rollback em `%APPDATA%\ChromeExtBackupPro\Rollbacks`.
2. Em caso de discrepância ou erro, o rollback automático é imediatamente acionado.
3. Pode reverter manualmente através do Histórico ou do menu de restauro.

---

## 7. Comparador de Versões (Diff)

Permite inspecionar o que mudou entre duas versões de uma extensão (ex: v1.66 vs v1.67):
1. No menu lateral, clique em **Comparar**.
2. Selecione a **Versão A** e a **Versão B**.
3. Clique em **Comparar Ficheiros & Hashes**.
4. O ecrã apresenta:
   - Ficheiros adicionados (verde)
   - Ficheiros removidos (vermelho)
   - Ficheiros alterados (laranja)
   - Ficheiros iguais (cinzento)
   - Diferença líquida de tamanho (+/- KB) e hashes SHA-256.

---

## 8. Backup Automático Agendado

1. Aceda a **Agendamentos**.
2. Marque a opção **Ativar Backup Automático Agendado**.
3. Defina a frequência (*Diário*, *Semanal* ou *Ao Iniciar Sessão no Windows*) e o horário (ex: `03:00`).
4. Clique em **Guardar e Registar no Windows Task Scheduler**.
5. O Windows executará a tarefa em segundo plano mesmo com o navegador fechado.

---

## 9. Encriptação com Palavra-passe (AES-256-GCM)

1. Aceda a **Definições**.
2. Ative a opção **Ativar encriptação AES-256-GCM**.
3. Defina uma palavra-passe mestre forte.
4. Todos os backups criados passarão a ter o cabeçalho `CRXENC01` e cifra militar autenticada.
5. *Aviso de segurança: Palavras-passe não são salvas em texto simples. Guarde a sua senha em local seguro.*

---

## 10. Chaves de Licenciamento

A aplicação dispõe de três níveis de serviço:
- **Gratuito (Free):** Até 3 backups manuais no perfil padrão.
- **Premium Pro:** Backups ilimitados, múltiplos perfis, versionamento, incremental, encriptação AES-256 e agendamento.
- **Premium Ultimate:** Múltiplos computadores, espelho secundário, diagnóstico avançado e retenção empresarial.

Para ativar uma licença:
1. Aceda a **Licença**.
2. Insira o nome do titular e a chave no formato `PREM-XXXX-XXXX-XXXX-XXXX` ou `ULTM-XXXX-XXXX-XXXX-XXXX`.
3. Clique em **Validar e Ativar Chave**.
