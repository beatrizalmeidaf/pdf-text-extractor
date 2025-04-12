from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from tika import parser
import re
import shutil
import os
from datetime import datetime

# inicializa FastAPI 
app = FastAPI(
    title="PDF Text Extractor",
    description="API para extração de texto de arquivos PDF",
    version="1.0.0"
)

# permite que aplicações em diferentes domínios acessem a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# cria diretorios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# HTML template
with open('index.html', 'r', encoding='utf-8') as f:
    HTML_CONTENT = f.read()

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

def extract_text_from_pdf(pdf_path: str) -> str:
    parsed_pdf = parser.from_file(pdf_path)
    text_content = parsed_pdf.get('content', '') or parsed_pdf.get('text', '')
    
    if not text_content:
        raise ValueError("Nenhum texto foi extraído do PDF.")
    
    # divide o texto em páginas
    pages = text_content.split('\f')
    cleaned_pages = []
    
    for page in pages:
        # remove números de página mantendo a formatação
        cleaned_page = clean_page_numbers(page)
        if cleaned_page.strip():  
            cleaned_pages.append(cleaned_page.strip())
    
    # junta as páginas com uma quebra de linha dupla entre elas
    final_text = '\n'.join(cleaned_pages)
    
    return final_text

@app.get("/", response_class=HTMLResponse)
async def root():
    """Retorna a página HTML como resposta"""
    return HTML_CONTENT

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Rota de Upload de PDF
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado não é um PDF."
        )
    
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extracted_text = extract_text_from_pdf(pdf_path)
        return JSONResponse(content={
            "filename": file.filename,
            "text": extracted_text
        })
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

@app.post("/download/")
async def download_pdf(file: UploadFile = File(...)):
    """
    Processa o PDF e retorna o txt para download
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado não é um PDF."
        )
    
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extracted_text = extract_text_from_pdf(pdf_path)
        
        return PlainTextResponse(
            content=extracted_text,
            headers={
                "Content-Disposition": f"attachment; filename={os.path.splitext(file.filename)[0]}.txt",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)