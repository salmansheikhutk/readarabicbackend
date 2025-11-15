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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ReadArabic PDF Backend'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
