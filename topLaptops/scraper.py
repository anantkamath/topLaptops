from topLaptops import app, mongo
import requests
import time
from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool

def scrapeLaptop(laptop):
    '''
    Scrapes single laptop
    '''
    url = "http://amazon.in/dp/"+laptop['asin']
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
    
    retriesLeft = app.config['SCRAPER_MAX_RETRIES']

    while retriesLeft:
        page = requests.get(url, headers=headers)
        if page.status_code == 200:
            break
        time.sleep(3)
    if page:
        soup = BeautifulSoup(page.content, "lxml")

        techTable = soup.find("div", {"class": "section techD"}).find("tbody")
        for row in techTable.find_all("tr"):
            if row.contents[0] == "Processor Speed":
                print('cpu')
                laptop['cpu'] = row.contents[1]
            elif row.contents[0] == "RAM Size":
                laptop.['ram'] = row.contents[1]
            elif row.contents[0] == "Hard Drive Size":
                laptop.['hdd'] = row.contents[1]
    print(laptop)
    return laptop

def scrapeSearchPage(pageNumber, numberOfLaptops):
    '''
    Scrapes a single page from Amzon search results (max 24 laptops)

    '''
    if numberOfLaptops <= 0:
        return []

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
    laptops = []

    retriesLeft = app.config['SCRAPER_MAX_RETRIES']
    url = "http://www.amazon.in/s/?fst=as%3Aoff&rh=n%3A976392031%2Cn%3A!976393031%2Cn%3A1375424031%2Cp_n_condition-type%3A8609960031&ie=UTF8&page=" + \
        str(pageNumber)

    while retriesLeft:
        page = requests.get(url, headers=headers)
        if page.status_code == 200:
            break
        time.sleep(3)
    if page:
        soup = BeautifulSoup(page.content, "lxml")

        # Get all laptops on the current page
        resultDivs = soup.find_all("li", {"class": "s-result-item"})

        for i in range(numberOfLaptops):
            resultDiv = resultDivs[i]
            # Scrape the product name:
            name = resultDiv.find(
                "h2", {"class": "s-access-title"}).contents[0]

            # Price
            priceSpan = resultDiv.find("span", {"class": "s-price"})
            # If the listing contains the price (some listings have only
            # offers, not prices)
            if priceSpan:
                price = priceSpan.contents[1]
            # If not, we scrape the 'lowest offer'
            else:
                priceSpan = resultDiv.find_all(
                    "span", {"class": "a-color-price"})[1]
                price = priceSpan.contents[2]
            price = float(price.replace(',', ''))

            # Rating eg. "3 out of 5"
            rating = resultDiv.find(
                "i", {"class": "a-icon-star"}).contents[0].contents[0]
            # Strip the " out of 5" suffix
            i = rating.find(' ')
            if(i > 0):
                rating = rating[:i]

            # Scrape number of reviews
            numReviews = resultDiv.find_all(
                "a", {"class": "a-size-small a-link-normal a-text-normal"})[-1].contents[0]

            # Scrape the product id (ASIN: Amazon Identifying Number). 
            # (Useful for generating the product URL later)
            
            asin = resultDiv["data-asin"]

            laptop = {
                'asin': asin,
                'name': name,
                'price': price,
                'rating': rating,
                'numReviews': numReviews
            }

            laptops.append(laptop)
    else:
        app.logger.error('Scraping failed. Retried' +
                         str(app.config['SCRAPER_MAX_RETRIES']) + ' times')
    #print(laptops)

    pool = ThreadPool(8)
    results = pool.map(scrapeLaptop, laptops)
    pool.close()
    pool.join()

    return results

def scoreLaptops(laptops):
    for laptop in laptops:
        score = (100000/laptop.price)*laptop.rating + 5

def scrapeLaptops():
    '''
    Scrape as many laptops as required
    '''
    laptops = []
    laptopsToScrape = app.config['SCRAPER_NUM_LAPTOPS']

    # Amzon returns 24 results per page, we need to split our scraping
    # into several pages

    jobs = []
    for i in range(laptopsToScrape // 24):
        jobs.append((i + 1, 24))
    if(laptopsToScrape % 24):
        jobs.append((len(jobs) + 1, laptopsToScrape % 24))

    # Use a thread pool to parallelize the scraping
    pool = ThreadPool(8)
    results = pool.starmap(scrapeSearchPage, jobs)
    pool.close()
    pool.join()

    for result in results:
        laptops += result

    return laptops


def updateDb():
    '''
    Update db with newly scraped laptops
    '''
    with app.app_context():
        laptops = scrapeLaptops()
        mongo.db.laptops.remove({})
        mongo.db.laptops.insert_many(laptops)
