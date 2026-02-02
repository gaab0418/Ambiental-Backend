"""
Default Checklist Template

Defines the default checklist items created automatically when a process is created.
"""

from typing import List, Dict

DEFAULT_CHECKLIST_ITEMS: List[Dict[str, str]] = [
    {
        "title": "Verificar documentação básica",
        "description": "Confirmar que todos os documentos obrigatórios foram anexados"
    },
    {
        "title": "Analisar localização do processo",
        "description": "Validar endereço e coordenadas geográficas"
    },
    {
        "title": "Conferir licenças anteriores",
        "description": "Verificar histórico de licenciamento e processos anteriores"
    },
    {
        "title": "Validar dados técnicos",
        "description": "Revisar informações técnicas e especificações do projeto"
    },
    {
        "title": "Aprovar processo",
        "description": "Decisão final sobre aprovação ou rejeição do processo"
    },
]


def get_default_checklist_items() -> List[Dict[str, str]]:
    """
    Get the default checklist items for a new process.
    
    Returns:
        List of checklist item dictionaries with title and description.
    """
    return DEFAULT_CHECKLIST_ITEMS.copy()
