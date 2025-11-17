from flask import Flask, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Turath.io API configuration
BASE_URL = 'https://files.turath.io/books-v3-unobfus'

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

@app.route('/api/books', methods=['GET'])
def list_books():
    """List available books (only book 10)"""
    try:
        book_id = 10
        book_data = load_book(book_id)
        
        books = []
        if book_data:
            # Extract title from meta
            title = book_data.get('meta', {}).get('name', f'Book {book_id}')
            # Extract author info if available
            author_info = book_data.get('meta', {}).get('info', '')
            author = 'Unknown'
            if 'مؤلف' in author_info or 'المؤلف' in author_info:
                # Try to extract author name from info field
                lines = author_info.split('\n')
                for line in lines:
                    if 'مؤلف' in line or 'المؤلف' in line:
                        author = line.split(':')[-1].strip() if ':' in line else line.strip()
                        break
            
            books.append({
                'id': book_id,
                'title': title,
                'author': author,
                'url': f'/api/book/{book_id}'
            })
        
        return jsonify({
            'success': True,
            'books': books,
            'count': len(books)
        })
    except Exception as e:
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ReadArabic PDF Backend'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
