import json
from memvid import MemvidEncoder, MemvidChat, MemvidRetriever
import os


# # Carica il file JSON
with open("english_stories_with_emb.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Estrai solo le descrizioni
chunks = [item["description"] for item in data if "description" in item]
breakpoint()
# Inizializza MemvidEncoder
encoder = MemvidEncoder()

# Aggiungi i chunks
encoder.add_chunks(chunks)

# Costruisci il video + indice
encoder.build_video("test.mp4", "test.json")

# retriever = MemvidRetriever("test.mp4","test.json")

# results = retriever.search("create a modal to filter a table", top_k=3)

#print(results) 
