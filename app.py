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
CORS(app)  # Enable CORS for React frontend

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# Turath.io API configuration
BASE_URL = 'https://files.turath.io/books-v3-unobfus'

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'readarabic'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', '5432')
}

def get_db_connection():
    """Create a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ReadArabic PDF Backend'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
