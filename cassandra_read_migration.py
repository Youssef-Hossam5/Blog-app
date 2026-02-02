"""
Cassandra Read Migration Script
This script modifies the application to read from Cassandra instead of MongoDB.
Update app.py to use this configuration for read-only Cassandra usage.
"""

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement

def setup_cassandra_read_session():
    """
    Create a Cassandra session configured for read operations.
    
    Usage in app.py:
    ----------------
    from cassandra_read_migration import setup_cassandra_read_session
    
    # Replace the Cassandra connection with:
    cassandra_session = setup_cassandra_read_session()
    
    # Replace MongoDB reads with Cassandra reads:
    # OLD: posts = list(posts_collection.find())
    # NEW: rows = cassandra_session.execute("SELECT * FROM posts")
    #      posts = [dict(row) for row in rows]
    """
    
    try:
        cluster = Cluster(['127.0.0.1'])
        session = cluster.connect('blog_keyspace')
        print("✓ Cassandra read session established")
        return session
    except Exception as e:
        print(f"❌ Failed to connect to Cassandra: {e}")
        return None

def get_all_posts(cassandra_session):
    """Fetch all posts from Cassandra"""
    try:
        rows = cassandra_session.execute("SELECT * FROM posts ORDER BY created_at DESC")
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []

def get_post_by_id(cassandra_session, post_id):
    """Fetch a single post by ID"""
    try:
        row = cassandra_session.execute(
            "SELECT * FROM posts WHERE post_id = %s",
            (post_id,)
        ).one()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching post: {e}")
        return None

def get_comments_by_post(cassandra_session, post_id):
    """Fetch all comments for a post"""
    try:
        rows = cassandra_session.execute(
            "SELECT * FROM comments WHERE post_id = %s ORDER BY created_at DESC",
            (post_id,)
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return []

def get_posts_by_author(cassandra_session, author):
    """Fetch all posts by a specific author"""
    try:
        rows = cassandra_session.execute(
            "SELECT * FROM posts WHERE author = %s",
            (author,)
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching posts by author: {e}")
        return []

def count_posts_per_author(cassandra_session):
    """Get count of posts per author"""
    try:
        rows = cassandra_session.execute("SELECT * FROM posts")
        author_counts = {}
        for row in rows:
            author = row.author
            author_counts[author] = author_counts.get(author, 0) + 1
        return author_counts
    except Exception as e:
        print(f"Error counting posts: {e}")
        return {}

def migration_checklist():
    """
    Checklist for migrating from MongoDB reads to Cassandra reads
    """
    print("""
    ═══════════════════════════════════════════════════════════════
    Cassandra Read Migration Checklist
    ═══════════════════════════════════════════════════════════════
    
    1. ☐ Run cassandra_setup.py (create keyspace and tables)
    2. ☐ Run migrate_to_cassandra.py (copy MongoDB data to Cassandra)
    3. ☐ Update app.py routes to use Cassandra for reads:
       
       from cassandra_read_migration import *
       
       # In the home() route:
       posts = get_all_posts(cassandra_session)
       author_counts = count_posts_per_author(cassandra_session)
       
       # In the post_detail() route:
       post = get_post_by_id(cassandra_session, post_id)
       comments = get_comments_by_post(cassandra_session, post_id)
    
    4. ☐ Test all read operations work correctly with Cassandra
    5. ☐ Monitor both MongoDB and Cassandra for consistency
    6. ☐ Run cleanup_mongodb.py to remove MongoDB-only data
    
    ═══════════════════════════════════════════════════════════════
    """)

if __name__ == "__main__":
    migration_checklist()
