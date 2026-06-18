import os
import re

test_dir = '/home/eason/proj/open-webui/chip_agent/tests'
for root, _, files in os.walk(test_dir):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
                
            original = content
            
            # test_project_retriever, test_pdk_retriever, test_eda_subgraph
            content = content.replace('called_filter["category"] == "Project_Doc"', 'called_filter["category"] == {"$in": ["Project_Doc"]}')
            content = content.replace('called_filter["category"] == "PDK"', 'called_filter["category"] == {"$in": ["PDK"]}')
            content = content.replace('called_filter["category"] == "EDA"', 'called_filter["category"] == {"$in": ["EDA"]}')
            
            # test_metadata_mapper, etc.
            content = content.replace('category="pdk"', 'categories=["PDK"]')
            content = content.replace('category="eda"', 'categories=["EDA"]')
            content = content.replace('category="general"', 'categories=["General"]')
            content = content.replace('category="PDK"', 'categories=["PDK"]')
            
            content = content.replace('.category ==', '.categories ==')
            content = content.replace('.category is', '.categories is')
            content = content.replace('["category"] ==', '["categories"] ==')
            content = content.replace('["category"] is', '["categories"] is')
            content = content.replace('{"category":', '{"categories":')
            
            if content != original:
                with open(path, 'w') as f:
                    f.write(content)
                print(f'Fixed {path}')
