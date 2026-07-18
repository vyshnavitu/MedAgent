import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# ✅ Expanded medical keywords
IMPORTANT_KEYWORDS = [
    "symptoms", "signs", "clinical features",
    "diagnosis", "diagnostic", "tests", "screening",
    "treatment", "therapy", "management", "intervention",
    "prevention", "prognosis", "outcome",
    "causes", "etiology", "risk factors", "risk",
    "complications", "comorbidity",
    "pathophysiology", "mechanism", "disease", "condition",
    "infection", "disorder", "syndrome",
    "drug", "drugs", "medication", "medications",
    "dosage", "dose", "administration",
    "side effects", "adverse effects", "contraindications",
    "interactions",
    "procedure", "surgery", "clinical management",
    "guidelines", "protocol", "recommendation",
    "monitoring", "follow-up", "assessment", "evaluation",
    "emergency", "critical care", "severity", "acute", "chronic",
    "cardiovascular", "respiratory", "neurological",
    "endocrine", "gastrointestinal", "renal",
    "epidemiology", "incidence", "prevalence",
    "mortality", "morbidity", "public health",
    "diet", "nutrition", "exercise", "lifestyle",
    "vaccination", "immunization",
    "laboratory", "blood test", "imaging",
    "x-ray", "mri", "ct scan", "ultrasound"
]

# ❌ Remove useless sections
BAD_KEYWORDS = ["references", "bibliography", "index", "acknowledgement"]

def load_pdfs(pdf_folder="data/"):
    print(os.listdir(pdf_folder))
    docs = []

    for file in os.listdir(pdf_folder):
        if file.endswith(".pdf"):
            doc = fitz.open(os.path.join(pdf_folder, file))

            filtered_text = ""

            for page_num, page in enumerate(doc):
                page_text = page.get_text().lower()

                # ✅ Skip empty pages
                if len(page_text.strip()) < 100:
                    continue

                # ❌ Skip useless sections
                if any(bad in page_text for bad in BAD_KEYWORDS):
                    continue

                # ✅ Count keyword matches (better filtering)
                match_count = sum(keyword in page_text for keyword in IMPORTANT_KEYWORDS)

                if match_count >= 2:
                    filtered_text += page_text

                # ✅ OPTIONAL: limit pages for speed
                if page_num > 100:
                    break

            docs.append({"source": file, "text": filtered_text})

    return docs


def chunk_documents(docs):
    chunks = []

    for doc in docs:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        split_texts = text_splitter.split_text(doc["text"])

        for chunk in split_texts:
            chunks.append({
                "text": chunk,
                "source": doc["source"]   # ✅ ADD THIS
            })

    return chunks


if __name__ == "__main__":
    print("Loading PDFs...")
    docs = load_pdfs("data/")
    print(f"Loaded {len(docs)} document(s)")

    print("Chunking documents...")
    chunks = chunk_documents(docs)
    print(f"Total chunks: {len(chunks)}")

    # Preview first 3 chunks
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Source: {chunk['source']}")
        print(f"Text: {chunk['text'][:200]}...")