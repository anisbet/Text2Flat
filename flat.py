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


class FlatWriter:
    def __init__(self):
        self.symphonyTags = {
            "userId" : "USER_ID",                        # 21221012345678
            "userGroupId" : "USER_GROUP_ID",             # 
            "userName" : "USER_NAME",                    # Billy, Balzac
            "userFirstName" : "USER_FIRST_NAME",         # Balzac
            "userLastName" : "USER_LAST_NAME",           # Billy
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
            "userAddr1Begin" : "USER_ADDR1_BEGIN",       # Start of section
            "street" : "STREET",                         # Street address
            "citySlashState" : "CITY/STATE",             # City / State unchanged from original config on ILS.
            "cityProv" : "CITYPROV",                     #  Alternate for some libs.
            "citySlashProv" : "CITY/PROV",               #
            "postalcode" : "POSTALCODE",                 # T5J 2V4
            "phone" : "PHONE",                           # 780-496-4058
            "phone1" : "PHONE1",                         # 403-555-1212
            "email" : "EMAIL",                           # name@example.com
            "userAddr1End" : "USER_ADDR1_END",           #
            "userAddr2Begin" : "USER_ADDR2_BEGIN",       #
            "userAddr2End" : "USER_ADDR2_END",           #
            "userAddr3Begin" : "USER_ADDR3_BEGIN",       #
            "userAddr3End" : "USER_ADDR3_END",           #
            "userXinfoBegin" : "USER_XINFO_BEGIN",       #
            "notifyVia" : "NOTIFY_VIA",                  # 'PHONE'
            "note" : "NOTE",                             # 'ILS Team Test Account - DO NOT REMOVE!'
            "retrnmail" : "RETRNMAIL",                   # 'YES'
            "userXinfoEnd" : "USER_XINFO_END",           #
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
        self._tagMap_ = {
            "firstName" :  "userFirstName",
            "lastName" :   "userLastName",
            "birthday" :   "userBirthDate",
            "gender" :     "userCategory2",
            "email" :      "email",
            "phone" :      "phone",
            "street" :     "street",
            "city" :       "citySlashProv",
            "province" :   "cityProv",
            "country" :    "country",
            "postalcode" : "postalcode",
            "barcode" :    "userId",
            "pin" :        "userPin",
            "type" :       "userProfile",
            "expiry" :     "userPrivExpires",
            "branch" :     "userLibrary",
            "status" :     "userStatus",
            "notes" :      "note"
        }

        # Arrays of address and extended info blocks. Extend for addr2 and addr3
        self.addr1 = {}
        self.xinfo = {}

        # fields in addr1 object which require start and end tags.
        self.blocks = {
            "postalcode" : self.addr1,
            "phone" : self.addr1,
            "street" : self.addr1,
            "city" : self.addr1,
            "email" : self.addr1,
            "notes" : self.xinfo
        }

        # 
        # Common messages required when processing Flat data.
        # 
        self._messages_ = {
            noJson: 'Customer json data empty or missing.',
            noFlatContainer: 'Flat container missing.',
            invalidDate: 'contains an invalid date.',
            missingFlatData: 'Expected an array of flat data to output.',
            errorFileClose: 'Failed to close flat file.',
            errorFileWrite: 'Failed to write flat data to file.',
            errorFileOpen: 'Failed to open flat file for writing.',
            invalidSymphonyTag: 'Failed to update flatDefaults with tag '
        }

        # 
        # Checks the account for predefined data fields (see flat.dateFields)
        # and replaces the dates with ANSI dates as required by Symphony.
        # 
        # Tests:
        # Should find and convert date fields to ANSI date strings.
        # Date fields with invalid dates are removed from the map, and reported.
        # @param {*} jsonMap Map of the customer's data.
        # 
        def _convertDates_(self, flatCustomer:dict):
            pass

        def updateDefaults(self, defaultMap, defaults):
            pass

        # 
        # Converts json data to flat data. The returned ojbect is also json which can be
        # sent to file with the write() function.
        # 
        # Tests:
        # Customer data exists and is valid resolve flat data.
        # Customer data exists but is not valid reject with message.
        # Customer data does not exist reject with message.
        # 
        # @param {*} jsonCustomer the json data of customer registration data.
        # @param {*} flatCustomer an assciative array for the customer's flat data.
        # @param {*} flatDefaults Dictionary of default flat values.
        # @resolve message of success.
        # @reject  message(s) of issues with the account data if there was a problem
        # during conversion. 
        # 
        def toFlat(self, jsonCustomer:dict,flatCustomer:dict,flatDefaults:dict):
            #  
            # Add the defaults before the blocks.
            # But first update the default Symphony fields.
            # 
            
            #  Add the block data.# 
            # addr1 = {}
            
            # xinfo = {}
            pass
    

        # 
        # Writes flat (json) data to a given file name or to stdout if a file name 
        # is not provided.
        # 
        # Tests:
        # Flat data exists and is complete and no file name provided write to stdout, resolve with success message.
        # Flat data exists and is complete write to stream, resolve with success message.
        # Flat data does not exist, or is invalid reject with message.
        # 
        # @param {*} flatCustomer a Customer object which includes 'data':[]
        # and 'errors':[]
        # @param {*} fileName name of the flat file including path and file extension.
        # If none provided the flat data is written to STDOUT.
        #  
        # @resolve if the customer data was successfully written to the argument file,
        # @reject if there was a problem either with the data itself, or while writing
        # to file.
        # 
        def write(self, flatCustomer:dict,fileName:str):
            pass

if __name__ == '__main__':
    import doctest
    doctest.testmod()