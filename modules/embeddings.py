import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from modules.ingest import load_pdfs, chunk_documents


def build_vectorstore():
    docs = load_pdfs()
    print(f"Loaded docs: {len(docs)}")

    chunks = chunk_documents(docs)
    print(f"Chunks created: {len(chunks)}")

    texts = [c["text"] for c in chunks] 
    metadatas = [{"source": c["source"]} for c in chunks]
    print(f"Texts extracted: {len(texts)}")

    print("Loading embeddings...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_folder="models"
    )

    os.makedirs("vectorstore", exist_ok=True)

    vectorstore = FAISS.from_texts(texts, embeddings,metadatas=metadatas)
    vectorstore.save_local("vectorstore/")

    print("✅ Vector store built successfully!")


def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_folder="models"
    )

    return FAISS.load_local(
        "vectorstore/",
        embeddings,
        allow_dangerous_deserialization=True
    )


if __name__ == "__main__":
    build_vectorstore()