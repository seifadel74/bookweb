import os
import requests
import time

def download_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)

def get_openlibrary_cover(title, author):
    # Search OpenLibrary API
    search_url = f"https://openlibrary.org/search.json?title={title}&author={author}"
    response = requests.get(search_url)
    if response.status_code == 200:
        data = response.json()
        if data.get('docs') and len(data['docs']) > 0:
            cover_id = data['docs'][0].get('cover_i')
            if cover_id:
                return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    return None

# Create the book_covers directory if it doesn't exist
covers_dir = os.path.join('static', 'book_covers')
os.makedirs(covers_dir, exist_ok=True)

# List of books to download covers for
books = [
    {"title": "Pride and Prejudice", "author": "Jane Austen", "filename": "pride_prejudice.jpg"},
    {"title": "The Hobbit", "author": "Tolkien", "filename": "hobbit.jpg"},
    {"title": "Dune", "author": "Frank Herbert", "filename": "dune.jpg"},
    {"title": "The Silent Patient", "author": "Alex Michaelides", "filename": "silent_patient.jpg"},
    {"title": "Project Hail Mary", "author": "Andy Weir", "filename": "hail_mary.jpg"},
    {"title": "The Midnight Library", "author": "Matt Haig", "filename": "midnight_library.jpg"},
    {"title": "Mexican Gothic", "author": "Silvia Moreno-Garcia", "filename": "mexican_gothic.jpg"},
    {"title": "The Seven Husbands of Evelyn Hugo", "author": "Taylor Jenkins Reid", "filename": "evelyn_hugo.jpg"},
    {"title": "Atomic Habits", "author": "James Clear", "filename": "atomic_habits.jpg"},
    {"title": "Six of Crows", "author": "Leigh Bardugo", "filename": "six_of_crows.jpg"},
    {"title": "The Thursday Murder Club", "author": "Richard Osman", "filename": "thursday_club.jpg"},
    {"title": "The Invisible Life of Addie LaRue", "author": "V.E. Schwab", "filename": "addie_larue.jpg"},
    {"title": "Klara and the Sun", "author": "Kazuo Ishiguro", "filename": "klara_sun.jpg"},
    {"title": "The Paris Apartment", "author": "Lucy Foley", "filename": "paris_apartment.jpg"},
    {"title": "Beach Read", "author": "Emily Henry", "filename": "beach_read.jpg"}
]

# Download each cover
for book in books:
    filepath = os.path.join(covers_dir, book['filename'])
    if not os.path.exists(filepath):
        print(f"Downloading cover for {book['title']}...")
        cover_url = get_openlibrary_cover(book['title'], book['author'])
        if cover_url:
            try:
                download_image(cover_url, filepath)
                print(f"Downloaded cover for {book['title']}")
                # Be nice to the API
                time.sleep(1)
            except Exception as e:
                print(f"Error downloading cover for {book['title']}: {e}")
        else:
            print(f"No cover found for {book['title']}")
    else:
        print(f"Skipping {book['filename']} (already exists)") 