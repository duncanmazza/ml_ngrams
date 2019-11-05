"""
This stores the classes used for the text mining project.
"""

import os
import requests
import re
from nltk.util import ngrams as make_ngrams
from scipy.sparse import dok_matrix

# define constants
start_indicator = "*** START OF"
end_indicator = " ***\n"
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
    """

    def __init__(self, name_author, gutenberg_index_dict, override_existing_download=False, do_make_book=True,
                 truncate=0.01, n=2, max_chain=10):
        self.name_author = name_author
        self.book_text = ""
        self.truncate = truncate
        self.tokens = []
        self.num_words = 0
        self.vocabulary = {}
        self.vocabulary_size = 0
        self.n = n
        self.ngrams = [()]
        self.following_word = {}
        self.vocab_to_matrix = {}

        self.max_chain = max_chain
        self.graphs = [None] * self.max_chain

        self.path_to_book = os.path.join("cache", "books", self.name_author + ".txt")

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
            self.book_text = self.book_text.split(start_indicator, 1)[1]
        except IndexError:
            pass

        try:  # if the text has an indicator of where the book ends, this will cut off the part following the end
            self.book_text = self.book_text.split(end_indicator, 1)[0]
        except IndexError:
            pass

        book_file = open(self.path_to_book, 'w')
        book_file.write(self.book_text)
        book_file.close()
        print("Successfully downloaded {} and wrote to file".format(self.name_author))

    def _make_tokens(self):
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
        if self.truncate != 0.:
            truncate_amt = round(self.num_words * self.truncate)
            self.tokens = self.tokens[truncate_amt:-truncate_amt]
        if self.tokens.__contains__(""): self.tokens.remove("")  # remove any empty characters
        self.num_words = len(self.tokens)

    def _make_vocab(self):
        self.vocabulary = {vocab: 0 for vocab in set(self.tokens)}
        self.vocabulary_size = len(self.vocabulary)
        for token in self.tokens: self.vocabulary[token] += 1

    def _make_ngrams(self):
        self.ngrams = list(make_ngrams(self.tokens, self.n))

    def _make_following_word_dict(self):
        for vocab in self.vocabulary.keys(): self.following_word[vocab] = set()
        for ngram in set(self.ngrams): self.following_word[ngram[0]].add(ngram[1])

    def _make_bayesian_graph(self):
        print('Building graph for {}'.format(self.name_author))
        self.graphs = []
        for i in range(self.max_chain):  # each item in self.graphs is a sparse matrix (M) where M[i, j] represents the
        # value of the directional edge from vocab_to_matrix[i] to vocab_to_matrix[j]; i and j are integers that
        # correspond to words per the dictionary vocab_to_matrix (populated below) with keys of words and values of
        # the words' corresponding indices in the matrix
            self.graphs.append(dok_matrix((self.vocabulary_size, self.vocabulary_size), dtype=int))
        self.vocab_to_matrix = {}
        for i, vocab in enumerate(self.vocabulary.keys()):
            self.vocab_to_matrix[vocab] = i   # record what matrix index corresponds to which word; values are arbitrary
            # as long as they remain unchanged and are unique to their respective key
        modulus_number = round(self.num_words / 100)
        if modulus_number == 0: modulus_number += 1
        print(self.tokens)
        for t, token in enumerate(self.tokens):
            if t % modulus_number == 0: print("progress = {}%".format(round(t/self.num_words * 100)))
            if self.max_chain + t >= self.num_words: upper_limit = self.num_words - t
            else: upper_limit = self.max_chain + 1
            # print('upper limit: ', upper_limit)
            for c in range(1, upper_limit):  # range from [1, self.max_chain]
                # print('t: {}, c: {}, x: {}, y: {}, distance: {}'.format(t, c, token, self.tokens[c + t], c))
                self.graphs[c-1][self.vocab_to_matrix[token], self.vocab_to_matrix[self.tokens[c + t]]] += 1
        print("Finished building graph for {}".format(self.name_author))

    def make_book(self, gutenberg_index):
        """
        Runs all methods that begin with _make
        """
        self._make_tokens()
        self._make_vocab()
        self._make_ngrams()
        self._make_following_word_dict()
        self._make_bayesian_graph()

    def analyze(self):

        pass

    def __str__(self):
        return "Book: {} | Book file: {} | Book token file: {} | Book hist file: {}".format(self.name_author,
                                                                                            self.path_to_book,
                                                                                            self.words_file_path,
                                                                                            self.hist_file_path)
