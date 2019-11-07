"""
This stores the classes used for the text mining project.
"""

import os
import requests
import re
from scipy.sparse import dok_matrix
import numpy as np
import matplotlib.pyplot as plt

# define constants
start_indicator = "*** START OF"
end_indicator = " ***\n"
contractions = {
    "aren't": "are not",
    "can't": "cannot",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "dont",  # Special case to not change; as in: why don't you do something doesn't translate well to why
    "hadn't": "had not",  # do not you do something.
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
                 truncate=0.01, n=2, max_chain=10, alpha=1):
        self.name_author = name_author
        self.book_text = ""
        self.truncate = truncate
        self.tokens = []
        self.num_words = 0
        self.vocabulary_size = 0
        self.n = n
        self.alpha = alpha
        self.max_chain = max_chain
        self.graphs = [None] * self.max_chain

        self.vocabulary = dict()
        self.following_word = dict()
        self.vocab_to_matrix = dict()
        self.sum_w_d_p_list_s_cache = dict()

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

        # if the text has an indicator of where the book starts, this will cut off the header
        if self.book_text.__contains__(start_indicator):
            self.book_text= self.book_text.split(start_indicator, 1)[1]

        # if the text has an indicator of where the book ends, this will cut off the part following the end
        if self.book_text.__contains__(end_indicator):
            self.book_text = self.book_text.split(end_indicator, 1)[0]


        book_file = open(self.path_to_book, 'w')
        book_file.write(self.book_text)
        book_file.close()
        print("Successfully downloaded {} and wrote to file".format(self.name_author))

    @staticmethod
    def _parse(s):
        s = s.lower()  # Convert to lowercases
        s = re.sub('\n', ' ', s)  # Replace \n with spaces
        # remove contractions
        for contraction in contractions:
            s = re.sub(contraction, contractions[contraction], s)
        s = re.sub("'", '', s)  # delete all apostrophes
        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)  # Replace all non alphanumeric characters with spaces
        s = re.sub(' +', ' ', s)  # Replace series of spaces with single space
        return s.split(" ")

    def _make_tokens(self):
        """
        Tokenizes a book into a list of words and writes the data as text file
        (data is pickled).
        @param truncate: remove the first and last `truncate`% words from the book (to ignore things like the title,
         table of contents, chapters, etc.)
        """
        s = self.book_text
        self.tokens = self._parse(s)
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

    def _make_following_word_dict(self):
        for vocab in self.vocabulary.keys(): self.following_word[vocab] = set()
        for t in range(self.num_words-1): self.following_word[self.tokens[t]].add(self.tokens[t+1])

    def _make_bayesian_graphs(self):
        """
        Build the list of bayesian graphs, where the graph at index i represents the directional graph between words in
        the text vector (self.tokens), where the nodes are vocabulary words and the directional edges are the number of
        occurrences of the parent node separated by the child node by distance i in the text.
        :return: void
        """
        print('Building graph for {}'.format(self.name_author))
        self.graphs = []
        for i in range(self.max_chain):
            self.graphs.append(dok_matrix((self.vocabulary_size, self.vocabulary_size), dtype=int))
        self.vocab_to_matrix = {}
        for i, vocab in enumerate(self.vocabulary.keys()): self.vocab_to_matrix[
            vocab] = i  # record what matrix index corresponds to which word; values are arbitrary as long as they
        # remain unchanged and are unique to their respective key

        for t, token in enumerate(self.tokens):

            # enable the last `self.max_chain` words in the text serve as the basis for the search window by shortening
            # the search window so that it doesn't overextend the list of words
            if not self.max_chain + t >= self.num_words:
                upper_limit = self.max_chain + 1
            else:
                upper_limit = self.num_words - t

            for c in range(1, upper_limit):  # iterate over search window
                self.graphs[c - 1][self.vocab_to_matrix[token], self.vocab_to_matrix[self.tokens[c + t]]] += 1
        print("Finished building graph for {}\n".format(self.name_author))

    def query_graph(self, d, _from, _to):
        """
        Returns the value of the directional edge from _from to _to in graph d, where d is the distance value associated
        with the graph. If there is no edge (an edge will exist if its value is >= 1), then 0 is returned
        :param d: distance
        :param _from: start node
        :param _to: end node
        :return: edge value
        """
        return self.graphs[d][self.vocab_to_matrix[_from], self.vocab_to_matrix[_to]]

    def make_book(self, gutenberg_index):
        """
        Runs all methods that begin with _make
        :return: void
        """
        self._make_tokens()
        self._make_vocab()
        self._make_following_word_dict()
        self._make_bayesian_graphs()

    def _p_s(self, _s):
        """
        Returns P(s)
        :param _s: word in book vocabulary
        :return: p(s) where p(s) = (number of occurances of s) / (number of words in book)
        """
        return self.vocabulary[_s] / self.num_words

    def _p_d_i_j(self, d, _p, _s, tuple_s):
        """
        Returns P^d(i, j)
        :param d: distance
        :param _p: previous word
        :param _j: suggested word
        :param tuple_s: tuple of all possible suggested words
        :return: (wight of graph d from _p to _s) / (sum of wights of graph d from _p to all list_s); if the denominator
         is 0, then return 0 to avoid dividing by 0
        """
        val_w_d_p_s = self.query_graph(d, _p, _s)
        # first, check caches for whether these values have already been queried
        val_sum_w_d_p_list_s = self.sum_w_d_p_list_s_cache.get((d, _p, tuple_s))
        if val_sum_w_d_p_list_s is None:
            val_sum_w_d_p_list_s = 0
            for _s_ in tuple_s: val_sum_w_d_p_list_s += self.query_graph(d, _p, _s_)
            self.sum_w_d_p_list_s_cache[
                (d, _p, tuple_s)] = val_sum_w_d_p_list_s  # store so that this calculation isn't redone
        if val_sum_w_d_p_list_s == 0:  # return 0 to avoid dividing by 0
            return 0
        else:
            return val_w_d_p_s / val_sum_w_d_p_list_s

    def generate_cond_prob_arr(self, tuple_s, list_p_forward):
        """
        :param tuple_s: list of unique suggested words (order is arbitrary but must be maintained so words can
         correspond to values in cond_prob_arr)
        :param list_p_rev: (ordered) list of previous words preceding suggested word
        :return: numpy array of length len(list_s_set) that contains the conditional probabilities
        """
        cond_prob_arr = np.zeros((len(tuple_s)))

        # calculate create an array that has the previous words in reverse order
        list_p_rev = [list_p_forward[p] for p in range(len(list_p_forward) - 1, -1, -1)]

        # iterate over the suggested words
        for j, _s in enumerate(tuple_s):
            prior_val = self._p_s(_s)
            likelihood_arr = np.ones((len(list_p_rev))) * self.alpha  # initialize with alpha value
            for i in range(len(list_p_rev)):
                likelihood_arr[i] += self._p_d_i_j(i, list_p_rev[i], _s, tuple_s)
            log_sum_likelihood_val = np.sum(np.log(likelihood_arr))  # TODO: divide by something for laplace smoothing?
            cond_prob_arr[j] = np.exp(np.log(prior_val + self.alpha) + log_sum_likelihood_val)

        return cond_prob_arr / np.sum(cond_prob_arr)  # normalize so values sum to 1

    def limit_s_to(self, length, list_s):
        len_list_s = len(list_s)
        if len_list_s > length:
            random_idx = np.random.randint(0, len_list_s - length, length)
            return list(np.array(list_s)[random_idx])
        else:
            return list_s

    def apply_naive_bayes(self, extend_by=20):
        starting_idx = np.random.randint(0, self.num_words - self.max_chain)
        seed = self.tokens[starting_idx:self.max_chain + starting_idx]
        actual_sentence = self.tokens[starting_idx:starting_idx + extend_by + self.max_chain]
        generated_sentence = seed.copy()
        i = 0
        while (i < extend_by):
            list_p_forward = generated_sentence[len(generated_sentence) - self.max_chain:]  # ascending
            # query all words that follow the most recent previous word in the text, and procure a simple random sample
            # of these suggested words if there are more than 100
            list_s = self.limit_s_to(1000, list(self.following_word[list_p_forward[-1]]))
            for prev_word in list_p_forward[-2:]:
                if list_s.__contains__(prev_word) and len(list_s) > 1: list_s.remove(prev_word)  # disallow a word to be
                # repeated  within the last two previous words, while ensuring that there are a nonzero number of
                # suggested words
            cond_prob_arr = self.generate_cond_prob_arr(tuple(list_s), list_p_forward)
            next_word = str(list_s[np.random.choice(np.array(range(0, len(list_s))), size=1, p=cond_prob_arr)[0]])
            generated_sentence.append(next_word)
            i += 1

        print('--------\nSeed:\n"{}..."\nGenerated sentence:\n"{}"\nActual:\n"{}"\n'.format(" ".join(seed),
            " ".join(generated_sentence), " ".join(actual_sentence)))

        self.analyze_result(generated_sentence[self.max_chain:], actual_sentence[self.max_chain:])

    def analyze_result(self, post_seed_generated, post_seed_actual):
        conjoined_vocab = list(set(post_seed_actual + post_seed_generated))
        conjoined_vocab.sort(key=lambda x: -self.vocabulary[x])
        conjoined_vocab_loc = {}
        for i, vocab in enumerate(conjoined_vocab):
            conjoined_vocab_loc[vocab] = i
        len_conjoined_vocab = len(conjoined_vocab)
        _generated_count = np.zeros(len_conjoined_vocab)
        _actual_vocab_count= np.zeros(len_conjoined_vocab)

        for word in post_seed_generated:
            _generated_count[conjoined_vocab_loc[word]] += 1
        for word in post_seed_actual:
            _actual_vocab_count[conjoined_vocab_loc[word]] += 1

        _generated_count /= np.sum(_generated_count)
        _actual_vocab_count /= np.sum(_actual_vocab_count)

        x = np.arange(len_conjoined_vocab)  # the label locations
        width = 0.35  # the width of the bars

        fig, ax = plt.subplots()
        ax.bar(x - width / 2, _generated_count, width, label='Post-seed Generated')
        ax.bar(x + width / 2, _actual_vocab_count, width, label='Post-seed Actual')

        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax.set_ylabel('Frequency')
        ax.set_title('Frequency of Generated vs. Actual Words in Markov Chain and Book Excerpt Respectively (sorted '
                     'left-to-right from most-frequent to least frequent in the whole text body)\n')
        ax.set_xticks(x)
        ax.set_xticklabels(conjoined_vocab)
        ax.legend()

        fig.tight_layout()
        fig.set_size_inches(15, 7)
        plt.xticks(rotation=90)
        ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.01), ncol=2, borderaxespad=0, frameon=False)
        plt.show()

    @staticmethod
    def autolabel(rects, ax):
        """
        Attach a text label above each bar in *rects*, displaying its height
        """
        for rect in rects:
            height = rect.get_height()
            ax.annotate('{}'.format(height), xy=(rect.get_x() + rect.get_width() / 2, height), xytext=(0, 3),
                        textcoords="offset points", ha='center', va='bottom')

    def __str__(self):
        return "Book: {}\nBook text file: {} ".format(self.name_author, self.path_to_book)
