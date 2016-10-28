from flask import Flask
from flask_pymongo import PyMongo
import os

app = Flask(__name__)
app.config.from_pyfile('config.cfg')
app.config['MONGO_HOST'] = os.environ['DB_PORT_27017_TCP_ADDR']
mongo = PyMongo(app)

import topLaptops.views