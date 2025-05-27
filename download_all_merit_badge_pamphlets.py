# %%
# Imports -- All standard libraries
import requests as r
from random import randint
import json
import re
from time import sleep
from urllib import parse
from pathlib import Path


# %%
# Variables / Prep
save_folder = r'./merit badge downloads'
Path(f"{save_folder}").mkdir(parents=True, exist_ok=True)   #Create the download directory if needed.

all_merit_badges_page = r'https://www.scouting.org/skills/merit-badges/all/'

def current_chrome_user_agent():
    '''
    Retrieve and extract the current Chrome User-Agent string from useragentstring.com
    '''
    source = 'https://useragentstring.com/pages/Chrome/'
    req = r.get(url=source)
    
    if req.status_code == 200:
        #Success, so extract
        match = re.search(r'(?:<li>)(?:<a[^>]*>)(.*?)(?:<\/a[^>]*>)(?:<\/li>)', req.content.decode('utf-8') , re.IGNORECASE | re.DOTALL)
        
    if match:
        #If a regex result is found in the source, return the first found value
        return match.groups()[0]
    
    #Default
    return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'


headers = {'User-Agent': current_chrome_user_agent() } #Impersonate Chrome's user-agent or Cloudflare will reject the requests.

def get_current_scouting_wordpress_page(url, headers):
    '''
    Extract the wordpress JSON page from the public pages' header.
    As of 2025-05-27: https://www.scouting.org/skills/merit-badges/all/ => https://www.scouting.org/wp-json/wp/v2/pages/175174
    This ensures that if scouting.org updates the wordpress page, the applet can find the new "all merit badges" data page.
    '''
    public_all_merit_badge_page = r.get(url=url, headers=headers)

    for item in public_all_merit_badge_page.headers["Link"].split(";"):         #Break up the Link section of the responses' header.
        if 'https://api.w.org/' in item:                                        #Find the portion that defines the wordpress json page.
            result = item.split(', ')[-1][1:-1]                                 #Trim the <> off.
            print(f"Found wordpress page: {result}")
            return result
            break                                                                   
    print("Something went wrong in finding the current all merit badge page on scouting.org. DEFAULTING... ")
    return r'https://www.scouting.org/wp-json/wp/v2/pages/175174'               #Current wordpress json page for all merit badges as of 2025-05-27 as fall back.

base_page = get_current_scouting_wordpress_page(url=all_merit_badges_page, headers=headers)                                                 #Page with links to all Merit Badges


valid_merit_badge_pages_regex = r'<a href="\/merit-badges\/([^\/]*)\/">(?!WEB)'                                                             #Link format for each merit badge requirements page
valid_merit_badge_pamphlets_regex = r'href="https:\/\/filestore\.scouting\.org\/(?:.*)\/Pamphlets([^"]*)"'


scouting_org_pdfs = []
no_pdfs = []
downloaded_pdfs = []
failed_pdfs = []




# Subroutines
# %%

def find_pdf(merit_badge):
    '''
    Given the string that uniquely identifies any merit badge requirements shown on the scouting.org website
    using the form of https://www.scouting.org/merit-badges/{x} this will find the pamphlet PDF within the page.

    This is rate-limited to avoid abusing the scouting website.
    '''

    #Rate limit
    sleep_duration = randint(1,10)
    sleep(sleep_duration/10)

    #Retrieve
    url = f"https://www.scouting.org/merit-badges/{merit_badge}/"
    mb_page = r.get(url=url, headers=headers)
    
    #Scan
    result = re.findall(valid_merit_badge_pamphlets_regex, mb_page.content.decode('utf-8'))
    
    #Manage Output
    if len(result): #Only add actual results. If none is found, don't add anything to the files list.
        print(f"   FOUND: https://filestore.scouting.org/filestore/Merit_Badge_ReqandRes/Pamphlets{result[0]}\n\n", sep='')
        scouting_org_pdfs.append(f"https://filestore.scouting.org/filestore/Merit_Badge_ReqandRes/Pamphlets{result[0]}")
    else:
        no_pdfs.append(f"{merit_badge}")
        print(f"   NOT FOUND {merit_badge}.\n\n", sep='')



# %%
def download_merit_badge_pdf_pamphlet(url):
    try:
        file = url.split('/')[-1]                       #Extract the PDF's file name from its URL
        outfile = parse.unquote(file).replace("_"," ")  #Replace underscores with spaces for readability.
        with r.get(url=url, headers=headers) as pdf:
            with open(f'{save_folder}/{outfile}', 'wb') as fd:
                fd.write(pdf.content)

    except Exception as e:
        print(f"an error has occurred while downloading {url}: {e}")    
        failed_pdfs.append(f"{save_folder}/{outfile}")
        return
    
    downloaded_pdfs.append(f"{save_folder}/{outfile}")
    print(f"file written: {save_folder}/{outfile}")



# Processing begins

# %%
all_merit_badges_page = r.get(base_page, headers=headers)
all_merit_badges = sorted(set(re.findall(valid_merit_badge_pages_regex, json.loads(all_merit_badges_page.content)["content"]["rendered"])))     #Extract and deduplicate the list of merit badges based on links on the all merit badges page


#Find pamphlets for each merit badge
for merit_badge in all_merit_badges:
    print(f"Scanning for pamphlet PDF on requirement page for: {merit_badge}")
    find_pdf(merit_badge)   #Builds scouting_org_pdfs [list]


#Download all found merit badge pamphlets.
for i, pamphlet in enumerate(scouting_org_pdfs):

    #Rate limit
    sleep_duration = randint(10,40)
    sleep(sleep_duration/10)

    #Download the pamphlet
    print(f"Downloading {i}/{len(scouting_org_pdfs)}... delay {sleep_duration/10} url={pamphlet}")
    download_merit_badge_pdf_pamphlet(pamphlet)


#Display results.
print(f"**************************************************************************************************************")
print(f"***** {len(downloaded_pdfs)} merit badge pamphlets has been downloaded to {save_folder} *****")
if no_pdfs:
    print(f"***** {len(no_pdfs)} merit badge pamphlets were not found:\n{no_pdfs} *****")
if failed_pdfs:
    print(f"***** {len(failed_pdfs)} merit badge pamphlets failed to download {save_folder}:\n{failed_pdfs} *****")
print(f"**************************************************************************************************************")

print("\n\n\n")
input("Work complete... press Enter to continue")
