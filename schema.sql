-- Create book_categories table
CREATE TABLE IF NOT EXISTS book_categories (
    cat_id INT PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL
);

-- Create books_metadata table
CREATE TABLE IF NOT EXISTS books_metadata (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type INT NOT NULL,
    printed INT NOT NULL,
    info TEXT,
    version VARCHAR(10),
    author_id INT,
    cat_id INT,
    date_built BIGINT,
    author_page_start INT,
    pdf_link TEXT,
    pdf_size BIGINT,
    cover_id INT,
    CONSTRAINT fk_category FOREIGN KEY (cat_id) REFERENCES book_categories(cat_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_books_cat_id ON books_metadata(cat_id);
CREATE INDEX IF NOT EXISTS idx_books_name ON books_metadata(name);

-- Insert some sample categories (you can modify these)
INSERT INTO book_categories (cat_id, category_name) VALUES
(1, 'الفقه'),
(2, 'الحديث'),
(3, 'التفسير'),
(4, 'العقيدة'),
(5, 'السيرة'),
(6, 'اللغة العربية'),
(7, 'التاريخ'),
(8, 'الأدب')
ON CONFLICT (cat_id) DO NOTHING;

-- Create authors table
CREATE TABLE IF NOT EXISTS authors (
    author_id INT PRIMARY KEY,
    author_name TEXT NOT NULL,
    author_name_ar TEXT,
    death_year INT,
    bio TEXT
);

-- Create index for faster author lookups
CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(author_name);

-- If you have a CSV or data file, you can populate authors like this:
-- Example: Extract unique authors from books_metadata.info field
-- This SQL will help you create the authors table data:

/*
To populate the authors table from your existing books_metadata:

1. First, extract author names from the info field:
   SELECT DISTINCT 
       author_id,
       SUBSTRING(info FROM 'المؤلف:\s*(.+?)(?:\n|\[|$)') as author_name
   FROM books_metadata
   WHERE info LIKE '%المؤلف:%'
   ORDER BY author_id;

2. Then insert into authors table:
   INSERT INTO authors (author_id, author_name)
   SELECT DISTINCT 
       author_id,
       TRIM(SUBSTRING(info FROM 'المؤلف:\s*(.+?)(?:\n|\[|$)'))
   FROM books_metadata
   WHERE info LIKE '%المؤلف:%' 
   AND author_id IS NOT NULL
   ON CONFLICT (author_id) DO UPDATE 
   SET author_name = EXCLUDED.author_name;
*/

-- Insert sample book (Book ID 10 from Turath.io)
INSERT INTO books_metadata (id, name, type, printed, info, cat_id) VALUES
(10, 'صحيح البخاري', 1, 1, 'الجامع المسند الصحيح المختصر من أمور رسول الله صلى الله عليه وسلم وسننه وأيامه', 2)
ON CONFLICT (id) DO NOTHING;
