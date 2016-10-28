## Overview
A Flask + MongoDB based service to scrape and sort laptops from Amazon India's website

## Endpoints
##### /laptops [GET]:
Returns top 10 laptops in JSON format (ranked by criteria defined later in this doc), along with datetime that this data was scraped


##### /refreshDb [GET]:
Runs the scraper and recreates the data in the database

### Running
To run locally, 
```
$ ./runserver.py
```

Or deploy as docker images:
```
$ docker-compose build
$ docker-compose up
```

The server should be available on **http://localhost:5000**

### Installing dependencies (only if running locally)
```
$ pip install -r requirements.txt
```
### Configuration
You can edit the following configurations in topLaptops/config.cfg

* **SCRAPER_USER_AGENT** User agent for the scraper
* **SCRAPER_NUM_LAPTOPS:** Number of laptops to scrape (default 40)
* **SCRAPER_MAX_RETRIES:** Max retries for each http request
* **SCRAPER_SCRAPE_LAPTOP_HARDWARE_DETAILS:** Described below

### Dependencies

* flask
* pymongo
* Flask-PyMongo
* requests
* beautifulsoup4
* lxml

* docker-compose to build and run this as dockerized services

## Implementation Details
The laptops are scraped from the search pages and detail pages of each individual page in a parallel fashion using thread pools.

If the SCRAPER_SCRAPE_LAPTOP_HARDWARE_DETAILS option is set to true, this scrapes the RAM, CPU and HDD details of each laptop which is then used to rank the laptop. If it is false, only the ratings, price and number of reviews are used to calculate the ranking.

Scraping these hardware details takes considerably more time so decide accordingly.

### Scoring system

The laptops are assigned scores to allow them to be ranked as follows:

**Score** =  HDD/200 + CPU*2  + RAM*0.75 + (numReviews/100)*(rating^2)/3
The score is further adjusted for price by adding a parameter to decide if it is overpriced or underpriced for it's specifications/reviews as follows:

**Benchmark price** = **Score x 1000**

**Score** = Score + (Benchmark price - price)/100

Thus a 'value for money' metric is also incorporated in the ranking logic.

The square of ratings is used to punish poorly rated laptops and favor highly rated ones, which is weighted by the number of reviews so that the score of laptops rated on either extreme by fluke are not affected mistakenly.

The benchmark price can perhaps be calculated by some sort of averaging or linear regression to give a better idea of the laptop being overpriced or not.

## Future improvements/ TODO:
* The service depends on python threads for running scraping tasks in the background, with a high degree of parallelism, but keeping track of background tasks and state between requests is difficult in Flask. On a larger scale, **Celery+RabbitMQ** or **Celery+Redis** can be considered to take the weight of the server and allow better tracking of async/background tasks.
* Further the scraper can be broken down in to individual parts that can be containerized and deployed in a distributed fashion to achieve efficient horizontal scaling
