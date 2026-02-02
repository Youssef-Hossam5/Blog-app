"""
Cassandra Keyspace and Table Setup Script
This script initializes the Cassandra database for the blog application.
"""

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

def setup_cassandra():
    """Initialize Cassandra keyspace and tables"""
    
    try:
        # Connect to Cassandra (adjust IP if needed)
        cluster = Cluster(['127.0.0.1'])
        session = cluster.connect()
        
        print("✓ Connected to Cassandra")
        
        # Create keyspace if it doesn't exist
        session.execute("""
            CREATE KEYSPACE IF NOT EXISTS blog_keyspace
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
        """)
        print("✓ Created/verified blog_keyspace")
        
        # Connect to the keyspace
        session.shutdown()
        session = cluster.connect('blog_keyspace')
        
        # Create posts table
        session.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                post_id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                author TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        print("✓ Created/verified posts table")
        
        # Create comments table
        session.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id UUID PRIMARY KEY,
                post_id TEXT,
                commenter TEXT,
                comment TEXT,
                created_at TIMESTAMP
            )
        """)
        print("✓ Created/verified comments table")
        
        # Create index for comments by post_id for efficient querying
        session.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_post_id
            ON comments (post_id)
        """)
        print("✓ Created/verified comments index by post_id")
        
        # Create index for posts by author
        session.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_author
            ON posts (author)
        """)
        print("✓ Created/verified posts index by author")
        
        print("\n✅ Cassandra setup completed successfully!")
        
        session.shutdown()
        cluster.shutdown()
        
    except Exception as e:
        print(f"❌ Error setting up Cassandra: {e}")
        print("\nMake sure Cassandra is running:")
        print("  Windows: cassandra.bat or cassandra -f")
        print("  Linux/Mac: cassandra")
        raise

if __name__ == "__main__":
    setup_cassandra()
