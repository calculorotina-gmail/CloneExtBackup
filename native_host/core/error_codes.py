"""
Standard Error Codes and Messages for Chrome Extension Backup Pro.
Every error includes an unambiguous code, technical description, affected operation,
affected target file/directory, and an actionable user resolution.
"""

ERROR_DEFINITIONS = {
    # Backup errors (BK-xxxx)
    "BK-0001": {
        "title": "Diretório de extensão não encontrado",
        "description": "O diretório local correspondente à extensão selecionada não foi encontrado no perfil do Chrome.",
        "solution": "Verifique se a extensão ainda está instalada no perfil selecionado ou recarregue a lista de extensões."
    },
    "BK-0002": {
        "title": "Destino sem espaço suficiente",
        "description": "O disco ou unidade de destino não possui espaço livre suficiente para concluir o backup.",
        "solution": "Liberte espaço na unidade de destino ou configure um novo caminho de backup nas Definições."
    },
    "BK-0003": {
        "title": "Ficheiro bloqueado pelo Chrome",
        "description": "Um ou mais ficheiros da extensão estão bloqueados por um processo ativo do Google Chrome.",
        "solution": "Feche o Google Chrome completamente e tente executar o backup novamente."
    },
    "BK-0004": {
        "title": "Erro ao calcular hash de integridade",
        "description": "Falha ao calcular a assinatura criptográfica SHA-256 de um ficheiro da extensão.",
        "solution": "Verifique as permissões de leitura do ficheiro e se o disco não apresenta setores danificados."
    },
    "BK-0005": {
        "title": "Erro na compactação do arquivo",
        "description": "Ocorreu uma falha durante o processo de compressão do ficheiro de backup.",
        "solution": "Tente alterar o nível de compressão para 'Sem compressão' nas Definições e repita a operação."
    },
    "BK-0006": {
        "title": "Erro na encriptação do backup",
        "description": "Não foi possível encriptar o ficheiro com a palavra-passe fornecida.",
        "solution": "Certifique-se de que a palavra-passe cumpre os requisitos mínimos de segurança e tente novamente."
    },
    "BK-0007": {
        "title": "Falha ao copiar para o destino secundário",
        "description": "O backup principal foi concluído com sucesso, mas a cópia para o segundo destino falhou.",
        "solution": "Verifique se a unidade externa ou pasta de rede secundária está conectada e acessível."
    },
    "BK-0008": {
        "title": "Permissão de escrita negada no destino",
        "description": "O Windows negou permissão para gravar na pasta de backup selecionada.",
        "solution": "Verifique as permissões da pasta no Windows ou execute a operação como Administrador."
    },
    "BK-0042": {
        "title": "Ficheiro em uso exclusivo",
        "description": "Não foi possível copiar o ficheiro porque está atualmente aberto em modo exclusivo por outro processo.",
        "solution": "Feche o Google Chrome e quaisquer ferramentas de depuração abertas e tente novamente."
    },

    # Restore errors (RS-xxxx)
    "RS-0001": {
        "title": "Backup corrompido ou inválido",
        "description": "A validação de integridade prévia ao restauro detetou ficheiros corrompidos ou hashes divergentes.",
        "solution": "O restauro foi cancelado por segurança. Utilize uma versão anterior válida do backup."
    },
    "RS-0002": {
        "title": "Google Chrome em execução",
        "description": "O restauro direto de ficheiros de extensão requer que o Google Chrome esteja fechado para evitar corrupção.",
        "solution": "Feche todas as janelas e instâncias do Chrome em execução antes de continuar com o restauro."
    },
    "RS-0003": {
        "title": "Falha ao criar ponto de rollback",
        "description": "Não foi possível criar uma cópia de segurança de segurança da instalação existente antes do restauro.",
        "solution": "A operação foi interrompida para proteger a instalação atual. Verifique o espaço em disco."
    },
    "RS-0004": {
        "title": "Palavra-passe de desencriptação incorreta",
        "description": "A palavra-passe fornecida para desencriptar o ficheiro de backup é inválida.",
        "solution": "Insira a palavra-passe correta definida no momento da criação do backup. Por motivos de segurança, palavras-passe esquecidas não podem ser recuperadas."
    },
    "RS-0005": {
        "title": "Falha ao restaurar ficheiros",
        "description": "Ocorreu um erro ao gravar os ficheiros restaurados no perfil do Chrome.",
        "solution": "O sistema irá acionar o rollback automático para restabelecer a versão anterior."
    },
    "RS-0006": {
        "title": "Falha na reversão (Rollback)",
        "description": "Ocorreu um erro crítico ao tentar restaurar o ponto de salvaguarda pré-restauro.",
        "solution": "Consulte os ficheiros salvos na pasta de rollback e os logs da aplicação para recuperação manual."
    },
    "RS-0007": {
        "title": "Incompatibilidade de perfil ou arquitetura",
        "description": "O backup foi criado para uma configuração ou perfil que difere do perfil de destino selecionado.",
        "solution": "Confirme se deseja restaurar neste perfil ou utilize a opção 'Exportar como extensão descompactada'."
    },

    # Validation errors (VL-xxxx)
    "VL-0001": {
        "title": "Manifesto de backup ausente ou corrompido",
        "description": "O ficheiro manifest.json do backup não foi localizado ou não contém uma estrutura JSON válida.",
        "solution": "O ficheiro selecionado não é um backup válido da aplicação ou está danificado."
    },
    "VL-0002": {
        "title": "Discrepância de hash SHA-256",
        "description": "Um ou mais ficheiros foram alterados após a criação do backup original.",
        "solution": "Verifique a lista de ficheiros alterados no relatório de integridade."
    },
    "VL-0003": {
        "title": "Ficheiros ausentes no arquivo",
        "description": "Ficheiros listados no manifesto de integridade não existem no arquivo de backup.",
        "solution": "O arquivo pode estar incompleto ou ter sido truncado durante a transferência."
    },

    # License errors (LC-xxxx)
    "LC-0001": {
        "title": "Funcionalidade restrita ao plano Premium",
        "description": "A funcionalidade solicitada (agendamento, múltiplos perfis, encriptação ou destinos secundários) requer licença Premium.",
        "solution": "Ative uma chave de licença válida na página de Licença para desbloquear todas as funcionalidades."
    },
    "LC-0002": {
        "title": "Chave de licença inválida",
        "description": "O formato ou assinatura criptográfica da chave de ativação fornecida não é válido.",
        "solution": "Verifique a chave inserida e certifique-se de que não existem espaços adicionais."
    },

    # System / Native Host errors (NT-xxxx)
    "NT-0001": {
        "title": "Caminho do Chrome User Data não encontrado",
        "description": "Não foi possível localizar automaticamente a pasta de dados do utilizador do Google Chrome no Windows.",
        "solution": "Especifique o caminho personalizado do Chrome User Data na aba de Definições."
    },
    "NT-0002": {
        "title": "Tentativa de travessia de caminho (Path Traversal detetada)",
        "description": "Uma operação tentou aceder a caminhos fora dos diretórios autorizados do sistema.",
        "solution": "A operação foi bloqueada pelo subsistema de segurança da aplicação."
    }
}


def create_error_response(code: str, operation: str = "", affected_file: str = "", extra_details: str = "") -> dict:
    """Creates a structured error dictionary conforming to application requirements."""
    spec = ERROR_DEFINITIONS.get(code, {
        "title": "Erro desconhecido",
        "description": f"Ocorreu um erro não especificado (Código: {code}).",
        "solution": "Consulte os ficheiros de log da aplicação para mais informações."
    })

    return {
        "success": False,
        "error": {
            "code": code,
            "title": spec["title"],
            "description": spec["description"],
            "operation": operation,
            "affected_file": affected_file,
            "solution": spec["solution"],
            "extra_details": extra_details
        }
    }
