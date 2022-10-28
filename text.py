#!/usr/bin/env python3
############################################################################
# This file flat.js contains utility functions for writing patron
# information into Symphony's flat file format.
#
# Copyright 2022 Andrew Nisbet, dev-ils.com
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# A class that formats JSON into flat file format.
#
############################################################################
import os
from os import path
import re
#
# This class parses the raw text file.
class TextParser:
    # Expects the configuration dictionary and a file name to read or string of data to parse.
    def __init__(self, configs:dict, data:str=''):
        self._messages_ = {}
        self._messages_['missingConfig'] = "**error missing configuration section"
        self._messages_['missingCorpus'] = "**error expected a lookup file for"
        self._messages_['missingFile'] = "**error expected a file but it doesn't exist"
        self._messages_['missingRequired'] = "**error no 'required' fields were specified."

        # The data in columns can be unique in cases like postal codes or email addresses, but
        # other columns can have values that overlap. For example our library has someone with
        # the first name of Ave, which of course play havoc when checking for address strings.
        # One way to hedge our bets is to use a process of elemination, identify easy columns
        # early, and by process of elimination eventually identify harder types of data.
        self.preferred_search_order = ['userId','branch','profile','pcode','email','phone','birthday',
            'expiry','street','province','gender','city','lname','fname']
        self.delimiter = ','
        # You can rebind the names of columns to whatever you want
        # TODO: implement this as per flat.py
        self._tagMap_ = {
            'userId': 'userId',
            'email': 'email',
            'pcode': 'postalcode',
            'country': 'country',
            'province': 'province',
            'phone': 'phone',
            'gender': 'gender',
            'city': 'city',
            'street': 'street',
            'fname': 'firstName',
            'lname': 'lastName',
            'branch': 'branch',
            'profile': 'profile',
            'birthday': 'birthday',
            'expiry': 'expiry'
        }
        # A dictionary of strategies for finding specific data. Usually regular expressions.
        self.known_strategies = {}
        self.known_strategies['userId'] = re.compile(r'^\d{6,15}$')
        self.known_strategies['email'] = re.compile(r'^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$')
        self.known_strategies['postalcode'] = re.compile(r'^[a-zA-Z]\d[a-zA-Z](\s{1,})?\d[a-zA-Z]\d$')
        self.known_strategies['country'] = re.compile(r'^(CA|Canada)')
        self.known_strategies['province'] = re.compile(r'^(NL|PE|NS|NB|QC|ON|MB|SK|AB|BC|YT|NT|NU)')
        self.known_strategies['phone'] = re.compile(r'^(\+)?(\()?\d{3}(-| |\)(\s|-)?)?\d{3}(-| )?\d{4}$')
        self.known_strategies['gender'] = re.compile(r'^((M|m)(ale)?|(F|f)(emale)?|(P|p)refer\s+not\s+to\s+say|(N|n)(ot\s+listed)?|(X|x))$')
        # self.known_strategies['city'] = self._corpus_compare_
        # self.known_strategies['street'] = self._corpus_compare_
        # self.known_strategies['firstName'] = self._corpus_compare_
        # self.known_strategies['lastName'] = self._corpus_compare_
        # self.known_strategies['branch'] = self._corpus_compare_
        # self.known_strategies['profile'] = self._corpus_compare_
        # self.known_strategies['birthday'] = self._getRequestedDate_
        # self.known_strategies['expiry'] = self._getRequestedDate_

        # Set up configs which include:
        # Does the configuration specify a new binding for field names?
        fieldNames:dict = configs.get('fieldNames')
        if fieldNames != None:
            for oldName,newName in fieldNames.items():
                self.renameField(oldName, newName)
        # Names of expected corpuses
        self.corpusNames = ['street','firstName','lastName','city','branch','profile']
        # The names of the corpuses and the files that contain the corpus data as values, all betted
        self.corpusDictionary = {}
        # Vet and Load the corpus names then match and test the associated corpus files
        corpusDict:dict = configs.get('corpus')
        if corpusDict == None:
            raise ValueError(f"{self._messages_['missingConfig']} 'corpus'.")
        for corpusName in self.corpusNames:
            corpusFile:str = corpusDict.get(corpusName)
            if corpusFile == None:
                raise ValueError(f"{self._messages_['missingCorpus']} '{corpusName}'.")
            if path.exists(corpusFile) == False:
                raise ValueError(f"{self._messages_['missingFile']} '{corpusFile}'.")
            self.corpusDictionary[corpusName] = corpusFile
        # Find out if the delimiter is set and use ',' by Default
        delim:str = configs.get('delimiter')
        if delim != None:
            self.delimiter = delim
        # What are the required fields?
        reqList:list = configs.get('required')
        if reqList == None:
            raise ValueError(f"{self._messages_['missingRequired']}.")
        self.requiredFields:list = reqList
        # What are the optional fields?
        optList:list = configs.get('optional')
        if optList == None:
            optList = []
        self.optionalFields:list = optList
        

    # Returns the index position of a given field string in a line of data
    # param: data - list of strings fields from a single line of input file. 
    # param: field - string name of the target field. 
    # def _getRequestedDate_(self, data:list, field:str):
    #     for idx, d in enumerate(data):
    #         if field == 'birthday':
    #             if self._isBirthDate_(d):
    #                 return idx
    #         if field == 'expiry':
    #             if self._isExpiry_(d):
    #                 return idx
    # Allows you to redefine field names of the incoming customer data. 
    # If you prefer 'nom' to 'firstName', this function will remap it.  
    # If the original name is not defined, no bindings are changed.
    # param: oldName - str, original tag name, like 'email'.
    # param: newName - str, new tag name, like 'customerEmail'.
    def renameField(self,oldName:str='',newName:str=''):
        if oldName != '' or newName != '':
            if oldName in self._tagMap_.keys():
                originalValue = self._tagMap_.pop(oldName)
                self._tagMap_[newName] = originalValue

    # Get the list of column names.
    # return: all the names of the columns as they are currently set
    def getCurrentFields(self):
        return list(self._tagMap_.keys())
    
    # TODO: remove as not required except for testing.
    def getCorpusNames(self):
        return list(self.corpusDictionary.keys())

    # TODO: remove as not required except for testing.
    def getCorpusFiles(self):
        return list(self.corpusDictionary.values())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    config = {'delimiter': ',',
        'corpus':{'street': 'street.txt', 'firstName': 'fname.txt', 'lastName': 'lname.txt', 
        'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
        'required': ['fname', 'lname'],
        'optional': ['gender'],
        'fieldNames': {'fname':'firstName', 'birthday': 'dob'}
        }
    t = TextParser(config)
    print(t.getCorpusNames())
    # ['street', 'firstName', 'lastName', 'city', 'branch', 'profile']
    print(t.getCorpusFiles())
    # ['street.txt', 'fname.txt', 'lname.txt', 'alberta_towns.txt', 'epl_branches.txt', 'user_profiles.txt']
    print(t.getCurrentFields())