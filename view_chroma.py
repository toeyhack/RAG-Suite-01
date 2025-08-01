import chromadb
import os

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

    # 2. ดึง ID ของไฟล์ที่มีปัญหาออกมาทั้งหมด
    filename_to_check = "urban_forest_rules.txt"
    print(f"\n--- Fetching all IDs for filename: '{filename_to_check}' ---")
    
    results = collection.get(where={"source_filename": filename_to_check}, include=[])
    
    if results['ids']:
        print(f"Found {len(results['ids'])} chunks with the filename '{filename_to_check}'.")
        print("Here are the IDs you need to delete:")
        for doc_id in results['ids']:
            print(f"- {doc_id}")
    else:
        print("No documents found with that filename. This is strange. Let's try getting all IDs.")
        all_results = collection.get(limit=collection.count(), include=[])
        if all_results['ids']:
            print(f"Found {len(all_results['ids'])} total documents in the collection.")
            print("Please manually copy these IDs for deletion:")
            for doc_id in all_results['ids']:
                print(f"- {doc_id}")
        else:
            print("No documents found in the collection at all.")

except Exception as e:
    print(f"ERROR: Could not connect to ChromaDB or perform operation. Error: {e}")