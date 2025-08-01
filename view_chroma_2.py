import chromadb
import os
import json
import hashlib

# Configuration (ต้องตรงกับที่ใช้ใน app.py ของคุณ)
CHROMA_HOST = os.getenv("CHROMA_HOST", "10.10.32.78")
CHROMA_PORT = os.getenv("CHROMA_PORT", "8001")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_documents")

try:
    # 1. เชื่อมต่อ ChromaDB Client
    client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print(f"Connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}, collection: {COLLECTION_NAME}")
    print(f"Total documents in collection: {collection.count()}")

    # 2. ดึงข้อมูลตัวอย่างบางส่วน
    print("\n--- First 10 documents in collection (peek) ---")
    results = collection.peek(limit=10)
    
    if results['ids']:
        for i in range(len(results['ids'])):
            doc_id = results['ids'][i]
            doc_metadata = results['metadatas'][i]
            doc_content = results['documents'][i]
            print(f"--- Document ID: {doc_id} ---")
            print(f"Metadata: {doc_metadata}")
            print(f"Content: {doc_content[:200]}...")
            print("-" * 30)
    else:
        print("No documents found in collection or peek limit too low.")

    # --- ส่วนใหม่: เพิ่มฟังก์ชันการลบและการแสดงรายการ ---
    print("\n--- Document Management Options ---")
    print("1. Delete by ID(s)")
    print("2. Delete by Metadata filter")
    print("3. Delete by filename (using source_filename metadata)")
    print("4. List all unique filenames") # <--- เพิ่มหัวข้อใหม่
    print("5. Exit")
    
    option = input("Enter option number (1-5): ")

    if option == '1':
        ids_to_delete_str = input("Enter comma-separated IDs to delete (e.g., id1,id2): ")
        ids_to_delete = [id.strip() for id in ids_to_delete_str.split(',')]
        if ids_to_delete:
            print(f"Attempting to delete documents with IDs: {ids_to_delete}")
            collection.delete(ids=ids_to_delete)
            print("Deletion by ID completed.")
        else:
            print("No IDs provided for deletion.")

    elif option == '2':
        print("Enter metadata filter in JSON format (e.g., {\"document_type\": \"สมุนไพรพื้นบ้าน\"})")
        filter_str = input("Filter JSON: ")
        try:
            filter_dict = json.loads(filter_str)
            if filter_dict:
                print(f"Attempting to delete documents with metadata filter: {filter_dict}")
                collection.delete(where=filter_dict)
                print("Deletion by metadata filter completed.")
            else:
                print("Empty filter provided. No documents deleted.")
        except json.JSONDecodeError:
            print("Invalid JSON format for filter. Deletion cancelled.")
        except Exception as e:
            print(f"Error during deletion with metadata filter: {e}")

    elif option == '3':
        filename_to_delete = input("Enter source filename to delete (e.g., herbs_7_with_usage.txt): ")
        if filename_to_delete:
            # ใช้ hashlib.sha256 เพื่อให้ลบได้สอดคล้องกับ app.py เวอร์ชันล่าสุด
            filename_hash = hashlib.sha256(filename_to_delete.encode('utf-8')).hexdigest()
            print(f"Attempting to delete documents from filename: {filename_to_delete} (hash: {filename_hash})")
            collection.delete(where={"_filename_hash": filename_hash})
            print("Deletion by filename completed.")
        else:
            print("No filename provided for deletion.")
    
    elif option == '4': # <--- ส่วนใหม่: List all unique filenames
        print("--- All Unique Filenames in Collection ---")
        results = collection.get(limit=collection.count(), include=['metadatas'])
        unique_filenames = set()
        if results['metadatas']:
            for metadata in results['metadatas']:
                if 'source_filename' in metadata:
                    unique_filenames.add(metadata['source_filename'])
        
        if unique_filenames:
            for filename in sorted(list(unique_filenames)):
                print(f"- {filename}")
        else:
            print("No filenames found in the collection.")
    
    elif option == '5':
        print("Exiting.")
    
    else:
        print("Invalid option selected.")

    # 3. แสดงจำนวนเอกสารหลังการทำงาน (เพื่อยืนยัน)
    print(f"\nTotal documents in collection after operation: {collection.count()}")

except Exception as e:
    print(f"ERROR: Could not connect to ChromaDB or perform operation. Error: {e}")
