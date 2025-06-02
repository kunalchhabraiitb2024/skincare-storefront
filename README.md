# AI-Powered Skincare Store

An intelligent skincare store that uses AI to provide personalized product recommendations and answer skincare-related questions.

## Live Demo

- Frontend: [https://skincare-storefront.vercel.app](https://skincare-storefront.vercel.app)
- Backend API: [https://skincare-storefront.onrender.com](https://skincare-storefront.onrender.com)

## Features

- Natural language search for skincare products
- AI-powered product recommendations
- Question answering about skincare products
- Smart follow-up questions for better recommendations
- Beautiful, responsive UI

## Tech Stack

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python)
- **AI/LLM**: Google Gemini API
- **Vector DB**: ChromaDB for semantic search
- **Deployment**: 
  - Frontend: Vercel
  - Backend: Render

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Google Cloud account for Gemini API
- Vercel account
- Render account

## Environment Variables

### Backend (.env)
```
GOOGLE_API_KEY=your_gemini_api_key
```

### Frontend (.env.local)
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/kunalchhabraiitb2024/skincare-storefront.git
cd skincare-storefront
```

2. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

4. Start the development servers:

Backend:
```bash
cd backend
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm run dev
```

5. Visit `http://localhost:3000` to see the application

## Deployment

### Backend (Render)

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd backend && python wsgi.py`
4. Add environment variables:
   - `GOOGLE_API_KEY`

### Frontend (Vercel)

1. Push your code to GitHub
2. Import the project in Vercel
3. Add environment variables:
   - `NEXT_PUBLIC_BACKEND_URL`
4. Deploy

## Key Project Structure

```
skincare-storefront/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
|   |   └── process_docs.py
│   ├── data/
│   │   ├── chroma_db/
│   │   └── skincare catalog.xlsx
|   |   └── Additional info (brand, reviews, customer tickets).docx
│   ├── requirements.txt
│   └── wsgi.py
|   └── setup.py
└── frontend/
    ├── app/
    │   ├── components/
    |          ├── ProductCard.tsx
    |          ├── SearchBar.tsx
    │   ├── page.tsx
    │   └── layout.tsx
    ├── public/
    └── package.json
```

## API Endpoints

- `GET /` - API health check
- `GET /products` - Get all products
- `POST /search` - Search products with conversational interface

## Next Steps

1. Add user authentication
2. Implement shopping cart functionality
3. Add product reviews and ratings
4. Enhance AI recommendations with user feedback
5. Add product filtering and sorting
6. Implement order tracking

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
