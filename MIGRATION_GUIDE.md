# MongoDB to Cassandra Migration Guide

## Overview
This guide documents the complete migration strategy from MongoDB to Cassandra for the blog application, including:
- **Phase 1**: Double writes (write to both MongoDB and Cassandra)
- **Phase 2**: Read migration (gradually switch reads to Cassandra)
- **Phase 3**: Cleanup (remove MongoDB)

---

## Current Status: Phase 1 - Double Writes ✅

### What's Implemented
- ✅ Cassandra connection in `app.py`
- ✅ Double-write logic in all CREATE/UPDATE/DELETE operations
- ✅ MongoDB remains primary read/write source
- ✅ Cassandra receives copies of all writes

### Files Involved
- `app.py` - Main application with double-write implementation
- `cassandra_setup.py` - Initializes Cassandra schema
- `migrate_to_cassandra.py` - Copies existing MongoDB data to Cassandra

---

## Phase 2: Read Migration (In Progress)

### What This Phase Does
Gradually transition read operations from MongoDB to Cassandra while keeping writes in both systems.

### Files Involved
- `cassandra_read_migration.py` - Helper functions for Cassandra reads
- `app.py` (to be updated) - Switch read operations

### Implementation Steps

#### Step 1: Setup Cassandra
```bash
python cassandra_setup.py
```
Creates the `blog_keyspace` and initializes tables:
- `posts` table
- `comments` table

#### Step 2: Migrate Existing Data
```bash
python migrate_to_cassandra.py
```
Copies all documents from MongoDB to Cassandra:
- Copies all posts
- Copies all comments
- Maintains relationships and timestamps

#### Step 3: Update Application Reads (Optional)
Modify `app.py` to read from Cassandra:

```python
from cassandra_read_migration import (
    get_all_posts,
    get_post_by_id,
    get_comments_by_post,
    count_posts_per_author
)

# In home() route - replace this:
# posts = list(posts_collection.find())
# With this:
posts = get_all_posts(cassandra_session)
author_counts = count_posts_per_author(cassandra_session)

# In post_detail() route - replace this:
# post = posts_collection.find_one({"_id": ObjectId(post_id)})
# comments = list(comments_collection.find(...))
# With this:
post = get_post_by_id(cassandra_session, post_id)
comments = get_comments_by_post(cassandra_session, post_id)
```

#### Step 4: Verification
Run tests to ensure:
- All reads return correct data from Cassandra
- All writes sync to both systems
- No data loss during migration
- Timestamps preserved correctly

---

## Phase 3: Cleanup (Deferred)

### What This Phase Does
Removes MongoDB completely and relies solely on Cassandra.

### Files Involved
- `cleanup_mongodb.py` - Drops MongoDB collections

### When to Execute
Only after:
1. ✅ All data migrated to Cassandra
2. ✅ Application successfully reading from Cassandra
3. ✅ Thorough testing completed
4. ✅ Full backup of MongoDB data created

### Cleanup Steps
```bash
# BACKUP FIRST!
# mongodump --db blog_db --out ./backup

# Then cleanup
python cleanup_mongodb.py
```

This will:
1. Drop `posts` collection from MongoDB
2. Drop `comments` collection from MongoDB
3. Provide instructions for removing MongoDB code from `app.py`

---

## Data Schema

### MongoDB Collections

#### posts
```javascript
{
  _id: ObjectId,
  title: String,
  content: String,
  author: String,
  created_at: Date,
  updated_at: Date
}
```

#### comments
```javascript
{
  _id: ObjectId,
  post_id: ObjectId,
  commenter: String,
  comment: String,
  created_at: Date
}
```

### Cassandra Tables

#### posts
```sql
CREATE TABLE posts (
  post_id TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  author TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

#### comments
```sql
CREATE TABLE comments (
  comment_id UUID PRIMARY KEY,
  post_id TEXT,
  commenter TEXT,
  comment TEXT,
  created_at TIMESTAMP
)
```

---

## API Endpoints

### Create Post
```
POST /create
Parameters: title, content, author
Action: Writes to MongoDB AND Cassandra (double write)
```

### Read Posts
```
GET /
Query params: sort=date|alphabetical
Action: Reads from MongoDB (or Cassandra after Phase 2)
```

### Read Single Post with Comments
```
GET /post/<post_id>
Action: Reads post + comments from MongoDB (or Cassandra after Phase 2)
```

### Create Comment
```
POST /post/<post_id>/comment
Parameters: commenter, comment
Action: Writes to MongoDB AND Cassandra (double write)
```

### Update Post
```
POST /edit/<post_id>
Parameters: title, content, author
Action: Updates in MongoDB AND Cassandra (double write)
```

### Delete Post
```
POST /delete/<post_id>
Action: Deletes from MongoDB AND Cassandra (double write)
```

---

## Monitoring & Verification

### Check Migration Progress
```bash
# Check MongoDB
python -c "
from pymongo import MongoClient
client = MongoClient()
db = client.blog_db
print(f'Posts: {db.posts.count_documents({})}')
print(f'Comments: {db.comments.count_documents({})}')
"

# Check Cassandra
python -c "
from cassandra.cluster import Cluster
cluster = Cluster()
session = cluster.connect('blog_keyspace')
print('Posts:', session.execute('SELECT COUNT(*) FROM posts').one()[0])
print('Comments:', session.execute('SELECT COUNT(*) FROM comments').one()[0])
session.shutdown()
"
```

### Verify Data Consistency
Both systems should have identical data during migration phases:
- Same number of posts
- Same number of comments
- Same timestamps
- Same content

---

## Troubleshooting

### Cassandra Connection Failed
```
Error: Failed to connect to Cassandra
Solution:
  1. Ensure Cassandra is running
  2. Check default connection IP: 127.0.0.1:9042
  3. Verify blog_keyspace exists: cassandra_setup.py
```

### Migration Script Errors
```
Error: Failed to migrate posts
Solution:
  1. Ensure MongoDB is running with data
  2. Ensure Cassandra is initialized (cassandra_setup.py)
  3. Check post timestamps are datetime objects
  4. Check for duplicate post_id conflicts
```

### Data Inconsistency After Cleanup
```
Error: Data missing after cleanup_mongodb.py
Solution:
  1. Restore from backup: mongorestore --db blog_db ./backup
  2. Re-run migrate_to_cassandra.py
  3. Verify read operations in app.py are using Cassandra
  4. Check for application errors in logs
```

---

## Rollback Plan

If issues occur during migration:

### Rollback from Phase 1 (Double Writes)
```bash
# Cassandra data can be safely ignored
# Application continues using MongoDB only
# Remove double-write code from app.py if needed
```

### Rollback from Phase 2 (Read Migration)
```bash
# Switch back to MongoDB reads in app.py
# Cassandra still receives writes (optional to keep)
# Or skip cleanup and run with both systems
```

### Rollback from Phase 3 (After Cleanup)
```bash
# Restore MongoDB from backup
# Re-run migrate_to_cassandra.py
# Update app.py to resume MongoDB reads
```

---

## Timeline & Recommendations

### Recommended Schedule
- **Week 1**: Setup Phase 1 (double writes)
- **Week 2-3**: Monitor Phase 1, prepare Phase 2
- **Week 4**: Execute Phase 2 (read migration)
- **Week 5+**: Thorough testing Phase 2
- **Week 6+**: Execute Phase 3 (cleanup) when confident

### Success Criteria
- ✅ Zero data loss during migration
- ✅ Application performance maintained
- ✅ All read/write operations functional
- ✅ Timestamps preserved correctly
- ✅ Comments linked to correct posts

---

## Files Summary

| File | Purpose | Status |
|------|---------|--------|
| `app.py` | Main application with double writes | ✅ Ready |
| `cassandra_setup.py` | Initialize Cassandra schema | ✅ Ready |
| `migrate_to_cassandra.py` | Migrate MongoDB → Cassandra | ✅ Ready |
| `cassandra_read_migration.py` | Helper for Cassandra reads | ✅ Ready |
| `cleanup_mongodb.py` | Remove MongoDB data | ✅ Ready |

---

## Questions & Support

For each migration phase:
1. Run the setup script
2. Verify data in both systems
3. Check application logs
4. Proceed to next phase only when confident
5. Keep backups throughout the process
