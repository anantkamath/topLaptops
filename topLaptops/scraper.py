from topLaptops import app, mongo
import requests
import time
from bs4 import BeautifulSoup

def scrapeLaptops():
    currPage = 1
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
    
    laptops = []
    laptopsToScrape = app.config['SCRAPER_NUM_LAPTOPS']
    while(len(laptops) < laptopsToScrape):
        retriesLeft = app.config['SCRAPER_MAX_RETRIES']
        url = "http://www.amazon.in/s/?fst=as%3Aoff&rh=n%3A976392031%2Cn%3A!976393031%2Cn%3A1375424031%2Cp_n_condition-type%3A8609960031&ie=UTF8&page="+str(currPage)
        while retriesLeft:
            page = requests.get(url, headers=headers)
            if page.status_code==200:
                break
            time.sleep(3)      
        if page:
            soup = BeautifulSoup(page.content, "lxml")

            # Get all laptops on the current page
            resultDivs = soup.find_all("li", { "class" : "s-result-item" })

            for resultDiv in resultDivs:
                if len(laptops) >= laptopsToScrape:
                    break
                # Scrape the product name:
                name = resultDiv.find("h2", { "class" : "s-access-title" }).contents[0]
                
                # Price
                priceSpan = resultDiv.find("span", {"class": "s-price"})
                # If the listing contains the price (some listings have only offers, not prices)
                if priceSpan:
                    price = priceSpan.contents[1]
                # If not, we scrape the 'lowest offer'
                else:
                    priceSpan = resultDiv.find_all("span", {"class": "a-color-price"})[1]
                    price = priceSpan.contents[2]
                price = price.strip(',')

                # Rating eg. "3 out of 5"
                rating = resultDiv.find("i", {"class": "a-icon-star"}).contents[0].contents[0]
                # Strip the " out of 5" suffix
                i = rating.find(' ')
                if(i > 0):
                    rating = rating[:i]

                # Scrape number of reviews
                numReviews = resultDiv.find_all("a", {"class": "a-size-small a-link-normal a-text-normal"})[-1].contents[0]

                ''' 
                    Scrape the product id (ASIN: Amazon Identifying Number). 
                    Useful for generating the product URL later
                '''
                asin = resultDiv["data-asin"]                

                laptop = {
                        'asin': asin,
                        'name': name,
                        'price': price,
                        'rating': rating,
                        'numReviews': numReviews
                        }
     
                laptops.append(laptop)
            currPage += 1
        else:
            app.logger.error('Scraping failed. Retried' + str(app.config['SCRAPER_MAX_RETRIES']) + ' times')
    return laptops
 
def updateDb():
    #time.sleep(10)
    laptops = scrapeLaptops()
    mongo.db.laptops.remove({})
    mongo.db.laptops.insert_many(laptops)