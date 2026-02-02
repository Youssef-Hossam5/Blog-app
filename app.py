from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
import json

app = Flask(__name__)

# -------------------
# MongoDB Connection
# -------------------
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client.blog_db
posts_collection = mongo_db.posts
comments_collection = mongo_db.comments
author_stats_collection = mongo_db.author_stats

# Create MongoDB indexes for better performance
posts_collection.create_index('created_at')
posts_collection.create_index('title')
posts_collection.create_index('author')
comments_collection.create_index('post_id')
author_stats_collection.create_index('author')

# -------------------
# Cassandra Connection (Optional)
# -------------------
CASSANDRA_AVAILABLE = False
cassandra_session = None
try:
    from cassandra.cluster import Cluster
    cassandra_cluster = Cluster(['127.0.0.1'])
    cassandra_session = cassandra_cluster.connect('blog_keyspace', wait_for_all_pools=True)
    CASSANDRA_AVAILABLE = True
except Exception as e:
    print(f'Info: Cassandra not available: {e}')
    CASSANDRA_AVAILABLE = False
    cassandra_session = None


# -------------------
# Database Helper Functions
# -------------------

def increment_author_post_count(author_name):
    """Increment post count for an author in the author_stats collection"""
    author_stats_collection.update_one(
        {'author': author_name},
        {
            '$inc': {'post_count': 1},
            '$set': {'updated_at': datetime.utcnow()}
        },
        upsert=True
    )


def decrement_author_post_count(author_name):
    """Decrement post count for an author in the author_stats collection"""
    author_stats_collection.update_one(
        {'author': author_name},
        {
            '$inc': {'post_count': -1},
            '$set': {'updated_at': datetime.utcnow()}
        },
        upsert=True
    )


def get_author_post_counts_from_db():
    """
    Get post count per author from author_stats collection (STORED IN DB)
    Returns a dict of author -> post_count
    """
    stats = author_stats_collection.find({}, {'author': 1, 'post_count': 1})
    author_counts = {item['author']: item.get('post_count', 0) for item in stats}
    return author_counts

def get_posts_sorted_by_date_mongodb(order='desc'):
    """
    Get all posts sorted by date using MongoDB query (DATABASE-LEVEL)
    Sorting happens in the database, not in Python.
    """
    sort_direction = -1 if order == 'desc' else 1
    posts = list(posts_collection.find().sort('created_at', sort_direction))
    return posts


def get_posts_sorted_by_title_mongodb():
    """
    Get all posts sorted by title alphabetically using MongoDB query (DATABASE-LEVEL)
    Sorting happens in the database with proper collation.
    """
    posts = list(posts_collection.find().collation({'locale': 'en'}).sort('title', 1))
    return posts


# -------------------
# CRUD Operations
# -------------------

# CREATE - Add new post (Double Write: MongoDB + Cassandra)
@app.route('/create', methods=['GET', 'POST'])
def create_post():
    """Create a new blog post with double write strategy"""
    if request.method == 'POST':
        post_data = {
            'title': request.form['title'],
            'content': request.form['content'],
            'author': request.form['author'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Write to MongoDB
        mongo_result = posts_collection.insert_one(post_data)
        post_id = str(mongo_result.inserted_id)

        # Increment author post count in author_stats collection
        increment_author_post_count(post_data['author'])

        # Double write to Cassandra (if available)
        if CASSANDRA_AVAILABLE:
            try:
                cassandra_session.execute(
                    '''
                    INSERT INTO posts (post_id, title, content, author, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (post_id, post_data['title'], post_data['content'],
                     post_data['author'], post_data['created_at'], post_data['updated_at'])
                )
            except Exception as e:
                print(f'Cassandra write failed: {e}')

        return redirect(url_for('home'))

    return render_template('create.html')


# READ - Get all posts with sorting options (DATABASE-LEVEL QUERIES)
@app.route('/')
def home():
    """Display all posts with sorting options (date or alphabetical)"""
    sort_by = request.args.get('sort', 'date')  # date or alphabetical

    # Use MongoDB queries for sorting - NOT Python-level sorting
    if sort_by == 'alphabetical':
        posts = get_posts_sorted_by_title_mongodb()
    else:  # default to date
        posts = get_posts_sorted_by_date_mongodb(order='desc')

    # Get author post counts from stored author_stats collection
    author_counts = get_author_post_counts_from_db()

    return render_template('index.html', posts=posts, author_counts=author_counts, sort_by=sort_by)


# READ - Get single post details with comments
@app.route('/post/<post_id>')
def post_detail(post_id):
    """Display a single post with its comments"""
    try:
        post = posts_collection.find_one({'_id': ObjectId(post_id)})
        if post:
            # Get comments for this post - sorted by date descending (DATABASE-LEVEL)
            comments = list(comments_collection.find({'post_id': ObjectId(post_id)}).sort('created_at', -1))
            return render_template('post.html', post=post, comments=comments)
        return redirect(url_for('home'))
    except:
        return redirect(url_for('home'))


# UPDATE - Edit post (Double Write)
@app.route('/edit/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    """Edit an existing blog post"""
    try:
        post = posts_collection.find_one({'_id': ObjectId(post_id)})

        if request.method == 'POST':
            update_data = {
                'title': request.form['title'],
                'content': request.form['content'],
                'author': request.form['author'],
                'updated_at': datetime.utcnow()
            }

            # Update in MongoDB
            posts_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$set': update_data}
            )

            # Double write to Cassandra (if available)
            if CASSANDRA_AVAILABLE:
                try:
                    cassandra_session.execute(
                        '''
                        UPDATE posts SET title=%s, content=%s, author=%s, updated_at=%s
                        WHERE post_id=%s
                        ''',
                        (update_data['title'], update_data['content'],
                         update_data['author'], update_data['updated_at'], post_id)
                    )
                except Exception as e:
                    print(f'Cassandra update failed: {e}')

            return redirect(url_for('post_detail', post_id=post_id))

        return render_template('edit.html', post=post)
    except:
        return redirect(url_for('home'))


# DELETE - Remove post (Double Write)
@app.route('/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    """Delete a blog post and its comments"""
    try:
        # Get post to find author
        post = posts_collection.find_one({'_id': ObjectId(post_id)})
        
        # Delete from MongoDB
        posts_collection.delete_one({'_id': ObjectId(post_id)})
        comments_collection.delete_many({'post_id': ObjectId(post_id)})

        # Decrement author post count if post was found
        if post:
            decrement_author_post_count(post['author'])

        # Delete from Cassandra (if available)
        if CASSANDRA_AVAILABLE:
            try:
                cassandra_session.execute('DELETE FROM posts WHERE post_id=%s', (post_id,))
                cassandra_session.execute('DELETE FROM comments WHERE post_id=%s', (post_id,))
            except Exception as e:
                print(f'Cassandra delete failed: {e}')

        return redirect(url_for('home'))
    except:
        return redirect(url_for('home'))


# COMMENTS - Add comment to post
@app.route('/post/<post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a blog post with double write strategy"""
    try:
        comment_data = {
            'post_id': ObjectId(post_id),
            'commenter': request.form['commenter'],
            'comment': request.form['comment'],
            'created_at': datetime.utcnow()
        }

        # Write to MongoDB
        comments_collection.insert_one(comment_data)

        # Double write to Cassandra (if available)
        if CASSANDRA_AVAILABLE:
            try:
                cassandra_session.execute(
                    '''
                    INSERT INTO comments (comment_id, post_id, commenter, comment, created_at)
                    VALUES (uuid(), %s, %s, %s, %s)
                    ''',
                    (str(post_id), comment_data['commenter'], comment_data['comment'],
                     comment_data['created_at'])
                )
            except Exception as e:
                print(f'Cassandra comment write failed: {e}')

        return redirect(url_for('post_detail', post_id=post_id))
    except Exception as e:
        print(f'Error adding comment: {e}')
        return redirect(url_for('post_detail', post_id=post_id))


# API endpoint for author statistics from stored collection
@app.route('/api/author-stats')
def author_stats():
    """
    Get author statistics from author_stats collection (STORED IN DB)
    Returns post count per author that's maintained in the database.
    """
    author_counts = get_author_post_counts_from_db()
    return jsonify(author_counts)


# API endpoint to verify double writes
@app.route('/api/stats')
def stats():
    """Get statistics about the databases (MongoDB and Cassandra)"""
    stats_data = {
        'mongodb': {
            'posts': posts_collection.count_documents({}),
            'comments': comments_collection.count_documents({})
        },
        'cassandra': {
            'posts': 0,
            'comments': 0
        }
    }

    if CASSANDRA_AVAILABLE:
        try:
            stats_data['cassandra']['posts'] = cassandra_session.execute('SELECT COUNT(*) FROM posts').one()[0]
            stats_data['cassandra']['comments'] = cassandra_session.execute('SELECT COUNT(*) FROM comments').one()[0]
        except Exception as e:
            stats_data['cassandra']['error'] = str(e)

    return jsonify(stats_data)


if __name__ == '__main__':
    app.run(debug=True)
