#!/usr/bin/env python3

from flask import Flask, redirect, url_for

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item


app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind=engine
DBSession = sessionmaker(bind = engine)
session = DBSession()


@app.route('/')
def root():
    return redirect(url_for('show_catalog'))


@app.route('/catalog')
def show_catalog():
    category = session.query(Category).first()
    print(category)
    return 'All Categories and Latest added Items'


@app.route('/catalog/<string:category>/items')
def show_category(category):
    return 'Category {0} and Its Items'.format(category)


@app.route('/catalog/<string:category>/<string:item>')
def show_item(category, item):
    return 'Category {0} and Item {1}'.format(category, item)


@app.route('/catalog/add')
def add_item():
    return 'Add Item'


@app.route('/catalog/<string:category>/add')
def add_item_to_category(category):
    return 'Adding item for Category {0}'.format(category)


@app.route('/catalog/<string:category>/<string:item>/edit')
def edit_item(category, item):
    return 'Edit Item {1} in Category {0}'.format(category, item)


@app.route('/catalog/<string:category>/<string:item>/delete')
def delete_item(category, item):
    return 'Delete Item {1} in Category {0}'.format(category, item)


@app.route('/catalog.json')
def show_json(category, item):
    return 'Delete Item {1} in Category {0}'.format(category, item)


if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000, threaded=False)