# 🛒 CartPilot AI
### Your Intelligent Shopping and Payment Agent

CartPilot AI is an AI-powered shopping assistant that helps users discover, compare, and purchase products through natural-language conversations. It combines Google Gemini AI with a product recommendation engine, smart cart management, and secure PayPal Sandbox checkout.

The goal is to make online shopping simpler, smarter, and more personalized by transforming natural-language shopping requests into actionable product recommendations.

---

## ✨ Key Features

### 🤖 AI-Powered Shopping Assistant
- Understands shopping requests written in natural language.
- Uses Google Gemini AI to extract product categories, budgets, and preferences.
- Converts user requirements into structured shopping intents.
- Provides personalized product recommendations.
- Explains why products match the user's requirements.
- Supports follow-up conversations and product comparisons.

### 🔍 Smart Product Discovery
- Searches products from a database.
- Filters products based on user requirements.
- Ranks suitable products according to preferences.
- Displays product information and availability.
- Uses actual database information for recommendations.

### 🛒 Intelligent Cart Management
- Add recommended products to the shopping cart.
- Manage product quantities.
- Calculate subtotal and total.
- Validate product prices and stock on the backend.

### 💳 PayPal Sandbox Integration
- Creates PayPal Sandbox orders through the backend.
- Redirects users to PayPal for payment approval.
- Captures approved payments through the backend.
- Verifies payment status before displaying success.
- Uses Sandbox transactions for demonstration and testing.

**Note:** PayPal Sandbox is used for testing. The project does not process real payments.

### 🔐 Security and Reliability
- Keeps API credentials on the backend.
- Validates product prices and availability using server-side data.
- Requires user approval before payment.
- Verifies payment capture before confirming an order.
- Separates AI recommendations from payment execution.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js, Vite, JavaScript |
| UI | CSS, Lucide React |
| API Communication | Axios |
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data Validation | Pydantic |
| AI Integration | Google Gemini API |
| Payment Gateway | PayPal REST API (Sandbox) |
| Version Control | Git and GitHub |

---

## 🏗️ System Architecture

```text
                 USER
                   |
                   v
          React Frontend (Vite)
                   |
                   v
          FastAPI Backend
                   |
          +--------+--------+
          |                 |
          v                 v
      Gemini AI         SQLite Database
          |                 |
          v                 v
   Intent Extraction   Product Search
          |                 |
          +--------+--------+
                   |
                   v
        Product Recommendations
                   |
                   v
              Shopping Cart
                   |
                   v
        Backend Price Validation
                   |
                   v
          PayPal Sandbox API
                   |
                   v
         User Payment Approval
                   |
                   v
         Backend Payment Capture
                   |
                   v
        Payment Verification
                   |
                   v
          Order Confirmation
```

---

## 📁 Project Structure

```text
CartPilotAI/
│
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── cart.py
│   │   │   ├── chat.py
│   │   │   └── products.py
│   │   │
│   │   ├── services/
│   │   │   ├── cart_service.py
│   │   │   ├── chat_service.py
│   │   │   └── gemini_client.py
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py
│   │   │
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── .env
│   ├── requirements.txt
│   └── test_paypal_connection.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── index.html
│
├── .gitignore
└── README.md
```

*The structure above shows the main project files; additional files and components may be present.*

---

## ⚙️ Installation and Setup

### 1. Prerequisites

Install the following before running the project:

- Python 3.10 or later
- Node.js and npm
- Git
- VS Code (recommended)
- Google Gemini API key
- PayPal Developer Sandbox account

### 2. Clone the Repository

```bash
git clone https://github.com/ingawalemadhura5722-glitch/CartPilotAI.git
cd CartPilotAI
```

### 3. Backend Setup

Navigate to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file inside the `backend` folder.

Add the following configuration:

```env
GEMINI_API_KEY=your_gemini_api_key

PAYPAL_CLIENT_ID=your_paypal_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_paypal_sandbox_secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
```

Add any additional configuration variables required by your implementation.

**Important:** Replace the placeholder values with your own credentials. Never upload `.env` or expose API secrets on GitHub.

### 5. Run the Backend

From the backend directory, run:

```bash
python -m uvicorn app.main:app --reload
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 6. Frontend Setup

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in the terminal (usually `http://localhost:5173`).

---

## 🧠 How CartPilot AI Works

1. **User Input:** The user describes what they want to purchase in natural language.
2. **AI Understanding:** Gemini AI extracts the category, budget, and shopping preferences.
3. **Intent Validation:** The backend validates the structured shopping intent.
4. **Product Search:** The application searches the product database.
5. **Product Ranking:** Matching products are filtered and ranked.
6. **AI Explanation:** The assistant explains product recommendations and comparisons using available product information.
7. **Cart Management:** The user adds selected products to the shopping cart.
8. **Price Validation:** The backend independently verifies product prices, quantities, and stock.
9. **Payment Creation:** The backend creates a PayPal Sandbox order.
10. **User Approval:** The user reviews and approves the payment through PayPal.
11. **Payment Capture:** The backend captures and verifies the approved payment.
12. **Confirmation:** The application confirms the payment only after successful backend verification.

---

## 💱 Currency Handling

The product catalog maintains prices in INR (₹).

For the PayPal Sandbox demonstration, the application uses a configurable INR-to-USD demo conversion rate where required by the payment flow.

This conversion is for demonstration purposes and should not be interpreted as a live foreign exchange rate.

---

## 🧪 Testing

The following areas should be tested before demonstration:

- Natural-language shopping requests.
- AI intent extraction and validation.
- Product search and recommendations.
- Product comparison and explanations.
- Adding and updating cart items.
- Backend price and stock validation.
- PayPal Sandbox order creation.
- Buyer approval and payment capture.
- Successful, failed, and cancelled payment handling.
- Protection of API credentials.

---

## 🔒 Security Considerations

- Gemini and PayPal credentials must remain on the backend.
- The frontend must not determine the authoritative payment amount.
- Product prices and stock must be validated using server-side data.
- AI-generated responses must not be treated as authoritative product or payment records.
- Payment success must depend on verified backend capture results.
- Users must explicitly approve payments.
- Sandbox credentials must never be replaced with real credentials in a public demo repository.

---

## 🚀 Future Enhancements

- Integration with real product catalog APIs.
- Real-time inventory synchronization.
- Advanced recommendation algorithms.
- Personalized shopping profiles.
- Multiple payment gateway support.
- Order history and tracking dashboard.
- Voice-based shopping assistant.
- Deployment to a cloud platform.
- Advanced fraud detection and transaction monitoring.

---

## 🎯 Project Objective

CartPilot AI aims to bridge the gap between traditional e-commerce platforms and intelligent conversational shopping.

Instead of manually searching through hundreds of products, users can simply describe their requirements and receive relevant recommendations, comparisons, and a guided checkout experience.

**From shopping intent to intelligent recommendations to payment — all in one place.**

---

## 👩‍💻 Developer

**Madhura Ingawale**

- GitHub: [@ingawalemadhura5722-glitch](https://github.com/ingawalemadhura5722-glitch)
- Project Repository: [CartPilot AI](https://github.com/ingawalemadhura5722-glitch/CartPilotAI)

---

## 📄 License

This project is developed as a hackathon project and educational demonstration. Add a specific open-source license if you intend to permit reuse, modification, or distribution.