from modules.embeddings import load_vectorstore

def get_retriever():
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    return retriever


if __name__ == "__main__":
    retriever = get_retriever()

    query = "What is diabetes?"
    docs = retriever.invoke(query)

    for i, doc in enumerate(docs):
        print(f"\n--- Document {i+1} ---")
        print(doc.page_content[:500])