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
res = converter.convert("benchmarks/dataset/2309.07900v2.pdf")
print("SUCCESS:", len(res.document.export_to_markdown()))
