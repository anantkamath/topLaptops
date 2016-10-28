from topLaptops import app, mongo
from flask import jsonify
from .scraper import updateDb
from threading import Thread

@app.route('/refreshDb')
def refreshDb():
    thr = Thread(target=updateDb)
    thr.start()
    return 'DB refresh/scraping started', 202

@app.route('/laptops')
def getLaptops():
    laptops = []
    for laptop in mongo.db.laptops.find({}, {'_id': False}):
        laptops.append(laptop)
    laptops.sort(key=lambda x: x['price'])
    return jsonify({'laptops': laptops})
