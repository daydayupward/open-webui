import re

filepath = "/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md"
try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    images = re.findall(r'!\[.*?\]\((.*?)\)', content)
    print(f"Found {len(images)} images in {filepath}:")
    for img in images:
        print(f"  {img}")
except Exception as e:
    print(f"Error reading file: {e}")
