"""
This stores the classes used for the text mining project.
"""

import os
import requests
import re

contractions = {
    "aren't": "are not",
    "can't": "cannot",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "dont",       # Special case to not change; as in: why don't you do something doesn't translate well to why
    "hadn't": "had not",   #   do not you do something.
    "hasn't": "has not",
    "haven't": "have not",
    "he'd": "he would",
    "he'll": "he will",
    "he's": "he is",
    "i'd": 'i would',
    "i'll": "i will",
    "i'm": "i am",
    "i've": "i have",
    "isn't": "is not",
    "let's": "let us",
    "mightn't": "might not",
    "mustn't": "must not",
    "shan't": "shall not",
    "she'd": "she would",
    "she'll": "she will",
    "she's": "she is",
    "shouldn't": "should not",
    "that's": "that is",
    "there's": "there is",
    "they'd": "they would",
    "they'll": "they will",
    "they're": "they are",
    "they've": "they have",
    "we'd": "we would",
    "we're": "we are",
    "we've": "we have",
    "weren't": "were not",
    "what'll": "what will",
    "what're": "what are",
    "what's": "what is",
    "what've": "what have",
    "where's": "where is",
    "who'd": "who would",
    "who'll": "who will",
    "who're": "who are",
    "who's": "who is",
    "who've": "who have",
    "won't": "will not",
    "wouldn't": "would not",
    "you'd": "you would",
    "you'll": "you will",
    "you're": "you are",
    "you've": "you have"
}


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

        book_link_number = ''
        for i in range(1, len(book_number)):
            # generating the unique part of the download link for the book
            book_link_number = book_link_number + book_number[i - 1:i] + "/"
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

    def _make_tokens(self, truncate=0.01):
        """
        Tokenizes a book into a list of words and writes the data as text file
        (data is pickled).
        @param truncate: remove the first and last `truncate`% words from the book (to ignore things like the title,
         table of contents, chapters, etc.)
        """
        s = self.book_text
        s = s.lower()  # Convert to lowercases
        s = re.sub('\n', ' ', s)  # Replace \n with spaces
        # remove contractions
        for contraction in contractions:
            s = re.sub(contraction, contractions[contraction], s)
        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)  # Replace all non alphanumeric characters with spaces
        s = re.sub(' +', ' ', s)  # Replace series of spaces with single space

        self.tokens = s.split(" ")
        self.num_words = len(self.tokens)
        if truncate != 0.:
            truncate_amt = round(self.num_words * truncate)
            self.tokens = self.tokens[truncate_amt:-truncate_amt]

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
        for method_name in self.__class__.__dict__:
            if method_name[:5] == "_make":
                self.__class__.__dict__[method_name](self)

    def __str__(self):
        return "Book: {} | Book file: {} | Book token file: {} | Book hist file: {}".format(self.name_author,
                                                                                            self.path_to_book,
                                                                                            self.words_file_path,
                                                                                            self.hist_file_path)
