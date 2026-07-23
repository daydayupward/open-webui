import asyncio
from src.utils import get_embeddings
import numpy as np

# Exact texts of the two chunks from innovusUG.pdf
chunk_bus_planning = """**The following steps describe the bus planning flow in Innovus:**
**1. Importing the design**
**2. Initial Floorplanning**
**3. Loading the netlist**
**4. Defining the bus guides**
**5. Creating the bus constraints**
**6. Running bus placement**
**7. Routing bus wires**
**8. Optimizing and verifying bus routing**
**9. Saving the design**"""

chunk_mixed_placer = """**Below is a diagram showing the steps in the mixed placer flow:**
![](/static/uploads/images/d2db46ea46ac64cb7ad2d0e6e3d42309.png)"""

async def main():
    query = "innovusUG mixed placer flow chart and steps"
    
    embeddings = get_embeddings()
    query_vector = await asyncio.to_thread(embeddings.embed_query, query)
    
    bus_vector = await asyncio.to_thread(embeddings.embed_query, chunk_bus_planning)
    mixed_vector = await asyncio.to_thread(embeddings.embed_query, chunk_mixed_placer)
    
    # Calculate cosine similarity
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
    sim_bus = cosine_sim(query_vector, bus_vector)
    sim_mixed = cosine_sim(query_vector, mixed_vector)
    
    print(f"Query: '{query}'")
    print(f"Cosine Similarity (Bus Planning): {sim_bus:.4f}")
    print(f"Cosine Similarity (Mixed Placer): {sim_mixed:.4f}")

if __name__ == '__main__':
    asyncio.run(main())
