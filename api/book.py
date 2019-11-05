"""
This stores the classes used for the text mining project.
"""

import os
import requests


class InvalidBookError(Exception):
    """Raised when the book could not be successfully acquired"""
    pass


class Book:
    """
    A book object stores all relevant information about the book (identified by
    name_author) and provides methods for processing each book's data.

    All attributes:
    self.name_author - "Book Title, by Author Name"
    self.path_to_book - "books/path_to_book_text_file"
    self.words_file_path - "books/path_to_the_book_token_file.txt"
    self.words - book parsed into a list of words
    self.hist_file_path - "books/path_to_the_hist_file.txt"
    self.hist - histogram of book's word usage
    """

    def __init__(self, name_author, gutenberg_index_dict, override_existing_download=False, do_make_book=True):
        """
        Downloads the book from project gutenberg if the book is in
        gutenberg_index. The link to the book is generated from the book's
        associated number in the gutenberg_index, and is downloaded as a text
        file. Returns False if the book couldn't be downloaded or already was
        downloaded (and override_existing_download == False), returns true if
        the book was successfully downloaded.
        """
        self.name_author = name_author
        self.tokens = []
        self.book_text = ""
        self.num_words = 0
        self.path_to_book = os.path.join("cache", "books", self.name_author + ".txt")
        self.start_indicator = "*** START OF"
        self.end_indicator = " ***\n"

        if os.path.exists(self.path_to_book):  # Check if the book already exists and override it if indicated.
            print("Book file already exists")
            if override_existing_download:
                print("Overriding existing download: deleting {}".format(self.path_to_book))
                os.remove(self.path_to_book)
            else:
                book_file = open(self.path_to_book, 'r')
                self.book_text = book_file.read()
                book_file.close()
        else:  # download book
            self.download_book(gutenberg_index_dict)  # populates self.book_text

        if do_make_book:
            self.make_book(gutenberg_index_dict)

    def download_book(self, gutenberg_index_dict):
        book_number = gutenberg_index_dict.get(self.name_author)
        if book_number is None:
            print("Book name/author not in the index.")
            raise InvalidBookError

        # TODO: improve
        book_link_number = book_number + "/"
        for i in range(1, len(book_number)):
            # generating the unique part of the download link for the book
            book_link_number += book_number[i - 1:i] + "/"
        book_link_number = book_link_number + book_number + "/" + book_number + ".txt"

        try:
            print("Downloading {}".format(self.name_author))
            self.book_text = requests.get("http://mirrors.xmission.com/gutenberg/{}".format(book_link_number)).text
            if self.book_text[0:6] == "<html>":  # some links require a different format which is handled below
                book_link_number = book_link_number[0:len(book_link_number) - 4] + "-0.txt"
                self.book_text = requests.get("http://mirrors.xmission.com/gutenberg/{}".format(book_link_number)).text
        except requests.exceptions.MissingSchema:
            print("Invalid url / could not download from this link")
            raise InvalidBookError

        try:  # if the text has an indicator of where the book starts, this will cut off the header
            self.book_text = self.book_text.split(self.start_indicator, 1)[1]
        except IndexError:
            pass

        try:  # if the text has an indicator of where the book ends, this will cut off the part following the end
            self.book_text = self.book_text.split(self.end_indicator, 1)[0]
        except IndexError:
            pass

        book_file = open(self.path_to_book, 'w')
        book_file.write(self.book_text)
        book_file.close()
        print("Successfully downloaded {} and wrote to file".format(self.name_author))

    def tokenize_book(self):
        """
        Tokenizes a book into a list of words and writes the data as text file
        (data is pickled).
        """
        # TODO: populate self.tokens
        pass

    def _make_hist(self):
        """
        Makes a hist (in the form of a dictionary) of word frequency usage
        for the book. Pickles and writes the data to a text file.
        """
        # TODO: make histogram of book
        pass


    def make_book(self, gutenberg_index):
        """
        Runs all methods that begin with _make
        """
        self.tokenize_book()
        for method_name in self.__class__.__dict__:
            if method_name[:5] == "_make":
                self.__class__.__dict__[method_name](self)

    def __str__(self):
        return "Book: {} | Book file: {} | Book token file: {} | Book hist file: {}".format(self.name_author,
            self.path_to_book, self.words_file_path, self.hist_file_path)
