# Architecture & Design Document

## System Overview

This blog application demonstrates a production-grade migration from MongoDB to Cassandra using the **double-write pattern** and eventual **read migration** strategy.

`

                    Flask Web Application                     
                  (Blog CRUD + Comments)                      

                  
        
                            
              
     MongoDB           Cassandra
     (Phase1)           (Phase1)
              
    
Legend:
Phase 1: Double Writes - Both MongoDB and Cassandra
Phase 2: Read Migration - Only read from Cassandra
Phase 3: Cleanup - Only Cassandra remains
`

---

## Architecture Layers

### 1. **Presentation Layer** (Flask Templates)
- HTML5 forms for CRUD operations
- Bootstrap-inspired responsive design
- Real-time sorting controls
- Comment submission forms

### 2. **Application Layer** (Flask Routes)
Key routes with database operations:

\\\
/                     GET  posts (with sorting)
/create               POST new post (double write)
/post/<id>            GET  post + comments
/post/<id>/comment    POST comment (double write)
/edit/<id>            POST update (double write)
/delete/<id>          POST delete (double write)
/api/author-stats     GET  aggregated counts
/api/stats            GET  sync verification
\\\

### 3. **Database Layer** (MongoDB + Cassandra)


Collection: posts
 _id (ObjectId)              [PRIMARY]
 title (String)              [INDEX - alphabetical sorting]
 content (String)
 author (String)             [INDEX - aggregation]
 created_at (DateTime)       [INDEX - date sorting]
 updated_at (DateTime)

Collection: comments
 _id (ObjectId)              [PRIMARY]
 post_id (ObjectId)          [INDEX - finding comments by post]
 commenter (String)
 comment (String)
 created_at (DateTime)
`

**Index Strategy:**
- \created_at\: Enables fast date sorting
- \	itle\: Enables fast alphabetical sorting
- \uthor\: Enables fast aggregation queries
- \post_id\ (comments): Enables fast comment retrieval

### Cassandra Schema

`
Table: posts
 post_id (TEXT)              [PRIMARY KEY]
 title (TEXT)
 content (TEXT)
 author (TEXT)               [INDEXED]
 created_at (TIMESTAMP)
 updated_at (TIMESTAMP)

Table: comments
 comment_id (UUID)           [PRIMARY KEY]
 post_id (TEXT)              [INDEXED]
 commenter (TEXT)
 comment (TEXT)
 created_at (TIMESTAMP)
`


---

## Data Consistency Model

### MongoDB
- **Consistency:** ACID transactions (within single collection)
- **Replication:** Configurable (default: Primary)
- **Eventual Consistency:** After replica sync

### Cassandra
- **Consistency:** Eventual consistency
- **Replication:** Multi-node (default: replication_factor=1 for dev)
- **Tunable Consistency:** CL (Consistency Level) per query

### Implications for Blog App

| Operation | Consistency | Risk |
|-----------|-----------|------|
| Create post | Eventually consistent | Minimal (posts are immutable once created) |
| Add comment | Eventually consistent | Minimal (comments are immutable) |
| Edit post | Eventually consistent | User sees old version briefly |
| Delete post | Eventually consistent | Post might be visible briefly after deletion |

---

## Error Handling Strategy

### Write Failures

`
User creates post
    
     MongoDB write   FAIL
        Request fails immediately
           User sees error
           No data persisted
    
     Not attempted
`

`
User creates post
    
     MongoDB write   SUCCESS
    
     Cassandra write   FAIL
         Error logged
            Request succeeds (MongoDB is source of truth)
            /api/stats shows inconsistency
            Migration script will re-sync
`

### Read Failures

`
User views posts
    
     MongoDB read   FAIL
        Show error page
    
     User must start MongoDB
`

---

## Security Considerations

### Current Implementation (Educational)
-  No authentication
-  No input validation
-  No HTTPS
-  No rate limiting

### Production Recommendations

1. **Authentication**
   - JWT tokens
   - Session management
   - User roles (admin, editor, commenter)

2. **Input Validation**
   - XSS prevention
   - SQL injection prevention
   - File upload validation

3. **Encryption**
   - TLS/HTTPS
   - Database connection encryption
   - At-rest encryption

4. **Rate Limiting**
   - API rate limits
   - Brute force protection
   - DDoS mitigation

5. **Monitoring**
   - Audit logs
   - Error tracking
   - Performance monitoring

---

## Testing Strategy

### Unit Tests
- Database query results
- Sorting correctness
- Aggregation accuracy

### Integration Tests
- End-to-end CRUD operations
- Double-write synchronization
- API endpoint responses

### Load Tests
- Thousands of posts
- Concurrent writes
- Query performance

### Migration Tests
- Data integrity during migration
- Zero downtime verification
- Rollback procedures

---

## Deployment Checklist

### Pre-Production (Phase 1)
- [ ] MongoDB running on production server
- [ ] Cassandra running on production server
- [ ] Database backups automated
- [ ] Monitoring alerts configured
- [ ] Error logging enabled
- [ ] Performance baselines established

### Phase 2 Preparation
- [ ] Historical data migrated
- [ ] Read queries tested against Cassandra
- [ ] Fallback procedures documented
- [ ] Team trained on new query patterns

### Phase 3 Execution
- [ ] MongoDB backups verified
- [ ] Cassandra fully replicated (replication_factor  3)
- [ ] Read queries fully migrated
- [ ] Team ready for rollback

---

## Troubleshooting Guide

### Sorting Not Working
**Problem:** Posts appear out of order
**Cause:** Missing database index or Python-level sorting
**Solution:** Verify indexes: \db.posts.getIndexes()\

### Aggregation Returning Wrong Counts
**Problem:** Author post counts incorrect
**Cause:** Using Python loop instead of pipeline
**Solution:** Check \get_author_post_counts_mongodb()\

### Data Mismatch Between MongoDB and Cassandra
**Problem:** \/api/stats\ shows different counts
**Cause:** Double-write failure or incomplete migration
**Solution:** Run \python migrate_to_cassandra.py\

---

## Future Enhancements

1. **Search Indexing**
   - Elasticsearch for full-text search
   - Faceted search support

2. **Caching Layer**
   - Redis for hot data
   - Query result caching

3. **Analytics**
   - Post popularity metrics
   - Author engagement tracking
   - Trend analysis

4. **Scaling**
   - MongoDB sharding
   - Cassandra ring expansion
   - Load balancing

5. **Advanced Features**
   - Categories/tags
   - User follow system
   - Recommendation engine

---

Generated: February 2024
