import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import time
import lxml
import re

def scrape_website(url, attempts=0):
    # Send GET request to the website
    response = requests.get(url)
    time.sleep(1)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        if attempts > 0:
            print('Success')
        return response
    elif attempts < 3:
        print("Error:", response.status_code, "Trying again.")
        time.sleep(1)
        return scrape_website(url, attempts + 1)
    else:
        # Handle the request error
        print("Error: ", response.status_code, 'Failed on:', url)
        return None

def info_grabber(fp, url=True):
    '''
    Returns a dictionary that can be a row in a dataframe of the important info from a given XML url

    :param fp: Filepath of xml
    :param url: Whether a filepath is local or url
    '''
    if url:
        xml = scrape_website(fp)
        xml.encoding = 'UTF-8'
        xml = xml.text.strip()
    else:
        try:
            with open(fp, 'r') as file:
                xml = file.read()
        except FileNotFoundError:
            print(f"File not found: {fp}")
            return dict()
    if xml is None:
        return dict()
    
    soup = BeautifulSoup(xml, 'xml')

    row = dict()
    row['ba'] = soup.find('BusinessName')
    row['EIN'] = soup.find('EIN')
    row['Tax Year'] = soup.find('TaxPeriodBeginDt')
    row['Location (Zipcode)'] = soup.find('USAddress')
    row['Federate Campaigns'] = soup.find('FederatedCampaignsAmt')
    row['Membership Dues'] = soup.find('MembershipDuesAmt')
    row['Fundraising Events'] = soup.find('ContriRptFundraisingEventAmt')
    row['Related Organizations'] = soup.find('RelatedOrganizationsAmt')
    row['Government Grants'] = soup.find('GovernmentGrantsAmt')
    row['All Other Contributions'] = soup.find('AllOtherContributionsAmt')
    row['Noncash Contributions'] = soup.find('NoncashContributionsAmt')
    row['Total'] = soup.find('TotalContributionsAmt')
    # Can make default=0

    if row['Location (Zipcode)'] is not None:
        row['Location (Zipcode)'] = row['Location (Zipcode)'].find('ZIPCd')
    else:
        row['Location (Zipcode)'] = None
        
    row = dict(map(lambda item: (item[0], item[1].text if item[1] is not None else None), row.items()))

    if row['ba'] is not None:
        row['ba'] = row['ba'].strip()
    else:
        row['ba'] = 'Not found'
    if row['Tax Year'] is not None:
        row['Tax Year'] = pd.Timestamp(row['Tax Year']).year
    else:
        row['Tax Year'] = np.nan

    row = dict(map(lambda item: (item[0], item[1] if item[1] is not None else 0), row.items()))

    return row

def contact_grabber(fp, url=True):
    '''
    Return a dataframe of the important names and their positions in an organization for each year

    :param fp: filepath of the xml file
    :param url: Whether the fp is a url or not. Default = True
    '''
    if url:
        xml = scrape_website(fp)
    else:
        xml = requests.get(fp)
    if xml is None:
        return dict()
    xml.encoding = 'UTF-8'
    xml = xml.text.strip()
    soup = BeautifulSoup(xml, 'xml')

    people = soup.find_all('Form990PartVIISectionAGrp')
    names = [x.find('PersonNm').text for x in people if x.find('PersonNm') is not None]
    titles = [x.find('TitleTxt').text for x in people if x.find('TitleTxt') is not None]
    try:
        organization = [soup.find('BusinessName').text.strip()] * len(names)
    except AttributeError:
        organization = ['Not found'] * len(names)
    try:
        year = [pd.Timestamp(soup.find('TaxPeriodBeginDt').text).year] * len(names)
    except AttributeError:
        year = [0] * len(names)
        
    return pd.DataFrame({'organization': organization, 'year': year, 'names': names, 'titles': titles})

def get_xmls(ein):
    '''
    Return a list of xml urls from ProRepublica based on an organization's EIN

    :param ein: Employer Identification number as String or Int
    '''
    url = f'https://projects.propublica.org/nonprofits/organizations/{ein}'
    html = scrape_website(url)
    if html is None:
        return []
    soup = BeautifulSoup(html.text)
    links = soup.find_all('a', class_='action xml')
    base_url = 'https://projects.propublica.org'
    # urls = [base_url + x.get('href') for x in links if x.text == '990']
    urls = [x for x in soup.find_all(class_='action xml') if re.search(r'990\b', x.text)]
    urls = [base_url + x.get('href') if x.name == 'a' else base_url + x.select_one('select.action.xml option[data-href]').get('data-href') for x in urls]
    return urls

def grabber(eins, verbose=False, clean=False):
    if type(eins) == int:
        eins = [eins]
    data = []
    # contacts = pd.DataFrame()
    overall_index = 0
    for index, ein in enumerate(eins):
        print(str(index) + (' / ') + str(len(eins)))
        xmls = get_xmls(ein)
        for xml in xmls:
            if verbose:
                print(f'{overall_index} {xml}')
            data.append(info_grabber(xml))
            #contacts = pd.concat([contacts, contact_grabber(xml)])
            overall_index += 1
    print(str(len(eins)) + (' / ') + str(len(eins)))
    info = pd.DataFrame(data)
    if not clean:
        return info

    no_error = info.dropna().reset_index(drop=True)
    no_error.loc[:, 'EIN':'Total'] = no_error.loc[:, 'EIN':'Total'].astype(int)
    no_error.loc[:, 'EIN_YEAR'] = no_error['EIN'].astype(str) + '_' + no_error['Tax Year'].astype(str)
    no_error = no_error.set_index('EIN_YEAR')

    return no_error

def find_errors(info):
    '''
    Takes a dataframe of 990 rows and returns a tuple of the indices where it failed to grab the data properly

    :param info: The dataframe of 990 rows
    '''
    accurate = info[['Federate Campaigns', 'Membership Dues', 'Fundraising Events', 'Related Organizations', 'Government Grants', 'All Other Contributions']].sum(axis=1) == info['Total']
    return tuple(accurate[~accurate].index)