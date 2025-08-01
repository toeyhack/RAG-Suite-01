RAG System with FastAPI, Ollama & ChromaDB
โปรเจกต์นี้คือระบบ Retrieval-Augmented Generation (RAG) ที่สร้างขึ้นด้วย FastAPI เพื่อเป็น Backend API สำหรับการตอบคำถามจากเอกสารของคุณโดยเฉพาะ ระบบนี้ใช้ Ollama สำหรับโมเดลภาษาและการทำ Embedding และใช้ ChromaDB เป็นฐานข้อมูล Vector

คุณสมบัติหลัก
การนำเข้าข้อมูล (Ingestion): รองรับการอัปโหลดไฟล์หลายประเภท ได้แก่ .pdf, .docx, .txt, และ .md

ระบบตอบคำถาม RAG: ตอบคำถามจากเนื้อหาในเอกสารที่อัปโหลดเท่านั้น ช่วยลดการสร้างข้อมูลปลอม (Hallucination)

การสนทนา: มีระบบจดจำประวัติการสนทนา (Conversation Memory) ช่วยให้ AI เข้าใจบริบทต่อเนื่อง

Dashboard: มีหน้าเว็บ Dashboard ง่ายๆ สำหรับดูรายการเอกสารและลบข้อมูลที่ไม่ต้องการ

การตั้งค่าที่ยืดหยุ่น: สามารถปรับเปลี่ยนโมเดล Embedding และ LLM ได้อย่างง่ายดายผ่าน Environment Variables

การตั้งค่าเริ่มต้น (Prerequisites)
Python 3.10+: ติดตั้ง Python

Ollama: ติดตั้ง Ollama และดาวน์โหลดโมเดลที่ต้องการ (เช่น nomic-embed-text:latest และ llama3.1)

Bash

ollama pull nomic-embed-text:latest
ollama pull llama3.1
ChromaDB: รัน ChromaDB Client โดยใช้ Docker หรือติดตั้งแบบ Standalone (โปรเจกต์นี้ใช้การเชื่อมต่อแบบ Client)

Bash

docker run -p 8001:8000 chromadb/chroma
การติดตั้งและการใช้งาน
1. Clone โปรเจกต์
Bash

git clone <URL_ของ_repository_ของคุณ>
cd <ชื่อโฟลเดอร์โปรเจกต์>
2. สร้างและเปิดใช้งาน Virtual Environment
แนะนำให้ใช้ conda หรือ venv เพื่อจัดการไลบรารี

Bash

# ใช้ conda
conda create -n rag-env python=3.10
conda activate rag-env

# หรือใช้ venv
python -m venv rag-env
source rag-env/bin/activate  # สำหรับ macOS/Linux
# rag-env\Scripts\activate.bat  # สำหรับ Windows
3. ติดตั้งไลบรารีที่จำเป็น
โปรเจกต์นี้ใช้ไลบรารีที่อยู่ใน requirements.txt

Bash

pip install -r requirements.txt
4. ตั้งค่า Environment Variables
สร้างไฟล์ชื่อ .env ใน Root Folder ของโปรเจกต์ และเพิ่มข้อมูลต่อไปนี้:

Code snippet

CHROMA_HOST=10.10.32.78
CHROMA_PORT=8001
CHROMA_COLLECTION_NAME=rag_documents
EMBEDDING_MODEL_NAME=nomic-embed-text:latest
SESSION_SECRET_KEY="a_strong_random_secret_key"
CHROMA_HOST และ CHROMA_PORT: ที่อยู่ของ ChromaDB Server

CHROMA_COLLECTION_NAME: ชื่อ Collection ที่ใช้เก็บเอกสาร

EMBEDDING_MODEL_NAME: ชื่อโมเดลสำหรับทำ Embedding ใน Ollama

SESSION_SECRET_KEY: คีย์ลับสำหรับจัดการ Session ใน FastAPI (ต้องตั้งค่าเป็นค่าที่คาดเดายาก)

5. รัน FastAPI Server
Bash

uvicorn app:app --reload --host 0.0.0.0 --port 8002
เมื่อรันสำเร็จ คุณจะสามารถเข้าถึง API ได้ที่ http://0.0.0.0:8002

การใช้งาน API
คุณสามารถใช้เครื่องมืออย่าง Postman, Insomnia หรือ Python script เพื่อเรียกใช้ API ดังนี้:

อัปโหลดเอกสาร: POST ไปที่ /ingest

สอบถามคำถาม: POST ไปที่ /query พร้อมส่ง JSON Payload {"query": "คำถามของคุณ"}

ดู Dashboard: เข้าไปที่ http://0.0.0.0:8002/dashboard

ลบเอกสาร: DELETE ไปที่ /delete_document

ไฟล์และโครงสร้าง
app.py: ไฟล์หลักของ FastAPI Server ที่รวมฟังก์ชันทั้งหมดของระบบ RAG

requirements.txt: รายชื่อไลบรารีที่จำเป็นสำหรับโปรเจกต์

view_chroma.py: สคริปต์สำหรับตรวจสอบและจัดการเอกสารใน ChromaDB จาก Command Line

.env: ไฟล์สำหรับเก็บ Environment Variables

การปรับปรุงและพัฒนาเพิ่มเติม
โค้ดนี้ถูกออกแบบมาให้สามารถปรับปรุงต่อได้ง่าย คุณสามารถ:

เพิ่มการรองรับไฟล์ประเภทอื่นๆ

ปรับปรุง Prompt Template ใน app.py เพื่อให้ LLM ตอบได้ตรงใจมากขึ้น

ปรับเปลี่ยนค่า chunk_size และ chunk_overlap เพื่อทดลองหาค่าที่เหมาะสมที่สุด

สร้าง UI สำหรับผู้ใช้งานโดยเฉพาะด้วย Streamlit หรือ React
