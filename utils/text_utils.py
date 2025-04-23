import re
import logging

logger = logging.getLogger(__name__)

def is_page_number_line(line: str, max_page_num: int = 1000) -> bool:
    """
    Determina se uma linha contém apenas um número de página.
    Considera números alinhados à direita como números de página.
    """
    # remove espaços no início e fim
    stripped_line = line.strip()
    
    # se a linha está vazia não é número de página
    if not stripped_line:
        return False
        
    # se é apenas um número e está dentro do limite razoável de páginas
    if stripped_line.isdigit() and int(stripped_line) <= max_page_num:
        # verifica se o número está alinhado à direita na linha original
        if line.rstrip() == line.rstrip().rjust(len(line)):
            return True
    
    return False

def clean_page_numbers(text: str) -> str:
    """
    Remove números de página do texto mantendo a formatação.
    """
    lines = text.split('\n')
    cleaned_lines = []
    previous_line = ''
    
    for i, line in enumerate(lines):
        # pula a linha se for um número de página isolado
        if is_page_number_line(line):
            continue
            
        # preserva números que fazem parte da estrutura do documento
        # remove apenas números que parecem ser números de página no final da linha
        cleaned_line = re.sub(r'\s+\d+\s*$', '', line)
        
        # se a linha anterior termina com hífen e esta linha começa com espaços,
        # mantém a formatação original
        if previous_line.rstrip().endswith('-'):
            cleaned_lines.append(cleaned_line)
        else:
            # remove qualquer ponto sozinho no início da linha
            cleaned_line = re.sub(r'^\s*\.\s*', '', cleaned_line)
            cleaned_lines.append(cleaned_line)
            
        previous_line = cleaned_line
    
    return '\n'.join(cleaned_lines)

def process_extracted_text(text_content: str) -> str:
    """
    Processa o texto extraído do PDF, limpando e formatando.
    """
    if not text_content:
        logger.warning("Nenhum texto para processar.")
        return ""
        
    # divide o texto em páginas
    pages = text_content.split('\f')
    cleaned_pages = []
    
    for page in pages:
        # remove números de página mantendo a formatação
        cleaned_page = clean_page_numbers(page)
        if cleaned_page.strip():  
            cleaned_pages.append(cleaned_page.strip())
    
    # junta as páginas com uma quebra de linha dupla entre elas
    final_text = '\n\n'.join(cleaned_pages)
    
    return final_text