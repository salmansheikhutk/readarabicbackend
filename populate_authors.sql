-- Create authors table
CREATE TABLE IF NOT EXISTS authors (
    author_id INT PRIMARY KEY,
    author_name TEXT NOT NULL
);

-- Extract and insert authors from books_metadata
INSERT INTO authors (author_id, author_name)
SELECT DISTINCT ON (author_id)
    bm.author_id,
    TRIM(SPLIT_PART(SUBSTRING(bm.info FROM 'المؤلف:[^\n]+'), ':', 2)) as author_name
FROM books_metadata bm
WHERE bm.author_id IS NOT NULL 
  AND bm.info LIKE '%المؤلف:%'
  AND TRIM(SPLIT_PART(SUBSTRING(bm.info FROM 'المؤلف:[^\n]+'), ':', 2)) != ''
ON CONFLICT (author_id) DO NOTHING;
