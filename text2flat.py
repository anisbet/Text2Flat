#!/usr/bin/env python3
#######################################################################################################################
# Text2flat converts text to a flat user format as specified by SirsiDynix.
# Copyright (c) 2022 Andrew Nisbet
#
# Purpose:  taking a file which contains account information one per line, determine which columns contain what data
#           and parse it into a flat file that can be loaded with loadflatuser on a Symphony system.
#
#           TODO: Read mapping files to convert arbitrary text into appropriate values. For example
#           if you are expecting a school name such as "St. Mary's" and wanted that converted to a USER_CAT3 you can
#           add that to a file like St. Mary | STMARYGOO or what ever your ILS is expecting.
#
#######################################################################################################################

from text import TextParser
from flat import FlatWriter
import json
import os
from os import path
import argparse
import sys

# The allowed fields are:
#   firstName, 
#   lastName, 
#   street, 
#   city, 
#   province, 
#   state, 
#   postalCode, 
#   couintry, 
#   phone, 
#   birthday, 
#   expiry, 
#   email, 
#   gender
# All other tags are ignored. Any can be required, ignored, or omitted.

# The configuration class loads requested configuration JSON, or
# allows settings via setters and getters.
# param: required fields - list, not empty.
# param: optional fields - list, may be empty.
# param: delimiter - str, character used as delimiter in input file.
#        Default=','
# param: locale - str, country code used, default 'CA'. The value 'US'
#        tells text2flat to use US postal codes and US state names.
#        Other settings may change in the future such as expected first
#        and last names and street names.
# param: street names file - str, common list of accepted street names.
#        For example, Avenue, Ave. etc.
# param: first names file - str, common list of first names.
# param: last names file - str, common list of last names.
#        For example, Adams, Smith etc.
# A complete JSON document looks like:
# {
#   required : [], 
#   optional : [], 
#   delimiter : ",", 
#   locale : "CA", 
#   streetNames : "street_names.txt", 
#   commonFirstNames : "first_names.txt",
#   commonLastNames : "last_names.txt"
# }

class Configuration:
    """
    >>> c = Configuration()
    configuration file "text2flat.json" not found.
    >>> c = Configuration('c.json')
    configuration file "c.json" not found.
    >>> c = Configuration('config.json')
    configuration file "config.json" not found.
    """
    def __init__(self, config:str):
        self.settings = {}
        if config != None and path.isfile(config):
            f = open(config)
            self.settings = json.load(f)
        else:
            print(f'configuration file "{config}" not found.')

# Orchestrates the process of identifying data types within the
# input text document and creating the flat files ready for loading
# into a SirsiDynix Symphony ILS system.
class Text2Flat:
    """
    >>> t = Text2Flat('test_data_0.csv')
    
    """
    def __init__(self, input:str, config:Configuration=None):
        if input != None and path.isfile(input):
            self.data = input
        else:
            print(f'input customer data file "{input}" not found.')
            sys.exit(-1)
        self.config = config
        self.text_parser = TextParser()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    parser = argparse.ArgumentParser(description="Generates flat user data from column data automatically.")
    parser.add_argument("-i", "--in_text", action="store", type=str, required=True,
                        help="The text file that contains all the customer data one-per-line.")
    parser.add_argument("-d", "--delimiter", action="store", type=str, required=False,
                        help="The character used to delineate fields in the input file.")
    parser.add_argument("-c", "--config_file", action="store", type=str, required=False,
                        help="The json configuration file.")
    args = parser.parse_args()
    # The path/file.txt
    input_file = args.in_text
    configuration = Configuration(args.config_file)
    parser = TextParser(input_file, configuration)