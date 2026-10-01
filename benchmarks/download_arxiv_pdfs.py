import os
import urllib.request
import concurrent.futures

# Using a list of fixed arxiv ids to guarantee we get real papers
# To get 500, we can use the arXiv API to fetch 500 recent AI papers
import urllib.parse
import xml.etree.ElementTree as ET

import os
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

def fetch_arxiv_pdfs(max_results=200, output_dir="benchmarks/dataset"):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Buscando metadados de {max_results} papers no arXiv (com delay para evitar block)...")
    
    pdf_urls = []
    # Paginate by 50 to avoid 429
    for start in range(0, max_results, 50):
        url = f"http://export.arxiv.org/api/query?search_query=cat:cs.AI&start={start}&max_results=50"
        print(f"Querying arXiv start={start}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
                        if link.attrib.get("title") == "pdf":
                            pdf_urls.append(link.attrib.get("href"))
            time.sleep(4) # Respect arXiv rate limits
        except Exception as e:
            print(f"Erro na API do arXiv: {e}")
            break
                
    pdf_urls = pdf_urls[:max_results]
    print(f"Encontrados {len(pdf_urls)} URLs de PDF. Iniciando download sequencial para não sobrecarregar...")
    
    downloaded = 0
    for url in pdf_urls:
        pdf_id = url.split("/")[-1]
        out_path = os.path.join(output_dir, f"{pdf_id}.pdf")
        if os.path.exists(out_path):
            downloaded += 1
            continue
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.10 pdf-test/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response, open(out_path, 'wb') as out_file:
                out_file.write(response.read())
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"Baixados {downloaded}/{len(pdf_urls)} PDFs reais...")
            time.sleep(1) # Delay between downloads
        except Exception as e:
            print(f"Falha ao baixar {url}: {e}")

    print(f"Download concluído: {downloaded} PDFs acadêmicos reais baixados em {output_dir}.")

if __name__ == "__main__":
    fetch_arxiv_pdfs(200)

