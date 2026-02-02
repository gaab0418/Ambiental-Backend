"""
Technical Report Generator

Generates PDF technical reports from process and checklist data.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from jinja2 import Template
from datetime import datetime
from typing import Dict, Any, List
import os


# Default template for technical reports
DEFAULT_TEMPLATE = """
PARECER TÉCNICO N° {{ process.protocol }}

Data de Emissão: {{ current_date }}
Responsável Técnico: {{ user.full_name }}

===============================================================================
1. IDENTIFICAÇÃO DO PROCESSO
===============================================================================

Título: {{ process.title }}
Protocolo: {{ process.protocol }}
Status: {{ process.status }}
Prioridade: {{ process.priority }}
Responsável: {{ process.responsible }}
Localização: {{ process.location }}
Prazo: {{ process.deadline }}
Progresso: {{ process.progress }}%

===============================================================================
2. RESUMO DO PROCESSO
===============================================================================

{{ process.summary }}

===============================================================================
3. ANÁLISE DO CHECKLIST DE CONFERÊNCIA
===============================================================================

Total de Itens: {{ checklist.total }}
Completados: {{ checklist.completed }} ({{ checklist.completion_rate }}%)
Pendentes: {{ checklist.pending }}

3.1 Itens Verificados:

{{ checklist.items_list }}

===============================================================================
4. PARECER TÉCNICO
===============================================================================

Com base na análise do checklist de conferência, verificou-se que o processo
encontra-se com {{ checklist.completion_rate }}% de conclusão das etapas previstas.

{% if checklist.completion_rate >= 100 %}
CONCLUSÃO: O processo está COMPLETO e APROVADO para prosseguimento.
Todos os itens do checklist foram devidamente verificados e atendidos.
{% elif checklist.completion_rate >= 80 %}
CONCLUSÃO: O processo encontra-se em FASE AVANÇADA de execução.
Recomenda-se atenção aos {{ checklist.pending }} item(ns) pendente(s) para conclusão.
{% elif checklist.completion_rate >= 50 %}
CONCLUSÃO: O processo encontra-se em ANDAMENTO REGULAR.
É necessário completar os {{ checklist.pending }} item(ns) pendente(s) restantes.
{% else %}
CONCLUSÃO: O processo encontra-se em FASE INICIAL.
Recomenda-se priorizar a conclusão dos {{ checklist.pending }} item(ns) pendente(s).
{% endif %}

===============================================================================
5. ASSINATURA
===============================================================================

Responsável: {{ user.full_name }}
E-mail: {{ user.email }}
Organização: {{ organization.name }}

Data de Emissão: {{ current_datetime }}
"""


def generate_technical_report(
    process_data: Dict[str, Any],
    checklist_data: Dict[str, Any],
    user_data: Dict[str, Any],
    organization_data: Dict[str, Any],
    output_path: str
) -> str:
    """
    Generate a technical report PDF from process and checklist data.
    
    Args:
        process_data: Dictionary with process information
        checklist_data: Dictionary with checklist information (items, stats)
        user_data: Dictionary with user information
        organization_data: Dictionary with organization information
        output_path: Path where the PDF will be saved
        
    Returns:
        Path to the generated PDF file
    """
    
    # Prepare template context
    now = datetime.now()
   
    # Format checklist items as list
    items_list = []
    for idx, item in enumerate(checklist_data.get('items', []), 1):
        status_mark = "✓" if item.get('is_completed') else " "
        items_list.append(f"{idx}. [{status_mark}] {item.get('title', 'Sem título')}")
    
    context = {
        'process': {
            'title': process_data.get('title', 'N/A'),
            'protocol': process_data.get('protocol', 'N/A'),
            'status': process_data.get('status', 'N/A'),
            'priority': process_data.get('priority', 'N/A'),
            'responsible': process_data.get('responsible', 'Não informado'),
            'location': process_data.get('location', 'Não informado'),
            'progress': process_data.get('progress', 0),
            'deadline': process_data.get('deadline', 'Não informado'),
            'summary': process_data.get('summary', 'Sem resumo disponível'),
        },
        'checklist': {
            'total': checklist_data.get('total', 0),
            'completed': checklist_data.get('completed', 0),
            'pending': checklist_data.get('pending', 0),
            'completion_rate': checklist_data.get('completion_rate', 0),
            'items_list': '\n'.join(items_list) if items_list else 'Nenhum item encontrado',
        },
        'user': {
            'full_name': user_data.get('full_name', 'N/A'),
            'email': user_data.get('email', 'N/A'),
            'phone': user_data.get('phone', 'N/A'),
        },
        'organization': {
            'name': organization_data.get('name', 'N/A'),
            'cnpj_cpf': organization_data.get('cnpj_cpf', 'N/A'),
            'email': organization_data.get('email', 'N/A'),
            'phone': organization_data.get('phone', 'N/A'),
            'address': organization_data.get('address', 'N/A'),
            'website': organization_data.get('website', 'N/A'),
        },
        'current_date': now.strftime('%d/%m/%Y'),
        'current_time': now.strftime('%H:%M'),
        'current_datetime': now.strftime('%d/%m/%Y às %H:%M'),
        'current_year': now.strftime('%Y'),
        'current_month': now.strftime('%B'),
    }
    
    # Render template
    template = Template(DEFAULT_TEMPLATE)
    content = template.render(**context)
    
    # Create PDF
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, 
                             spaceAfter=12, spaceBefore=6))
    
    # Add content as paragraphs
    for line in content.split('\n'):
        if line.strip():
            if line.startswith('='):
                # Separator line
                elements.append(Spacer(1, 12))
            elif line.startswith('PARECER TÉCNICO'):
                # Title
                elements.append(Paragraph(f"<b>{line}</b>", styles['Title']))
                elements.append(Spacer(1, 12))
            elif any(line.startswith(str(i) + '.') for i in range(1, 10)):
                # Section header
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(f"<b>{line}</b>", styles['Heading2']))
                elements.append(Spacer(1, 6))
            elif ':' in line and not line.startswith(' '):
                # Field: value
                parts = line.split(':', 1)
                elements.append(Paragraph(f"<b>{parts[0]}:</b> {parts[1].strip()}", styles['Normal']))
            else:
                # Normal text
                elements.append(Paragraph(line, styles['Justify']))
        else:
            elements.append(Spacer(1, 6))
    
    # Build PDF
    doc.build(elements)
    
    return output_path
