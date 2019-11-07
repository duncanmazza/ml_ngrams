"""
This software will take a list of books (book_list) and automatically find,
download, and generate all associated files for the books.
"""

from api.librarian import Librarian

book_list = (
    ('Frankenstein', 'Mary Wollstonecraft (Godwin) Shelley'),
    # ('Watersprings', 'Arthur Christopher Benson')
    # ... any other book in Project Gutenberg
)

if __name__ == "__main__":
    # acquire books from the book list
    librarian = Librarian(book_list, global_truncate=0.4, global_alpha=1, global_max_chain=2)
    while True:
        for book_name in librarian.acquired_books:
            book = librarian.acquired_books[book_name]
            print("Applying naive bayes to: {}".format(book_name))
            book.apply_naive_bayes(extend_by=15)

        print('Generate another sample? (y or Y) -> ')
        while True:
            i = input()
            if i == "y" or "Y":
                break