"""
This software will take a list of books (book_list) and automatically find,
download, and generate all associated files for the books.
"""

from api.librarian import Librarian

book_list = [
    ('Frankenstein, by Mary Wollstonecraft (Godwin) Shelley'),
    ('Watersprings, by Arthur Christopher Benson'),
]

if __name__ == "__main__":
    # TODO: add an argument parser

    # acquire books from the book list
    librarian = Librarian(book_list)
