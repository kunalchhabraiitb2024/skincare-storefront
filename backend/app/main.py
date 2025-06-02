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
import uuid
from datetime import datetime
import uuid
from datetime import datetime

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Skincare Store API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage (in production, use Redis or database)
sessions: Dict[str, Dict] = {}

# Initialize Gemini
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Successfully initialized Gemini model: gemini-1.5-flash")
except Exception as e:
    print(f"Error initializing Gemini: {e}")
    model = None

try:
    base_dir = Path(__file__).parent.parent
    chroma_dir = base_dir / "data" / "chroma_db"
    print(f"Using ChromaDB directory: {chroma_dir.absolute()}")
    
    chroma_dir.mkdir(parents=True, exist_ok=True)
    
    chroma_client = chromadb.PersistentClient(path=str(chroma_dir.absolute()))
    
    time.sleep(5)

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
        df = pd.read_excel("data/skincare catalog.xlsx")
        
        df['price (USD)'] = pd.to_numeric(df['price (USD)'], errors='coerce')

        records = df.to_dict('records')
        
        return records
    except Exception as e:
        print(f"Error loading catalog: {e}")
        return []

# Enhanced Models
class ConversationTurn(BaseModel):
    query: str
    query_type: str
    answer: str
    timestamp: datetime
    products_shown: Optional[List[str]] = []

class SessionData(BaseModel):
    session_id: str
    conversation_history: List[ConversationTurn] = []
    user_preferences: Dict[str, Any] = {}
    created_at: datetime
    last_activity: datetime

# Models
class SearchQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
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
    session_id: str
    conversation_context: Optional[str] = None

# Session Management Functions
def create_session() -> str:
    """Create a new session and return session ID."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session_id": session_id,
        "conversation_history": [],
        "user_preferences": {},
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    print(f"Created new session: {session_id}")
    return session_id

def get_session(session_id: str) -> Optional[Dict]:
    """Get session data by session ID."""
    if session_id in sessions:
        sessions[session_id]["last_activity"] = datetime.now()
        return sessions[session_id]
    return None

def add_to_conversation_history(session_id: str, query: str, query_type: str, answer: str, products: List[str] = []):
    """Add a conversation turn to session history."""
    if session_id in sessions:
        conversation_turn = {
            "query": query,
            "query_type": query_type,
            "answer": answer,
            "timestamp": datetime.now(),
            "products_shown": products
        }
        sessions[session_id]["conversation_history"].append(conversation_turn)
        
        # Keep only last 10 conversations to prevent memory issues
        if len(sessions[session_id]["conversation_history"]) > 10:
            sessions[session_id]["conversation_history"] = sessions[session_id]["conversation_history"][-10:]

def get_conversation_context(session_id: str) -> str:
    """Get conversation context for better responses."""
    if session_id not in sessions:
        return ""
    
    history = sessions[session_id]["conversation_history"]
    if not history:
        return ""
    
    # Create a summary of recent conversation
    context_parts = []
    for turn in history[-3:]:  # Last 3 turns
        context_parts.append(f"User asked: {turn['query']}")
        if turn['answer']:
            context_parts.append(f"We responded about: {turn['answer'][:100]}...")
    
    return " | ".join(context_parts)

def extract_user_preferences(session_id: str, query: str):
    """Extract and store user preferences from query."""
    if session_id not in sessions:
        return
    
    preferences = sessions[session_id]["user_preferences"]
    query_lower = query.lower()
    
    # Extract skin type
    if any(term in query_lower for term in ['dry skin', 'oily skin', 'combination skin', 'sensitive skin']):
        if 'dry' in query_lower:
            preferences['skin_type'] = 'dry'
        elif 'oily' in query_lower:
            preferences['skin_type'] = 'oily'
        elif 'combination' in query_lower:
            preferences['skin_type'] = 'combination'
        elif 'sensitive' in query_lower:
            preferences['skin_type'] = 'sensitive'
    
    # Extract concerns
    concerns = []
    if 'acne' in query_lower or 'breakout' in query_lower:
        concerns.append('acne')
    if 'aging' in query_lower or 'wrinkle' in query_lower:
        concerns.append('anti-aging')
    if 'dark spot' in query_lower or 'pigmentation' in query_lower:
        concerns.append('dark_spots')
    if 'hydration' in query_lower or 'moisture' in query_lower:
        concerns.append('hydration')
    
    if concerns:
        preferences['concerns'] = list(set(preferences.get('concerns', []) + concerns))
    
    print(f"Updated preferences for session {session_id}: {preferences}")

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
    """Classify query as 'QUESTION' or 'RECOMMENDATION' with improved logic."""
    print(f"\n=== Classifying Query: '{query}' ===")
    if model:
        try:
            prompt = f"""
            Classify the following user query as either 'QUESTION' or 'RECOMMENDATION'.
            
            QUESTION: User is asking for information, explanations, comparisons, or general knowledge
            Examples: "What is retinol?", "How does vitamin C help skin?", "Is this product good for sensitive skin?"
            
            RECOMMENDATION: User is seeking personalized product suggestions based on their specific needs
            Examples: "I need something for dry skin", "Recommend products for acne", "What should I use for anti-aging?"
            
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

    # Enhanced fallback logic
    query_lower = query.lower()
    
    # Strong question indicators
    question_indicators = [
        'what is', 'what are', 'how does', 'how is', 'why does', 'why is',
        'tell me about', 'explain', 'define', 'difference between',
        'can you explain', 'help me understand', 'is it true that',
        'good for', 'suitable for', 'safe for', 'will this', 'does this'
    ]
    
    # Strong recommendation indicators  
    recommendation_indicators = [
        'recommend', 'suggest', 'need something', 'looking for', 'find me',
        'i have', 'my skin is', 'for my', 'help with my', 'best for',
        'products for', 'what should i use', 'routine for'
    ]
    
    # Check for strong indicators first
    for indicator in recommendation_indicators:
        if indicator in query_lower:
            print(f"Keyword Classification: RECOMMENDATION (matched: {indicator})")
            return "RECOMMENDATION"
            
    for indicator in question_indicators:
        if indicator in query_lower:
            print(f"Keyword Classification: QUESTION (matched: {indicator})")
            return "QUESTION"
    
    # Default based on query structure
    if '?' in query:
        print("Keyword Classification: QUESTION (contains question mark)")
        return "QUESTION"
    else:
        print("Keyword Classification: Defaulting to RECOMMENDATION")
        return "RECOMMENDATION"

def generate_fallback_answer(query: str, context: List[str], user_preferences: Dict[str, Any] = {}) -> str:
    """Generate a helpful answer without using LLM based on context and query analysis."""
    if not context:
        return f"I couldn't find specific information related to \"{query}\" in my knowledge base. However, I've found some relevant products below that might help!"
    
    query_lower = query.lower()
    
    # Extract useful information from context
    products_mentioned = []
    categories_found = set()
    ingredients_found = set()
    
    for ctx in context:
        if "Product:" in ctx:
            # Extract product name
            lines = ctx.strip().split('\n')
            for line in lines:
                if line.strip().startswith("Product:"):
                    product_name = line.replace("Product:", "").strip()
                    products_mentioned.append(product_name)
                elif line.strip().startswith("Category:"):
                    category = line.replace("Category:", "").strip()
                    categories_found.add(category)
                elif line.strip().startswith("Ingredients:"):
                    ingredients = line.replace("Ingredients:", "").strip()
                    # Split ingredients by semicolon or comma
                    for ingredient in ingredients.replace(';', ',').split(','):
                        ingredients_found.add(ingredient.strip())
    
    # Build a contextual response
    response_parts = []
    
    # User preference context
    if user_preferences.get('skin_type'):
        skin_type = user_preferences['skin_type']
        response_parts.append(f"For your {skin_type} skin")
    
    # Query-specific responses
    if any(word in query_lower for word in ['moisturizer', 'cream', 'hydrat']):
        if 'dry' in query_lower or user_preferences.get('skin_type') == 'dry':
            response_parts.append("I found some excellent hydrating options that should help with dryness.")
        elif 'oily' in query_lower or user_preferences.get('skin_type') == 'oily':
            response_parts.append("I found lightweight, oil-free moisturizers that won't clog pores.")
        else:
            response_parts.append("I found some great moisturizing products that should help.")
    
    elif any(word in query_lower for word in ['serum', 'treatment']):
        response_parts.append("I found some targeted serums that could address your skincare concerns.")
    
    elif any(word in query_lower for word in ['spf', 'sunscreen', 'sun protection']):
        response_parts.append("I found some excellent sun protection products to keep your skin safe.")
    
    elif any(word in query_lower for word in ['acne', 'breakout', 'blemish']):
        response_parts.append("I found some products designed to help with acne and blemish control.")
    
    elif any(word in query_lower for word in ['sensitive', 'gentle']):
        response_parts.append("I found some gentle, sensitive skin-friendly options.")
    
    else:
        response_parts.append("Based on your query, I found some relevant products that might interest you.")
    
    # Add ingredient highlights if found
    if ingredients_found:
        key_ingredients = list(ingredients_found)[:3]  # Top 3 ingredients
        response_parts.append(f"These products feature ingredients like {', '.join(key_ingredients)}.")
    
    # Add category information
    if categories_found:
        if len(categories_found) == 1:
            category = list(categories_found)[0]
            response_parts.append(f"All products are from the {category} category.")
    
    # Combine response parts
    if response_parts:
        return " ".join(response_parts) + " Check out the recommendations below!"
    else:
        return "I found some products that match your search. Take a look at the recommendations below!"

def generate_answer(query: str, context: List[str], conversation_context: str = "", user_preferences: Dict[str, Any] = {}) -> str:
    """Generate an answer based on the query, context, and conversation history."""
    print(f"\n=== Generating Answer ===")
    if not model:
        print("LLM model not available, using fallback answer generation.")
        return generate_fallback_answer(query, context, user_preferences)
    
    if not context:
        print("No context available for answer generation.")
        return f"I couldn't find specific information related to \"{query}\" in my knowledge base."

    try:
        # Build enhanced prompt with conversation context and preferences
        preference_context = ""
        if user_preferences:
            prefs = []
            if 'skin_type' in user_preferences:
                prefs.append(f"Skin type: {user_preferences['skin_type']}")
            if 'concerns' in user_preferences:
                prefs.append(f"Concerns: {', '.join(user_preferences['concerns'])}")
            if prefs:
                preference_context = f"\nUser Profile: {' | '.join(prefs)}"
        
        conv_context = ""
        if conversation_context:
            conv_context = f"\nConversation History: {conversation_context}"
        
        prompt = f"""
        You are a skincare expert and personal shopper. Answer the following query based on the provided context.
        Be specific, helpful, and provide detailed information with citations.
        
        Guidelines:
        - Use a conversational, friendly tone as if you're a knowledgeable friend
        - Reference previous conversation if relevant
        - Tailor advice to user's known preferences and skin type
        - Provide actionable advice when possible
        - If you mention specific products, brands, or ingredients, cite them naturally
        - Keep responses concise but informative (2-3 sentences max)
        - If the context doesn't contain enough information, be honest about limitations

        Query: "{query}"{preference_context}{conv_context}

        Context:
        {chr(10).join([f'Source {i+1}: {text}' for i, text in enumerate(context)])}

        Answer (be conversational and cite sources naturally):
        """
        
        response = model.generate_content(prompt)
        answer_text = response.text.strip()
        print("Answer generated successfully.")
        return answer_text
    except Exception as e:
        print(f"Error generating answer with LLM: {e}")
        return "I am sorry, I encountered an error while trying to answer your question."

def generate_follow_up_question(query: str, context: List[str], user_preferences: Dict[str, Any] = {}, conversation_context: str = "") -> str:
    """Generate a smart follow-up question based on the query, context, and user history."""
    print(f"\n=== Generating Follow-up Question ===")
    if not model:
        # Enhanced fallback questions based on query content and preferences
        query_lower = query.lower()
        
        # If we know user's skin type, ask about specific concerns
        if user_preferences.get('skin_type'):
            skin_type = user_preferences['skin_type']
            if skin_type == 'dry':
                return "Are you looking for hydrating serums or rich moisturizers for your dry skin?"
            elif skin_type == 'oily':
                return "Would you prefer lightweight, oil-free formulas for your oily skin?"
            elif skin_type == 'sensitive':
                return "Are you looking for fragrance-free, gentle formulations?"
        
        # Default fallbacks based on query
        if any(word in query_lower for word in ['serum', 'serums']):
            return "What specific skin concerns are you targeting with serums - hydration, brightening, or anti-aging?"
        elif any(word in query_lower for word in ['moisturizer', 'cream', 'lotion']):
            return "What's your skin type? (dry, oily, combination, or sensitive)"
        elif any(word in query_lower for word in ['acne', 'pimple', 'breakout']):
            return "How would you describe your acne - occasional breakouts or persistent issues?"
        elif any(word in query_lower for word in ['anti-aging', 'wrinkle', 'fine line']):
            return "What's your primary aging concern - fine lines, firmness, or dark spots?"
        else:
            return "What's your main skin concern right now?"

    try:
        # Build context for follow-up generation
        pref_context = ""
        if user_preferences:
            known_info = []
            if 'skin_type' in user_preferences:
                known_info.append(f"skin type: {user_preferences['skin_type']}")
            if 'concerns' in user_preferences:
                known_info.append(f"concerns: {', '.join(user_preferences['concerns'])}")
            if known_info:
                pref_context = f" (We know: {', '.join(known_info)})"

        conv_context_str = ""
        if conversation_context:
            conv_context_str = f"\nPrevious conversation: {conversation_context}"

        prompt = f"""
        Generate ONE smart follow-up question to help narrow down the user's skincare needs.
        Make it specific, actionable, and conversational.
        
        Query: "{query}"{pref_context}
        Available context: {context[:2] if context else "No specific context"}{conv_context_str}
        
        Guidelines:
        - Don't ask about information we already know about the user
        - Ask about specific skin concerns, routines, or product preferences
        - Make it feel like a personal shopper conversation
        - Keep it under 15 words
        - Don't ask about budget or brand preferences
        - Be contextual to their current question
        
        Examples of good follow-ups:
        - "What time of day would you use this - morning or evening routine?"
        - "Are you looking for day or night skincare?"
        - "Do you prefer lightweight or rich textures?"
        - "What specific results are you hoping to see?"
        
        Generate one follow-up question:
        """
        
        response = model.generate_content(prompt)
        follow_up_text = response.text.strip()
        # Clean up the response
        if follow_up_text.startswith('"') and follow_up_text.endswith('"'):
            follow_up_text = follow_up_text[1:-1]
        print("Follow-up question generated successfully.")
        return follow_up_text
    except Exception as e:
        print(f"Error generating follow-up question: {e}")
        return "What specific skin concerns are you targeting?"

def calculate_relevance_score(product: Dict[str, Any], query: str, user_preferences: Dict[str, Any] = {}) -> float:
    """Calculate a relevance score for a product based on the query and user preferences."""
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
        
        # User preference bonuses
        if user_preferences:
            # Skin type preference bonus
            if 'skin_type' in user_preferences:
                skin_type = user_preferences['skin_type']
                tags_lower = product.get('tags', '').lower()
                if skin_type == 'dry' and any(term in tags_lower for term in ['hydrating', 'moisturizing', 'nourishing']):
                    score += 1.0
                    print(f"Skin type bonus (dry): {product.get('name', 'Unknown Product')}")
                elif skin_type == 'oily' and any(term in tags_lower for term in ['oil-free', 'lightweight', 'mattifying']):
                    score += 1.0
                    print(f"Skin type bonus (oily): {product.get('name', 'Unknown Product')}")
                elif skin_type == 'sensitive' and any(term in tags_lower for term in ['gentle', 'fragrance-free', 'hypoallergenic']):
                    score += 1.0
                    print(f"Skin type bonus (sensitive): {product.get('name', 'Unknown Product')}")
            
            # Concern-based bonus
            if 'concerns' in user_preferences:
                concerns = user_preferences['concerns']
                tags_lower = product.get('tags', '').lower()
                for concern in concerns:
                    if concern == 'acne' and any(term in tags_lower for term in ['acne', 'blemish', 'salicylic']):
                        score += 0.8
                    elif concern == 'anti-aging' and any(term in tags_lower for term in ['anti-aging', 'retinol', 'peptide']):
                        score += 0.8
                    elif concern == 'dark_spots' and any(term in tags_lower for term in ['brightening', 'vitamin c', 'niacinamide']):
                        score += 0.8
                    elif concern == 'hydration' and any(term in tags_lower for term in ['hydrating', 'hyaluronic', 'moisturizing']):
                        score += 0.8
        
        # Add margin as a business factor (0.1 to 0.5 points based on margin)
        if 'margin (%)' in product and isinstance(product['margin (%)'], (int, float)):
            margin_score = min(product['margin (%)'] * 0.01, 0.5)  # Cap at 0.5 points
            score += margin_score
            print(f"Margin bonus (+{margin_score:.2f}): {product.get('name', 'Unknown Product')}")
        else:
            print(f"Warning: 'margin (%)' not found or invalid in product {product.get('name', 'Unknown')}")
        
        print(f"Final score for {product.get('name', 'Unknown Product')}: {score}")
        return score
    except Exception as e:
        print(f"Error calculating relevance score for {product.get('name', 'Unknown Product')}: {e}")
        return 0.0

def simple_rank_products(products: List[Dict[str, Any]], query: str, user_preferences: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    """Simple keyword-based ranking when Gemini is not available."""
    print("\n=== Simple Ranking ===")
    query_lower = query.lower()
    print(f"Query (lowercase): {query_lower}")
    print(f"User preferences: {user_preferences}")
    
    # Calculate relevance scores for all products
    scored_products = []
    all_scores_zero = True
    for product in products:
        score = calculate_relevance_score(product, query, user_preferences)
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
    filtered_ranked_products = [p for p in ranked_products if calculate_relevance_score(p, query, user_preferences) > 0]
    
    print(f"\nFound {len(filtered_ranked_products)} products with score > 0")
    if not filtered_ranked_products:
        print("No matching products found with score > 0, returning all products.")
        # This case should ideally not be reached if all_scores_zero check works, but as a safeguard
        return products
    
    return filtered_ranked_products

def rank_products(products: List[Dict[str, Any]], query: str, context: List[str], user_preferences: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    """Rank products based on relevance, user preferences, and margin."""
    if not model:
        print("Using simple ranking as Gemini model is not available")
        return simple_rank_products(products, query, user_preferences)[:5]

    try:
        # Use the flash model which has better free tier limits and is faster
        # We will create a simpler prompt for it.
        pref_context = ""
        if user_preferences:
            pref_parts = []
            if 'skin_type' in user_preferences:
                pref_parts.append(f"Skin type: {user_preferences['skin_type']}")
            if 'concerns' in user_preferences:
                pref_parts.append(f"Concerns: {', '.join(user_preferences['concerns'])}")
            if pref_parts:
                pref_context = f"\nUser preferences: {' | '.join(pref_parts)}"

        prompt = f"""
        Query: "{query}"{pref_context}
        Context:
        {chr(10).join([f'<doc>{text}</doc>' for text in context])}

        Given the query, user preferences, and context, rank the following products by relevance. Consider tag matches, category relevance, description/ingredient matches, and user preferences.
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
             return simple_rank_products(products, query, user_preferences)[:5]

        # For now, just return the LLM ranked products up to 5
        
        print("\nLLM Ranked Products (Top 5):")
        for i, product in enumerate(ranked_products[:5]):
             score = calculate_relevance_score(product, query, user_preferences) # Log relevance score for context
             print(f"{i+1}. {product.get('name', 'Unknown Product')} (Score: {score:.2f}, Margin: {product.get('margin (%)', 0):.2f})")
        
        return ranked_products[:5]

    except Exception as e:
        print(f"Error ranking products with LLM: {e}")
        print("Falling back to simple ranking")
        return simple_rank_products(products, query, user_preferences)[:5]

# Routes
@app.get("/")
async def read_root():
    return {"message": "Welcome to Skincare Store API"}

@app.get("/products")
async def get_products():
    products = load_catalog()
    return products

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    session_data = get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Return safe session info (no sensitive data)
    return {
        "session_id": session_id,
        "conversation_count": len(session_data.get("conversation_history", [])),
        "user_preferences": session_data.get("user_preferences", {}),
        "created_at": session_data.get("created_at"),
        "last_activity": session_data.get("last_activity")
    }

@app.post("/session/clear")
async def clear_session(session_data: dict):
    """Clear a session."""
    session_id = session_data.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
        return {"message": "Session cleared successfully"}
    return {"message": "Session not found or already cleared"}

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

        # Get or create session
        session_id = query.session_id
        if not session_id:
            session_id = create_session()
            print(f"New session created: {session_id}")
        else:
            print(f"Existing session used: {session_id}")
        
        session_data = get_session(session_id)
        if not session_data:
            print(f"Session not found, creating new session data for: {session_id}")
            session_data = {
                "session_id": session_id,
                "conversation_history": [],
                "user_preferences": {},
                "created_at": datetime.now(),
                "last_activity": datetime.now()
            }
            sessions[session_id] = session_data

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
        conversation_context = get_conversation_context(session_id)
        user_preferences = session_data.get('user_preferences', {})
        answer = generate_answer(query.query, context, conversation_context, user_preferences)
        
        # Rank products based on query, context, and user preferences
        try:
            ranked_products = rank_products(products, query.query, context, user_preferences)
            print(f"Returning {len(ranked_products)} ranked products.")
        except Exception as e:
            print(f"Error ranking products: {e}")
            ranked_products = []
            print("Returning empty product list due to ranking error.")

        # Generate follow-up question only for recommendation type
        follow_up = None
        if query_type == "RECOMMENDATION":
            try:
                follow_up = generate_follow_up_question(query.query, context, user_preferences, conversation_context)
                print(f"Follow-up question: {follow_up}")
            except Exception as e:
                print(f"Error generating follow-up: {e}")
                follow_up = "What specific skin concerns are you targeting?"
        
        # Extract user preferences from the query
        extract_user_preferences(session_id, query.query)

        # Add the conversation turn to the session history
        add_to_conversation_history(session_id, query.query, query_type, answer, [p.get('product_id') for p in ranked_products])
        
        return SearchResponse(
            query_type=query_type,
            answer=answer,
            products=ranked_products,
            follow_up_question=follow_up,
            context=context,
            session_id=session_id,
            conversation_context=get_conversation_context(session_id)
        )
    except Exception as e:
        print(f"Unexpected error in search_products: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

def generate_fallback_answer(query: str, context: List[str], user_preferences: Dict[str, Any] = {}) -> str:
    """Generate a helpful answer without using LLM based on context and query analysis."""
    if not context:
        return f"I couldn't find specific information related to \"{query}\" in my knowledge base. However, I've found some relevant products below that might help!"
    
    query_lower = query.lower()
    
    # Extract useful information from context
    products_mentioned = []
    categories_found = set()
    ingredients_found = set()
    
    for ctx in context:
        if "Product:" in ctx:
            # Extract product name
            lines = ctx.strip().split('\n')
            for line in lines:
                if line.strip().startswith("Product:"):
                    product_name = line.replace("Product:", "").strip()
                    products_mentioned.append(product_name)
                elif line.strip().startswith("Category:"):
                    category = line.replace("Category:", "").strip()
                    categories_found.add(category)
                elif line.strip().startswith("Ingredients:"):
                    ingredients = line.replace("Ingredients:", "").strip()
                    # Split ingredients by semicolon or comma
                    for ingredient in ingredients.replace(';', ',').split(','):
                        ingredients_found.add(ingredient.strip())
    
    # Build a contextual response
    response_parts = []
    
    # User preference context
    if user_preferences.get('skin_type'):
        skin_type = user_preferences['skin_type']
        response_parts.append(f"For your {skin_type} skin")
    
    # Query-specific responses
    if any(word in query_lower for word in ['moisturizer', 'cream', 'hydrat']):
        if 'dry' in query_lower or user_preferences.get('skin_type') == 'dry':
            response_parts.append("I found some excellent hydrating options that should help with dryness.")
        elif 'oily' in query_lower or user_preferences.get('skin_type') == 'oily':
            response_parts.append("I found lightweight, oil-free moisturizers that won't clog pores.")
        else:
            response_parts.append("I found some great moisturizing products that should help.")
    
    elif any(word in query_lower for word in ['serum', 'treatment']):
        response_parts.append("I found some targeted serums that could address your skincare concerns.")
    
    elif any(word in query_lower for word in ['spf', 'sunscreen', 'sun protection']):
        response_parts.append("I found some excellent sun protection products to keep your skin safe.")
    
    elif any(word in query_lower for word in ['acne', 'breakout', 'blemish']):
        response_parts.append("I found some products designed to help with acne and blemish control.")
    
    elif any(word in query_lower for word in ['sensitive', 'gentle']):
        response_parts.append("I found some gentle, sensitive skin-friendly options.")
    
    else:
        response_parts.append("Based on your query, I found some relevant products that might interest you.")
    
    # Add ingredient highlights if found
    if ingredients_found:
        key_ingredients = list(ingredients_found)[:3]  # Top 3 ingredients
        response_parts.append(f"These products feature ingredients like {', '.join(key_ingredients)}.")
    
    # Add category information
    if categories_found:
        if len(categories_found) == 1:
            category = list(categories_found)[0]
            response_parts.append(f"All products are from the {category} category.")
    
    # Combine response parts
    if response_parts:
        return " ".join(response_parts) + " Check out the recommendations below!"
    else:
        return "I found some products that match your search. Take a look at the recommendations below!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
