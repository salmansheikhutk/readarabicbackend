-- Users table for Google OAuth authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    profile_picture TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User vocabulary/learning words
CREATE TABLE IF NOT EXISTS user_vocabulary (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word VARCHAR(255) NOT NULL,
    translation TEXT,
    book_id INTEGER REFERENCES books_metadata(id) ON DELETE SET NULL,
    page_number INTEGER,
    volume_number INTEGER,
    word_position INTEGER,
    learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_vocabulary_unique_word UNIQUE (user_id, word, book_id, page_number, word_position)
);

-- Reading history - track current position in books
CREATE TABLE IF NOT EXISTS reading_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books_metadata(id) ON DELETE CASCADE,
    current_page INTEGER DEFAULT 0,
    current_volume INTEGER DEFAULT 1,
    last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reading_history_unique UNIQUE (user_id, book_id)
);

-- Indexes
CREATE INDEX idx_user_vocabulary_user_book ON user_vocabulary(user_id, book_id);
CREATE INDEX idx_reading_history_user_id ON reading_history(user_id);
CREATE INDEX idx_users_google_id ON users(google_id);
