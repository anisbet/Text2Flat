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
import datetime
#
# This class parses the raw text file.
class TextParser:
    # Expects the configuration dictionary and a file name to read or 
    # string of data to parse. Debug is not part of the transformation config.
    def __init__(self, configs:dict, data:str='', debug:bool=False):
        self._debug_ = debug
        self._messages_ = {}
        self._messages_['missingConfig'] = "**error missing configuration section"
        self._messages_['missingCorpus'] = "**error expected a lookup file for"
        self._messages_['missingFile'] = "**error expected a file but it doesn't exist"
        self._messages_['missingRequired'] = "**error no 'required' fields were specified."
        self.delimiter = ','
        if configs == None or len(configs) < 1:
            raise ValueError(f"{self._messages_['missingConfig']}")
        # You can rebind the names of columns to whatever you want
        # These keys are in order and python guarantees key order as of python 3.10.
        self._tagMap_ = {
            'userId': 'userId',
            'branch': 'branch',
            'profile': 'profile',
            'postalcode': 'postalcode',
            'email': 'email',
            'phone': 'phone',
            'birthday': 'birthday',
            'expiry': 'expiry',
            'province': 'province',
            'country': 'country',
            'city': 'city',
            'gender': 'gender',
            'street': 'street',
            'firstName': 'firstName',
            'lastName': 'lastName'
        }
        # A dictionary of strategies for finding specific data. Usually regular expressions.
        self.known_strategies = {}
        self.known_strategies['userId'] = re.compile(r'^\d{6,15}$')
        self.known_strategies['branch'] = self._corpusCompare_
        self.known_strategies['profile'] = self._corpusCompare_
        self.known_strategies['postalcode'] = re.compile(r'^[a-zA-Z]\d[a-zA-Z](\s{1,})?\d[a-zA-Z]\d$')
        self.known_strategies['email'] = re.compile(r'^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$')
        self.known_strategies['phone'] = re.compile(r'^(\+)?(\()?\d{3}(-| |\)(\s|-)?)?\d{3}(-| )?\d{4}$')
        self.known_strategies['birthday'] = self._getRequestedDate_
        self.known_strategies['expiry'] = self._getRequestedDate_
        self.known_strategies['country'] = re.compile(r'^(CA|Canada)')
        self.known_strategies['province'] = re.compile(r'^(NL|PE|NS|NB|QC|ON|MB|SK|AB|BC|YT|NT|NU)')
        self.known_strategies['street'] = self._corpusCompare_
        self.known_strategies['city'] = self._corpusCompare_
        self.known_strategies['gender'] = re.compile(r'^((M|m)(ale)?|(F|f)(emale)?|(P|p)refer\s+not\s+to\s+say|(N|n)(ot\s+listed)?|(X|x))$')
        self.known_strategies['firstName'] = self._corpusCompare_
        self.known_strategies['lastName'] = self._corpusCompare_
        # Note: we can't just use the _tags_.keys() because if the key changes the order of
        # keys is no longer guaranteed.
        self.preferredSearchOrder = ['userId','branch','profile','postalcode','email','phone','birthday',
            'expiry','street','province','gender','city','lastName','firstName']
        # Covers: yyyy-mm-dd, yyyy/mm/dd, mm-dd-yyyy, mm/dd/yyyy, yyyymmdd, mmddyyyy date searches
        self.reg_mmddyyyy = re.compile(r'^(0[1-9]|1[012])[-/]?(0[1-9]|[12][0-9]|3[01])[-/]?(19|20)\d\d')
        self.reg_ddmmyyyy = re.compile(r'^(0[1-9]|[12][0-9]|3[01])[-/]?(0[1-9]|1[012])[-/]?(19|20)\d\d')
        self.reg_yyyymmdd = re.compile(r'^(19|20)\d\d[-/]?(0[1-9]|1[012])[-/]?(0[1-9]|[12][0-9]|3[01])')
        # Set up configs which include:
        # Does the configuration specify a new binding for field names?
        self._rebindFieldNames_(configs)
        # Find out if the delimiter is set and use ',' by Default
        self._setDelimiter_(configs)
        self.optionalList = []
        self.requiredList = []
        # Keep track of if the field is required or optional. 
        self.requestedFields = {}
        # Load and order requested fields in order of search reliability.
        self._loadRequestedFields_(configs)
        # Names of expected corpuses
        self.corpusNames = ['street','firstName','lastName','city','branch','profile']
        # The names of the corpuses and the files that contain the corpus data as values, all betted
        self.corpusDictionary = {}
        self._loadCorpora_(configs)
        # TODO: Create customers JSON and control output of flat files.

    # Specify a new binding for field names. 
    def _rebindFieldNames_(self,configs):
        fieldNames:dict = configs.get('fieldBindings')
        if fieldNames != None:
            for oldName,newName in fieldNames.items():
                self.renameField(oldName, newName)
    
    # Loads the corpora of first names, last names, and street names.
    def _loadCorpora_(self, configs):
        # Vet and Load the corpus names then match and test the associated corpus files
        corpusDict:dict = configs.get('corpus')
        if corpusDict == None:
            raise ValueError(f"{self._messages_['missingConfig']} 'corpus'.")
        # Translate user preferred names to cononical names for corpora.
        for corpusName in self.corpusNames:
            for newFieldName in self._tagMap_.keys():
                if corpusDict.get(newFieldName) != None and corpusName == self._tagMap_.get(newFieldName):
                    self.corpusDictionary[corpusName] = corpusDict.get(newFieldName)
        for corpusName in self.corpusNames:
            try:
                corpusFile = self.corpusDictionary[corpusName]
                if corpusFile == None:
                    raise ValueError(f"{self._messages_['missingCorpus']} '{corpusName}'.")
                if path.exists(corpusFile) == False:
                    raise ValueError(f"{self._messages_['missingFile']} '{corpusFile}'.")
            except KeyError:
                raise ValueError(f"{self._messages_['missingCorpus']} '{corpusName}'.")
        if self._debug_:
            for k,v in self.corpusDictionary.items():
                print(f"corpus dictionary {k} set to file {v}")

    # Set the delimiter used as field separators.
    def _setDelimiter_(self, configs):
        delim:str = configs.get('delimiter')
        if delim != None:
            self.delimiter = delim

    # Load the requested fields. 
    def _loadRequestedFields_(self, configs):
        # What are the required fields?
        requiredList:list = configs.get('required')
        if requiredList == None:
            raise ValueError(f"{self._messages_['missingRequired']}.")
        self.requiredList = requiredList
        # What are the optional fields?
        optionalList:list = configs.get('optional')
        if optionalList == None:
            # It's okay if there aren't any.
            self.optionalList = []
        # The data in columns can be unique in cases like postal codes or email addresses, but
        # other columns can have values that overlap. For example our library has someone with
        # the first name of Ave, which of course play havoc when checking for address strings.
        # One way to hedge our bets is to use a process of elemination, identify easy columns
        # early, and by process of elimination eventually identify harder types of data.
        # Check the required list and optional list 
        for orderedField in self.preferredSearchOrder:
            # if the user field match a binding they predefined continue search otherwise signal warning. 
            for optionalField in self.optionalList:
                if self._tagMap_.get(optionalField) != None and orderedField == self._tagMap_.get(optionalField):
                    self.requestedFields[orderedField] = False
            # Do this again for required fields and update any duplicate making required fields take precidence. 
            for requiredField in self.requiredList:
                if self._tagMap_.get(requiredField) != None and orderedField == self._tagMap_.get(requiredField):
                    self.requestedFields[orderedField] = True
        if self._debug_:
            for k,v in self.requestedFields.items():
                print(f"requested fields (in order) {k} => {v}")
        
    # A fast way to tell if an enormous corpus has words that can be found in an arbitrary
    # but specific field is to convert the field to a set of words, then find the intersection
    # with the set of the corpus. If there is more than one successful match a word in the corpus
    # matched a word in the field.
    def _corpusCompare_(self, data: list, field: str):
        corpus_to_read = corpus_dict[field]
        if corpus_to_read == None:
            print(f"don't know how to read a corpus for '{field}'")
            return -1
        corpus: list = []
        f = open(corpus_to_read)
        for line in f.readlines():
            corpus.append(line.lower().rstrip(os.linesep))
        corpusSet = set(corpus)
        # Free up some space for really big lists.
        corpus = []
        for idx, d in enumerate(data):
            wordsInTheField = re.split(r'\W+',d.lower())
            wordsInFieldSet = set(wordsInTheField)
            # Set contains empty values which don't matter much
            wordsInFieldSet.discard('')
            # Logically AND the two sets and the length is great than 0 an element matches in both sets.
            if len(corpusSet & wordsInFieldSet) > 0:
                if idx not in self.fields_collected.values():
                    return idx
    
    # Searches a given line from data and determines the index of either a birthday or expiry.
    # param: data - list of customer data read from source. 
    # param: field - string name of the field of search. Either birth date or expiry date are 
    #  currently supported. 
    def _getRequestedDate_(self, data:list, field:str):
        for idx, d in enumerate(data):
            if field == 'birthday':
                if self.isBirthDate(d):
                    return idx
            if field == 'expiry':
                if self.isExpiry(d):
                    return idx

    # Tests if a string is likely to be an expiry date.
    # return: True if the date is sometime in the future, and false otherwise.
    def isExpiry(self, some_date:str):
        """
        Tests is supplied date is a reasonable expiry date. Reasonable is anywhere from tomorrow 
        on up.
        >>> config = {'corpus':{'street': 'street.txt', 'firstName': 'fname.txt', 'lastName': 'lname.txt', 
        ... 'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
        ... 'required': ['firstName', 'lastName', 'street', 'postalcode'],
        ... 'optional': ['gender']
        ... }
        >>> t = TextParser(config)
        >>> t.isExpiry("2023-01-01")
        True
        >>> t.isExpiry("2043-01-01")
        True
        >>> t.isExpiry("2018-01-01")
        False
        >>> today = datetime.datetime.now()
        >>> t.isExpiry(f"{today}")
        False
        >>> tomorrow = datetime.datetime.now() + datetime.timedelta(20)
        >>> t.isExpiry(f"{tomorrow}")
        True
        >>> t.isExpiry("Foo")
        False
        """
        test_date = self.getDate(some_date)
        if test_date == None:
            return False
        tomorrow = datetime.datetime.now() + datetime.timedelta(1)
        possible_expiry = datetime.datetime.strptime(test_date, "%Y%m%d")
        if possible_expiry > tomorrow:
            return True
        return False
    

    # Tests if a string is likely to be a birth date.
    # return: True if the date is in the past on the order of years past, and false otherwise.
    def isBirthDate(self, some_date:str):
        """
        Tests if supplied date is in the medium to far past. Far past is no longer than 114 years and no less than 
        1 year, though that can potentially be problematic.
        >>> config = {'corpus':{'street': 'street.txt', 'firstName': 'fname.txt', 'lastName': 'lname.txt', 
        ... 'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
        ... 'required': ['firstName', 'lastName', 'street', 'postalcode'],
        ... 'optional': ['gender']
        ... }
        >>> t = TextParser(config)
        >>> t.isBirthDate("23-12-2019")
        True
        >>> t.isBirthDate("01-01-1888")
        False
        >>> t.isBirthDate("1963-08-22")
        True
        >>> t.isBirthDate("Toast")
        False
        """
        test_date = self.getDate(some_date)
        if test_date == None:
            return False
        two_years = 2 * 365
        one_hundred_years = 100 * 365
        two_years_ago = datetime.datetime.now() - datetime.timedelta(two_years)
        age = datetime.datetime.strptime(test_date, "%Y%m%d")
        if age < two_years_ago:
            one_hundred_years_ago = datetime.datetime.now() - datetime.timedelta(one_hundred_years)
            if age > one_hundred_years_ago:
                return True
        return False

    # Given a string parse out a date if possible, and if not, return None.
    def getDate(self, some_date:str):
        """
        Guesses if the argument is a date field and if it is, is it a birth date, expiry, or neither.
        For example:
        >>> config = {'corpus':{'street': 'street.txt', 'firstName': 'fname.txt', 'lastName': 'lname.txt', 
        ... 'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
        ... 'required': ['firstName', 'lastName', 'street', 'postalcode'],
        ... 'optional': ['gender']
        ... }
        >>> t = TextParser(config)
        >>> t.getDate("2022-11-04")
        '20221104'
        >>> t.getDate("2022/11/04")
        '20221104'
        >>> t.getDate("11/04/2022 11:04")
        '20221104'
        >>> t.getDate("11/04/2022 11:04")
        '20221104'
        >>> t.getDate("NEVER")
        'NEVER'
        >>> t.getDate("nonsense")
        
        >>> t.getDate("23-12-2020")
        '20201223'
        >>> t.getDate("12-23-2020")
        '20201223'
        >>> t.getDate("12232020")
        '20201223'
        >>> t.getDate("2020-12-23")
        '20201223'
        >>> t.getDate("2020")
        
        >>> t.getDate("2020-12-23 19:37:10 GMT")
        '20201223'
        >>> t.getDate("2020-12-23T19:37:10.12234 GMT")
        '20201223'
        >>> t.getDate("2022-11-06 18:02:01.558085")
        '20221106'
        >>> t.getDate("Bar")
        
        >>> t.getDate("2022-31-06 18:02:01.558085")
        
        >>> t.getDate("31-06-2022 18:02:01.558085")
        
        >>> t.getDate("12/23/2020")
        '20201223'
        """
        # Special reserved word for never expires. 
        if some_date == 'NEVER':
            return some_date
        test_date = some_date
        new_date = ""
        for ch in ['/','-']:
            if ch in some_date:
                some_date = some_date.replace(ch,'')
        # Trim off any trailing timestamps.
        some_date = some_date[:8]
        if self.reg_mmddyyyy.match(test_date):
            try:
                new_date = datetime.datetime.strptime(some_date, "%m%d%Y").date()
            except ValueError:
                return
        elif self.reg_ddmmyyyy.match(test_date):
            try:
                new_date = datetime.datetime.strptime(some_date, "%d%m%Y").date()
            except ValueError:
                return
        elif self.reg_yyyymmdd.match(test_date):
            try:
                new_date = datetime.datetime.strptime(some_date, "%Y%m%d").date()
            except ValueError:
                return
        else:
            return
        yyyymmdd = ''.join(c for c in str(new_date) if c not in '-')[0:8]
        return yyyymmdd
        
    # Allows you to redefine field names of the incoming customer data. 
    # If you prefer 'nom' to 'firstName', this function will remap it.  
    # If the original name is not defined, no bindings are changed.
    # param: oldName - str, original tag name, like 'email'.
    # param: newName - str, new tag name, like 'customerEmail'.
    def renameField(self,oldName:str='',newName:str=''):
        """
        >>> config = {'corpus':{'street': 'street.txt', 'firstName': 'fname.txt', 'lastName': 'lname.txt', 
        ... 'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
        ... 'required': ['firstName', 'lastName', 'street', 'postalcode'],
        ... 'optional': ['gender']
        ... }
        >>> t = TextParser(config)
        >>> t.renameField('firstName','fooName')
        >>> t.getCurrentFields()
        ['userId', 'branch', 'profile', 'postalcode', 'email', 'phone', 'birthday', 'expiry', 'province', 'country', 'city', 'gender', 'street', 'lastName', 'fooName']
        >>> t.renameField('postalcode','zipCode')
        >>> t.getCurrentFields()
        ['userId', 'branch', 'profile', 'email', 'phone', 'birthday', 'expiry', 'province', 'country', 'city', 'gender', 'street', 'lastName', 'fooName', 'zipCode']
        """
        if oldName != '' or newName != '':
            if oldName in self._tagMap_.keys():
                originalValue = self._tagMap_.pop(oldName)
                self._tagMap_[newName] = originalValue

    # Get the list of column names.
    # return: all the names of the columns as they are currently set
    def getCurrentFields(self):
        return list(self._tagMap_.keys())
    
    def getCorpusNames(self):
        return list(self.corpusDictionary.keys())

    def getCorpusFiles(self):
        return list(self.corpusDictionary.values())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    # config = {'delimiter': ',',
    #     'corpus':{'bazzStreet': 'street.txt', 'fooName': 'fname.txt', 'barName': 'lname.txt', 
    #     'city': 'alberta_towns.txt', 'branch': 'epl_branches.txt', 'profile' : 'user_profiles.txt'},
    #     'required': ['fooName', 'barName', 'bizz', 'bazzStreet', 'boo'],
    #     'optional': ['gender'],
    #     'fieldBindings': {'firstName':'fooName', 'lastName': 'barName', 'birthday': 'boo', 'street':'bazzStreet'}
    #     }
    # t = TextParser(config)
    # print(t.getCorpusNames())
    # ['street', 'firstName', 'lastName', 'city', 'branch', 'profile']
    # print(t.getCorpusFiles())
    # ['street.txt', 'fname.txt', 'lname.txt', 'alberta_towns.txt', 'epl_branches.txt', 'user_profiles.txt']
    # print(t.getCurrentFields())