from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import traceback
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

app = Flask(__name__)
# Enable CORS for React frontend - allow both local and production domains
CORS(app, 
     origins=[
         "http://localhost:3000",
         "https://readarabic-react-dev-fc4e6ef30adb.herokuapp.com",  # dev
         "https://readarabic-react-main-cbf1b4fd8391.herokuapp.com",  # prod heroku
         "https://www.readarabic.io"  # prod custom domain
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# Turath.io API configuration
BASE_URL = 'https://files.turath.io/books-v3-unobfus'

# Database configuration - using DATABASE_URL for Heroku compatibility
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/readarabic')
# Heroku uses postgres:// but psycopg2 needs postgresql://
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def get_db_connection():
    """Create a database connection using DATABASE_URL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        traceback.print_exc()
        return None

def load_book(book_id: int):
    """Load a book from the source URL using its ID."""
    print(f"Loading book {book_id}")
    try:
        url = f"{BASE_URL}/{book_id}.json"
        response = requests.get(url)
        if response.status_code == 200:
            book_data = response.json()
            print(f"Successfully loaded book {book_id}")
            return book_data
        else:
            print(f"Failed to fetch book {book_id}, status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching book {book_id}: {e}")
        traceback.print_exc()
        return None

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all book categories."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT cat_id, category_name, 
                   (SELECT COUNT(*) FROM books_metadata WHERE cat_id = book_categories.cat_id) as book_count
            FROM book_categories
            ORDER BY category_name
        """)
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        print(f"Error fetching categories: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/authors', methods=['GET'])
def get_authors():
    """Get all authors."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT a.author_id, a.author_name, 
                   COUNT(bm.id) as book_count
            FROM authors a
            LEFT JOIN books_metadata bm ON bm.author_id = a.author_id
            GROUP BY a.author_id, a.author_name
            HAVING COUNT(bm.id) > 0
            ORDER BY a.author_name
        """)
        authors = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'authors': authors
        })
    except Exception as e:
        print(f"Error fetching authors: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/books', methods=['GET'])
def list_books():
    """List books with optional filtering by category or search term."""
    try:
        cat_id = request.args.get('category', type=int)
        author_id = request.args.get('author', type=int)
        limit = request.args.get('limit', 10000, type=int)  # Set high default to fetch all books
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query based on filters
        query = """
            SELECT bm.id, bm.name, bm.type, bm.info, bm.version, 
                   bm.cat_id, bc.category_name,
                   bm.pdf_link, bm.pdf_size, bm.author_id
            FROM books_metadata bm
            LEFT JOIN book_categories bc ON bm.cat_id = bc.cat_id
            WHERE 1=1
        """
        params = []
        
        if cat_id:
            query += " AND bm.cat_id = %s"
            params.append(cat_id)
        
        if author_id:
            query += " AND bm.author_id = %s"
            params.append(author_id)
        
        query += " ORDER BY bm.id ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        books = cursor.fetchall()
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM books_metadata bm WHERE 1=1"
        count_params = []
        if cat_id:
            count_query += " AND bm.cat_id = %s"
            count_params.append(cat_id)
        if author_id:
            count_query += " AND bm.author_id = %s"
            count_params.append(author_id)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'books': books,
            'count': len(books),
            'total': total,
            'offset': offset,
            'limit': limit
        })
    except Exception as e:
        print(f"Error fetching books: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/book/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Retrieve a specific book by ID"""
    try:
        book_data = load_book(book_id)
        
        if book_data is None:
            return jsonify({
                'success': False,
                'error': 'Book not found'
            }), 404
        
        return jsonify({
            'success': True,
            'book': book_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/define/<word>', methods=['GET'])
def define_word(word):
    """Get word definition from AraTools API"""
    try:
        print(f"\n{'='*60}")
        print(f"WORD DEFINITION REQUEST")
        print(f"{'='*60}")
        print(f"Selected word: {word}")
        
        # AraTools API endpoint
        api_url = f"https://aratools.com/api/v1/dictionary/lookup/ar/{word}"
        print(f"API URL: {api_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Calling AraTools API...")
        response = requests.get(api_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        print(f"AraTools Response Status: {response.status_code}")
        print(f"Raw response keys: {list(data.keys())}")
        print(f"Definitions found: {len(data.get('words', []))}")
        print(f"Response Data:")
        print(f"{'-'*60}")
        if 'words' in data and data['words']:
            print(f"\nFormatted definitions:")
            for idx, result in enumerate(data['words'], 1):
                form = result.get('voc_form', result.get('form', 'N/A'))
                gloss = result.get('nice_gloss', 'N/A')
                root = result.get('root')
                if root and isinstance(root, str):
                    root = '-'.join(root)
                else:
                    root = ''
                print(f"{idx}. Form: {form}")
                print(f"   Gloss: {gloss}")
                if root:
                    print(f"   Root: {root}")
                print()
        else:
            print(f"\nNo words found in response")
        print(f"{'-'*60}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'word': word,
            'definition': data
        })
    except requests.exceptions.Timeout:
        print(f"ERROR: Request timeout for word '{word}'")
        return jsonify({
            'success': False,
            'error': 'Request timeout - AraTools API did not respond in time'
        }), 504
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request exception for word '{word}': {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch definition: {str(e)}'
        }), 500
    except Exception as e:
        print(f"ERROR: Unexpected error for word '{word}': {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auth/google/callback', methods=['POST'])
def google_auth_callback():
    """Exchange Google OAuth code for user info"""
    print("\n=== GOOGLE AUTH CALLBACK ===")
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        code = data.get('code')
        redirect_uri = data.get('redirect_uri')
        print(f"Code: {code[:20]}... Redirect URI: {redirect_uri}")
        
        if not code:
            return jsonify({
                'success': False,
                'error': 'No authorization code provided'
            }), 400
        
        # Exchange code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        print(f"Token response: {token_json}")
        
        if 'error' in token_json:
            print(f"Token error: {token_json}")
            return jsonify({
                'success': False,
                'error': token_json.get('error_description', 'Token exchange failed')
            }), 400
        
        # Get user info using access token
        access_token = token_json.get('access_token')
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        # Get user details
        google_id = userinfo.get('id')
        email = userinfo.get('email')
        name = userinfo.get('name', '')
        profile_picture = userinfo.get('picture', '')
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Insert or update user
        cursor.execute("""
            INSERT INTO users (google_id, email, name, profile_picture)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (google_id) 
            DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                profile_picture = EXCLUDED.profile_picture
            RETURNING id, google_id, email, name, profile_picture, created_at
        """, (google_id, email, name, profile_picture))
        
        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'user': dict(user)
        })
        
    except Exception as e:
        print(f"Error in Google auth callback: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary', methods=['POST'])
def save_vocabulary():
    """Save a word to user's vocabulary"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        word = data.get('word')
        translation = data.get('translation')
        book_id = data.get('book_id')
        page_number = data.get('page_number')
        volume_number = data.get('volume_number')
        word_position = data.get('word_position')
        
        if not user_id or not word or not translation:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user has active subscription
        cursor.execute("""
            SELECT COUNT(*) as sub_count FROM subscriptions 
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
        
        sub_result = cursor.fetchone()
        has_subscription = sub_result['sub_count'] > 0
        
        # If no subscription, check vocabulary count
        if not has_subscription:
            cursor.execute("""
                SELECT COUNT(*) as vocab_count FROM user_vocabulary WHERE user_id = %s
            """, (user_id,))
            
            vocab_result = cursor.fetchone()
            vocab_count = vocab_result['vocab_count']
            
            print(f"🔍 User {user_id} - No subscription - Vocab count: {vocab_count}")
            
            # Check if this exact entry already exists (updates are allowed)
            cursor.execute("""
                SELECT id FROM user_vocabulary 
                WHERE user_id = %s AND word = %s AND book_id = %s AND page_number = %s AND word_position = %s
            """, (user_id, word, book_id, page_number, word_position))
            
            existing = cursor.fetchone()
            
            print(f"🔍 Word '{word}' - Existing entry: {existing is not None}")
            
            # Block if they have 5+ words and this is a new entry
            if vocab_count >= 5 and not existing:
                print(f"🚫 BLOCKING: User has {vocab_count} words and this is a NEW entry")
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'FREE_LIMIT_REACHED',
                    'message': 'Free tier limited to 5 words. Please upgrade to continue.',
                    'vocab_count': vocab_count
                }), 403
        
        # Insert or update vocabulary
        cursor.execute("""
            INSERT INTO user_vocabulary (user_id, word, translation, book_id, page_number, volume_number, word_position)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, word, book_id, page_number, word_position) 
            DO UPDATE SET 
                translation = EXCLUDED.translation,
                learned_at = CURRENT_TIMESTAMP
            RETURNING id, word, translation, learned_at
        """, (user_id, word, translation, book_id, page_number, volume_number, word_position))
        
        vocab = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vocabulary': dict(vocab)
        })
        
    except Exception as e:
        print(f"Error saving vocabulary: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary/<int:user_id>/recent-books', methods=['GET'])
def get_recent_books(user_id):
    """Get recently read books based on user's vocabulary"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get unique book IDs with most recent learned_at, ordered by recency
        query = """
            SELECT uv.book_id,
                   bm.id, bm.name, bm.type, bm.info, bm.version, 
                   bm.cat_id, bc.category_name,
                   MAX(uv.learned_at) as last_read
            FROM user_vocabulary uv
            JOIN books_metadata bm ON uv.book_id = bm.id
            LEFT JOIN book_categories bc ON bm.cat_id = bc.cat_id
            WHERE uv.user_id = %s
            GROUP BY uv.book_id, bm.id, bm.name, bm.type, bm.info, 
                     bm.version, bm.cat_id, bc.category_name
            ORDER BY last_read DESC
            LIMIT 5
        """
        
        cursor.execute(query, (user_id,))
        books = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'books': books
        })
        
    except Exception as e:
        print(f"Error fetching recent books: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary/<int:user_id>', methods=['GET'])
def get_vocabulary(user_id):
    """Get user's vocabulary, optionally filtered by book"""
    try:
        book_id = request.args.get('book_id', type=int)
        print(f"\n=== GET VOCABULARY ===")
        print(f"User ID: {user_id}")
        print(f"Book ID: {book_id}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, word, translation, book_id, page_number, volume_number, word_position, learned_at
            FROM user_vocabulary
            WHERE user_id = %s
        """
        params = [user_id]
        
        if book_id:
            query += " AND book_id = %s"
            params.append(book_id)
        
        query += " ORDER BY learned_at DESC"
        
        cursor.execute(query, params)
        vocabulary = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"Found {len(vocabulary)} vocabulary items")
        
        return jsonify({
            'success': True,
            'vocabulary': vocabulary
        })
        
    except Exception as e:
        print(f"Error fetching vocabulary: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary/<int:vocab_id>', methods=['PUT'])
def update_vocabulary(vocab_id):
    """Update vocabulary translation"""
    try:
        data = request.get_json()
        translation = data.get('translation')
        
        if not translation:
            return jsonify({
                'success': False,
                'error': 'Translation is required'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        
        # Update translation
        cursor.execute("""
            UPDATE user_vocabulary
            SET translation = %s
            WHERE id = %s
        """, (translation, vocab_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Translation updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating vocabulary: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary/due/<int:user_id>', methods=['GET'])
def get_due_vocabulary(user_id):
    """Get vocabulary words that are due for review"""
    try:
        book_id = request.args.get('book_id', type=int)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get words due for review (next_review_date <= now)
        query = """
            SELECT id, word, translation, book_id, page_number, volume_number, word_position,
                   easiness_factor, next_review_date, review_count, correct_count, incorrect_count
            FROM user_vocabulary
            WHERE user_id = %s AND next_review_date <= NOW()
        """
        params = [user_id]
        
        if book_id:
            query += " AND book_id = %s"
            params.append(book_id)
        
        query += " ORDER BY next_review_date ASC"
        
        cursor.execute(query, params)
        due_words = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vocabulary': due_words,
            'count': len(due_words)
        })
        
    except Exception as e:
        print(f"Error fetching due vocabulary: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vocabulary/<int:vocab_id>/review', methods=['PUT'])
def update_vocabulary_review(vocab_id):
    """Update vocabulary review statistics after practice"""
    try:
        data = request.get_json()
        correct = data.get('correct', False)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch current vocabulary item
        cursor.execute("""
            SELECT easiness_factor, review_count, correct_count, incorrect_count
            FROM user_vocabulary
            WHERE id = %s
        """, (vocab_id,))
        
        vocab = cursor.fetchone()
        if not vocab:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Vocabulary item not found'
            }), 404
        
        # Spaced repetition algorithm
        easiness = float(vocab['easiness_factor']) if vocab['easiness_factor'] else 2.5
        review_count = vocab['review_count'] or 0
        correct_count = vocab['correct_count'] or 0
        incorrect_count = vocab['incorrect_count'] or 0
        
        if correct:
            correct_count += 1
            easiness = max(1.3, easiness + 0.1)  # Increase easiness
            
            # Calculate next review interval
            if review_count == 0:
                interval_days = 1
            elif review_count == 1:
                interval_days = 3
            elif review_count == 2:
                interval_days = 7
            else:
                interval_days = int(7 * (easiness ** (review_count - 2)))
            
            review_count += 1
        else:
            incorrect_count += 1
            easiness = max(1.3, easiness - 0.2)  # Decrease easiness
            interval_days = 1  # Reset to 1 day
            review_count = 0  # Reset review count
        
        # Calculate next review date
        from datetime import datetime, timedelta
        next_review = datetime.now() + timedelta(days=interval_days)
        
        # Update database
        cursor.execute("""
            UPDATE user_vocabulary
            SET easiness_factor = %s,
                next_review_date = %s,
                review_count = %s,
                correct_count = %s,
                incorrect_count = %s
            WHERE id = %s
        """, (easiness, next_review, review_count, correct_count, incorrect_count, vocab_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'interval_days': interval_days,
            'next_review_date': next_review.isoformat()
        })
        
    except Exception as e:
        print(f"Error updating vocabulary review: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/subscription/status/<int:user_id>', methods=['GET'])
def get_subscription_status(user_id):
    """Get user's subscription status"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get active or cancelled subscription that's still valid
        cursor.execute("""
            SELECT id, subscription_type, status, amount, currency,
                   started_at, expires_at, next_billing_date, cancelled_at,
                   (SELECT COUNT(DISTINCT word) FROM user_vocabulary WHERE user_id = %s) as vocab_count
            FROM subscriptions
            WHERE user_id = %s 
              AND (status = 'active' OR (status = 'cancelled' AND expires_at > NOW()))
            ORDER BY started_at DESC
            LIMIT 1
        """, (user_id, user_id))
        
        subscription = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if subscription:
            return jsonify({
                'success': True,
                'subscription': dict(subscription),
                'is_premium': True
            })
        else:
            # Free tier
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT COUNT(DISTINCT word) as vocab_count
                FROM user_vocabulary
                WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'subscription': None,
                'is_premium': False,
                'vocab_count': result['vocab_count'] if result else 0,
                'free_limit': 5
            })
    
    except Exception as e:
        print(f"Error fetching subscription status: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/subscription/create', methods=['POST'])
def create_subscription():
    """Create a new subscription after PayPal approval"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        subscription_type = data.get('subscription_type')  # 'monthly' or 'annual'
        paypal_subscription_id = data.get('paypal_subscription_id')
        paypal_plan_id = data.get('paypal_plan_id')
        
        if not all([user_id, subscription_type, paypal_subscription_id]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Set amount based on subscription type
        amount = 4.99 if subscription_type == 'monthly' else 49.99
        
        # Calculate expiration date
        from datetime import datetime, timedelta
        started_at = datetime.now()
        if subscription_type == 'monthly':
            expires_at = started_at + timedelta(days=30)
            next_billing = started_at + timedelta(days=30)
        else:
            expires_at = started_at + timedelta(days=365)
            next_billing = started_at + timedelta(days=365)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user already has a subscription (active or cancelled)
        cursor.execute("""
            SELECT id FROM subscriptions WHERE user_id = %s
        """, (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing subscription
            cursor.execute("""
                UPDATE subscriptions 
                SET subscription_type = %s, 
                    status = 'active', 
                    paypal_subscription_id = %s, 
                    paypal_plan_id = %s,
                    amount = %s, 
                    currency = 'USD', 
                    started_at = %s, 
                    expires_at = %s, 
                    next_billing_date = %s,
                    cancelled_at = NULL
                WHERE user_id = %s
                RETURNING id, subscription_type, status, amount, expires_at
            """, (subscription_type, paypal_subscription_id, paypal_plan_id, 
                  amount, started_at, expires_at, next_billing, user_id))
        else:
            # Insert new subscription
            cursor.execute("""
                INSERT INTO subscriptions 
                (user_id, subscription_type, status, paypal_subscription_id, paypal_plan_id, 
                 amount, currency, started_at, expires_at, next_billing_date)
                VALUES (%s, %s, 'active', %s, %s, %s, 'USD', %s, %s, %s)
                RETURNING id, subscription_type, status, amount, expires_at
            """, (user_id, subscription_type, paypal_subscription_id, paypal_plan_id, 
                  amount, started_at, expires_at, next_billing))
        
        subscription = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'subscription': dict(subscription)
        })
    
    except Exception as e:
        print(f"Error creating subscription: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/subscription/cancel/<int:user_id>', methods=['POST'])
def cancel_subscription(user_id):
    """Cancel user's active subscription"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Update subscription status to cancelled
        cursor.execute("""
            UPDATE subscriptions
            SET status = 'cancelled',
                cancelled_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND status = 'active'
            RETURNING id, subscription_type, status, cancelled_at
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'subscription': dict(result)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No active subscription found'
            }), 404
    
    except Exception as e:
        print(f"Error cancelling subscription: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ReadArabic PDF Backend'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
