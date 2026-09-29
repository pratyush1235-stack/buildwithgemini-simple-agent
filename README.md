# NovaSmart Inventory Assistant

An intelligent, safety-conscious AI inventory management assistant built with the Google Agent Development Kit (ADK), Vertex AI Memory Bank, Firestore, and multimodal Gemini capabilities.

![NovaSmart Inventory Assistant Demo](demo.gif)

---

## 🌟 What NovaSmart Inventory Assistant Does

NovaSmart Inventory Assistant is an enterprise-grade agent designed to streamline warehouse and pantry operations. It combines real-time database management, automated reorder threshold monitoring, market price benchmarking, vendor location search, and AI-driven product media generation.

### Key Capabilities & Implemented Features

- 🧠 **Cross-Session Long-Term Memory (Vertex AI Memory Bank)**
  - Automatically remembers user facts, preferences, and food/chemical allergies across chat sessions via `VertexAiMemoryBankService` and `PreloadMemoryTool`.
  - Ensures ingredient checks and item recommendations strictly prioritize user dietary restrictions and safety.

- 📦 **Real-Time Inventory Database (Google Cloud Firestore)**
  - Performs direct CRUD and query operations on the `items` collection in Firestore.
  - Features built-in low stock alert scanning (`check_reorder_alerts`) to flag items below threshold quantities and calculate restock costs.

- 🎨 **Multimodal Media Generation & Cloud Storage (Vertex AI & GCS)**
  - **Product Photography**: Generates high-resolution product photos using `gemini-3.1-flash-lite-image` in the `global` region (`generate_item_image`).
  - **Showcase Video**: Generates cinematic product showcase videos using Google's Omni model `gemini-omni-flash-preview` in the `global` region (`generate_item_video`).
  - **Artifact & Storage Pipeline**: Saves generated media directly as ADK session artifacts and publishes bytes to a public Google Cloud Storage bucket (`inventory-assets-qwiklabs-gcp-01-c7b63de2e7a5`).

- 🏷️ **External Market Price Benchmarking**
  - Fetches real-world benchmark prices, product ratings, and specifications via market APIs (`search_external_market_prices`).

- 📍 **Vendor Location & Geocoding (Google Maps & Places APIs)**
  - Converts physical addresses or cities into geographic coordinates via Google Geocoding API (`geocode_address`).
  - Locates nearby grocery stores, suppliers, and vendors using Google Places API (New) (`find_nearby_places`).

- 🖥️ **Rich UI Rendering (A2UI v0.8 & Basic Catalog)**
  - Emits A2UI structured components (Card, Row, Column, Text, Image, Icon) for clean inline display in chat interfaces.

---

## 🛠️ Architecture & Google Cloud Services

| Service / Feature | Role in Application |
| :--- | :--- |
| **Agent Development Kit (ADK)** | Core agent orchestration, model client, tool dispatch, and callbacks. |
| **Vertex AI Memory Bank** | Long-term memory store for session persistence and allergy safety constraints. |
| **Google Cloud Firestore** | NoSQL database hosting the `items` inventory collection. |
| **Google Cloud Storage (GCS)** | Public asset bucket for hosting generated product images and videos. |
| **Vertex AI Imagen & Omni Models** | Multimodal generation (`gemini-3.1-flash-lite-image` and `gemini-omni-flash-preview`). |
| **Google Maps & Places APIs** | Geocoding addresses and discovering nearby vendor locations. |
| **FastAPI Proxy (A2A Protocol)** | Backend proxy translating browser requests to Agent Engine over Agent-to-Agent (A2A) protocol. |

---

## 🚀 Local Development & Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for Playwright demo recorder)
- Google Cloud SDK (`gcloud`) authenticated to your GCP Project

### 2. Environment Configuration
Create a `.env` file in the project root:

```bash
GOOGLE_CLOUD_PROJECT="qwiklabs-gcp-01-c7b63de2e7a5"
GOOGLE_CLOUD_LOCATION="us-east1"
GOOGLE_MAPS_API_KEY="your_maps_key"
```

### 3. Running the Agent Backend & Proxy

To start the agent and local FastAPI chat server:

```bash
# 1. Install Python dependencies
uv pip install -r requirements.txt

# 2. Run the frontend proxy server locally
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/606763693613/locations/us-east1/reasoningEngines/132660475937685504"
export AGENT_DIRECTORY="app"
python main.py
```

The chat interface will be available locally on port `8080`.

---

## 🎥 Recording Demo Videos

To record a Playwright screen capture demo of the agent interface:

```bash
# Install Playwright dependencies locally if needed
npm install playwright && npx playwright install chromium

# Run the demo recorder
NODE_PATH=./node_modules node .agents/skills/record-demo/record-agent.js \
  -q "List low stock inventory items" \
  -q "Generate a product image for organic almond milk and check its reorder status" \
  --wait 30000 \
  --speed 1.5 \
  -o agent_demo.webm
```
