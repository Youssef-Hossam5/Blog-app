import unittest
from app import app, posts_collection, comments_collection
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import json

class BlogApplicationTestCase(unittest.TestCase):
    \"\"\"Comprehensive test suite for the blog application\"\"\"

    def setUp(self):
        \"\"\"Set up test client and clean database before each test\"\"\"
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Clear database before each test
        posts_collection.delete_many({})
        comments_collection.delete_many({})

    def tearDown(self):
        \"\"\"Clean up after each test\"\"\"
        posts_collection.delete_many({})
        comments_collection.delete_many({})

    # ==================== CREATE TESTS ====================
    def test_create_post_get_form(self):
        \"\"\"Test that create form is accessible\"\"\"
        response = self.client.get('/create')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create', response.data)

    def test_create_post_post(self):
        \"\"\"Test creating a new post\"\"\"
        response = self.client.post('/create', data={
            'title': 'Test Post',
            'content': 'This is a test post',
            'author': 'John Doe'
        })
        
        # Should redirect to home
        self.assertEqual(response.status_code, 302)
        
        # Check post was created in database
        post = posts_collection.find_one({'title': 'Test Post'})
        self.assertIsNotNone(post)
        self.assertEqual(post['author'], 'John Doe')
        self.assertEqual(post['content'], 'This is a test post')

    # ==================== READ TESTS ====================
    def test_home_page_no_posts(self):
        \"\"\"Test home page with no posts\"\"\"
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_page_with_posts(self):
        \"\"\"Test home page displays posts\"\"\"
        # Create test posts
        posts_collection.insert_one({
            'title': 'First Post',
            'content': 'First content',
            'author': 'Author A',
            'created_at': datetime.utcnow()
        })
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'First Post', response.data)

    def test_post_detail_view(self):
        \"\"\"Test viewing a single post\"\"\"
        # Create test post
        result = posts_collection.insert_one({
            'title': 'Detail Test',
            'content': 'Detail content',
            'author': 'Test Author',
            'created_at': datetime.utcnow()
        })
        post_id = result.inserted_id
        
        response = self.client.get(f'/post/{post_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Detail Test', response.data)

    # ==================== SORTING TESTS ====================
    def test_sort_by_date_descending(self):
        \"\"\"Test posts sorted by date (most recent first) - DATABASE-LEVEL\"\"\"
        # Create posts with different dates
        post1 = posts_collection.insert_one({
            'title': 'Oldest Post',
            'content': 'content',
            'author': 'Author A',
            'created_at': datetime(2024, 1, 1)
        })
        
        post2 = posts_collection.insert_one({
            'title': 'Newest Post',
            'content': 'content',
            'author': 'Author B',
            'created_at': datetime(2024, 1, 3)
        })
        
        post3 = posts_collection.insert_one({
            'title': 'Middle Post',
            'content': 'content',
            'author': 'Author C',
            'created_at': datetime(2024, 1, 2)
        })
        
        # Get posts sorted by date (default)
        response = self.client.get('/?sort=date')
        self.assertEqual(response.status_code, 200)
        
        # Verify order in response (newest first)
        content = response.data.decode('utf-8')
        newest_pos = content.find('Newest Post')
        middle_pos = content.find('Middle Post')
        oldest_pos = content.find('Oldest Post')
        
        # Newest should appear before oldest
        self.assertGreater(newest_pos, 0)
        self.assertGreater(middle_pos, 0)
        self.assertGreater(oldest_pos, 0)
        self.assertLess(newest_pos, oldest_pos)

    def test_sort_by_title_alphabetically(self):
        \"\"\"Test posts sorted alphabetically by title - DATABASE-LEVEL\"\"\"
        # Create posts with non-alphabetical titles
        posts_collection.insert_many([
            {
                'title': 'Zebra Post',
                'content': 'content',
                'author': 'Author A',
                'created_at': datetime.utcnow()
            },
            {
                'title': 'Apple Post',
                'content': 'content',
                'author': 'Author B',
                'created_at': datetime.utcnow()
            },
            {
                'title': 'Mango Post',
                'content': 'content',
                'author': 'Author C',
                'created_at': datetime.utcnow()
            }
        ])
        
        # Get posts sorted alphabetically
        response = self.client.get('/?sort=alphabetical')
        self.assertEqual(response.status_code, 200)
        
        # Verify alphabetical order in response
        content = response.data.decode('utf-8')
        apple_pos = content.find('Apple Post')
        mango_pos = content.find('Mango Post')
        zebra_pos = content.find('Zebra Post')
        
        # Apple should appear before Mango, Mango before Zebra
        self.assertGreater(apple_pos, 0)
        self.assertGreater(mango_pos, 0)
        self.assertGreater(zebra_pos, 0)
        self.assertLess(apple_pos, mango_pos)
        self.assertLess(mango_pos, zebra_pos)

    # ==================== AUTHOR COUNT TESTS ====================
    def test_author_post_count_aggregation(self):
        \"\"\"Test author post counts using MongoDB aggregation - DATABASE-LEVEL\"\"\"
        # Create posts from different authors
        posts_collection.insert_many([
            {'title': 'Post 1', 'content': 'content', 'author': 'John', 'created_at': datetime.utcnow()},
            {'title': 'Post 2', 'content': 'content', 'author': 'John', 'created_at': datetime.utcnow()},
            {'title': 'Post 3', 'content': 'content', 'author': 'Jane', 'created_at': datetime.utcnow()},
            {'title': 'Post 4', 'content': 'content', 'author': 'John', 'created_at': datetime.utcnow()},
            {'title': 'Post 5', 'content': 'content', 'author': 'Jane', 'created_at': datetime.utcnow()},
        ])
        
        # Get author stats
        response = self.client.get('/api/author-stats')
        self.assertEqual(response.status_code, 200)
        
        stats = json.loads(response.data)
        
        # Verify counts are correct (aggregated in database)
        self.assertEqual(stats.get('John'), 3)
        self.assertEqual(stats.get('Jane'), 2)

    def test_author_stats_api(self):
        \"\"\"Test author statistics API endpoint\"\"\"
        # Create sample posts
        posts_collection.insert_many([
            {'title': 'Post 1', 'content': 'content', 'author': 'Alice', 'created_at': datetime.utcnow()},
            {'title': 'Post 2', 'content': 'content', 'author': 'Bob', 'created_at': datetime.utcnow()},
            {'title': 'Post 3', 'content': 'content', 'author': 'Alice', 'created_at': datetime.utcnow()},
        ])
        
        response = self.client.get('/api/author-stats')
        self.assertEqual(response.status_code, 200)
        
        stats = json.loads(response.data)
        self.assertEqual(stats['Alice'], 2)
        self.assertEqual(stats['Bob'], 1)

    # ==================== COMMENT TESTS ====================
    def test_add_comment(self):
        \"\"\"Test adding a comment to a post\"\"\"
        # Create test post
        post_id = posts_collection.insert_one({
            'title': 'Comment Test',
            'content': 'Test content',
            'author': 'Post Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        # Add comment
        response = self.client.post(f'/post/{post_id}/comment', data={
            'commenter': 'Commenter Name',
            'comment': 'Great post!'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify comment was created
        comment = comments_collection.find_one({'commenter': 'Commenter Name'})
        self.assertIsNotNone(comment)
        self.assertEqual(comment['comment'], 'Great post!')

    def test_comments_sorted_by_date(self):
        \"\"\"Test comments are sorted by date (DATABASE-LEVEL)\"\"\"
        # Create post
        post_id = posts_collection.insert_one({
            'title': 'Comment Sort Test',
            'content': 'Test',
            'author': 'Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        # Add multiple comments with different dates
        comments_collection.insert_many([
            {
                'post_id': post_id,
                'commenter': 'User1',
                'comment': 'First comment',
                'created_at': datetime(2024, 1, 1)
            },
            {
                'post_id': post_id,
                'commenter': 'User2',
                'comment': 'Third comment',
                'created_at': datetime(2024, 1, 3)
            },
            {
                'post_id': post_id,
                'commenter': 'User3',
                'comment': 'Second comment',
                'created_at': datetime(2024, 1, 2)
            }
        ])
        
        response = self.client.get(f'/post/{post_id}')
        self.assertEqual(response.status_code, 200)
        
        # Comments should be ordered newest first (database-level sorting)
        content = response.data.decode('utf-8')
        third_pos = content.find('Third comment')
        second_pos = content.find('Second comment')
        first_pos = content.find('First comment')
        
        # Verify newest is displayed first
        self.assertLess(third_pos, second_pos)
        self.assertLess(second_pos, first_pos)

    # ==================== UPDATE TESTS ====================
    def test_edit_post_get_form(self):
        \"\"\"Test that edit form is accessible\"\"\"
        # Create test post
        post_id = posts_collection.insert_one({
            'title': 'Original Title',
            'content': 'Original content',
            'author': 'Original Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        response = self.client.get(f'/edit/{post_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Original Title', response.data)

    def test_edit_post_update(self):
        \"\"\"Test updating a post\"\"\"
        # Create test post
        post_id = posts_collection.insert_one({
            'title': 'Original Title',
            'content': 'Original content',
            'author': 'Original Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        # Update post
        response = self.client.post(f'/edit/{post_id}', data={
            'title': 'Updated Title',
            'content': 'Updated content',
            'author': 'Updated Author'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify post was updated
        updated_post = posts_collection.find_one({'_id': post_id})
        self.assertEqual(updated_post['title'], 'Updated Title')
        self.assertEqual(updated_post['content'], 'Updated content')
        self.assertEqual(updated_post['author'], 'Updated Author')

    # ==================== DELETE TESTS ====================
    def test_delete_post(self):
        \"\"\"Test deleting a post\"\"\"
        # Create test post
        post_id = posts_collection.insert_one({
            'title': 'Delete Test',
            'content': 'This will be deleted',
            'author': 'Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        # Delete post
        response = self.client.post(f'/delete/{post_id}')
        self.assertEqual(response.status_code, 302)
        
        # Verify post was deleted
        deleted_post = posts_collection.find_one({'_id': post_id})
        self.assertIsNone(deleted_post)

    def test_delete_post_with_comments(self):
        \"\"\"Test that deleting a post also deletes its comments\"\"\"
        # Create post
        post_id = posts_collection.insert_one({
            'title': 'Post with Comments',
            'content': 'Content',
            'author': 'Author',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        # Add comments
        comments_collection.insert_many([
            {'post_id': post_id, 'commenter': 'User1', 'comment': 'Comment 1', 'created_at': datetime.utcnow()},
            {'post_id': post_id, 'commenter': 'User2', 'comment': 'Comment 2', 'created_at': datetime.utcnow()},
        ])
        
        # Verify comments exist
        initial_count = comments_collection.count_documents({'post_id': post_id})
        self.assertEqual(initial_count, 2)
        
        # Delete post
        self.client.post(f'/delete/{post_id}')
        
        # Verify post and comments are deleted
        final_count = comments_collection.count_documents({'post_id': post_id})
        self.assertEqual(final_count, 0)

    # ==================== DATABASE STATISTICS TESTS ====================
    def test_database_stats_api(self):
        \"\"\"Test database statistics API\"\"\"
        # Create test data
        posts_collection.insert_many([
            {'title': 'Post 1', 'content': 'content', 'author': 'Author 1', 'created_at': datetime.utcnow()},
            {'title': 'Post 2', 'content': 'content', 'author': 'Author 2', 'created_at': datetime.utcnow()},
        ])
        
        comments_collection.insert_many([
            {'post_id': ObjectId(), 'commenter': 'User1', 'comment': 'Comment 1', 'created_at': datetime.utcnow()},
            {'post_id': ObjectId(), 'commenter': 'User2', 'comment': 'Comment 2', 'created_at': datetime.utcnow()},
            {'post_id': ObjectId(), 'commenter': 'User3', 'comment': 'Comment 3', 'created_at': datetime.utcnow()},
        ])
        
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        stats = json.loads(response.data)
        self.assertEqual(stats['mongodb']['posts'], 2)
        self.assertEqual(stats['mongodb']['comments'], 3)


if __name__ == '__main__':
    print('\\n' + '='*70)
    print('BLOG APPLICATION TEST SUITE')
    print('='*70)
    print('\\nRunning comprehensive tests for MongoDB blog application')
    print('Tests focus on:')
    print('   CRUD Operations (Create, Read, Update, Delete)')
    print('   Database-Level Sorting (Date and Alphabetical)')
    print('   Database-Level Aggregation (Author Post Counts)')
    print('   Comments Management')
    print('   Database Statistics')
    print('\\n' + '='*70 + '\\n')
    
    unittest.main(verbosity=2)
