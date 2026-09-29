"""Seed script to populate initial sample items into Firestore database."""

from google.cloud import firestore

# CRITICAL: Hardcode the GCP project ID string as required for Agent Platform compatibility.
FIRESTORE_PROJECT = "qwiklabs-gcp-01-c7b63de2e7a5"

COLLECTION_NAME = "items"

INITIAL_ITEMS = [
    {
        "name": "Wireless Noise-Canceling Headphones",
        "category": "Electronics",
        "quantity": 15,
        "price": 199.99,
        "description": "High-fidelity Bluetooth headphones with active noise cancellation.",
        "status": "in_stock",
    },
    {
        "name": "Ergonomic Mesh Office Chair",
        "category": "Furniture",
        "quantity": 8,
        "price": 249.50,
        "description": "Adjustable lumbar support chair designed for long desk hours.",
        "status": "in_stock",
    },
    {
        "name": "Organic Whole Bean Coffee (1kg)",
        "category": "Pantry",
        "quantity": 30,
        "price": 22.00,
        "description": "Medium roast fair-trade arabica coffee beans.",
        "status": "in_stock",
    },
    {
        "name": "Smart Fitness Tracker Watch",
        "category": "Electronics",
        "quantity": 0,
        "price": 120.00,
        "description": "Waterproof fitness tracker with heart rate monitor and sleep tracking.",
        "status": "out_of_stock",
    },
]


def seed():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT}...")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    collection_ref = db.collection(COLLECTION_NAME)

    print(f"Seeding items into '{COLLECTION_NAME}' collection...")
    for item in INITIAL_ITEMS:
        # Use lowercase hyphenated name as doc ID
        doc_id = item["name"].lower().replace(" ", "-").replace("(", "").replace(")", "")
        collection_ref.document(doc_id).set(item)
        print(f"  ✓ Seeded: {item['name']} (ID: {doc_id})")

    print("Seeding complete!")


if __name__ == "__main__":
    seed()
