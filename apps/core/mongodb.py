"""
MongoDB connection helper for Django Local Worker Project
Designed for MongoDB Atlas Free Tier (M0 - 512MB) Optimization:
- Lightweight JSON documents only (NO binary/base64 storage)
- Automatic TTL (Time-To-Live) indexes on logs to prevent storage overflow
- Fast indexed queries
- Rich helpers for Worker Portfolios and In-App Chat Messaging
"""
import logging
import uuid
from datetime import datetime, timezone
from django.conf import settings

logger = logging.getLogger(__name__)

_mongo_client = None


def get_mongo_client():
    """
    Returns a singleton MongoClient instance configured with project settings.
    Automatically handles TLS/SSL certificates using certifi.
    """
    global _mongo_client
    if _mongo_client is not None:
        return _mongo_client

    import pymongo
    import certifi

    mongo_uri = getattr(settings, 'MONGO_URI', '')
    if not mongo_uri:
        raise ValueError("MONGO_URI is not configured in Django settings or .env")

    try:
        _mongo_client = pymongo.MongoClient(
            mongo_uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        return _mongo_client
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB client: {e}")
        raise


def get_mongo_db(db_name=None):
    """
    Returns the MongoDB Database object.
    If db_name is not provided, defaults to settings.MONGO_DB_NAME.
    """
    client = get_mongo_client()
    target_db = db_name or getattr(settings, 'MONGO_DB_NAME', 'local_worker_db')
    return client[target_db]


def get_mongo_collection(collection_name, db_name=None):
    """
    Returns a specific collection from MongoDB.
    """
    db = get_mongo_db(db_name=db_name)
    return db[collection_name]


def ping_mongodb():
    """
    Tests the connection to the MongoDB cluster.
    Returns a tuple: (is_connected: bool, info_or_error: str)
    """
    try:
        client = get_mongo_client()
        result = client.admin.command('ping')
        return True, f"Connected successfully! Server response: {result}"
    except Exception as e:
        return False, str(e)


def init_mongodb_indexes():
    """
    Initializes indexes and automatic TTL (Time-to-Live) to keep storage usage
    extremely low and completely free forever within Atlas Free Tier (512MB).
    """
    import pymongo
    db = get_mongo_db()

    try:
        # 1. Search logs: Auto-expire after 30 days (2,592,000 seconds)
        db.search_logs.create_index([("created_at_dt", pymongo.ASCENDING)], expireAfterSeconds=2592000)
        db.search_logs.create_index([("keyword", pymongo.TEXT), ("province", pymongo.ASCENDING)])

        # 2. Activity audit logs: Auto-expire after 60 days (5,184,000 seconds)
        db.activity_audit_logs.create_index([("timestamp_dt", pymongo.ASCENDING)], expireAfterSeconds=5184000)
        db.activity_audit_logs.create_index([("booking_id", pymongo.ASCENDING)])

        # 3. Worker portfolios: Fast search index
        db.worker_portfolios.create_index([("worker_id", pymongo.ASCENDING)], unique=True)

        # 4. Reviews & Feedback: Fast lookup
        db.reviews_and_feedback.create_index([("worker_id", pymongo.ASCENDING), ("rating", pymongo.DESCENDING)])

        # 5. Chat Messages: Fast room lookup and TTL (expire chat older than 90 days)
        db.chat_messages.create_index([("booking_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)])
        db.chat_messages.create_index([("timestamp_dt", pymongo.ASCENDING)], expireAfterSeconds=7776000)

        return True, "Indexes and TTL auto-cleanup configured successfully."
    except Exception as e:
        logger.error(f"Error initializing MongoDB indexes: {e}")
        return False, str(e)


# ==========================================
# Worker Portfolio Gallery Helpers (MongoDB)
# ==========================================
def get_worker_portfolio(worker_id):
    """
    Retrieve full portfolio showcase list for a specific worker.
    """
    try:
        db = get_mongo_db()
        doc = db.worker_portfolios.find_one({"worker_id": int(worker_id)})
        if doc and 'gallery' in doc:
            return doc['gallery']
        return []
    except Exception as e:
        logger.error(f"Error fetching portfolio from MongoDB: {e}")
        return []


def add_worker_portfolio_item(worker_id, title, description, category_name=None, before_image=None, after_image=None):
    """
    Add a new showcase item (Before/After images & description) to a worker's portfolio document in MongoDB.
    """
    try:
        db = get_mongo_db()
        item = {
            "item_id": str(uuid.uuid4())[:8],
            "title": title.strip(),
            "description": description.strip() if description else "",
            "category_name": category_name or "งานทั่วไป",
            "before_image": before_image,
            "after_image": after_image,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
        }

        db.worker_portfolios.update_one(
            {"worker_id": int(worker_id)},
            {
                "$push": {"gallery": item},
                "$set": {"updated_at": datetime.now().strftime('%Y-%m-%d %H:%M')}
            },
            upsert=True
        )
        return True, item
    except Exception as e:
        logger.error(f"Error adding portfolio item to MongoDB: {e}")
        return False, str(e)


def delete_worker_portfolio_item(worker_id, item_id):
    """
    Remove a specific portfolio item from worker's MongoDB gallery.
    """
    try:
        db = get_mongo_db()
        db.worker_portfolios.update_one(
            {"worker_id": int(worker_id)},
            {"$pull": {"gallery": {"item_id": item_id}}}
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting portfolio item from MongoDB: {e}")
        return False


# ==========================================
# In-App Chat Messaging Helpers (MongoDB)
# ==========================================
def send_chat_message(booking_id, sender_user, message_text, image_url=None):
    """
    Save a real-time chat message into MongoDB collection `chat_messages`.
    """
    try:
        db = get_mongo_db()
        now_dt = datetime.now(timezone.utc)
        doc = {
            "booking_id": int(booking_id),
            "sender_id": sender_user.id,
            "sender_name": sender_user.full_name,
            "sender_role": sender_user.role,
            "message": message_text.strip() if message_text else "",
            "image_url": image_url,
            "timestamp": now_dt.strftime('%H:%M'),
            "date": now_dt.strftime('%d/%m/%Y'),
            "timestamp_dt": now_dt,
            "is_read": False,
        }
        res = db.chat_messages.insert_one(doc)
        doc['_id'] = str(res.inserted_id)
        return True, doc
    except Exception as e:
        logger.error(f"Error saving chat message to MongoDB: {e}")
        return False, str(e)


def get_chat_messages(booking_id):
    """
    Retrieve all messages for a specific booking request from MongoDB.
    """
    try:
        db = get_mongo_db()
        cursor = db.chat_messages.find({"booking_id": int(booking_id)}).sort("timestamp_dt", 1)
        messages = []
        for msg in cursor:
            msg['id'] = str(msg['_id'])
            del msg['_id']
            messages.append(msg)
        return messages
    except Exception as e:
        logger.error(f"Error retrieving chat messages from MongoDB: {e}")
        return []


def mark_chat_messages_as_read(booking_id, current_user_id):
    """
    Mark messages sent to current_user as read.
    """
    try:
        db = get_mongo_db()
        db.chat_messages.update_many(
            {"booking_id": int(booking_id), "sender_id": {"$ne": int(current_user_id)}},
            {"$set": {"is_read": True}}
        )
    except Exception as e:
        logger.error(f"Error marking chat read: {e}")


def get_storage_stats():
    """
    Returns database storage size statistics.
    """
    try:
        db = get_mongo_db()
        stats = db.command("dbstats")
        data_size_kb = round(stats.get('dataSize', 0) / 1024, 2)
        storage_size_kb = round(stats.get('storageSize', 0) / 1024, 2)
        collections_count = stats.get('collections', 0)
        objects_count = stats.get('objects', 0)
        return {
            'data_size_kb': data_size_kb,
            'storage_size_kb': storage_size_kb,
            'collections_count': collections_count,
            'objects_count': objects_count,
            'free_limit_mb': 512,
        }
    except Exception as e:
        return {'error': str(e)}


def close_mongo_client():
    """
    Closes the current MongoDB client connection if open.
    """
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
