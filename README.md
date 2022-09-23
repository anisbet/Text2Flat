# Text2Flat
The goal of the project is a script that can convert arbitrary customer information into a flat file.

## Definitions
* Flat file - a standard representation of customer information used for loading said information into a SirsiDynix
  Symphony ILS system.
* Tabular data - data in table form. This should include 'xslx', 'CSV', and clipboard data optionally.

## Specification
* Each row in the input represents a single customer's information required for registration.
* The script must be able to identify the type of data represented in each column.
* The script must do it's best to create a flat-file representation of the customer data or report why it couldn't.
* The output file is a well formed flat file as defined by SirsiDynix.

# Development notes
## Assumptions
The input data will have columns that are incomplete and may be ragged. Since the initial rows may be missing data
the script must update its understanding of the input data as it find counter examples of information.

* TODO: Parse the file in two stages, one to identify columns, the next to extract and translate the data into flat files.
* Identify phone numbers - *Done*
* Identify postal codes - *Done*
* Identify gender - *Done*
* Identify email - *Done*
* Identify country - *Done* (only Canada is supported at this time)
* Idnetify province - *Done* (only Canadian provinces are supported)
* TODO: Identify dates and infer their use. That is if a date is in the future it may be an expiry date. A date in years
    past is probably a dob but update this with checks for variance in dates. Dates that are all very similar could
    should cast the dob hypothesis in doubt.
    Find the column with likely date. The target date is yyyymmdd format, but input could be mm/dd/yyyy, or dd/mm/yyyy,
    or even yyyy-mm-dd, mm-dd-yyyy or dd-mm-yyyy. In each case test for '/' or '-'. Next look at each value in the
    column and look for numbers bigger than 12 in the first 2 positions, check if the next 2 numbers are 12>=n>=1, and
    finally test that the year position is 4 digits. Keep track of which date format is used in each date column.
* TODO: Identify first name, last name
    This can be challenging because guardian names may appear in the same row. The registrant's name
    should appear in a lower order column than the guardians name in the input. We can create a list of first names
    and a list of last names from existing entries in the ILS and compare them over the names in columns and guess the
    likelihood that an arbitrary but specific name is a first or last name. A name like 'Terry Grace' may not be
    a good indicator, but over all the data in a file one column should show more matches in both first and last names.
    Once you can identify a column as first name, note it for parsing the file.
* TODO: Identify street addresses - in testing.
* TODO: Identify supplied user barcodes, which should produce a different flat file that includes 'update' in the name.
* TODO: Keep track of which columns contain what data.
* TODO: Report rejected registrants with reasons.
* TODO: Output a single FLAT file version of all the valid customers' data.
* TODO: Allow the user to map how some columns map to flat file entries.

# Test Data
You can download data from [Mockeroo](https://www.mockaroo.com/schemas/447387) by curl-ing this URL:
```bash
curl "https://api.mockaroo.com/api/8eaffe90?count=1000&key=c939c280" >Dirty_User_Registration_Data.csv
```

