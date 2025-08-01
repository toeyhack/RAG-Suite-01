# streamlit_app.py

import streamlit as st
import requests
import json
import os

# --- Configuration ---
# Make sure this matches the port your FastAPI backend is running on
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8002")

st.set_page_config(
    page_title="Thai RAG System PoC",
    page_icon="🤖",
    layout="centered"
)

st.title("🇹🇭 Thai RAG System PoC")
st.markdown("---")

# --- 1. Document Ingestion Section ---
st.header("1. อัปโหลดเอกสาร (Ingest Document)")
st.write("อัปโหลดไฟล์ PDF, DOCX, หรือ TXT เพื่อเพิ่มข้อมูลเข้าสู่ระบบ RAG")

uploaded_file = st.file_uploader(
    "เลือกไฟล์เอกสาร",
    type=["pdf", "docx", "txt"],
    help="รองรับไฟล์ .pdf, .docx, .txt"
)

metadata_input = st.text_input(
    "Metadata (JSON Format, Optional)",
    value='{"document_type": "general"}',
    help='ใส่ข้อมูลเพิ่มเติมในรูปแบบ JSON เช่น `{"document_type": "นโยบาย", "source": "HR_Policy_Manual"}`'
)

if st.button("อัปโหลดและประมวลผล", key="upload_button"):
    if uploaded_file is not None:
        try:
            # Prepare form data
            files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            # Check if metadata_input is valid JSON
            try:
                json_metadata = json.loads(metadata_input)
            except json.JSONDecodeError:
                st.error("Metadata ไม่ถูกต้อง กรุณาใส่ในรูปแบบ JSON ที่ถูกต้อง")
                st.stop() # Stop execution if JSON is invalid

            data = {'metadata': metadata_input} # Send as string, FastAPI will parse it

            with st.spinner("กำลังอัปโหลดและประมวลผลเอกสาร..."):
                response = requests.post(f"{FASTAPI_BASE_URL}/ingest", files=files, data=data)

                if response.status_code == 200:
                    st.success(f"อัปโหลดสำเร็จ: {response.json().get('message', 'เอกสารถูกประมวลผลแล้ว')}")
                    st.json(response.json())
                else:
                    st.error(f"เกิดข้อผิดพลาดในการอัปโหลด: {response.status_code}")
                    st.error(response.json().get("detail", "ไม่ทราบสาเหตุของข้อผิดพลาด"))
                    st.json(response.json()) # Show full error response
        except requests.exceptions.ConnectionError:
            st.error(f"ไม่สามารถเชื่อมต่อกับ FastAPI Backend ได้ กรุณาตรวจสอบว่า Backend กำลังทำงานอยู่ที่ {FASTAPI_BASE_URL} หรือไม่")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
    else:
        st.warning("กรุณาเลือกไฟล์เอกสารก่อนอัปโหลด")

st.markdown("---")

# --- 2. Chat with RAG Section ---
st.header("2. สนทนากับระบบ RAG")
st.write("พิมพ์คำถามของคุณเพื่อรับคำตอบจากข้อมูลที่ถูกประมวลผล")

query_input = st.text_area(
    "คำถามของคุณ",
    placeholder="ตัวอย่าง: 'สรรพคุณของขมิ้นชันมีอะไรบ้าง?' หรือ 'เงื่อนไขการลาป่วยมีอะไรบ้าง?'",
    height=100
)

col1, col2 = st.columns([1, 1])

with col1:
    filters_input = st.text_input(
        "Filters (JSON Format, Optional)",
        value='{}',
        help='ใส่ Filter เพื่อจำกัดการค้นหา เช่น `{"document_type": "สมุนไพร"}` หรือ `{"herb_name": "มะนาว"}`'
    )
with col2:
    top_k_input = st.number_input(
        "Top K Chunks",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="จำนวน Context Chunk ที่จะดึงมาช่วยในการตอบ"
    )

if st.button("ถาม RAG", key="query_button"):
    if query_input:
        try:
            # Check if filters_input is valid JSON
            try:
                json_filters = json.loads(filters_input)
            except json.JSONDecodeError:
                st.error("Filters ไม่ถูกต้อง กรุณาใส่ในรูปแบบ JSON ที่ถูกต้อง")
                st.stop() # Stop execution if JSON is invalid

            payload = {
                "query": query_input,
                "filters": json_filters,
                "top_k": top_k_input
            }

            with st.spinner("กำลังค้นหาและสร้างคำตอบ..."):
                response = requests.post(f"{FASTAPI_BASE_URL}/query", json=payload)

                if response.status_code == 200:
                    result = response.json()
                    st.subheader("คำตอบ:")
                    st.success(result.get("answer", "ไม่มีคำตอบ"))

                    st.subheader("แหล่งข้อมูลที่เกี่ยวข้อง:")
                    if result.get("relevant_sources"):
                        for source in result["relevant_sources"]:
                            st.markdown(f"- {source}")
                    else:
                        st.info("ไม่พบแหล่งข้อมูลที่เกี่ยวข้อง")

                    # Optionally show raw context chunks for debugging
                    # with st.expander("แสดง Context Chunks ที่ดึงมา"):
                    #     for i, chunk_data in enumerate(result.get("source_chunks", [])):
                    #         st.write(f"**Chunk {i+1}:**")
                    #         st.code(chunk_data.get("content", ""), language="text")

                else:
                    st.error(f"เกิดข้อผิดพลาดในการสอบถาม: {response.status_code}")
                    st.error(response.json().get("detail", "ไม่ทราบสาเหตุของข้อผิดพลาด"))
                    st.json(response.json()) # Show full error response
        except requests.exceptions.ConnectionError:
            st.error(f"ไม่สามารถเชื่อมต่อกับ FastAPI Backend ได้ กรุณาตรวจสอบว่า Backend กำลังทำงานอยู่ที่ {FASTAPI_BASE_URL} หรือไม่")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
    else:
        st.warning("กรุณาใส่คำถามของคุณ")

st.markdown("---")
st.info(f"FastAPI Backend URL: {FASTAPI_BASE_URL}")
# streamlit_app.py (เพิ่มส่วนนี้เข้าไปใน Streamlit App ของคุณ)

st.markdown("---")
st.header("3. ลบเอกสาร (Delete Document)")
st.write("ระบุชื่อไฟล์ที่ต้องการลบข้อมูลทั้งหมดออกจากระบบ (เช่น: `example.pdf`)")

filename_to_delete = st.text_input(
    "ชื่อไฟล์ที่ต้องการลบ",
    placeholder="ตัวอย่าง: my_policy_v1.pdf",
    key="delete_filename_input"
)

if st.button("ลบข้อมูลจากไฟล์นี้", key="delete_button"):
    if filename_to_delete:
        try:
            with st.spinner(f"กำลังลบข้อมูลจากไฟล์ {filename_to_delete}..."):
                # Use requests.delete for DELETE method
                response = requests.delete(f"{FASTAPI_BASE_URL}/delete_document", data={"filename": filename_to_delete})

                if response.status_code == 200:
                    st.success(f"ลบข้อมูลจาก '{filename_to_delete}' สำเร็จ!")
                    st.json(response.json())
                else:
                    st.error(f"เกิดข้อผิดพลาดในการลบ: {response.status_code}")
                    st.error(response.json().get("detail", "ไม่ทราบสาเหตุของข้อผิดพลาด"))
                    st.json(response.json())
        except requests.exceptions.ConnectionError:
            st.error(f"ไม่สามารถเชื่อมต่อกับ FastAPI Backend ได้")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
    else:
        st.warning("กรุณาใส่ชื่อไฟล์ที่ต้องการลบ")
