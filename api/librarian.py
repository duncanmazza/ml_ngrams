"""
This contains the functions that book.py and main.py reference
"""

import requests
import os
from api import book as cl
import pickle
import sys


class HelperFuncs:
    def __init__(self):
        pass

    @staticmethod
    def list_to_string(list):
        """
        Takes a list of strings and returns a string that is the combination of the
        strings in the list.

        >>> list_to_string(['this','is','a','test'])
        this is a test
        """
        return "".join(list)

    @staticmethod
    def check_folder_exist(folder, delete_folder_if_exists=False):
        """
        If existing books/ folder exists, the user is prompted to either delete it
        and make a new folder or keep it. If it doesn't exist, a books/ folder is
        made. The /books folder will store all of the books' files.
        """
        if os.path.exists(folder):
            if delete_folder_if_exists: os.remove(folder)
        else:
            os.system("mkdir {}".format(folder))


class Librarian(HelperFuncs):
    def __init__(self, book_list=(('Frankenstein, by Mary Wollstonecraft (Godwin) Shelley')), redownload_index=False,
                 use_hardcoded=True, delete_existing_book_folder=False, delete_existing_cache=False,
                 gutindex_info_path=os.path.join(os.getcwd(), "cache", "gutindex_info.bin")):
        HelperFuncs.__init__(self)
        # Hard coding conditions that the text parser will use:
        self.skip_line_if = [" ", "~", "TITLE"]
        self.end_title_if = ["  ", " 1", " 2", " 3", " 4", " 5", " 6", " 7", " 8", " 9"]

        self.redownload_index = redownload_index
        self.use_hardcoded = use_hardcoded
        self.delete_existing_book_folder = delete_existing_book_folder
        self.delete_existing_cache = delete_existing_cache
        self.book_list = book_list
        self.gutindex_info_path = gutindex_info_path

        self.library = {}
        self.gutenberg_index_dict = {}

        self.check_folder_exist("cache/", delete_folder_if_exists=self.delete_existing_cache)
        self.check_folder_exist("cache/books/", delete_folder_if_exists=self.delete_existing_book_folder)

        succ1 = self.check_GUTINDEX(self.gutindex_info_path)

        if not succ1:
            print("Error handling the index")
            sys.exit(-1)

        self.get_books()

    def parse_GUTINDEX_text(self, GUTINDEX_text):
        gutenberg_index_dict = {}
        gut_lines = GUTINDEX_text.split("\n")
        for line in gut_lines[260:]:
            if line == "<==End of GUTINDEX.ALL==>":
                break
            else:
                if len(line) != 0:  # Skip empty lines
                    if line[0] not in self.skip_line_if or line[0:5] not in self.skip_line_if:
                        # At this point, the line in consideration will have a book title/author name and index number
                        for i in range(len(line) - 1):
                            if line[i:i + 2] in self.end_title_if:
                                # Find where the book title ends in the line
                                book_name_author = line[0:i]
                                for j in range(0, len(line)):
                                    if line[len(line) - j - 1] == " ":
                                        # Pull out the index number of the book
                                        book_number = line[len(line) - j:len(line)]
                                        break
                                gutenberg_index_dict[book_name_author] = book_number
                                break
        return gutenberg_index_dict

    def check_GUTINDEX(self, gutindex_info_path, GUTINDEX_text_path=os.path.join(os.getcwd(), "cache", "GUTINDEX.txt")):
        """
        Handles the GUTINDEX.txt file - either download it for the first time or
        redownloads the file.
        """
        path_exists = os.path.exists(gutindex_info_path)
        if path_exists and not self.redownload_index:
            print("{} file already exists".format(gutindex_info_path))
            # Load the gutenberg_index dictionary
            gutenberg_index_file = open(self.gutindex_info_path, "rb")
            self.gutenberg_index_dict = pickle.loads(gutenberg_index_file.read())
            gutenberg_index_file.close()
            return True
        elif path_exists and self.redownload_index:
            print("Deleting old {} file".format(gutindex_info_path))
            os.remove(gutindex_info_path)

        if not os.path.exists(GUTINDEX_text_path):
            # TODO: FIX reading of the gutenberg text file (weird characters show up for some reason)
            print("Downloading the GUTINDEX file...")
            try:
                GUTINDEX_text = requests.get("https://www.gutenberg.org/dirs/GUTINDEX.ALL").text
            except requests.exceptions.MissingSchema:
                print("Invalid url / could not download from this link")
                return False
            print("Finished downloading the GUTINDEX file")
            GUTINDEX_file = open(GUTINDEX_text_path, "w")
            GUTINDEX_file.write(GUTINDEX_text)
            GUTINDEX_file.close()
        else:
            GUTINDEX_text_file = open(GUTINDEX_text_path, 'r')
            GUTINDEX_text = GUTINDEX_text_file.read()
            GUTINDEX_text_file.close()

        print("Generating gutenberg_index dictionary and writing as {}".format(gutindex_info_path))
        gutenberg_index_dict = self.parse_GUTINDEX_text(GUTINDEX_text)
        self.gutenberg_index_dict = gutenberg_index_dict

        GUTINDEX_file = open(gutindex_info_path, "wb")
        GUTINDEX_file.write(pickle.dumps(gutenberg_index_dict))
        GUTINDEX_file.close()
        return True

    def get_books(self, reset_library=True):
        """
        This function will prompt the user to either download books from the hard-coded list or to type in the desired
        books by hand. The program will then acquire the books if they haven't already, or if they have, loading them into
        book objects in the library dictionary.
        :param gutenberg_index_dict:
        :param num_texts_plot: either take input of one or two texts
        :return library: a dictionary of the book objects
        """
        if reset_library: self.library = {}  # reset library dictionary
        for book_name_author in self.book_list:
            print("Loading {}".format(book_name_author))
            self.library[book_name_author] = cl.Book(book_name_author, self.gutenberg_index_dict, do_make_book=True)


if __name__ == "__main__":
    # TODO: implement unit tests
    pass
