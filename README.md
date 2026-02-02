# MongoDB & Cassandra Dual-Write Blog Application

An application demonstrating a dual-write migration strategy from MongoDB to Cassandra.

## Project Overview

This application implements a **blog platform** with the following features:
-  Multi-author blog posts with timestamps
-  Comment system with database-level sorting
-  Main feed with multiple sorting strategies
-  Author post count tracking
-  Double-write pattern (MongoDB + Cassandra)
-  Migration tools for data transition
-  Complete CRUD operations

## Key Architectural Decisions

### DATABASE-LEVEL Operations (Not Python-Level)
This application implements critical optimizations:

#### 1. **Sorting is Database-Level**
- Posts sorted by date: Uses MongoDB sort() query operator
- Posts sorted alphabetically: Uses MongoDB sort() with collation
- Comments sorted by date: Uses MongoDB database-level sorting
- NOT fetching all data and sorting in Python


#### 2. **Indexes for Performance**
`
posts_collection.create_index('created_at')
posts_collection.create_index('title')
posts_collection.create_index('author')
comments_collection.create_index('post_id')
`

## Dependencies & Versions

### Requirements
\\\
Flask==3.0.0              # Web framework
pymongo==4.6.1           # MongoDB driver
cassandra-driver==3.29.0 # Cassandra driver
python-dateutil==2.8.2   # Date utilities
\\\

### Installation
\\\ash
pip install -r requirements.txt
\\\

## Architecture Overview

### 1. MongoDB Setup
`python
mongo_uri = 'mongodb://localhost:27017/'
mongo_db = mongo_client.blog_db
posts_collection = mongo_db.posts        # Stores blog posts
comments_collection = mongo_db.comments  # Stores comments
`

### 2. Cassandra Setup (Optional)
`python
cassandra_cluster = Cluster(['127.0.0.1'])
cassandra_session = cassandra_cluster.connect('blog_keyspace')
`

### 3. Double-Write Pattern
Every write operation (CREATE, UPDATE, DELETE) writes to both:
- MongoDB (primary datastore)
- Cassandra (migration target, if available)

## API Endpoints & Features

## Running the Application

### Prerequisites
- Python 3.8+
- MongoDB 4.0+ running on localhost:27017
- (Optional) Cassandra running on localhost:9042

### Start MongoDB
`ash
# Using Docker
docker run -d -p 27017:27017 mongo:latest

# Or local installation
mongod --dbpath /path/to/data
`

### Start Cassandra (Optional)
`ash
# Using Docker
docker run -d -p 9042:9042 cassandra:latest

# Or local installation
cassandra -f
`

### Run Application
`ash
python app.py
`

Visit: http://localhost:5000

## Testing

### Test Suite
Run the comprehensive test suite:
`ash
python test_suite.py
`

Tests cover:
- Creating posts with different authors
- Sorting posts by date
- Sorting posts alphabetically
- Author post count aggregation
- Comment creation and retrieval
- Double-write verification
- Database statistics

### Manual Testing

**1. Create Sample Data**
`ash
# Via web form: http://localhost:5000/create
# Or via API:
curl -X POST http://localhost:5000/create \\
  -d "title=First Post&author=John&content=Hello World"
`

**2. Verify Sorting**
`ash
# Test date sorting
curl http://localhost:5000/?sort=date

# Test alphabetical sorting
curl http://localhost:5000/?sort=alphabetical
`

**3. Check Author Counts**
`ash
curl http://localhost:5000/api/author-stats
`

**4. Verify Double Writes**
`ash
# Check if data exists in both databases
curl http://localhost:5000/api/stats
`

## Migration Strategy

### Phase 1: Double-Write (Current)
- All writes go to MongoDB and Cassandra
- Reads come from MongoDB
- Ensures data consistency

### Phase 2: Read Migration (cassandra_read_migration.py)
- Gradually migrate reads from MongoDB to Cassandra
- Implement read-write pattern to both stores
- Test Cassandra read performance

### Phase 3: Complete Migration
- All reads and writes to Cassandra
- MongoDB becomes read-only
- Finally, remove MongoDB

### Phase 4: Cleanup (cleanup_mongodb.py)
- Remove all MongoDB dependencies
- Remove MongoDB-specific code
- Final validation

## Project Structure

\\\
blog-app/
 app.py                      # Main Flask application
 requirements.txt            # Python dependencies
 cassandra_setup.py         # Cassandra initialization
 migrate_to_cassandra.py    # Bulk migration script
 cassandra_read_migration.py # Read query migration
 cleanup_mongodb.py         # Remove MongoDB
 test_suite.py              # Test cases
 templates/
     index.html             # Home feed template
     post.html              # Post detail template
     create.html            # Create post template
     edit.html              # Edit post template
\\\

## Key Implementation Details

### 1. Database-Level Sorting
`python
def get_posts_sorted_by_date_mongodb(order='desc'):
    sort_direction = -1 if order == 'desc' else 1
    # SORTING HAPPENS IN MONGODB, NOT PYTHON
    posts = list(posts_collection.find().sort('created_at', sort_direction))
    return posts
`

### 2. Database-Level Aggregation
`python
def get_author_post_counts_mongodb():
    pipeline = [
        {
            '\': {
                '_id': '\',
                'count': {'\': 1}  # COUNT IN DATABASE
            }
        }
    ]
    results = list(posts_collection.aggregate(pipeline))
    author_counts = {item['_id']: item['count'] for item in results}
    return author_counts
`

### 3. Double-Write Pattern
`python
# Write to MongoDB
mongo_result = posts_collection.insert_one(post_data)

# Double write to Cassandra (if available)
if CASSANDRA_AVAILABLE:
    cassandra_session.execute(INSERT_QUERY, parameters)
`

## Performance Optimizations

1. **MongoDB Indexes**: Created on frequently queried fields
   - created_at - for date sorting
   - 	itle - for alphabetical sorting
   -  uthor - for filtering by author

2. **Database-Level Sorting**: No Python sorting overhead

3. **Database-Level Aggregation**: Efficient group-by operations

4. **Connection Pooling**: Cassandra driver handles connection pooling


## License

MIT License
