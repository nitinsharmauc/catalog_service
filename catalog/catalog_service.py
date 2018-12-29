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
    return render_template("catalog.html", categories=categories, items=items)


@app.route('/catalog/<string:categoryName>/items')
def show_category(categoryName):
    categories = session.query(Category).all()
    selectedCategory = session.query(Category).filter_by(name=categoryName).one()
    items = session.query(Item).filter_by(category_id=selectedCategory.id).all()
    return render_template("category.html", categories=categories, items=items, selectedCategory=selectedCategory)


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


@app.route('/catalog/<string:categoryName>/<string:itemName>')
def show_item(categoryName, itemName):
    print(itemName)
    item = session.query(Item).filter_by(title=itemName).one()
    if(item):
        print(item.title)
        return render_template("item.html", item=item)
    else:
        flash('Item {0} in category {1} not found'.format(itemName, categoryName))
        return redirect(url_for('show_catalog'))


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



@app.route('/catalog/<string:categoryName>/add')
def add_item_to_category(categoryName):
    return 'Adding item for Category {0}'.format(categoryName)


@app.route('/catalog/<string:categoryName>/<string:itemName>/edit', methods=['GET', 'POST'])
def edit_item(categoryName, itemName):
    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            category = session.query(Category).filter_by(name=category_name).one()
            item = session.query(Item).filter_by(title=itemName).one()
            if category and item:
                item.title = request.form['title']
                item.description = request.form['description']
                item.category_id = category.id
                session.add(item)
                session.commit()
                flash('New Item added successfully!')
            else:
                flash('Item add error. Category or Item selected not present!')
        return redirect(url_for('show_catalog'))
    else:
        categories = session.query(Category).all()
        category = session.query(Category).filter_by(name=categoryName).one()
        item = session.query(Item).filter_by(title=itemName).one()
        return render_template('editItem.html', categories=categories, category=category, item=item)


@app.route('/catalog/<string:categoryName>/<string:itemName>/delete')
def delete_item(categoryName, itemName):
    return 'Delete Item {1} in Category {0}'.format(categoryName, itemName)


@app.route('/catalog.json')
def show_json(category, item):
    return 'Delete Item {1} in Category {0}'.format(category, item)


if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000, threaded=False)