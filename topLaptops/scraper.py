from topLaptops import app, mongo
import requests
import time
from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool
import random


def scrapeLaptop(laptop):
    '''
    Scrapes additional details for a single laptop (RAM, CPU, HDD)
    '''
    url = 'http://amazon.in/dp/' + laptop['asin']
    headers = {
        'User-Agent': app.config['SCRAPER_USER_AGENT']}

    retriesLeft = app.config['SCRAPER_MAX_RETRIES']

    time.sleep(random.uniform(0, 2))

    while retriesLeft:
        page = requests.get(url, headers=headers)
        if page.status_code == 200:
            break
        time.sleep(3)
    if page:
        soup = BeautifulSoup(page.content, 'lxml')

        techTable = soup.find('div', {'class': 'section techD'}).find('tbody')
        for row in techTable.find_all('tr'):

            if row.contents[0].contents[0] == 'Processor Speed':
                laptop['cpu'] = row.contents[1].contents[0]
            elif row.contents[0].contents[0] == 'RAM Size':
                laptop['ram'] = row.contents[1].contents[0]
            elif row.contents[0].contents[0] == 'Hard Drive Size':
                laptop['hdd'] = row.contents[1].contents[0]
    # print(laptop)
    return laptop


def scrapeSearchPage(pageNumber, numberOfLaptops):
    '''
    Scrapes laptops from a single page of Amzon search results (max 24 laptops)

    '''
    if numberOfLaptops <= 0:
        return []

    headers = {
        'User-Agent': app.config['SCRAPER_USER_AGENT']}
    laptops = []

    retriesLeft = app.config['SCRAPER_MAX_RETRIES']
    url = 'http://www.amazon.in/s/?fst=as%3Aoff&rh=n%3A976392031%2Cn%3A!976393031%2Cn%3A1375424031%2Cp_n_condition-type%3A8609960031&ie=UTF8&page=' + \
        str(pageNumber)

    while retriesLeft:
        page = requests.get(url, headers=headers)
        if page.status_code == 200:
            break
        time.sleep(3)
    if page:
        soup = BeautifulSoup(page.content, 'lxml')

        # Get all laptops on the current page
        resultDivs = soup.find_all('li', {'class': 's-result-item'})

        for i in range(numberOfLaptops):
            resultDiv = resultDivs[i]
            # print(resultDiv.encode('utf-8'))
            # Scrape the product name:
            name = resultDiv.find(
                'h2', {'class': 's-access-title'}).contents[0]

            # Price
            priceSpan = resultDiv.find('span', {'class': 's-price'})
            # If the listing contains the price (some listings have only
            # offers, not prices)
            if priceSpan:
                price = priceSpan.contents[1]
            # If not, we scrape the 'lowest offer'
            else:
                priceSpan = resultDiv.find_all(
                    'span', {'class': 'a-color-price'})[1]
                price = priceSpan.contents[2]
            price = float(price.replace(',', ''))

            # Rating eg. '3 out of 5'
            rating = resultDiv.find(
                'i', {'class': 'a-icon-star'}).contents[0].contents[0]
            # Strip the ' out of 5' suffix
            i = rating.find(' ')
            if(i > 0):
                rating = rating[:i]

            # Scrape number of reviews
            for link in resultDiv.find_all('a', {'class': 'a-size-small a-link-normal a-text-normal'}):
                if link['href'].endswith('customerReviews'):
                    numReviews = int(link.contents[0].replace(',', ''))

            if not numReviews:
                numReviews = 0

            # Scrape the product id (ASIN: Amzon Standard Identifying Number).
            # (Useful for generating the product URL later)

            asin = resultDiv['data-asin']

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

    if app.config['SCRAPER_SCRAPE_LAPTOP_HARDWARE_DETAILS']:
        pool = ThreadPool(8)
        results = pool.map(scrapeLaptop, laptops)
        pool.close()
        pool.join()

        return results
    else:
        return laptops


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


def scoreLaptops(laptops):
    '''
    Generate scores for laptops which will be used for sorting
    '''
    for laptop in laptops:
        score = 0

        if app.config['SCRAPER_SCRAPE_LAPTOP_HARDWARE_DETAILS']:
            hdd = laptop.get('hdd')
            if hdd:
                if 'TB' in hdd:
                    hdd = 1000 * int(''.join(c for c in hdd if c.isdigit()))
                else:
                    hdd = int(hdd[:hdd.find(' ')])
            else:
                hdd = 500

            score += hdd / 200.

            cpu = laptop.get('cpu', None)
            if cpu:
                cpu = float(''.join(c for c in cpu if c.isdigit()))
            else:
                cpu = 1.8
            score += cpu * 2

            ram = laptop.get('ram', None)
            if ram:
                ram = int(''.join(c for c in ram if c.isdigit()))
            else:
                ram = 3
            score += ram * 0.75

        numReviews = int(laptop['numReviews'])
        if numReviews > 300:
            numReviews = 300
        score += numReviews / 100. * \
            (float(laptop['rating'])**2) / 3.

        # Calculate a benchmark price, i.e. a price that would be appropriate
        # for a laptop of such a score.
        # Ideally might be a good idea to calculate this by regression?
        appropriatePrice = score * 10000
        difference = appropriatePrice - laptop['price']
        score += difference / 100

        laptop['score'] = round(score, 2)

        # Also optionally normalize the scores (TODO) to a scale of 100 or 10


def updateDb():
    '''
    Update db with newly scraped laptops
    '''
    with app.app_context():
        laptops = scrapeLaptops()
        scoreLaptops(laptops)

        # Clear the collection
        mongo.db.laptops.remove({})

        # Insert into db
        mongo.db.laptops.insert_many(laptops)
