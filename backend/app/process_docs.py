import os
from pathlib import Path
import pandas as pd
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from dotenv import load_dotenv
import docx

# Load environment variables
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def process_documents():
    """Process documents and create embeddings."""
    try:
        # Use absolute path for ChromaDB
        base_dir = Path(__file__).parent.parent
        chroma_dir = base_dir / "data" / "chroma_db"
        print(f"Using ChromaDB directory: {chroma_dir.absolute()}")
        
        # Initialize ChromaDB with PersistentClient
        chroma_client = chromadb.PersistentClient(
            path=str(chroma_dir.absolute()),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )

        # Delete existing collection if it exists
        try:
            chroma_client.delete_collection("skincare_docs")
            print("Deleted existing collection")
        except:
            print("No existing collection to delete")

        # Create new collection with default embedding function
        collection = chroma_client.create_collection(
            name="skincare_docs",
            embedding_function=chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        )
        print("Created new collection")

        # Process Excel catalog
        catalog_path = base_dir / "data" / "skincare catalog.xlsx"
        print(f"Looking for catalog at: {catalog_path.absolute()}")
        if catalog_path.exists():
            print("Found catalog file")
            df = pd.read_excel(catalog_path)
            print(f"Read {len(df)} rows from catalog")
            
            # Convert each product to a document
            documents = []
            metadatas = []
            ids = []
            
            for _, row in df.iterrows():
                product_text = f"""
                Product: {row['name']}
                Category: {row['category']}
                Description: {row['description']}
                Ingredients: {row['top_ingredients']}
                Tags: {row['tags']}
                """
                
                documents.append(product_text)
                metadatas.append({"source": "catalog", "product_id": str(row['product_id'])})
                ids.append(f"product_{row['product_id']}")
            
            # Add all products at once
            if documents:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Added {len(documents)} products to collection")
        else:
            print("Catalog file not found!")

        # Process additional info document
        info_path = base_dir / "data" / "Additional info (brand, reviews, customer tickets).docx"
        print(f"Looking for additional info at: {info_path.absolute()}")
        if info_path.exists():
            print("Found additional info file")
            text = extract_text_from_docx(info_path)
            print(f"Extracted {len(text)} characters from additional info")
            
            # Split text into chunks (simple splitting by paragraphs)
            chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
            print(f"Split into {len(chunks)} chunks")
            
            # Add chunks to collection
            if chunks:
                collection.add(
                    documents=chunks,
                    metadatas=[{"source": "additional_info", "chunk_id": str(i)} for i in range(len(chunks))],
                    ids=[f"info_{i}" for i in range(len(chunks))]
                )
                print(f"Added {len(chunks)} info chunks to collection")
        else:
            print("Additional info file not found!")

        # Verify collection contents
        count = collection.count()
        print(f"Final collection count: {count} documents")
        
        if count == 0:
            raise Exception("No documents were added to the collection!")

        print("Document processing completed successfully")
        return True

    except Exception as e:
        print(f"Error processing documents: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    process_documents()