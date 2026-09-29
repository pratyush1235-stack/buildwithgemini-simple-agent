"""Firestore tools for the agent to inspect and manage items in the inventory."""

import json
import os
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

load_dotenv()

# CRITICAL: Hardcode the GCP project ID string as required for Agent Platform compatibility.
FIRESTORE_PROJECT = "qwiklabs-gcp-01-c7b63de2e7a5"
PUBLIC_ASSET_BUCKET = "inventory-assets-qwiklabs-gcp-01-c7b63de2e7a5"
COLLECTION_NAME = "items"





def get_firestore_client() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT)


def list_items(category: str = "") -> list[dict]:
    """Lists items available in the inventory. Optionally filters by category (e.g. 'Electronics', 'Furniture', 'Pantry')."""
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    if category:
        query = collection_ref.where("category", "==", category)
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    items = []
    for doc in docs:
        item_data = doc.to_dict()
        item_data["id"] = doc.id
        items.append(item_data)

    return items


def get_item(name: str) -> dict:
    """Retrieves details of a specific item by name or item ID."""
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    # First try document ID directly
    doc_id = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
    doc_ref = collection_ref.document(doc_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Fallback to searching by name field case-insensitively
    docs = collection_ref.stream()
    for d in docs:
        data = d.to_dict()
        if data.get("name", "").lower() == name.lower():
            data["id"] = d.id
            return data

    return {"error": f"Item '{name}' not found in inventory."}


def add_item(
    name: str,
    category: str,
    quantity: int,
    price: float,
    description: str,
    status: str = "in_stock",
) -> str:
    """Adds a new item or updates an existing item in the inventory Firestore database.

    Args:
        name: Name of the item.
        category: Category of item (e.g. 'Electronics', 'Furniture', 'Pantry').
        quantity: Number of units available.
        price: Price per unit in USD.
        description: A brief description of the item.
        status: Availability status ('in_stock' or 'out_of_stock').
    """
    db = get_firestore_client()
    doc_id = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)

    item_data = {
        "name": name,
        "category": category,
        "quantity": quantity,
        "price": price,
        "description": description,
        "status": status,
    }

    doc_ref.set(item_data, merge=True)
    return f"Successfully saved item '{name}' (ID: {doc_id}) to Firestore inventory."


def check_reorder_alerts(threshold: int = 5) -> dict:
    """Scans the inventory in Firestore for items with quantity at or below the specified threshold.

    Args:
        threshold: The quantity threshold to trigger a reorder alert (default: 5).

    Returns:
        A dictionary containing the list of low stock items, total alert count, and estimated restock cost.
    """
    db = get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()

    low_stock_items = []
    total_restock_estimate = 0.0

    for doc in docs:
        data = doc.to_dict()
        qty = data.get("quantity", 0)
        if qty <= threshold:
            price = data.get("price", 0.0)
            reorder_qty = 10 - qty if qty < 10 else 5
            estimated_cost = round(reorder_qty * price, 2)
            total_restock_estimate += estimated_cost

            low_stock_items.append(
                {
                    "id": doc.id,
                    "name": data.get("name"),
                    "category": data.get("category"),
                    "current_quantity": qty,
                    "status": data.get("status"),
                    "suggested_reorder_quantity": reorder_qty,
                    "estimated_reorder_cost": estimated_cost,
                }
            )

    return {
        "threshold_used": threshold,
        "alert_count": len(low_stock_items),
        "total_restock_estimate_usd": round(total_restock_estimate, 2),
        "low_stock_items": low_stock_items,
    }


def search_external_market_prices(query: str) -> dict:
    """Searches external public market product data for real-world benchmark prices, ratings, and specifications.

    Args:
        query: The product name or search term to look up (e.g. 'headphones', 'keyboard', 'chair', 'phone').

    Returns:
        A dictionary containing real-world market products, average market price, and product listings.
    """
    api_key = os.getenv("PRODUCT_API_KEY", "")
    encoded_query = urllib.parse.quote(query)
    url = f"https://dummyjson.com/products/search?q={encoded_query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        products = data.get("products", [])
        results = []
        total_price = 0.0

        for item in products[:5]:
            p = float(item.get("price", 0.0))
            total_price += p
            results.append(
                {
                    "title": item.get("title"),
                    "brand": item.get("brand"),
                    "category": item.get("category"),
                    "price_usd": p,
                    "rating": item.get("rating"),
                    "stock": item.get("stock"),
                }
            )

        avg_price = round(total_price / len(results), 2) if results else 0.0

        return {
            "search_query": query,
            "results_found": len(products),
            "average_market_price_usd": avg_price,
            "market_products": results,
        }
    except Exception as e:
        return {"error": f"Failed to fetch market data for '{query}': {str(e)}"}


def get_maps_api_key() -> str:
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key or key == "PASTE_KEY_HERE":
        return ""
    return key


def geocode_address(address: str) -> dict:
    """Converts a physical address or place name into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The address or place name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco, CA').

    Returns:
        A dictionary containing formatted address, latitude, longitude, and place_id.
    """
    api_key = get_maps_api_key()
    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY is missing or set to PASTE_KEY_HERE in .env. Please replace PASTE_KEY_HERE in your local .env file with a valid Google Maps API Key."
        }

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]
            return {
                "address_query": address,
                "formatted_address": result.get("formatted_address"),
                "location": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                },
                "place_id": result.get("place_id"),
            }
        else:
            return {
                "error": f"Geocoding failed for address '{address}': {data.get('status', 'ZERO_RESULTS')}"
            }
    except Exception as e:
        return {"error": f"Failed to geocode address '{address}': {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
) -> dict:
    """Finds nearby points of interest of a given type near specified coordinates using Places API (New).

    Args:
        latitude: Latitude of center search location.
        longitude: Longitude of center search location.
        place_type: Type of place to search for (e.g. 'restaurant', 'cafe', 'store', 'park', 'gym').
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        A dictionary containing a list of nearby places with name, formatted address, location, and types.
    """
    api_key = get_maps_api_key()
    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY is missing or set to PASTE_KEY_HERE in .env. Please replace PASTE_KEY_HERE in your local .env file with a valid Google Maps API Key."
        }

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }

    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode())

        places_raw = res_data.get("places", [])
        results = []

        for p in places_raw:
            results.append(
                {
                    "name": p.get("displayName", {}).get("text", ""),
                    "address": p.get("formattedAddress", ""),
                    "location": p.get("location", {}),
                    "types": p.get("types", []),
                }
            )

        return {
            "search_center": {"latitude": latitude, "longitude": longitude},
            "place_type": place_type,
            "radius_meters": radius_meters,
            "results_found": len(results),
            "places": results,
        }
    except Exception as e:
        return {"error": f"Failed to search nearby places: {str(e)}"}


def generate_item_image(
    item_name: str, description: str, tool_context: ToolContext = None
) -> dict:
    """Generates a product image for an item using gemini-3.1-flash-lite-image in the global region. Saves the image as a session artifact and uploads bytes directly to public Cloud Storage.

    Args:
        item_name: The name of the item (e.g. 'Wireless Headphones', 'Ergonomic Desk Chair').
        description: A prompt description for generating the item's photo.
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary containing item_name, image_filename, public_image_url, and status.
    """
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"] = FIRESTORE_PROJECT
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

    client = genai.Client()
    prompt = f"Product photo of {item_name}: {description}. High resolution product photography, clean background."

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return {
                "error": f"Failed to generate image bytes for '{item_name}'. No image data returned."
            }

        safe_name = item_name.lower().replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_image.jpg"

        # 1. Save as artifact if tool_context is available
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(PUBLIC_ASSET_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_ASSET_BUCKET}/{filename}"

        return {
            "item_name": item_name,
            "image_filename": filename,
            "public_image_url": public_url,
            "status": f"Successfully generated image for '{item_name}', saved artifact, and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload image for '{item_name}': {str(e)}"}


def generate_item_video(
    item_name: str, description: str, tool_context: ToolContext = None
) -> dict:
    """Generates a short showcase video for an inventory item using gemini-omni-flash-preview in the global region. Saves the video as a session artifact and uploads video bytes directly to public Cloud Storage.

    Args:
        item_name: The name of the item (e.g. 'Organic Almond Milk', 'Wireless Headphones').
        description: A prompt description for generating the showcase video.
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary containing item_name, video_filename, public_video_url, and status.
    """
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"] = FIRESTORE_PROJECT
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

    client = genai.Client()
    prompt = f"Short product showcase video for {item_name}: {description}. Smooth motion, studio lighting, cinematic high quality product video."

    try:
        response = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["VIDEO"],
            ),
        )

        video_bytes = None
        mime_type = "video/mp4"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not video_bytes:
            return {
                "error": f"Failed to generate video bytes for '{item_name}'. No video data returned."
            }

        safe_name = item_name.lower().replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_video.mp4"

        # 1. Save as artifact if tool_context is available
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(PUBLIC_ASSET_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_ASSET_BUCKET}/{filename}"

        return {
            "item_name": item_name,
            "video_filename": filename,
            "public_video_url": public_url,
            "status": f"Successfully generated video for '{item_name}', saved artifact, and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload video for '{item_name}': {str(e)}"}





