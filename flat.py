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
import sys

class FlatWriter:
    def __init__(self, minFields=3):
        self.customersJson = []
        self.minimumFields = minFields
        self.totalErrors = 0
        self.symphonyTags = {
            "userId" : "USER_ID",                        # 21221012345678
            "userGroupId" : "USER_GROUP_ID",             # 
            "userName" : "USER_NAME",                    # Billy, Balzac
            "userFirstName" : "USER_FIRST_NAME",         # Balzac
            "userLastName" : "USER_LAST_NAME",           # Billy
            "userMiddleName" : "USER_MIDDLE_NAME",       # 
            "userPreferredName" : "USER_PREFERRED_NAME", # 
            "userNameDspPref" : "USER_NAME_DSP_PREF",    # 0
            "userLibrary" : "USER_LIBRARY",              # EPLMNA
            "userProfile" : "USER_PROFILE",              # EPL-STAFF
            "userPrefLang" : "USER_PREF_LANG",           # ENGLISH, or what-have-you
            "userPin" : "USER_PIN",                      # password
            "userStatus" : "USER_STATUS",                # OK, DELINQUENT, BARRED
            "userRoutingFlag" : "USER_ROUTING_FLAG",     # Y
            "userChgHistRule" : "USER_CHG_HIST_RULE",    # ALLCHARGES
            "userLastActivity" : "USER_LAST_ACTIVITY",   # 20130201
            "userPrivGranted" : "USER_PRIV_GRANTED",     # 20120705
            "userPrivExpires" : "USER_PRIV_EXPIRES",     # 20130705
            "userBirthDate" : "USER_BIRTH_DATE",         # 20050303
            "userCategory1" : "USER_CATEGORY1",          # 
            "userCategory2" : "USER_CATEGORY2",          # M - gender, or age group at Shortgrass
            "userCategory3" : "USER_CATEGORY3",          #
            "userCategory4" : "USER_CATEGORY4",          #
            "userCategory5" : "USER_CATEGORY5",          #
            "userAccess" : "USER_ACCESS",                # PUBLIC
            "userEnvironment" : "USER_ENVIRONMENT",      # PUBLIC
            "userMailingaddr" : "USER_MAILINGADDR",      # 1
            "street" : "STREET",                         # Street address
            "citySlashState" : "CITY/STATE",             # City / State unchanged from original config on ILS.
            "cityProv" : "CITYPROV",                     #  Alternate for some libs.
            "citySlashProv" : "CITY/PROV",               #
            "postalcode" : "POSTALCODE",                 # T5J 2V4
            "phone" : "PHONE",                           # 780-496-4058
            "phone1" : "PHONE1",                         # 403-555-1212
            "email" : "EMAIL",                           # name@example.com
            "careSlashOf" : "CARE/OF",
            "userAddr1" : "USER_ADDR1_",
            "userAddr2" : "USER_ADDR2_",
            "userAddr3" : "USER_ADDR3_",
            "userXinfo" : "USER_XINFO_",
            "notifyVia" : "NOTIFY_VIA",                  # 'PHONE'
            "note" : "NOTE",                             # 'ILS Team Test Account - DO NOT REMOVE!'
            "retrnmail" : "RETRNMAIL",                   # 'YES'
            "homephone" : "HOMEPHONE"                    #
        }

        # Reasonable default values. Some of these will have defaults 
        # from the ILS configuration, and these can be augmented, 
        # modified, or deleted.
        self._defaults_ = {
            "userNameDspPref" : "0",
            "userPrefLang" : "ENGLISH",
            "userRoutingFlag" : "Y",
            "userChgHistRule" : "ALLCHARGES",
            "userAccess" : "PUBLIC",
            "userEnvironment" : "PUBLIC",
            "userMailingaddr" : "1",
            "notifyVia" : "PHONE",
            "retrnmail" : "YES"
        }

        # How the tags used by text2flat convert to Symphony tags.
        # These can be modified with renameCustomerField().
        self._tagMap_ = {
            "userId" :     "userId",
            "profile" :    "userProfile",
            "firstName" :  "userFirstName",
            "lastName" :   "userLastName",
            "middleName" : "userMiddleName",
            "birthday" :   "userBirthDate",
            "gender" :     "userCategory2",
            "email" :      "email",
            "phone" :      "phone",
            "street" :     "street",
            "city" :       "citySlashState", # TODO: put these together
            "province" :   "citySlashState",
            "country" :    "country",
            "postalcode" : "postalcode",
            "barcode" :    "userId",
            "pin" :        "userPin",
            "type" :       "userProfile",
            "expiry" :     "userPrivExpires",
            "branch" :     "userLibrary",
            "status" :     "userStatus",
            "careOf" :     "careSlashOf",
            "note" :       "note"
        }

        # Arrays of address and extended info blocks. Extend for addr2 and addr3
        self.addr1 = {}
        # These are valid blocks but there is currently no way, and no reason
        # to use them with this application.
        self.addr2 = {}
        self.addr3 = {}
        self.xinfo = {}

        # fields in addr1 object which require start and end tags.
        self.blocks = {
            "postalcode" : self.addr1,
            "phone" : self.addr1,
            "street" : self.addr1,
            "city" : self.addr1,
            "email" : self.addr1,
            "careSlashOf" : self.addr1,
            "careOf" : self.addr1,
            "note" : self.xinfo,
            "notifyVia" : self.xinfo,
            "retrnmail" : self.xinfo
        }

        # 
        # Common messages required when processing Flat data.
        # 
        self._messages_ = {
            'noJson' : 'Empty customer data ',
            'invalidDate' : 'Contains an invalid date ',
            'missingData' : 'Not enough data to create a thin file ',
            'fileError' : 'Failed create flat file ',
            'invalidSymphonyTag' : 'Invalid Symphony tag(s) ',
            'unknownJsonTag' : 'Customer data includes unknown tag(s) '
        }

    # Returns all the current names expected in the input JSON file.
    # This means that it returns all the names that you expect to collect
    # from the custom API. For example the default name for the first name
    # field is 'firstName', but it can be changed to anything, say, 'fname'.
    def getCustomerTags(self):
        """
        >>> FlatWriter().getCustomerTags()
        ['userId', 'profile', 'firstName', 'lastName', 'middleName', 'birthday', 'gender', 'email', 'phone', 'street', 'city', 'province', 'country', 'postalcode', 'barcode', 'pin', 'type', 'expiry', 'branch', 'status', 'careOf', 'note']
        """
        return list(self._tagMap_.keys())

    # Allows you to redefine customer field names of the incoming customer data. 
    # If you prefer 'nom' to 'firstName', this function will remap it.  
    # If the original name is not defined, no bindings are changed.
    # param: oldName - str, original tag name, like 'email'.
    # param: newName - str, new tag name, like 'customerEmail'.
    # return: True if the old field was found and the name remapped and False otherwise.
    def renameCustomerField(self,oldName:str='',newName:str=''):
        """
        >>> f = FlatWriter()
        >>> f.renameCustomerField('firstName','nom')
        True
        >>> f.getCustomerTags()
        ['userId', 'profile', 'lastName', 'middleName', 'birthday', 'gender', 'email', 'phone', 'street', 'city', 'province', 'country', 'postalcode', 'barcode', 'pin', 'type', 'expiry', 'branch', 'status', 'careOf', 'note', 'nom']
        >>> f.renameCustomerField('Buffalo', 'nom')
        False
        >>> f.getCustomerTags()
        ['userId', 'profile', 'lastName', 'middleName', 'birthday', 'gender', 'email', 'phone', 'street', 'city', 'province', 'country', 'postalcode', 'barcode', 'pin', 'type', 'expiry', 'branch', 'status', 'careOf', 'note', 'nom']
        >>> f.renameCustomerField('this','that')
        False
        >>> f.renameCustomerField(None,None)
        False
        """
        if oldName == '' or newName == '':
            return False
        if oldName in self.getCustomerTags():
            originalValue = self._tagMap_.pop(oldName)
            self._tagMap_[newName] = originalValue
            return True
        else:
            return False

    # 
    # Checks the account for predefined data fields (see flat.dateFields)
    # and replaces the dates with ANSI dates as required by Symphony.
    # 
    # Tests:
    # Should find and convert date fields to ANSI date strings.
    # Date fields with invalid dates are removed from the map, and reported.
    # @param {*} jsonMap Map of the customer's data.
    # 
    def _ensureAnsiDates_(self):
        pass

    # Prints arbitrary information to STDERR, and optionally increments the total
    # error count for reporting purposes.
    # param: incrementErrors - bool True if reporting an analytic error, and False
    #   if you just need to print something to STDERR.
    def printError(self, incrementErrors:bool=False, *args, **kwargs):
        if incrementErrors == True:
            self.totalErrors += 1
        # Can use like: printError("foo", "bar", "baz", sep="---")
        print(*args, file=sys.stderr, **kwargs)
    
    # Returns all the names used by this application to identify all the
    # fields used by Symphony for flat files.
    # return: list of what the flat fields are call in this application.
    def getSymphonyTags(self):
        """
        >>> f = FlatWriter()
        >>> f.getSymphonyTags()
        ['userId', 'userGroupId', 'userName', 'userFirstName', 'userLastName', 'userMiddleName', 'userPreferredName', 'userNameDspPref', 'userLibrary', 'userProfile', 'userPrefLang', 'userPin', 'userStatus', 'userRoutingFlag', 'userChgHistRule', 'userLastActivity', 'userPrivGranted', 'userPrivExpires', 'userBirthDate', 'userCategory1', 'userCategory2', 'userCategory3', 'userCategory4', 'userCategory5', 'userAccess', 'userEnvironment', 'userMailingaddr', 'street', 'citySlashState', 'cityProv', 'citySlashProv', 'postalcode', 'phone', 'phone1', 'email', 'careSlashOf', 'userAddr1', 'userAddr2', 'userAddr3', 'userXinfo', 'notifyVia', 'note', 'retrnmail', 'homephone']
        """
        return list(self.symphonyTags.keys())

    # Allows you to set a new value for a system value in the customer data.
    # For example if you want to set the user catagory 5 value to some thing
    # by default, you can change it through this method. 
    # Note that any default will be reflected in the output of all customer data.
    # param: oldValue - str field name of the Symphony field as defined in 
    #   this application. For example 'userId' instead of 'USER_ID'. 
    #   See getSymphonyTags() for accepted names. If the field name is 
    #   not a recognized field, the method returns False.
    # param: newValue - str value to set the field to.
    def setDefaultSymphonyValue(self, fieldName:str='', newValue:str=''):
        """
        >>> f = FlatWriter()
        >>> f.setDefaultSymphonyValue('userRoutingFlag','N')
        True
        >>> f.setDefaultSymphonyValue('this','that')
        False
        >>> f.setDefaultSymphonyValue(None,None)
        False
        >>> f.setDefaultSymphonyValue('userLibrary','EPLMNA')
        True
        >>> print(f"{f._defaults_}")
        {'userNameDspPref': '0', 'userPrefLang': 'ENGLISH', 'userRoutingFlag': 'N', 'userChgHistRule': 'ALLCHARGES', 'userAccess': 'PUBLIC', 'userEnvironment': 'PUBLIC', 'userMailingaddr': '1', 'notifyVia': 'PHONE', 'retrnmail': 'YES', 'userLibrary': 'EPLMNA'}
        """
        if fieldName == '' or newValue == '':
            return False
        # Allow any Symphony tag to be set with a default. Any existing customer
        # data will overwrite the default value on output, but make sure the
        # request is for a valid Symphony tag. Invalid fields will fail to load.
        if fieldName in self.symphonyTags.keys():
            self._defaults_[fieldName] = newValue
            return True
        else:
            return False

    # Appends customer JSON data to the list of customers to output in the flat file.
    # param: customer JSON - dict
    # Return: True if the customer data was added and False if there wasn't 
    #   enough data to create a thin file
    def appendCustomer(self,customerJSON:dict):
        if customerJSON == None or len(customerJSON) < self.minimumFields:
            self.printError(True,self._messages_['noJson'])
            return False
        for defaultKey in self._defaults_.keys():
            # Add the defaults, but only if they are not set in the customer data
            if customerJSON.get(defaultKey) == None:
                customerJSON[defaultKey] = self._defaults_.get(defaultKey)
        self.customersJson.append(customerJSON)
        return True

    # Prints any or each of the block data.
    # param: t2fBlockName str - text2flat name of the block to print, like: 'userAddr1' or 'xInfo'.
    # param: block dict - data block.
    # return: count of errors encountered during the process.
    def _printBlock_(self,t2fBlockName:str,block:dict):
        customerErrors = 0
        print(f".{self.symphonyTags.get(f'{t2fBlockName}')}BEGIN.")
        for key in block.keys():
            symphonyFieldName = self._tagMap_.get(key)
            # Again default tags are added, but not expected to be part of the customer data
            if symphonyFieldName == None:
                symphonyFieldName = key
            symphonyField = self.symphonyTags.get(symphonyFieldName)
            if symphonyField == None:
                self.printError(True, f"**error, {self._messages_['invalidSymphonyTag']}=>{key}")
                customerErrors += 1
                continue
            print(f".{symphonyField}.   |a{block.get(key)}")
        print(f".{self.symphonyTags.get(f'{t2fBlockName}')}END.")
        return customerErrors
    # 
    # Converts customer data to flat data. The returned ojbect is also json which can be
    # sent to file with the write() function.
    # 
    # Tests:
    # Customer data exists and is valid resolve flat data.
    # Customer data exists but is not valid reject with message.
    # Customer data does not exist reject with message. 
    # 
    def toFlat(self):
        """
        TODO: finish the _ensureAnsiDate_() function and glob city/state.
        >>> custJson = {'firstName': 'Lewis','middleName': 'Fastest','lastName': 'Hamilton', 'birthday': '1974-08-22', 'gender': 'MALE', 'email': 'example@gmail.com', 'phone': '780-555-1212', 'street': '11535 74 Ave.', 'city': 'Edmonton', 'province': 'AB', 'postalcode': 'T6G0G9','barcode': '1101223334444', 'pin': 'IlikeBread', 'type': 'MAC-DSSTUD', 'expiry': '2021-08-22','careOf': 'Doe, John','branch': 'EPLWMC', 'status': 'OK', 'note': 'Hi' }
        >>> f = FlatWriter()
        >>> f.appendCustomer(custJson)
        True
        >>> f.toFlat()
        *** DOCUMENT BOUNDARY ***
        FORM=LDUSER
        .USER_FIRST_NAME.   |aLewis
        .USER_MIDDLE_NAME.   |aFastest
        .USER_LAST_NAME.   |aHamilton
        .USER_BIRTH_DATE.   |a19740822
        .USER_ID.   |a1101223334444
        .USER_PIN.   |aIlikeBread
        .USER_PROFILE.   |aMAC-DSSTUD
        .USER_PRIV_EXPIRES.   |a20210822
        .USER_STATUS.   |aOK
        .USER_NAME_DSP_PREF.   |a0
        .USER_PREF_LANG.   |aENGLISH
        .USER_ROUTING_FLAG.   |aY
        .USER_CHG_HIST_RULE.   |aALLCHARGES
        .USER_ACCESS.   |aPUBLIC
        .USER_ENVIRONMENT.   |aPUBLIC
        .USER_MAILINGADDR.   |a1
        .USER_LIBRARY.   |aEPLWMC
        .USER_ADDR1_BEGIN.
        .EMAIL.   |aexample@gmail.com
        .PHONE.   |a780-555-1212
        .STREET.   |a11535 74 Ave.
        .CITY/STATE.   |aEdmonton
        .POSTALCODE.   |aT6G0G9
        .CARE/OF.   |aDoe, John
        .USER_ADDR1_END.
        .USER_XINFO_BEGIN.
        .NOTE.   |aHi
        .NOTIFY_VIA.   |aPHONE
        .RETRNMAIL.   |aYES
        .USER_XINFO_END.
        """
        self.printError(True, f"processing flat files")
        for idx, customer in enumerate(self.customersJson):
            customerErrors = 0
            print(f"*** DOCUMENT BOUNDARY ***")
            print(f"FORM=LDUSER")
            for customerField in customer.keys():
                possibleBlock = self.blocks.get(customerField)
                if possibleBlock != None:
                    possibleBlock[customerField] = customer.get(customerField)
                    continue
                symphonyFieldName = self._tagMap_.get(customerField)
                if symphonyFieldName == None:
                    # If the symphonyFieldName isn't in the customer data it means it is a default
                    # system value.
                    symphonyFieldName = customerField
                symphonyField = self.symphonyTags.get(symphonyFieldName)
                if symphonyField == None:
                    self.printError(True,f"**error, {self._messages_['invalidSymphonyTag']}=>{symphonyFieldName}")
                    customerErrors += 1
                    continue
                print(f".{symphonyField}.   |a{customer.get(customerField)}")
            #
            # Now print the blocks if they have any content.
            # There are only two blocks to output, address 1 and xinfo.
            # That's because those are the only blocks that can be differentiated
            # in the customer data typically. This could change.
            # 
            if len(self.addr1) > 0:
                customerErrors += self._printBlock_('userAddr1', self.addr1)
            if len(self.addr2) > 0:
                customerErrors += self._printBlock_('userAddr2', self.addr2)
            if len(self.addr3) > 0:
                customerErrors += self._printBlock_('userAddr3', self.addr3)
            if len(self.xinfo) > 0:
                customerErrors += self._printBlock_('userXinfo', self.xinfo)
            self.printError(False, f"customer {idx +1} output with {customerErrors} error(s)")
        else:
            self.printError(False, f"processed {len(self.customersJson)} customer file(s) with {self.totalErrors} error(s)")

    # 
    # Writes flat customer data to file.
    # param: fileName - str /path/to/file.flat
    # 
    def write(self,fileName:str):
        # TODO: test and guard file creation.
        f = open(fileName, 'rw')
        f.write(self.toFlat())

if __name__ == '__main__':
    import doctest
    doctest.testmod()