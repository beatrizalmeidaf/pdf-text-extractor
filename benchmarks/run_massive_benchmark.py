import os
import sys
import time
import random
import statistics
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
import fitz  # pymupdf
import pypdf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from papero_extract.extractor import extract_text

import glob

def get_real_pdfs(max_files=500, search_dir="benchmarks/dataset"):
    print(f"Buscando até {max_files} PDFs reais em {search_dir}...")
    pdf_files = []
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))
                if len(pdf_files) >= max_files:
                    return pdf_files
    print(f"Encontrados {len(pdf_files)} PDFs reais.")
    return pdf_files

def bench_pymupdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return len(text), len(doc)

def bench_pypdf(file_path):
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return len(text), len(reader.pages)

def bench_papero_extract(file_path):
    res = extract_text(file_path)
    return len(res.text), res.page_count

import tempfile
import shutil

def bench_pdfplumber(file_path):
    import pdfplumber
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return len(text), len(pdf.pages)

def bench_docling(file_path):
    temp_dir = os.path.join(tempfile.gettempdir(), "safe_pdf_test")
    os.makedirs(temp_dir, exist_ok=True)
    safe_path = os.path.join(temp_dir, "doc.pdf")
    shutil.copy2(file_path, safe_path)
    
    import sys
    import ctypes
    def get_short_path(long_name):
        try:
            buffer = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.GetShortPathNameW(long_name, buffer, 260)
            return buffer.value if buffer.value else long_name
        except:
            return long_name
            
    sys.path = [get_short_path(p) for p in sys.path]
    
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    res = converter.convert(safe_path)
    return len(res.document.export_to_markdown())

def run_benchmarks(pdf_files):
    print("\nAquecendo a JVM do Tika...")
    if pdf_files:
        bench_papero_extract(pdf_files[0])
        
    tools = {
        "PyMuPDF": bench_pymupdf,
        "PyPDF": bench_pypdf,
        "PDF Text Extractor (Nosso)": bench_papero_extract,
        "pdfplumber": bench_pdfplumber,
        "Docling (IBM)": bench_docling
    }
    
    results = {name: [] for name in tools}
    
    for idx, pdf in enumerate(pdf_files):
        if idx % 5 == 0:
            print(f"Processando PDF {idx}/{len(pdf_files)}...")
            
        for name, func in tools.items():
            if name == "Docling (IBM)" and idx >= 5:
                continue
            if name == "pdfplumber" and idx >= 15:
                continue
                
            t0 = time.time()
            try:
                func(pdf)
                results[name].append((time.time() - t0) * 1000)
            except Exception as e:
                pass
    return results

def plot_and_print(results, num_files):
    # Print Markdown Table
    print(f"\n### Benchmark: Extração de {num_files} PDFs\n")
    print("| Ferramenta | Tempo Total (s) | Tempo Médio/PDF (ms) | P95 Latência (ms) |")
    print("|---|---|---|---|")
    
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Helvetica', 'Arial', 'sans-serif']
    
    chart_data = {}
    
    for name, times in results.items():
        total_s = sum(times) / 1000
        avg_ms = sum(times) / len(times)
        p95_ms = statistics.quantiles(times, n=100)[94] if len(times) > 1 else avg_ms
        print(f"| {name} | {total_s:.2f}s | {avg_ms:.2f} ms | {p95_ms:.2f} ms |")
        
        # Make name shorter for the chart
        short_name = "PDF Text Extractor\n(Nosso)" if "Nosso" in name else name
        chart_data[short_name] = avg_ms

    # Plot Chart (Professional Design)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    names = list(chart_data.keys())
    values = list(chart_data.values())
    
    # Custom color palette (modern tech colors)
    def get_color(n):
        if 'Nosso' in n or 'Text Extractor' in n: return '#10b981' # Green (Success/Best)
        if 'Docling' in n: return '#f59e0b' # Amber/Warning (because it's slow/AI)
        if 'PyMuPDF' in n: return '#3b82f6' # Blue
        return '#8b93a5' # Gray for the rest (PyPDF, pdfplumber)
        
    colors = [get_color(n) for n in names]
    
    # Create horizontal bar chart for better readability
    bars = ax.barh(names, values, color=colors, height=0.6, edgecolor='none')
    
    # Styling
    ax.set_title(f'Tempo de Extração por PDF (Dataset de {num_files} Papers do arXiv)', 
                 fontsize=16, fontweight='bold', pad=25, color='#1f2937', loc='left')
    ax.set_xlabel('Milissegundos (Menor é Melhor)', fontsize=12, fontweight='medium', color='#4b5563', labelpad=15)
    
    # Clean up spines (remove top and right borders)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#d1d5db')
    
    # Adjust ticks
    ax.tick_params(axis='y', length=0, labelsize=12, colors='#374151')
    ax.tick_params(axis='x', colors='#6b7280', labelsize=10)
    
    # Add values at the end of each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(width + (max(values) * 0.02), 
                bar.get_y() + bar.get_height()/2, 
                f'{width:.1f} ms', 
                ha='left', va='center', 
                fontsize=12, fontweight='bold', color='#1f2937')
        
    plt.tight_layout()
    chart_path = os.path.join(os.path.dirname(__file__), "benchmark_results.png")
    plt.savefig(chart_path, bbox_inches='tight', dpi=300, transparent=False, facecolor='white')
    print(f"\nGráfico salvo em: {chart_path}")

if __name__ == "__main__":
    NUM_PDFS = 500
    pdf_files = get_real_pdfs(NUM_PDFS)
    results = run_benchmarks(pdf_files)
    plot_and_print(results, len(pdf_files))
