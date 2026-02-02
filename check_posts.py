from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client.blog_db
posts = list(db.posts.find())

print(f'Total posts in database: {len(posts)}')
print()

for i, post in enumerate(posts, 1):
    print(f'Post {i}:')
    print(f'  Title: {post.get("title")}')
    print(f'  Author: {post.get("author")}')
    print(f'  Content: {post.get("content")[:100]}...' if len(post.get("content", "")) > 100 else f'  Content: {post.get("content")}')
    print()
