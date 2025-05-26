from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from pathlib import Path
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Skincare Store API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    # Use the flash model which has better free tier limits
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Successfully initialized Gemini model: gemini-1.5-flash")
except Exception as e:
    print(f"Error initializing Gemini: {e}")
    model = None

# Initialize ChromaDB
try:
    # Use absolute path for ChromaDB
    base_dir = Path(__file__).parent.parent
    chroma_dir = base_dir / "data" / "chroma_db"
    print(f"Using ChromaDB directory: {chroma_dir.absolute()}")
    
    # Ensure the directory exists
    chroma_dir.mkdir(parents=True, exist_ok=True)
    
    # Use PersistentClient
    chroma_client = chromadb.PersistentClient(path=str(chroma_dir.absolute()))
    
    # Add a small delay to ensure persistence is ready (workaround)
    time.sleep(5) # Increased wait to 5 seconds

    # Get the collection
    try:
        collection = chroma_client.get_collection("skincare_docs")
        print(f"Found collection with {collection.count()} documents")
    except ValueError as e:
        print(f"Error getting collection: {e}")
        print("This likely means process_docs.py hasn't been run or the persistence failed.")
        collection = None # Explicitly set collection to None if not found

except Exception as e:
    print(f"Error initializing ChromaDB client: {e}")
    chroma_client = None
    collection = None

# Load product catalog
def load_catalog():
    try:
        print("\n=== Loading Catalog ===")
        df = pd.read_excel("data/skincare catalog.xlsx")
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        # Check price column before conversion
        print("\nPrice column before conversion:")
        print(df['price (USD)'].head())
        print(f"Price column dtype: {df['price (USD)'].dtype}")
        
        # Convert price column to numeric, handling any non-numeric values
        df['price (USD)'] = pd.to_numeric(df['price (USD)'], errors='coerce')
        
        # Check price column after conversion
        print("\nPrice column after conversion:")
        print(df['price (USD)'].head())
        print(f"Price column dtype: {df['price (USD)'].dtype}")
        print(f"Number of NaN values: {df['price (USD)'].isna().sum()}")
        
        # Convert to records and check first few
        records = df.to_dict('records')
        print("\nFirst record:")
        print(records[0] if records else "No records")
        
        return records
    except Exception as e:
        print(f"Error loading catalog: {e}")
        return []

# Models
class SearchQuery(BaseModel):
    query: str
    context: Optional[List[str]] = []

class Product(BaseModel):
    product_id: str
    name: str
    category: str
    description: str
    top_ingredients: str
    tags: str
    price: Optional[float] = Field(alias="price (USD)") # Make price optional and float
    margin: Optional[float] = Field(alias="margin (%)") # Make margin optional and float

class SearchResponse(BaseModel):
    query_type: str # "QUESTION" or "RECOMMENDATION"
    answer: Optional[str] = None
    products: Optional[List[Product]] = None
    follow_up_question: Optional[str] = None
    context: Optional[List[str]] = None

def get_relevant_context(query: str, n_results: int = 3) -> List[str]:
    """Get relevant context from the document store."""
    if not chroma_client or not collection:
        print("ChromaDB client or collection not initialized")
        return []
        
    try:
        if collection.count() == 0:
            print("Collection is empty, no context available")
            return []
            
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        documents = results.get('documents', [[]])[0] # Safely access documents
        print(f"Retrieved {len(documents)} context documents.")
        # Add source information if available in the results, maybe embed it in the text or return separately
        # For now, just return the text content
        return documents
    except Exception as e:
        print(f"Error getting context: {e}")
        return []

def classify_query(query: str) -> str:
    """Classify query as 'QUESTION' or 'RECOMMENDATION'."""
    print(f"\n=== Classifying Query: '{query}' ===")
    if model:
        try:
            prompt = f"""
            Classify the following user query as either 'QUESTION' or 'RECOMMENDATION'.
            If the query is asking about a specific product or seeking information, classify as 'QUESTION'.
            If the query is asking for product recommendations or suggestions, classify as 'RECOMMENDATION'.
            Respond with only the word 'QUESTION' or 'RECOMMENDATION'.

            Query: "{query}"
            """
            response = model.generate_content(prompt)
            classification = response.text.strip().upper()
            if classification in ['QUESTION', 'RECOMMENDATION']:
                print(f"LLM Classification: {classification}")
                return classification
            else:
                print(f"LLM returned unexpected classification: {classification}. Falling back to keyword check.")
        except Exception as e:
            print(f"Error classifying query with LLM: {e}. Falling back to keyword check.")

    # Fallback to keyword check if LLM is not available or fails
    query_lower = query.lower()
    question_keywords = ['what is', 'how is', 'tell me about', 'explain', 'define', 'why', 'can you explain', '?', 'will', 'good for', 'suitable for', 'help with']
    recommendation_keywords = ['recommend', 'suggest', 'show me', 'find', 'products', 'for dry skin', 'serum', 'moisturizer']

    if any(keyword in query_lower for keyword in question_keywords):
        print("Keyword Classification: QUESTION")
        return "QUESTION"
    elif any(keyword in query_lower for keyword in recommendation_keywords):
         print("Keyword Classification: RECOMMENDATION")
         return "RECOMMENDATION"
    else:
        # Default to recommendation if unclear
        print("Keyword Classification: Defaulting to RECOMMENDATION")
        return "RECOMMENDATION"

def generate_answer(query: str, context: List[str]) -> str:
    """Generate an answer based on the query and context."""
    print(f"\n=== Generating Answer ===")
    if not model:
        print("LLM model not available for answer generation.")
        return "I am sorry, I cannot answer questions right now. Please try again later."
    
    if not context:
        print("No context available for answer generation.")
        return f"I couldn't find specific information related to \"{query}\" in my knowledge base."

    try:
        prompt = f"""
        You are a skincare expert. Answer the following query based on the provided context.
        Be specific, helpful, and provide detailed information. If you can recommend specific products from the context, mention them.
        If the context doesn't contain enough information, say so clearly.

        Query: "{query}"

        Context:
        {chr(10).join([f'<doc>{text}</doc>' for text in context])}

        Answer:
        """
        
        response = model.generate_content(prompt)
        answer_text = response.text.strip()
        print("Answer generated successfully.")
        return answer_text
    except Exception as e:
        print(f"Error generating answer with LLM: {e}")
        return "I am sorry, I encountered an error while trying to answer your question."

def generate_follow_up_question(query: str, context: List[str]) -> str:
    """Generate a follow-up question based on the query and context."""
    print(f"\n=== Generating Follow-up Question ===")
    if not model:
        # Fallback questions based on query content
        query_lower = query.lower()
        if any(word in query_lower for word in ['moist', 'hydrat', 'dry']):
            return "What is your skin type (dry, oily, combination)?"
        elif any(word in query_lower for word in ['age', 'wrinkle', 'fine line']):
            return "What specific aging concerns would you like to address?"
        else:
            return "What specific skin concerns are you targeting?"

    try:
        # Shorter, more concise prompt for the flash model
        prompt = f"""
        Query: "{query}"
        Context: {context}
        
        Generate one follow-up question to help narrow down their search.
        Keep it specific and natural.
        
        If about moisture/hydration, ask about skin type.
        If about specific concerns, ask about current routine.
        If about anti-aging, ask about age range.
        """
        
        response = model.generate_content(prompt)
        follow_up_text = response.text.strip()
        print("Follow-up question generated successfully.")
        return follow_up_text
    except Exception as e:
        print(f"Error generating follow-up question: {e}")
        return "What specific skin concerns are you targeting?"

def calculate_relevance_score(product: Dict[str, Any], query: str) -> float:
    """Calculate a relevance score for a product based on the query."""
    try:
        query_lower = query.lower()
        score = 0.0
        
        # Split query into words
        query_words = set(query_lower.split())
        print(f"\nCalculating score for: {product.get('name', 'Unknown Product')}")
        print(f"Query words: {query_words}")
        
        # Check tags (highest weight)
        if product.get('tags'):
            tags = product['tags'].lower().split('|')
            print(f"Checking tags: {tags}")
            for tag in tags:
                # Check if any query word is in the tag
                if any(word in tag for word in query_words):
                    score += 3.0
                    print(f"Tag match: {tag} for query: {query_lower}")
        
        # Check category
        category_lower = product.get('category', '').lower()
        print(f"Checking category: {category_lower}")
        if any(word in category_lower for word in query_words):
            score += 2.0
            print(f"Category match: {product['category']} for query: {query_lower}")
        
        # Check description
        description_lower = product.get('description', '').lower()
        if any(word in description_lower for word in query_words):
            score += 1.5
            print(f"Description match for: {product.get('name', 'Unknown Product')}")
        
        # Check ingredients
        ingredients_lower = product.get('top_ingredients', '').lower()
        if any(word in ingredients_lower for word in query_words):
            score += 1.0
            print(f"Ingredient match for: {product.get('name', 'Unknown Product')}")
        
        # Add margin as a tiebreaker (0.1 to 0.5 points)
        if 'margin (%)' in product and isinstance(product['margin (%)'], (int, float)):
             score += product['margin (%)'] * 0.5
        else:
             print(f"Warning: 'margin (%)' not found or invalid in product {product.get('name', 'Unknown')}")

        
        print(f"Final score for {product.get('name', 'Unknown Product')}: {score}")
        return score
    except Exception as e:
        print(f"Error calculating relevance score for {product.get('name', 'Unknown Product')}: {e}")
        return 0.0

def simple_rank_products(products: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Simple keyword-based ranking when Gemini is not available."""
    print("\n=== Simple Ranking ===")
    query_lower = query.lower()
    print(f"Query (lowercase): {query_lower}")
    
    # Calculate relevance scores for all products
    scored_products = []
    all_scores_zero = True
    for product in products:
        score = calculate_relevance_score(product, query)
        scored_products.append((product, score))
        if score > 0:
            all_scores_zero = False
        print(f"\nProduct: {product.get('name', 'Unknown Product')}")
        print(f"Score: {score}")
        print(f"Tags: {product.get('tags', '')}")
        print(f"Category: {product.get('category', '')}")
    
    # Sort by score in descending order
    ranked_products = [p for p, s in sorted(scored_products, key=lambda x: x[1], reverse=True)]
    
    # If all scores are zero, return the first 5 products from the original list
    if all_scores_zero:
        print("All scores are zero, returning the first 5 products from the original list.")
        return products[:5]
    
    # Otherwise, return the top products with a score > 0
    filtered_ranked_products = [p for p in ranked_products if calculate_relevance_score(p, query) > 0]
    
    print(f"\nFound {len(filtered_ranked_products)} products with score > 0")
    if not filtered_ranked_products:
        print("No matching products found with score > 0, returning all products.")
        # This case should ideally not be reached if all_scores_zero check works, but as a safeguard
        return products
    
    return filtered_ranked_products

def rank_products(products: List[Dict[str, Any]], query: str, context: List[str]) -> List[Dict[str, Any]]:
    """Rank products based on relevance and margin."""
    if not model:
        print("Using simple ranking as Gemini model is not available")
        return simple_rank_products(products, query)[:5]

    try:
        # Use the flash model which has better free tier limits and is faster
        # We will create a simpler prompt for it.
        prompt = f"""
        Query: "{query}"
        Context:
        {chr(10).join([f'<doc>{text}</doc>' for text in context])}

        Given the query and context, rank the following products by relevance. Consider tag matches, category relevance, and description/ingredient matches.
        Return only the product_id for the top 5 most relevant products, one product_id per line.

        Products: {products}
        """
        
        response = model.generate_content(prompt)
        # Assuming the response is a list of product IDs, one per line or comma separated
        # Split by lines and then potentially by commas/spaces if needed
        ranked_ids = []
        for line in response.text.splitlines():
            ranked_ids.extend([pid.strip() for pid in line.replace(',', ' ').split() if pid.strip()])
        
        # Create a mapping of product IDs to their full data
        product_map = {str(p.get('product_id')): p for p in products}
        
        # Return products in ranked order based on the LLM response
        ranked_products = []
        for pid in ranked_ids:
            if pid in product_map:
                ranked_products.append(product_map[pid])
        
        # If LLM ranking failed or didn't return enough products, fallback to simple ranking
        if not ranked_products or len(ranked_products) < 5:
             print("LLM ranking failed or insufficient results, falling back to simple ranking")
             return simple_rank_products(products, query)[:5]

        # Add any products that were relevant but not in the top LLM list (optional, depending on desired behavior)
        # For now, just return the LLM ranked products up to 5
        
        print("\nLLM Ranked Products (Top 5):")
        for i, product in enumerate(ranked_products[:5]):
             score = calculate_relevance_score(product, query) # Log relevance score for context
             print(f"{i+1}. {product.get('name', 'Unknown Product')} (Score: {score:.2f}, Margin: {product.get('margin (%)', 0):.2f})")
        
        return ranked_products[:5]

    except Exception as e:
        print(f"Error ranking products with LLM: {e}")
        print("Falling back to simple ranking")
        return simple_rank_products(products, query)[:5]

# Routes
@app.get("/")
async def read_root():
    return {"message": "Welcome to Skincare Store API"}

@app.get("/products")
async def get_products():
    products = load_catalog()
    return products

@app.post("/search", response_model=SearchResponse)
async def search_products(query: SearchQuery):
    try:
        print(f"\n=== New Search Request ===")
        print(f"Query: {query.query}")
        
        # Classify the query
        query_type = classify_query(query.query)
        print(f"Query Type: {query_type}")
        
        # Get relevant context for both question answering and recommendations
        try:
            context = get_relevant_context(query.query)
            print(f"Context found: {context}")
        except Exception as e:
            print(f"Error getting context: {e}")
            context = []

        # Get all products
        try:
            products = load_catalog()
            if not products:
                print("No products found in catalog")
                raise HTTPException(status_code=404, detail="No products found in catalog")
            print(f"Loaded {len(products)} products")
        except Exception as e:
            print(f"Error loading catalog: {e}")
            raise HTTPException(status_code=500, detail=f"Error loading catalog: {str(e)}")

        # Generate answer for both question and recommendation types
        answer = generate_answer(query.query, context)
        
        # Rank products based on query and context
        try:
            ranked_products = rank_products(products, query.query, context)
            print(f"Returning {len(ranked_products)} ranked products.")
        except Exception as e:
            print(f"Error ranking products: {e}")
            ranked_products = []
            print("Returning empty product list due to ranking error.")

        # Generate follow-up question only for recommendation type
        follow_up = None
        if query_type == "RECOMMENDATION":
            try:
                follow_up = generate_follow_up_question(query.query, context)
                print(f"Follow-up question: {follow_up}")
            except Exception as e:
                print(f"Error generating follow-up: {e}")
                follow_up = "What specific skin concerns are you targeting?"
        
        return SearchResponse(
            query_type=query_type,
            answer=answer,
            products=ranked_products,
            follow_up_question=follow_up,
            context=context
        )
    except Exception as e:
        print(f"Unexpected error in search_products: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 