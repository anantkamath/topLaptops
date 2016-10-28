from topLaptops import app, mongo
from flask import jsonify
from .scraper import updateDb

@app.route('/refreshDb')
def refreshDb():
    updateDb()
    return 'DB refresh/scraping started'

@app.route('/laptops')
def getLaptops():
    laptops = []
    for laptop in mongo.db.laptops.find({}, {'_id': False}):
        laptops.append(laptop)
    laptops.sort(key=lambda x: x['price'])
    return jsonify({'laptops': laptops})
