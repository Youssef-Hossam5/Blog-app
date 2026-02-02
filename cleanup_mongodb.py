"""
Cleanup Script: Remove MongoDB and migrate completely to Cassandra
This script removes all MongoDB-related dependencies and code.
Execute only after thoroughly testing Cassandra reads.
"""

from pymongo import MongoClient
import sys

def cleanup_mongodb():
    """
    Drop MongoDB collections (careful - this is destructive!)
    """
    
    print("=" * 70)
    print("WARNING: This will DELETE all data from MongoDB!")
    print("=" * 70)
    print("\nBefore proceeding:")
    print("  ✓ Ensure all data is migrated to Cassandra")
    print("  ✓ Ensure all reads are coming from Cassandra")
    print("  ✓ Have a backup of your MongoDB data")
    print("\n" + "=" * 70)
    
    confirm = input("\nType 'yes' to proceed with MongoDB cleanup: ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Cleanup cancelled")
        return
    
    try:
        mongo_client = MongoClient('mongodb://localhost:27017/')
        mongo_db = mongo_client.blog_db
        
        print("\n📊 Current MongoDB collections:")
        collections = mongo_db.list_collection_names()
        for coll in collections:
            count = mongo_db[coll].count_documents({})
            print(f"  • {coll}: {count} documents")
        
        print("\n🗑️  Dropping collections...")
        mongo_db.posts.drop()
        print("  ✓ Dropped 'posts' collection")
        
        mongo_db.comments.drop()
        print("  ✓ Dropped 'comments' collection")
        
        print("\n✅ MongoDB cleanup completed!")
        print("\n📝 Next steps:")
        print("  1. Update app.py to remove MongoDB imports and client code")
        print("  2. Keep only Cassandra imports and session management")
        print("  3. Remove this script and migrate_to_cassandra.py after verification")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)

def app_py_cleanup_instructions():
    """
    Instructions for cleaning up app.py
    """
    
    print("""
    ═══════════════════════════════════════════════════════════════
    Instructions for app.py Cleanup
    ═══════════════════════════════════════════════════════════════
    
    REMOVE these imports:
    ────────────────────
        from pymongo import MongoClient
        from bson.objectid import ObjectId
    
    REMOVE these lines:
    ──────────────────
        # MongoDB Connection
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client.blog_db
        posts_collection = mongo_db.posts
        comments_collection = mongo_db.comments
    
    ADD these imports:
    ──────────────────
        from cassandra_read_migration import (
            get_all_posts,
            get_post_by_id,
            get_comments_by_post,
            count_posts_per_author
        )
        import uuid
    
    UPDATE the home() route:
    ────────────────────────
        posts = get_all_posts(cassandra_session)
        author_counts = count_posts_per_author(cassandra_session)
    
    UPDATE the post_detail() route:
    ───────────────────────────────
        post = get_post_by_id(cassandra_session, post_id)
        comments = get_comments_by_post(cassandra_session, post_id)
    
    UPDATE CREATE routes to use only Cassandra double-writes
    UPDATE DELETE routes to use only Cassandra
    
    ═══════════════════════════════════════════════════════════════
    """)

if __name__ == "__main__":
    cleanup_mongodb()
    app_py_cleanup_instructions()
