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
    for laptop in mongo.db.laptops.find({}, {'_id': False}).sort([('score', -1)]).limit(10):
        laptops.append(laptop)
    #laptops.sort(key=lambda x: x['score'], reverse=True)

    datetimeUpdated = mongo.db.laptops.find_one().get('_id').generation_time
    return jsonify({'laptops': laptops, 'datetimeUpdated': datetimeUpdated})
