#!/usr/bin/env python3

from flask import Flask, redirect, url_for, render_template, request, flash

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item


app = Flask(__name__)

engine = create_engine('postgresql:///catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
def root():
    return redirect(url_for('show_catalog'))


@app.route('/catalog')
def show_catalog():
    categories = session.query(Category).all()
    items = session.query(Item).order_by(Item.creation_date.desc()).limit(3)
    return render_template("catalog.html", categories=categories, items=items)


@app.route('/catalog/<string:category_name>/items')
def show_category(category_name):
    categories = session\
        .query(Category)\
        .all()

    selected_category = session\
        .query(Category)\
        .filter_by(name=category_name)\
        .one()

    items = session\
        .query(Item)\
        .filter_by(category_id=selected_category.id)\
        .all()

    return render_template("category.html",
                           categories=categories,
                           items=items,
                           selectedCategory=selected_category)


@app.route('/catalog/categories/new', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        if request.form['name']:
            new_category = Category(name=request.form['name'])
            session.add(new_category)
            session.commit()
            flash('New Category added successfully!')
        return redirect(url_for('show_catalog'))
    else:
        return render_template('newCategory.html')


@app.route('/catalog/<string:category_name>', methods=['GET', 'POST'])
def edit_category(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    if category:
        if request.method == 'POST':
            if request.form['name']:
                category.name = request.form['name']
                session.add(category)
                session.commit()
                flash('Category {0} edited successfully!'
                      .format(category_name))
            return redirect(url_for('show_catalog'))
        else:
            return render_template('editCategory.html',
                                   category_name=category_name)
    else:
        flash('Category {0} not found'.format(category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/<string:category_name>/delete', methods=['GET', 'POST'])
def delete_category(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    if category:
        if request.method == 'POST':
            items = session\
                .query(Item)\
                .filter_by(category_id=category.id)\
                .delete()

            session.delete(category)
            session.commit()
            flash('Category {0} deleted successfully !'
                  .format(category.name))
            return redirect(url_for('show_catalog'))
        else:
            return render_template("deleteCategory.html",
                                   category=category)
    else:
        flash('Category {} not found'.format(category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/<string:category_name>/<string:item_name>')
def show_item(category_name, item_name):
    item = session\
        .query(Item)\
        .filter_by(title=item_name)\
        .one()

    if item:
        return render_template("item.html", item=item)
    else:
        flash('Item {0} in category {1} not found'
              .format(item_name, category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/items/new', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            category = session\
                .query(Category)\
                .filter_by(name=category_name)\
                .one()
            if category:
                new_item = Item(title=request.form['title'],
                                description=request.form['description'],
                                category_id=category.id)
                session.add(new_item)
                session.commit()
                flash('New Item added successfully!')
            else:
                flash('Item add error. Category selected not present!')
        return redirect(url_for('show_catalog'))
    else:
        categories = session.query(Category).all()
        return render_template('newItem.html',
                               categories=categories,
                               category=None)


@app.route('/catalog/<string:category_name>/items/new',
           methods=['GET', 'POST'])
def add_item_to_category(category_name):
    category = session\
        .query(Category)\
        .filter_by(name=category_name)\
        .one()
    if request.method == 'POST':
        if request.form['title']:
            if category:
                new_item = Item(title=request.form['title'],
                                description=request.form['description'],
                                category_id=category.id)
                session.add(new_item)
                session.commit()
                flash('New Item added successfully!')
            else:
                flash('Item add error. Category selected not present!')
        return redirect(url_for('show_catalog'))
    else:
        return render_template('newItem.html',
                               categories=None,
                               category=category)


@app.route('/catalog/<string:category_name>/<string:item_name>/edit',
           methods=['GET', 'POST'])
def edit_item(category_name, item_name):
    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            category = session\
                .query(Category)\
                .filter_by(name=category_name)\
                .one()

            item = session\
                .query(Item)\
                .filter_by(title=item_name)\
                .one()

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
        category = session.query(Category).filter_by(name=category_name).one()
        item = session\
            .query(Item)\
            .filter_by(title=item_name)\
            .one()
        return render_template('editItem.html',
                               categories=categories,
                               category=category,
                               item=item)


@app.route('/catalog/items/<string:itemName>/delete', methods=['GET', 'POST'])
def delete_item(item_name):
    item = session.query(Item).filter_by(title=item_name).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash('Item {0} deleted successfully !'.format(item.title))
        return redirect(url_for('show_catalog'))
    else:
        return render_template("deleteItem.html", item=item)


@app.route('/catalog.json')
def show_json(category, item):
    return 'Delete Item {1} in Category {0}'.format(category, item)


if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000, threaded=False)
