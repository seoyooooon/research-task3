import zipfile
import xml.etree.ElementTree as ET
import os

docx_path = r"c:\Users\megan\study-antigravity\research-task3\과제기획서_AI 에이전트를 활용한 콘텐츠 시청 기록 포스터 달력.docx"
if not os.path.exists(docx_path):
    print("File not found")
    exit()

try:
    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read('word/document.xml')
        
    root = ET.fromstring(xml_content)
    # namespaces
    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    paragraphs = []
    for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
        texts = [node.text for node in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
        if texts:
            paragraphs.append("".join(texts))

    print("\n".join(paragraphs))
except Exception as e:
    print(f"Error: {e}")
