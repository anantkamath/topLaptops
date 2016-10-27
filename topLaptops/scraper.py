from topLaptops import mongo
import requests
import time
from bs4 import BeautifulSoup

MAX_RETRIES = 5

def scrapeLaptops():
    url = "http://www.amazon.in/s/?fst=as%3Aoff&rh=n%3A976392031%2Cn%3A!976393031%2Cn%3A1375424031%2Cp_n_condition-type%3A8609960031&ie=UTF8"
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
    
    laptops = []
    retriesLeft = MAX_RETRIES
    while(retriesLeft):
        try:
            page = requests.get(url, headers=headers)
            if page.status_code==200:
                break
            time.sleep(3)
        except:
            # TODO log: requests error e
            # print(e)
            pass        
    if page:
        try:
            soup = BeautifulSoup(page.content, "lxml")

            # Get all 24 laptops
            resultDivs = soup.find_all("li", { "class" : "s-result-item" })
            print(len(resultDivs))

            for resultDiv in resultDivs:
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
                numReviews = resultDiv.find_all("a")[-1].contents[0]

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
        except Exception as e:
            print(e)
            # TODO log: parser error e
    else:
        pass
        # TODO log: could not scrape after MAX_RETRIES
    return laptops
 
def updateDb():
    #time.sleep(10)
    laptops = scrapeLaptops()
    mongo.db.laptops.remove({})
    mongo.db.laptops.insert_many(laptops)

if __name__ == "__main__":
    print(scrapeLaptops())