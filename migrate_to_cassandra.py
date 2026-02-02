"""
Migration Script: MongoDB to Cassandra
This script copies existing data from MongoDB to Cassandra.
Run this AFTER cassandra_setup.py has been executed.
"""

from pymongo import MongoClient
from cassandra.cluster import Cluster
from datetime import datetime
import sys

def migrate_to_cassandra():
    """Migrate data from MongoDB to Cassandra"""
    
    print("=" * 60)
    print("MongoDB → Cassandra Migration Script")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        mongo_client = MongoClient('mongodb://localhost:27017/')
        mongo_db = mongo_client.blog_db
        mongo_posts = mongo_db.posts
        mongo_comments = mongo_db.comments
        
        print("\n✓ Connected to MongoDB")
        
        # Connect to Cassandra
        cassandra_cluster = Cluster(['127.0.0.1'])
        cassandra_session = cassandra_cluster.connect('blog_keyspace')
        
        print("✓ Connected to Cassandra")
        
        # Migrate Posts
        print("\n📄 Migrating posts...")
        posts = list(mongo_posts.find())
        
        if not posts:
            print("  ℹ No posts to migrate")
        else:
            for i, post in enumerate(posts, 1):
                try:
                    cassandra_session.execute(
                        """
                        INSERT INTO posts (post_id, title, content, author, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(post['_id']),
                            post.get('title', ''),
                            post.get('content', ''),
                            post.get('author', 'Unknown'),
                            post.get('created_at', datetime.utcnow()),
                            post.get('updated_at', datetime.utcnow())
                        )
                    )
                    print(f"  ✓ Post {i}/{len(posts)}: {post.get('title', 'Untitled')}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate post {i}: {e}")
        
        # Migrate Comments
        print("\n💬 Migrating comments...")
        comments = list(mongo_comments.find())
        
        if not comments:
            print("  ℹ No comments to migrate")
        else:
            for i, comment in enumerate(comments, 1):
                try:
                    cassandra_session.execute(
                        """
                        INSERT INTO comments (comment_id, post_id, commenter, comment, created_at)
                        VALUES (uuid(), %s, %s, %s, %s)
                        """,
                        (
                            str(comment.get('post_id', '')),
                            comment.get('commenter', 'Anonymous'),
                            comment.get('comment', ''),
                            comment.get('created_at', datetime.utcnow())
                        )
                    )
                    print(f"  ✓ Comment {i}/{len(comments)}: {comment.get('commenter', 'Anonymous')}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate comment {i}: {e}")
        
        # Verify migration
        print("\n📊 Verifying migration...")
        
        posts_count = cassandra_session.execute("SELECT COUNT(*) FROM posts").one()[0]
        comments_count = cassandra_session.execute("SELECT COUNT(*) FROM comments").one()[0]
        
        print(f"  • Posts in Cassandra: {posts_count}")
        print(f"  • Comments in Cassandra: {comments_count}")
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Test the application with Cassandra reads")
        print("  2. Run 'python cassandra_read_migration.py' to switch reads to Cassandra")
        print("  3. Run 'python cleanup_mongodb.py' to remove MongoDB data")
        
        # Cleanup
        mongo_client.close()
        cassandra_session.shutdown()
        cassandra_cluster.shutdown()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("  • Make sure MongoDB is running (mongod)")
        print("  • Make sure Cassandra is running (cassandra)")
        print("  • Run 'python cassandra_setup.py' first to initialize Cassandra")
        sys.exit(1)

if __name__ == "__main__":
    migrate_to_cassandra()
