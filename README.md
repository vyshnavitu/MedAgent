# 🩺 MedAgent - AI Medical Assistant

An AI-powered Medical Assistant built using **Retrieval-Augmented Generation (RAG)** to answer medical questions from trusted medical documents. MedAgent combines Large Language Models, semantic search, and vector databases to provide context-aware and reliable responses.

---

## 🚀 Project Overview

MedAgent is a RAG-based healthcare chatbot that retrieves relevant information from medical documents before generating responses. Instead of relying only on the language model's knowledge, the system searches trusted medical PDFs and uses the retrieved context to answer user queries accurately.

This project demonstrates practical applications of AI in healthcare by integrating document retrieval, embeddings, vector search, and large language models.

---

## ✨ Features

- 📄 Medical PDF document ingestion
- 🔍 Semantic search using FAISS Vector Database
- 🤖 Retrieval-Augmented Generation (RAG)
- 💬 Context-aware medical question answering
- 🧠 Llama 3.1 (Groq API)
- 📑 Automatic text chunking
- 🏥 Multiple medical reference documents
- ⚡ Fast response generation
- 🌐 Streamlit web interface

---

## 🛠️ Tech Stack

### Programming Language
- Python

### Frameworks & Libraries
- Streamlit
- LangChain
- FAISS
- Sentence Transformers
- PyMuPDF
- Groq API

### AI Model
- Llama 3.1 8B Instant (Groq)

### Embedding Model
- all-MiniLM-L6-v2

---

## 📂 Project Structure

```
MedAgent
│
├── app.py
├── modules
│   ├── agent.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── llm.py
│   ├── qa_chain.py
│   ├── retriever.py
│   ├── metrics.py
│   └── chat_memory.py
│
├── data
├── reports
├── vectorstore
└── README.md
```

---

## ⚙️ How It Works

1. Load medical PDF documents.
2. Extract text using PyMuPDF.
3. Split documents into smaller chunks.
4. Generate embeddings using Sentence Transformers.
5. Store embeddings in FAISS.
6. Retrieve relevant chunks for the user's question.
7. Send retrieved context to Llama 3.1 through Groq.
8. Generate an accurate and context-aware response.

---

## 📚 Medical Knowledge Sources

The chatbot retrieves information from multiple trusted medical reference documents covering topics such as:

- Cardiovascular Diseases
- Diabetes
- Malaria
- General Diseases
- Standard Treatment Guidelines

---

## ▶️ Installation

### Clone the repository

```bash
git clone https://github.com/vyshnavitu/MedAgent.git
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file and add:

```
GROQ_API_KEY=your_api_key
```

### Run the application

```bash
streamlit run app.py
```

---

## 📈 Future Improvements

- Voice-based interaction
- Multi-language support
- Medical image analysis
- Cloud deployment
- User authentication
- Conversation history dashboard

---

## ⚠️ Disclaimer

This project is developed for educational and research purposes. It is **not intended to replace professional medical advice, diagnosis, or treatment**. Always consult qualified healthcare professionals for medical decisions.

---

## 👩‍💻 Author

**Vyshnavi TU**

B.Tech – Computer Science Engineering (AI & Data Science)

---

## ⭐ If you found this project useful, consider giving it a Star!
