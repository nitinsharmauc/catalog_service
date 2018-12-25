#!/usr/bin/env python3

from flask import Flask, redirect, url_for, render_template, request, flash

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item


app = Flask(__name__)

engine = create_engine('postgresql:///catalog')
Base.metadata.bind=engine
DBSession = sessionmaker(bind = engine)
session = DBSession()


@app.route('/')
def root():
    return redirect(url_for('show_catalog'))


@app.route('/catalog')
def show_catalog():
    categories = session.query(Category).all()
    items = session.query(Item).order_by(Item.creation_date.desc()).limit(3)
    return render_template("main.html", categories=categories, items=items)


@app.route('/catalog/<string:category>/items')
def show_category(category):
    return 'Category {0} and Its Items'.format(category)


@app.route('/catalog/categories/new', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        if request.form['name']:
            newCategory = Category(name=request.form['name'])
            session.add(newCategory)
            session.commit()
            flash('New Category added successfully!')
        return redirect(url_for('show_catalog'))
    else:
        return render_template('newCategory.html')


@app.route('/catalog/<string:category>')
def edit_category(category):
    return 'Edit Category {0}'.format(category)


@app.route('/catalog/<string:category>/delete')
def delete_category(category):
    return 'Delete Category {0}'.format(category)


@app.route('/catalog/<string:category>/<string:item>')
def show_item(category, item):
    return 'Category {0} and Item {1}'.format(category, item)


@app.route('/catalog/items/new', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            category = session.query(Category).filter_by(name=category_name).one()
            if category:
                newItem = Item(title=request.form['title'], description=request.form['description'], category_id=category.id)
                session.add(newItem)
                session.commit()
                flash('New Item added successfully!')
            else:
                flash('Item add error. Category selected not present!')
        return redirect(url_for('show_catalog'))
    else:
        categories = session.query(Category).all()
        return render_template('newItem.html', categories=categories)



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