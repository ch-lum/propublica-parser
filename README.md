# propublica-parser
Given an EIN (or list of EINs) scrape data from all of that organization's 990 forms on ProPublica

### Methods
`scrape_website(url, attempts=0)`
- Takes a URL and returns the response object if successful. Retries three times on failure (change this number if you want more leeway)

`info_grabber(fp, url=True)`
- Takes the URL/filepath of an XML file. The `url` parameter indicates whether the given filepath is a URL or local
- Returns a dictionary of the row information for section VIII (along with a couple other columns)
- Older (prior to 2013) XML files have different tags and thus can't be read. Results in a row of all zeroes and `'Not Found'` in the `ba` column
- Of successfully scraped columns, has ~1.5% error rate for rows (0.13% of cells are inaccurate), only in the `Fundraising Events` column due to inconsistent labeling in XMLs
    - This error rate is lower than our human error rate
- In 2013, they had a different way of tagging zip codes, so all 2013 zips will be 0
- **Grabs from very specific tags**, change this if you want different data such as contacts or other fields

`contact_grabber(fp, url=True)`
- Returns a dataframe of each contact in the 990 form, according to section VII
- **Incomplete** and edge cases aren't tested fully, as we didn't need the function.

`get_xmls(ein)`
- Takes the EIN of a company and returns a list of the URLs for each XML file that is linked on the ProPublica page for that given company
- Could use a filter to filter years, this version of the method instead grabs them ALL

`grabber(eins, verbose=False, clean=False)`
- Takes a list of EINs and uses `get_xmls()` to find each XML file, then uses `info_grabber()` to scrape each XML for the relevant information.
- Returns a pandas DataFrame, doesn't automatically save as csv.
- Takes around 22 minutes on my laptop for 71 businesses
- The `clean` parameter automatically cleans the dataframe by removing empty rows

`find_errors(info)`
- Data columns are supposed to add up to the total, if it doesn't this method will find it
- Takes a dataframe of 990 rows from `grabber` and returns a tuple of incides that didn't properly grab all of the data
    - Preferably indiced on `EIN_YEAR`
