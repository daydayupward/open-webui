import urllib.request, json
url = "http://localhost:8000/v1/documents/context?doc_id=ad660967614f0e86&collection=eda_manuals&chunk_text=Innovus+Text+Command"
resp = urllib.request.urlopen(url)
d = json.load(resp)
print("chunk_count:", d.get("chunk_count"))
c = d.get("content", "")
print("content preview:", c[:400])
mark_pos = c.find("<mark")
print("mark found at:", mark_pos)
