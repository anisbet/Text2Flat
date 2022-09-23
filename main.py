#!/usr/bin/env python3
#######################################################################################################################
# Text2flat converts text to a flat user format as specified by SirsiDynix.
# Copyright (c) 2020 Andrew Nisbet
#
# Purpose:  taking a file which contains account information one per line, and parse it into a flat file that can be
#           be loaded with loadflatuser on a Symphony system.
#
#           The script will also read mapping files to convert arbitrary text into appropriate values. For example
#           if you are expecting a school name such as "St. Mary's" and wanted that converted to a USER_CAT3 you can
#           add that to a file like St. Mary | STMARYGOO or what ever your ILS is expecting.
#
#######################################################################################################################
import argparse
import sys
import sqlite3 as sl
import datetime
import re

# Find dob.
def guess_dob():
    # reg = re.compile(r'^[A-Z]\d[A-Z]\d[A-Z]\d$')
    # mmddyyy
    reg_mmddyyyy = re.compile(r'^(0[1-9]|1[012])[- \/.](0[1-9]|[12][0-9]|3[01])[- \/.](19|20)\d\d$')
    reg_ddmmyyyy = re.compile(r'^(0[1-9]|[12][0-9]|3[01])[- \/.](0[1-9]|1[012])[- \/.](19|20)\d\d$')
    reg_yyyyddmm = re.compile(r'^(19|20)\d\d(0[1-9]|1[012])(0[1-9]|[12][0-9]|3[01])$')
    # This snippet will print the yyyymmdd from one month ago.
    start_date = datetime.datetime.now() - datetime.timedelta(30)
    # print(start_date)
    month_ago_yyyymmdd = ''.join(c for c in str(start_date) if c not in '-')[0:8]
    print("{}".format(month_ago_yyyymmdd))


con = sl.connect('my-test.db')


#     con.execute("""
#         CREATE TABLE USER (
#             id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#             name TEXT,
#             age INTEGER
#         );
#     """)
#
# sql = 'INSERT INTO USER (id, name, age) values(?, ?, ?)'
# data = [
#     (1, 'Alice', 21),
#     (2, 'Bob', 18),
#     (3, 'Andrew', 7)
# ]
# con.executemany(sql, data)

# test the result
# with con:
#     data = con.execute("SELECT * FROM USER WHERE age <= 21")
#     for row in data:
#         sys.stdout.write(f"->{row}\n")

# Keep track of the columns that have been found to contain data of specific categories.
# A list of mandatory data required for registration are first name, last name, street, postalcode, email.
# A list of recommended features are DOB, phone number, province, country.
# Optional features could be SMS number, school, care-of.
# All of these facets can change categories depending on the design goals. For example Calgary Public
# ran a registration project where the only requirement was the registrants' email address.
# The categories allow us to reject candidates with useful messages about how to correct their input.
def build_database(fields={'fname': 1, 'lname': 1, 'street': 1, 'pcode':1, 'email': 1, 'dob': 2,
                             'phone': 2, 'province': 2, 'country': 2, 'school': 3, 'care_of': 3}):
    """
    Given a list of priorities populate the MetaData table with those priorities.
    :param fields: dict containing field name, and priority for the data contained within. 1=required
    2 = recommended, 3 = optional.
    :return: none
    >>> build_database()
    ('fname', 1)
    ('lname', 1)
    ('street', 1)
    ('pcode', 1)
    ('email', 1)
    ('dob', 2)
    ('phone', 2)
    ('province', 2)
    ('country', 2)
    ('school', 3)
    ('care_of', 3)
    """
    con.execute("""
CREATE TABLE IF NOT EXISTS Priority (
    priority INTEGER,
    description TEXT NOT NULL PRIMARY KEY 
);
    """)
    con.execute("""
CREATE TABLE IF NOT EXISTS MetaData (
    field_name TEXT NOT NULL PRIMARY KEY,
    priority INTEGER
);
    """)
    sql_data = "CREATE TABLE IF NOT EXISTS {} (\nid INTEGER PRIMARY KEY AUTOINCREMENT,\n".format('Data')
    names: list = [*fields]
    for col_name in names:
        sql_data += "   {} CHAR(256),\n".format(col_name)
    sql_data = sql_data[:-2] + '\n'
    sql_data += ");"
    con.execute(sql_data)
    table = 'MetaData'
    cols: list = ['field_name', 'priority']
    for key, value in fields.items():
        sql_insert = "INSERT OR IGNORE INTO {} ({}) VALUES ('{}', {});".format(table, ','.join(cols), key, value)
        con.execute(sql_insert)
    # This next part is just for testing.
    cur = con.cursor()
    cur.execute("SELECT * FROM {}".format(table))
    rows = cur.fetchall()
    for row in rows:
        print(row)

# Finds the email in a list of words and returns it.
def guess_email(list_in) -> str:
    """
    Guesses which field contains the email field given basic heuristics.
    For example:
    >>> guess_email(["Andrew", "Nisbet", "email@example.com", "23/12/2020"])
    'email@example.com'
    """
    list_in: list[str]
    for word in list_in:
        if "@" in word:
            return word
    return ''


# Finds the delimiter used in the file to delimited fields in lines in the file.
def guess_delimiter(str_in) -> str:
    """
    Returns the delimiter used to separate values in columns.
    :param str_in: Any arbitrary string.
    :return: delimiter character

    For example:
    >>> guess_delimiter("This_is_a_string_of_sorts.")
    '_'
    >>> guess_delimiter("This is a string of sorts.")
    ' '
    >>> guess_delimiter("This, is, a, string, of, sorts.")
    ', '
    >>> guess_delimiter("")
    ''
    >>> guess_delimiter("Another|'string'|'but not'|what you | think")
    '|'
    """
    freq_dict: dict(str, int) = {}
    # Compute the frequencies of all the characters in the string, sort by frequency take the most common non-alpha
    # character sequence.
    for c in list(str_in.lower()):
        freq_dict[c] = freq_dict.get(c, 0) + 1
    # Sort the frequencies by value.
    ordered_chars = sorted(freq_dict, key=freq_dict.get, reverse=True)
    d_delimiter = ""
    while ordered_chars:
        c = ordered_chars.pop(0)
        # First non-alpha character, must be part of the delimiter.
        if not c.isalpha():
            d_delimiter += c
            while ordered_chars:
                c1 = ordered_chars.pop(0)
                # The sequence of non-alpha chars is over, return what we have so far as the delimiter.
                if c1.isalpha() or c1 == "'" or c1 == '"':
                    return d_delimiter
                else:
                    d_delimiter += c1
    return ''


# Guess at which field contains a postal code.
def guess_postalcode(list_in: list) -> str:
    """
    Return the first instance of a regex that matches a (Canadian) postal code.
    :param list_in: list of fields from the input customer data.
    :return: the postalcode string
    For example:
    >>> guess_postalcode(["Andrew", "Nisbet", "email@example.com", " T6g 0G4", "23/12/2020"])
    'T6G0G4'
    >>> guess_postalcode(["Andrew", "Nisbet", "email@example.com", " T60 0G4", "23/12/2020"])
    ''
    >>> guess_postalcode(["Andrew", "Nisbet", "email@example.com", " T6Z 0G4  ", "23/12/2020"])
    'T6Z0G4'
    """
    # This is a matter of regex through list.
    list_in: list
    reg = re.compile(r'^[A-Z]\d[A-Z]\d[A-Z]\d$')
    for entry in list_in:
        possible_pc = entry.upper().strip().replace(" ", "")
        if re.search(reg, possible_pc):
            return possible_pc
    return ''


def guess_phone(list_in: list) -> list:
    """
    Find a phone number in a list of strings.

    Guessing a phone number is as straight forward as a regular expression. North American phone numbers have
    10 meaningful numbers where the first three digits are the area code, the next three are the exchange number
    and the last four are the phone number.
    :param list_in: list of strings of customer data.
    :return: The phone number string or None if one wasn't found.
    >>> guess_phone(["123-4567890", "Nisbet", "email@example.com", " T6Z 0G4  ", "780-242-9978"])
    ['780-242-9978']
    >>> guess_phone(["123-4567890", "Nisbet", "email@example.com", " T6Z 0G4  ", "780 242-9978"])
    ['780-242-9978']
    >>> guess_phone(["123-4567890", "(555)-333-9999", "+1 (780) 555-1212", " T6Z 0G4  ", "780 242-9978"])
    ['555-333-9999', '780-555-1212', '780-242-9978']
    """
    reg = re.compile(r'([+]?1[\s|-])?\D?\d{3}\D{1,2}\d{3}-\d{4}')
    # reg = re.compile(r"^\(?\d{3}\D|\s?\d{3}\D\d{4}$")
    phone_list = []
    for entry in list_in:
        possible_phone = entry.upper().strip().replace('(', '').replace(')', '')
        if re.search(reg, possible_phone):
            # If the number starts with a country code remove it.
            if re.search(r'^([+]?1[\s|-])*', possible_phone):
                possible_phone = possible_phone.replace('+', '').replace('1', '', 1).strip()
            # Clean up the space between the area code and exchange.
            possible_phone = possible_phone.replace(' ', '-')
            phone_list.append(possible_phone)
    return phone_list


def guess_address(list_in: list) -> str:
    """
    Guess which string contains the address string. The matchpoint is markers typcially representing addresses such
    as digits, dash, dot (.), Capitalized words.
    :param list_in:
    :return:
    >>> guess_address(['Andrew', '1277 Elgin Cres.', '708-242-9978'])
    '1277 Elgin Cres.'
    >>> guess_address(['8 walkers ran fast', '1277 Elgin Cres.', '708 $that is what I said. I know that Street!'])
    '1277 Elgin Cres.'
    """
    names: list = []
    list_in: list
    addr_regex = re.compile(r"\d+\s[A-Z][a-z]+.?,?\s[A-Z][a-z]+.?,?\s?([A-Z][a-z]+)?")
    with open("./address_corpus.txt", 'r') as f:
        names = ([line.rstrip('\n') for line in f])
    freq: dict[int, float] = {}
    for i in range(len(list_in)):
        for j in range(len(names)):
            if re.search(addr_regex, list_in[i]):
                freq[i] = freq.get(i, 0.0) + 0.1
                if names[j] in list_in[i]:
                    freq[i] = freq.get(i, 0.0) + 0.1

    most_likely = sorted(freq, key=freq.get, reverse=True)
    return list_in[most_likely[0]]


def guess_first_name(list_in: list) -> list:
    """
    Guess the first name which the only thing we can use is that it probably comes before most other data,
    and starts with a capital letter, followed by one or more lower case letters that start and end the string.
    :param list_in: list of customer account data strings.
    :return: the guess of the customers first name in the row of data.
    >>> guess_first_name(['780-555-1212', 'damned text', 'Edward'])
    'Edward'
    """
    list_in: list
    name_regex = re.compile(r'^[A-Z][a-z]+(-?\s?[A-Z][a-z]+)?$')
    one_field = re.compile(r'^[A-Z][a-z]+(-[A-Z][a-z]+)?,\s+[A-Z][a-z]+$')
    for i in range(len(list_in)):
        # Simple, one field both first and last separated by comma as in 'Last, First'.
        if re.search(one_field, list_in[i]):
            names: list = list(list_in[i].split(','))
            return [names[1], names[0]]
        # Simpler, one field contains first name.
        if re.search(name_regex, list_in[i]):
            return list_in[i]
    return []

# Check for last name in columns since last names are more unique than first, you are likely to
# eleminate a field faster. For example, checking for 'andrew' in first names returns true for both
# first and last names but 'malenfant' is found in last names first.
# param: Sting file name of the corpus of names.
# param: 
def check_name(name_corpus: str, test_input: list) -> int:
    corpus = open(name_corpus).readlines()
    for i in test_input:
        if any(i.upper() in s for s in corpus):
            return i
    return -1


def guess_province(self, string: str) -> str:
    pass

class TextParser:
    def __init__(self, file_name: str, delim="|"):
        self.field_indices: dict = {}
        self.delimiter = delim
        sys.stdout.write(f"checking for delimiter in {file_name}\n")
        for line in open(file_name):
            self.delimiter = guess_delimiter(line)
            if self.delimiter != '':
                sys.stdout.write(f"delimiter set to '{self.delimiter}'\n")
                break
        if self.delimiter == '':
            sys.stderr.write(f"**error: couldn't detect the delimiter.\n\n")
            sys.exit(3)
        # TODO: take the line and set the data facet indicies of the split string.
        for line in open(file_name):
            pass




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    import doctest

    doctest.testmod()

    parser = argparse.ArgumentParser(description="Generates optimized sorter config from a Microsoft XSLS file.")
    parser.add_argument("-i", "--in_text", action="store", type=str, required=True,
                        help="The text file that contains all the customer data line-by-line.")
    parser.add_argument("-d", "--delimiter", action="store", type=str, required=False,
                        help="The character(s) used to deliniate fields.")
    args = parser.parse_args()
    # The path/file.txt
    input_file = args.in_text
    parser = TextParser(input_file, args.delimiter)
