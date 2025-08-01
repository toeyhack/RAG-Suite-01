# --- IMPORTS ---
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
import json
import os
import io
import hashlib

import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationSummaryBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document as LangchainDocument
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from starlette.middleware.sessions import SessionMiddleware

# Import สำหรับอ่านไฟล์
from pypdf import PdfReader
from docx import Document

app = FastAPI()

# --- Configuration for Session Middleware ---
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-super-secret-key-that-should-be-random-and-long")
if SECRET_KEY == "your-super-secret-key-that-should-be-random-and-long":
    print("WARNING: SESSION_SECRET_KEY is not set. Using default key. This is INSECURE for production.")
    print("Please set SESSION_SECRET_KEY environment variable with a strong, random key.")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# อนุญาต CORS สำหรับ Streamlit (โดยปกติรันที่ localhost:8501)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:8002", "http://127.0.0.1:8002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration สำหรับ RAG ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "10.10.32.78")
CHROMA_PORT = os.getenv("CHROMA_PORT", "8001")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_documents")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text:latest")

# --- Global Instances ---
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

embeddings = None
chroma_client = None
collection = None
vectorstore = None
retriever = None
llm_qa = None
llm_memory_summarizer = None
app.state.memories = {}

# --- Helper Functions ---
def get_pdf_text(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def get_docx_text(docx_file):
    document = Document(docx_file)
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"
    return text

def get_txt_text(txt_file):
    return txt_file.read().decode('utf-8')

# เพิ่มฟังก์ชันสำหรับอ่านไฟล์ .md
def get_md_text(md_file):
    return md_file.read().decode('utf-8')

def get_memory(request: Request):
    session_id = request.session.get("session_id", "default_session_id")
    if session_id not in app.state.memories:
        print(f"Initializing new memory for session: {session_id}")
        if llm_memory_summarizer:
            app.state.memories[session_id] = ConversationSummaryBufferMemory(
                llm=llm_memory_summarizer,
                max_token_limit=1000,
                memory_key="chat_history",
                return_messages=True
            )
        else:
            raise HTTPException(status_code=500, detail="LLM สำหรับ Memory ยังไม่ได้ถูก Initialize")
    return app.state.memories[session_id]

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# --- Event Listener for FastAPI startup ---
@app.on_event("startup")
async def startup_event():
    global embeddings, chroma_client, collection, vectorstore, retriever, llm_qa, llm_memory_summarizer

    try:
        embeddings = OllamaEmbeddings(base_url="http://localhost:11434", model=EMBEDDING_MODEL_NAME)
        print(f"Embedding model '{EMBEDDING_MODEL_NAME}' initialized successfully.")
    except Exception as e:
        print(f"ERROR: Could not initialize embedding model '{EMBEDDING_MODEL_NAME}'. Error: {e}")
        embeddings = None

    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        print(f"Connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}, using collection: {COLLECTION_NAME}")
        print(f"Current documents in collection: {collection.count()}")
        if embeddings:
            vectorstore = Chroma(
                client=chroma_client,
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings
            )
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        else:
            print("WARNING: Embeddings model not initialized, vectorstore and retriever will not be available.")
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}. Error: {e}")
        chroma_client = None
        collection = None
        vectorstore = None
        retriever = None

    try:
        llm_qa = Ollama(base_url="http://localhost:11434", model="llama3.1:8b", temperature=0.7)
        llm_memory_summarizer = ChatOllama(base_url="http://localhost:11434", model="llama3.1:8b", temperature=0.1)
        print("LLMs initialized successfully.")
    except Exception as e:
        print(f"ERROR: Could not initialize LLM models. Error: {e}")
        llm_qa = None
        llm_memory_summarizer = None


# --- API Endpoints ---
@app.get("/")
async def root():
    return {"message": "Hello, this is the RAG API."}

# --- ENDPOINT for Dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RAG Document Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .container { max-width: 800px; margin: 0 auto; }
            .file-list { list-style-type: none; padding: 0; }
            .file-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                border: 1px solid #ddd;
                margin-bottom: 5px;
                border-radius: 5px;
            }
            .file-name { font-size: 1.1em; flex-grow: 1; }
            .delete-btn {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 12px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 14px;
                margin-left: 10px;
                cursor: pointer;
                border-radius: 4px;
            }
            .status-message {
                margin-top: 20px;
                padding: 10px;
                border-radius: 5px;
                display: none;
            }
            .status-message.success { background-color: #d4edda; color: #155724; }
            .status-message.error { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RAG Document Dashboard</h1>
            <p>Documents in your ChromaDB collection. You can view and delete them here.</p>
            <div class="status-message" id="statusMessage"></div>
            <ul id="fileList" class="file-list">
                <li>Loading files...</li>
            </ul>
        </div>

        <script>
            const fileListElement = document.getElementById('fileList');
            const statusMessageElement = document.getElementById('statusMessage');

            async function fetchFiles() {
                try {
                    const response = await fetch('/files_list');
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const files = await response.json();
                    renderFileList(files);
                } catch (error) {
                    console.error('Failed to fetch files:', error);
                    fileListElement.innerHTML = '<li>Error loading files.</li>';
                }
            }

            function renderFileList(files) {
                fileListElement.innerHTML = '';
                if (files.length === 0) {
                    fileListElement.innerHTML = '<li>No documents found in the collection.</li>';
                    return;
                }
                files.forEach(filename => {
                    const listItem = document.createElement('li');
                    listItem.className = 'file-item';
                    listItem.innerHTML = `
                        <span class="file-name">${filename}</span>
                        <button class="delete-btn" data-filename="${filename}">Delete</button>
                    `;
                    fileListElement.appendChild(listItem);
                });
                document.querySelectorAll('.delete-btn').forEach(button => {
                    button.addEventListener('click', handleDelete);
                });
            }

            async function handleDelete(event) {
                const filename = event.target.dataset.filename;
                if (!confirm(`Are you sure you want to delete all chunks for "${filename}"?`)) {
                    return;
                }

                try {
                    const response = await fetch('/delete_document', {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ filename: filename })
                    });

                    const result = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(result.detail || 'Failed to delete document.');
                    }

                    showMessage(`Successfully deleted document: "${filename}".`, 'success');
                    fetchFiles();
                } catch (error) {
                    console.error('Deletion error:', error);
                    showMessage(error.message, 'error');
                }
            }

            function showMessage(message, type) {
                statusMessageElement.textContent = message;
                statusMessageElement.className = `status-message ${type}`;
                statusMessageElement.style.display = 'block';
                setTimeout(() => {
                    statusMessageElement.style.display = 'none';
                }, 5000);
            }

            document.addEventListener('DOMContentLoaded', fetchFiles);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/files_list")
async def get_files_list():
    if collection is None:
        raise HTTPException(status_code=500, detail="ChromaDB not initialized.")
    
    try:
        results = collection.get(limit=collection.count(), include=['metadatas'])
        unique_filenames = set()
        if results['metadatas']:
            for metadata in results['metadatas']:
                if 'source_filename' in metadata:
                    unique_filenames.add(metadata['source_filename'])
        
        return list(unique_filenames)
    except Exception as e:
        print(f"Error fetching filenames from ChromaDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve filenames from the database.")


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...), metadata: str = Form(None)):
    if collection is None or embeddings is None:
        raise HTTPException(status_code=500, detail="RAG system not initialized (ChromaDB or Embedding Model issue).")

    content = await file.read()
    filename = file.filename

    filename_hash = hashlib.sha256(filename.encode('utf-8')).hexdigest()
    
    try:
        collection.delete(where={"_filename_hash": {"$eq": filename_hash}})
        print(f"Successfully deleted all old chunks for filename '{filename}' before adding new ones.")
    except Exception as e:
        print(f"No old chunks found for filename '{filename}' to delete. Proceeding with new ingestion.")

    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Metadata JSON ไม่ถูกต้อง")

    metadata_dict["source_filename"] = filename
    metadata_dict["_filename_hash"] = filename_hash

    raw_text = ""
    file_stream = io.BytesIO(content)
    if filename.endswith(".pdf"):
        try:
            raw_text = get_pdf_text(file_stream)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์ PDF: {e}")
    elif filename.endswith(".docx"):
        try:
            raw_text = get_docx_text(file_stream)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์ DOCX: {e}")
    elif filename.endswith(".txt"):
        try:
            raw_text = get_txt_text(file_stream)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์ TXT: {e}")
    elif filename.endswith(".md"): # <--- ส่วนที่เพิ่มเข้ามา
        try:
            raw_text = get_md_text(file_stream)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์ Markdown: {e}")
    else:
        raise HTTPException(status_code=400, detail="รูปแบบไฟล์ไม่รองรับ (รองรับเฉพาะ .pdf, .docx, .txt, .md)") # <--- แก้ไขข้อความ

    if not raw_text:
        raise HTTPException(status_code=400, detail="ไม่พบข้อความในเอกสารที่ประมวลผลได้")

    text_chunks = text_splitter.split_text(raw_text)

    documents_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    for i, chunk in enumerate(text_chunks):
        documents_to_add.append(chunk)
        chunk_metadata = metadata_dict.copy()
        chunk_metadata["chunk_id"] = i
        metadatas_to_add.append(chunk_metadata)
        ids_to_add.append(f"{filename}_{i}")

    try:
        if documents_to_add:
            chunk_embeddings = embeddings.embed_documents(documents_to_add)
            collection.add(
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                embeddings=chunk_embeddings,
                ids=ids_to_add
            )
            print(f"Added {len(documents_to_add)} chunks to ChromaDB from {filename}")
            print(f"Total documents in collection now: {collection.count()}")
        else:
            print(f"No chunks to add for {filename}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการเพิ่มข้อมูลเข้า ChromaDB: {e}")

    return {
        "message": f"อัปโหลดและประมวลผล '{filename}' สำเร็จ",
        "filename": filename,
        "metadata": metadata_dict,
        "chunks_added": len(documents_to_add),
        "total_documents_in_db": collection.count() if collection else 0
    }

@app.delete("/delete_document")
async def delete_document(payload: dict):
    if collection is None:
        raise HTTPException(status_code=500, detail="ChromaDB ไม่พร้อมใช้งานสำหรับการลบเอกสาร")

    filename = payload.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="กรุณาใส่ชื่อไฟล์ที่ต้องการลบใน JSON payload: {'filename': 'your_file.pdf'}")

    try:
        file_hash = hashlib.sha256(filename.encode('utf-8')).hexdigest()
        deleted_results = collection.delete(where={"_filename_hash": {"$eq": file_hash}})
        
        deleted_ids_count = len(deleted_results.get('ids', [])) if deleted_results else 0
        
        if deleted_ids_count > 0:
            print(f"Deleted {deleted_ids_count} chunks related to '{filename}'.")
            return {"message": f"ลบข้อมูลจากไฟล์ '{filename}' สำเร็จ!", "chunks_deleted": deleted_ids_count}
        else:
            print(f"No chunks found for filename '{filename}' to delete. Check filename or metadata.")
            return {"message": f"ไม่พบข้อมูลสำหรับไฟล์ '{filename}'", "chunks_deleted": 0}

    except Exception as e:
        print(f"Error during document deletion: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการลบเอกสาร: {e}")


@app.post("/query")
async def query_rag(payload: dict, request: Request, memory: ConversationSummaryBufferMemory = Depends(get_memory)):
    if collection is None or embeddings is None or llm_qa is None or llm_memory_summarizer is None or vectorstore is None:
        raise HTTPException(status_code=500, detail="RAG system not fully initialized.")

    query = payload.get("query")
    filters = payload.get("filters", {})
    top_k = payload.get("top_k", 5)

    if not query:
        raise HTTPException(status_code=400, detail="กรุณาใส่คำถาม")
        
    try:
        retriever_kwargs = {"k": top_k}
        if filters:
            chroma_filters = {key: {"$eq": value} for key, value in filters.items()}
            retriever_kwargs["filter"] = chroma_filters

        retriever = vectorstore.as_retriever(search_kwargs=retriever_kwargs)
        
        relevant_docs = retriever.invoke(query)
        
        template = """
คุณคือผู้ช่วย AI ที่เชี่ยวชาญในการตอบคำถามจากข้อมูลที่ให้ไว้เท่านั้น
คุณจะได้รับ:
- ประวัติการสนทนา (ถ้ามี)
- บริบทจากเอกสาร (context)

กรุณาตอบคำถามโดยอ้างอิงเฉพาะข้อมูลที่มีในบริบทเท่านั้น
หากบริบทไม่เพียงพอในการตอบคำถาม ให้ตอบว่า:
"ไม่สามารถให้คำตอบได้ เนื่องจากไม่มีข้อมูล"

โปรดตอบอย่างสุภาพ ละเอียด และครบถ้วนที่สุด โดยใช้คำลงท้ายว่า "ครับ"

---
ประวัติการสนทนา:
{chat_history}
---
บริบทจากเอกสาร:
{context}
---
คำถาม:
{question}

คำตอบ:
"""

        
        prompt = PromptTemplate.from_template(template)
        
        rag_chain = (
            RunnablePassthrough.assign(context=(lambda x: format_docs(relevant_docs)))
            | prompt
            | llm_qa
            | StrOutputParser()
        )
        
        chat_history = memory.load_memory_variables({})["chat_history"]

        chain_input = {"question": query, "chat_history": chat_history}
        answer = rag_chain.invoke(chain_input)
        
        memory.save_context({"input": query}, {"output": answer})

        source_files = set([doc.metadata.get('source_filename', 'Unknown Source') for doc in relevant_docs])
        
        response_data = {
            "answer": answer,
            "relevant_sources": list(source_files),
            "source_chunks": [{"content": c.page_content, "metadata": c.metadata} for c in relevant_docs]
        }
        
        return response_data
    
    except Exception as e:
        print(f"Error during query: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสอบถาม: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)