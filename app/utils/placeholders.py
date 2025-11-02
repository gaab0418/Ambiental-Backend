"""
Template Placeholders System

This module defines all available placeholders that can be used in document templates.
Placeholders use Jinja2-style syntax: {{ placeholder_name }}
"""

from typing import Dict, List
from pydantic import BaseModel


class PlaceholderInfo(BaseModel):
    """Information about a single placeholder."""
    name: str
    description: str
    example: str
    category: str


class PlaceholderCategory(BaseModel):
    """A category of placeholders."""
    name: str
    description: str
    placeholders: List[PlaceholderInfo]


# Define all available placeholders
PLACEHOLDER_CATEGORIES: List[PlaceholderCategory] = [
    PlaceholderCategory(
        name="Usuário Atual",
        description="Informações sobre o usuário logado que está gerando o documento",
        placeholders=[
            PlaceholderInfo(
                name="user.full_name",
                description="Nome completo do usuário",
                example="João da Silva",
                category="Usuário Atual"
            ),
            PlaceholderInfo(
                name="user.email",
                description="E-mail do usuário",
                example="joao@exemplo.com.br",
                category="Usuário Atual"
            ),
            PlaceholderInfo(
                name="user.phone",
                description="Telefone do usuário",
                example="(11) 98765-4321",
                category="Usuário Atual"
            ),
        ]
    ),
    PlaceholderCategory(
        name="Organização",
        description="Informações sobre a organização/empresa",
        placeholders=[
            PlaceholderInfo(
                name="organization.name",
                description="Nome da organização",
                example="Empresa XYZ Ltda",
                category="Organização"
            ),
            PlaceholderInfo(
                name="organization.cnpj_cpf",
                description="CNPJ ou CPF da organização",
                example="12.345.678/0001-90",
                category="Organização"
            ),
            PlaceholderInfo(
                name="organization.email",
                description="E-mail da organização",
                example="contato@empresa.com.br",
                category="Organização"
            ),
            PlaceholderInfo(
                name="organization.phone",
                description="Telefone da organização",
                example="(11) 3456-7890",
                category="Organização"
            ),
            PlaceholderInfo(
                name="organization.address",
                description="Endereço da organização",
                example="Rua Exemplo, 123 - São Paulo, SP",
                category="Organização"
            ),
            PlaceholderInfo(
                name="organization.website",
                description="Site da organização",
                example="https://www.empresa.com.br",
                category="Organização"
            ),
        ]
    ),
    PlaceholderCategory(
        name="Data e Hora",
        description="Informações de data e hora do momento da geração",
        placeholders=[
            PlaceholderInfo(
                name="current_date",
                description="Data atual (formato: DD/MM/AAAA)",
                example="26/10/2025",
                category="Data e Hora"
            ),
            PlaceholderInfo(
                name="current_time",
                description="Hora atual (formato: HH:MM)",
                example="14:30",
                category="Data e Hora"
            ),
            PlaceholderInfo(
                name="current_datetime",
                description="Data e hora atual completa",
                example="26/10/2025 às 14:30",
                category="Data e Hora"
            ),
            PlaceholderInfo(
                name="current_year",
                description="Ano atual",
                example="2025",
                category="Data e Hora"
            ),
            PlaceholderInfo(
                name="current_month",
                description="Mês atual (por extenso)",
                example="Outubro",
                category="Data e Hora"
            ),
        ]
    ),
    PlaceholderCategory(
        name="Processo/Documento",
        description="Informações sobre o processo ou documento sendo gerado",
        placeholders=[
            PlaceholderInfo(
                name="document.title",
                description="Título do documento",
                example="Relatório de Licença Ambiental",
                category="Processo/Documento"
            ),
            PlaceholderInfo(
                name="document.number",
                description="Número do documento ou processo",
                example="2025/0001234",
                category="Processo/Documento"
            ),
            PlaceholderInfo(
                name="document.type",
                description="Tipo do documento",
                example="Licença Prévia",
                category="Processo/Documento"
            ),
        ]
    ),
]


def get_all_placeholders() -> List[PlaceholderCategory]:
    """
    Get all available placeholder categories and their placeholders.
    
    Returns:
        List of placeholder categories with their placeholders.
    """
    return PLACEHOLDER_CATEGORIES


def get_placeholder_dict() -> Dict[str, PlaceholderInfo]:
    """
    Get a flat dictionary of all placeholders for quick lookup.
    
    Returns:
        Dictionary mapping placeholder names to their info.
    """
    placeholder_dict = {}
    for category in PLACEHOLDER_CATEGORIES:
        for placeholder in category.placeholders:
            placeholder_dict[placeholder.name] = placeholder
    return placeholder_dict


def get_placeholder_names() -> List[str]:
    """
    Get a list of all placeholder names.
    
    Returns:
        List of placeholder names.
    """
    names = []
    for category in PLACEHOLDER_CATEGORIES:
        for placeholder in category.placeholders:
            names.append(placeholder.name)
    return names

