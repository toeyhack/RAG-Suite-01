# RAG System with FastAPI, Ollama & ChromaDB
โปรเจกต์นี้คือระบบ Retrieval-Augmented Generation (RAG) ที่สร้างขึ้นด้วย FastAPI เพื่อเป็น Backend API สำหรับการตอบคำถามจากเอกสารของคุณโดยเฉพาะ ระบบนี้ใช้ Ollama สำหรับโมเดลภาษาและการทำ Embedding และใช้ ChromaDB เป็นฐานข้อมูล Vector

# คุณสมบัติหลัก
การนำเข้าข้อมูล (Ingestion): รองรับการอัปโหลดไฟล์หลายประเภท ได้แก่ .pdf, .docx, .txt, และ .md

ระบบตอบคำถาม RAG: ตอบคำถามจากเนื้อหาในเอกสารที่อัปโหลดเท่านั้น ช่วยลดการสร้างข้อมูลปลอม (Hallucination)

การสนทนา: มีระบบจดจำประวัติการสนทนา (Conversation Memory) ช่วยให้ AI เข้าใจบริบทต่อเนื่อง

Dashboard: มีหน้าเว็บ Dashboard ง่ายๆ สำหรับดูรายการเอกสารและลบข้อมูลที่ไม่ต้องการ

การตั้งค่าที่ยืดหยุ่น: สามารถปรับเปลี่ยนโมเดล Embedding และ LLM ได้อย่างง่ายดายผ่าน Environment Variables
# การติดตั้ง 
1.ollama pull nomic-embed-text:latest
2.ollama pull llama3.1:8b
3.git clone โปรเจ็ค
5. cd โปรเจ็ค
4.conda create -n rag-suite python=3.10
5.conda activate rag-suite
6. pip install -r requirements.txt
7. python3 app.py -> รันโปรแกรมหลักของ RAG
8. streamlit run streamlit_app.py -> ส่วน GUI Streamlit
# GUI
9. http://ip:8002/redocs ->  API Docs
10. http://ip:8002/dashboard -> จัดการ File เอกสาร
# โปรแแกรมอื่นๆ
  - python3 view_chroma.py  -> ดู Chunk ของเอกสาร
  -  python3 view_chroma_2.py -> จัดการด, ลบเอกสาร

# การปรับแต่ง
CHROMA_HOST=10.10.32.78 -> เปลี่ยนเป็น IP ของคุณ
CHROMA_PORT=8001
CHROMA_COLLECTION_NAME=rag_documents
EMBEDDING_MODEL_NAME=nomic-embed-text:latest
SESSION_SECRET_KEY="a_strong_random_secret_key"
CHROMA_HOST และ CHROMA_PORT: ที่อยู่ของ ChromaDB Server

CHROMA_COLLECTION_NAME: ชื่อ Collection ที่ใช้เก็บเอกสาร

EMBEDDING_MODEL_NAME: ชื่อโมเดลสำหรับทำ Embedding ใน Ollama

SESSION_SECRET_KEY: คีย์ลับสำหรับจัดการ Session ใน FastAPI (ต้องตั้งค่าเป็นค่าที่คาดเดายาก)


