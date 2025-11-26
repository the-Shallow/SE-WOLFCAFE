<!-- # 🍴 Food Delivery System   -->
<!-- **AI-powered meal recommendation and delivery platform using FastAPI, LangGraph, and MongoDB.** -->

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-brightgreen?logo=fastapi)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-green?logo=mongodb)
![React](https://img.shields.io/badge/Frontend-React-blue?logo=react)
[![Coverage](https://img.shields.io/codecov/c/github/the-Shallow/SE-WOLFCAFE?label=Coverage&logo=78%)](https://se-wolfcafe.onrender.com/index.html)
[![License](https://img.shields.io/badge/License-MIT-yellow?logo=opensource-initiative)](LICENSE)
[![Contributions welcome](https://img.shields.io/badge/Contributions-welcome-brightgreen.svg)](docs/CONTRIBUTING.md)
[![Rubric](https://img.shields.io/badge/rubric-brightgreen.svg)](docs/SELF_ASSESSMENT.md)
[![Project Poster](https://img.shields.io/badge/poster-brightgreen.svg)](docs/POSTER.pdf)
[![Chat System Flowchart](https://img.shields.io/badge/chatsystem-brightgreen.svg)](docs/CHAT_SYSTEM_FLOWCHART.pdf)
---

## 🏗️ Overview  
**SafeBites** is a full-stack application that leverages **AI-driven natural language understanding** to simplify how users find, customize, and order food.  
It integrates **LangGraph + FAISS** for semantic search, enabling users to query menus conversationally (e.g., “Find vegan dishes under $10”).  

This system is designed for **scalability, modularity, and sustainability**, aligning with the *Software Engineering Project 2* guidelines.

---

## 🚀 Features
- 🍽️ **Restaurant & Menu Search** – Semantic retrieval using LangGraph + FAISS  
- 🤖 **AI Query Understanding** – Extracts intents and filters structured data  
- 🧠 **Allergen Detection** – Considers user preferences and allergens  
- 💾 **MongoDB Integration** – Persistent storage for restaurants, dishes, and users  
- ⚡ **FastAPI Backend** – Modular REST API with async support  
- 🎨 **React Frontend** – Responsive UI styled with TailwindCSS  

---

## 🧠 Architecture Overview
```plaintext
food-delivery-system/
├── frontend/          # React + Tailwind app
├── backend/           # FastAPI + LangGraph + MongoDB + FAISS
├── docs/              # Documentation, self-assessment, poster
└── README.md
🧩 Backend orchestrates LLM-based reasoning, semantic retrieval, and structured filtering.
🖥️ Frontend provides intuitive interactions for browsing and ordering.
```

## 👥 Intended Users

**SafeBites** is designed for:

- **End-users / Customers:** People who want to find, customize, and order food easily using AI-driven search.
- **Restaurant Owners:** Who want to manage menus, dishes, and customer preferences efficiently.
- **Developers / Researchers:** Interested in exploring AI-based semantic search, LangGraph integrations, and scalable food delivery systems.

## 📖 Example Use Cases

1. **Finding Vegan Dishes under $10:**  
   A user searches, "Find vegan dishes under $10," and the system returns relevant dishes using semantic search via FAISS and LangGraph.

2. **Custom Allergen Filtering:**  
   Users can input allergens, and the system will exclude dishes containing those ingredients, ensuring safe meal selection.

3. **Restaurant Menu Exploration:**  
   Users can browse menus by category, price, or cuisine type and see recommendations tailored to their preferences.

4. **Developer Exploration:**  
   Developers can test AI query understanding, embeddings, and modular FastAPI endpoints for building similar projects.


## 🧰 Tech Stack  

| **Layer** | **Technology** | **Description** |
|------------|----------------|-----------------|
| Frontend | React, TailwindCSS, Vite | Responsive user interface |
| Backend | FastAPI, LangGraph, LangChain | Modular async API services |
| Database | MongoDB | Stores users, dishes, and restaurant metadata |
| Vector Search | FAISS | Efficient semantic similarity search |
| AI Model | OpenAI / Local | Natural language understanding |
| Deployment | Local & Cloud | Consistent runtime environments |


## ⚙️ Local Setup  

### 🛠️ Prerequisites  

| **Tool** | **Required Version** | **Purpose** |
|-----------|----------------------|--------------|
| Python | 3.10+ | Backend runtime |
| pip / uv | latest | Dependency manager |
| Node.js | ≥ 18 | Frontend runtime |
| MongoDB | latest | Database |
| Git | — | Version control |

## 🧩 Backend Setup  
```
cd backend
python -m venv venv
# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 🔧 Install Dependencies  
```
pip install -r requirements.txt
```

### Create a .env file:
```
MONGO_URI=your_mongodb_uri
OPENAI_API_KEY=your_openai_key
JWT_SECRET=your_secret_key
```

### Run the API server:
```
uvicorn app.main:app --reload
Backend available at http://localhost:8000
```

## 🎨 Frontend Setup
```
cd frontend
npm install
```

### Configure Environment Variables
The frontend uses environment variables to configure the backend API URL. Create a `.env.local` file:
```
cp .env.example .env.local
```

For local development, the default configuration in `.env.development` points to `http://localhost:8000`.
For production builds, `.env.production` points to the production backend URL.

You can override these by creating `.env.local` with:
```
VITE_API_BASE_URL=http://localhost:8000
```

### Run Development Server
```
npm run dev
Frontend runs on http://localhost:5173
```

## 🧪 Testing
To run backend tests:
```
pytest
To view coverage:

pytest --cov=app
```
To run frontend tests:
```
Runs all tests:
npm run test

Runs SPECIFIC test file:
npm run test [filename].test

Runs tests in WATCH mode (re-runs on file changes):
npm run test -- --watch

Runs tests with COVERAGE:
npm run test -- --coverage
```

## 🤝 Contributing  

We welcome new contributors!  

To contribute:  
```
git checkout -b feature/your-feature
# Make your changes
git push origin feature/your-feature
Then open a Pull Request to the main branch.

📘 See the full CONTRIBUTING.md for setup, style guide, and testing conventions.
```

## 📜 License
This project is licensed under the MIT License.
See LICENSE for details.

## 🗂️ Additional Documents

| Document | Purpose |
|-----------|----------|
| **CONTRIBUTING.md** | Development and PR guidelines |
| **CODE_OF_CONDUCT.md** | Behavioral standards |
| **docs/SELF_ASSESSMENT.md** | Rubric evidence (Q1–Q16) |
| **docs/API_DOCS.md** | API endpoints and schema documentation |
| **docs/POSTER.pdf** | Visual project summary and future roadmap |

## 🧾 Rubric Reference:
Detailed mapping of rubric criteria to repository artifacts can be found in
docs/SELF_ASSESSMENT.md.

## 🚀 Future Roadmap (for Project 3)

| Feature | Description | Status |
|---------|------------|--------|
| 🧠 Personalized Dish Recommender | ML-based recommendations using user profile embeddings | Planned |
| 💬 Chat-based Ordering | Conversational ordering assistant using LLMs | Planned |
| 📦 Delivery Tracking | Real-time order tracking dashboard | Planned |
| 🧾 Admin Analytics Dashboard | Restaurant and order analytics visualization | Planned |


## 🧑‍💻 Contributors

| Name | Role | Contributions |
|------|------|---------------|
| Khush Patel & Richa Jha | Backend Developer | FastAPI, LangGraph, FAISS Integration |
| Mia Glen & Ishwarya | Frontend Developer | React + Tailwind UI |


## 💬 Contact

For inquiries or collaboration, reach out via GitHub **Issues** or **Discussions**:  

🔗 [Project Discussions](https://github.com/the-Shallow/SE-WOLFCAFE/discussions)


## ⭐ Support  

If you find this project useful, please give it a **star** on GitHub!  

Your support helps future teams continue development and improvement.
---
