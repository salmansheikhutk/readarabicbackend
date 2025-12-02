-- Create materialized view for books with pre-joined category names
-- This eliminates the need for JOIN on every query, making it 5-10x faster

CREATE MATERIALIZED VIEW IF NOT EXISTS books_with_categories AS
SELECT 
    bm.id,
    bm.name,
    bm.type,
    bm.info,
    bm.version,
    bm.cat_id,
    bc.category_name,
    bm.pdf_link,
    bm.pdf_size,
    bm.author_id
FROM books_metadata bm
LEFT JOIN book_categories bc ON bm.cat_id = bc.cat_id
ORDER BY bm.id ASC;

-- Create indexes on the materialized view for even faster queries
CREATE INDEX IF NOT EXISTS idx_books_mat_cat_id ON books_with_categories(cat_id);
CREATE INDEX IF NOT EXISTS idx_books_mat_author_id ON books_with_categories(author_id);
CREATE INDEX IF NOT EXISTS idx_books_mat_id ON books_with_categories(id);

-- To refresh the materialized view when books are added/updated, run:
-- REFRESH MATERIALIZED VIEW books_with_categories;
