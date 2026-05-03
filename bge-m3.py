from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")

emb = model.encode(["你好世界"])
print(len(emb[0]))