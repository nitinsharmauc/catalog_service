#!/usr/bin/env python3

from flask import Flask, redirect,\
    url_for, render_template,\
    request, flash, jsonify
# imports for the login
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import random
import string

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, exc
from database_setup import Base, Category, Item, User


app = Flask(__name__)

engine = create_engine('postgresql:///catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog app Client"


def __render_template_with_state(template_name_or_list, **context):
    """Utility function to create secret session key as well as
    login checks, before rendering any page
    """
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session["state"] = state
    user_logged_in = 'user_id' in login_session
    return render_template(template_name_or_list, STATE=state,
                           user_logged_in=user_logged_in,
                           **context)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    flash("you are now logged in as %s" % login_session['username'])

    return output


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    responseData = h.request(url, 'GET')
    result = responseData[0]

    str_response = responseData[1].decode('utf-8')
    response_json = json.loads(str_response)

    if result['status'] == '200' \
            or response_json.get('error') == "invalid_token":
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']

        flash('Successfully logged out')
    else:
        # For whatever reason, the given token was invalid.
        flash('Failed to logoff. Failed to revoke token for given user.')

    return redirect(url_for('show_catalog'))


def create_user(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_info(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except exc.NoResultFound:
        return None


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except exc.NoResultFound:
        return None


@app.route('/')
def root():
    return redirect(url_for('show_catalog'))


@app.route('/catalog')
def show_catalog():
    categories = session.query(Category).all()
    items = session.query(Item).order_by(Item.creation_date.desc()).limit(3)
    return __render_template_with_state("catalog.html", categories=categories,
                                        items=items)


@app.route('/catalog/<string:category_name>/items')
def show_category(category_name):
    categories = session\
        .query(Category)\
        .all()

    try:
        selected_category = session\
            .query(Category)\
            .filter_by(name=category_name)\
            .one()
    except exc.NoResultFound:
        flash('{} not found'.format(category_name))
        return redirect(url_for('show_catalog'))

    items = session\
        .query(Item)\
        .filter_by(category_id=selected_category.id)\
        .all()

    user_authorized = 'user_id' in login_session and\
                      selected_category.user.id == login_session["user_id"]

    return __render_template_with_state("category.html",
                                        categories=categories,
                                        items=items,
                                        selectedCategory=selected_category,
                                        user_authorized=user_authorized)


@app.route('/catalog/categories/new', methods=['GET', 'POST'])
def add_category():
    if 'user_id' not in login_session:
        flash('Please login to add new category!')
        return redirect(url_for('show_catalog'))
    if request.method == 'POST':
        if request.form['name']:
            new_category = Category(name=request.form['name'],
                                    user_id=login_session['user_id'])
            session.add(new_category)
            session.commit()
            flash('New Category added successfully!')
        return redirect(url_for('show_catalog'))
    else:
        return __render_template_with_state('newCategory.html')


@app.route('/catalog/<string:category_name>/edit', methods=['GET', 'POST'])
def edit_category(category_name):
    try:
        category = session\
            .query(Category)\
            .filter_by(name=category_name)\
            .one()
    except exc.NoResultFound:
        flash('{} not found'.format(category_name))
        return redirect(url_for('show_catalog'))

    if category:
        if 'user_id' in login_session and \
                category.user_id != login_session['user_id']:
            flash('You are not authorized to edit {}!'
                  .format(category.name))
            return redirect(url_for('show_catalog'))
        if request.method == 'POST':
            if request.form['name']:
                category.name = request.form['name']
                session.add(category)
                session.commit()
                flash('Category {0} edited successfully!'
                      .format(category_name))
            return redirect(url_for('show_catalog'))
        else:
            return __render_template_with_state('editCategory.html',
                                                category_name=category_name)
    else:
        flash('Category {0} not found'.format(category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/<string:category_name>/delete', methods=['GET', 'POST'])
def delete_category(category_name):
    try:
        category = session\
            .query(Category)\
            .filter_by(name=category_name)\
            .one()
    except exc.NoResultFound:
        flash('{} not found'.format(category_name))
        return redirect(url_for('show_catalog'))

    if category:
        if 'user_id' in login_session and\
                category.user_id != login_session['user_id']:
            flash('You are not authorized to delete {}'
                  .format(category.name))
            return redirect(url_for('show_catalog'))
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
            return __render_template_with_state("deleteCategory.html",
                                                category=category)
    else:
        flash('Category {} not found'.format(category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/<string:category_name>/<string:item_name>')
def show_item(category_name, item_name):
    try:
        item = session\
            .query(Item)\
            .filter_by(title=item_name)\
            .one()
    except exc.NoResultFound:
        flash('{} not found'.format(item_name))
        return redirect(url_for('show_catalog'))

    user_authorized = 'user_id' in login_session and \
                      item.user_id == login_session['user_id']

    if item:
        return __render_template_with_state("item.html", item=item,
                                            user_authorized=user_authorized)
    else:
        flash('Item {0} in category {1} not found'
              .format(item_name, category_name))
        return redirect(url_for('show_catalog'))


@app.route('/catalog/items/new', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in login_session:
        flash('Please login to add new Item!')
        return redirect(url_for('show_catalog'))

    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            try:
                category = session\
                    .query(Category)\
                    .filter_by(name=category_name)\
                    .one()
            except exc.NoResultFound:
                flash('Item add error. Category selected not present!')
                return redirect(url_for('show_catalog'))

            if category.user_id != login_session['user_id']:
                flash('You are not authorized to add item to {}'
                      .format(category.name))
                return redirect(url_for('show_catalog'))

            new_item = Item(title=request.form['title'],
                            description=request.form['description'],
                            category_id=category.id,
                            user_id=category.user_id)

            session.add(new_item)
            session.commit()
            flash('New Item added successfully!')

        return redirect(url_for('show_catalog'))
    else:
        categories = session\
            .query(Category)\
            .filter_by(user_id=login_session['user_id'])\
            .all()
        return __render_template_with_state('newItem.html',
                                            categories=categories,
                                            category=None)


@app.route('/catalog/<string:category_name>/items/new',
           methods=['GET', 'POST'])
def add_item_to_category(category_name):
    if 'user_id' not in login_session:
        flash('Please login to add new Item!')
        return redirect(url_for('show_catalog'))

    try:
        category = session\
            .query(Category)\
            .filter_by(name=category_name)\
            .one()
    except exc.NoResultFound:
        flash('{} not found'.format(category_name))
        return redirect(url_for('show_catalog'))

    if request.method == 'POST':
        if request.form['title']:
            if category.user_id != login_session['user_id']:
                flash('You are not authorized to add item to {}'
                      .format(category.name))
                return redirect(url_for('show_catalog'))

            new_item = Item(title=request.form['title'],
                            description=request.form['description'],
                            category_id=category.id)
            session.add(new_item)
            session.commit()
            flash('New Item added successfully!')
        return redirect(url_for('show_catalog'))
    else:
        return __render_template_with_state('newItem.html',
                                            categories=None,
                                            category=category)


@app.route('/catalog/<string:category_name>/<string:item_name>/edit',
           methods=['GET', 'POST'])
def edit_item(category_name, item_name):
    if 'user_id' not in login_session:
        flash('Please login to edit an Item!')
        return redirect(url_for('show_catalog'))

    if request.method == 'POST':
        if request.form['title']:
            category_name = request.form['category']
            try:
                category = session\
                    .query(Category)\
                    .filter_by(name=category_name)\
                    .one()
            except exc.NoResultFound:
                flash('{} not found'.format(category_name))
                return redirect(url_for('show_catalog'))

            if category.user_id != login_session['user_id']:
                flash('You are not authorized to add item to {}'
                      .format(category_name))
                return redirect(url_for('show_catalog'))

            try:
                item = session\
                    .query(Item)\
                    .filter_by(title=item_name)\
                    .one()
            except exc.NoResultFound:
                flash('{} not found'.format(item_name))
                redirect(url_for('show_catalog'))

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
        categories = session\
            .query(Category)\
            .filter_by(user_id=login_session['user_id'])\
            .all()
        try:
            category = session\
                .query(Category)\
                .filter_by(name=category_name,
                           user_id=login_session['user_id'])\
                .one()
            item = session\
                .query(Item)\
                .filter_by(title=item_name)\
                .one()
        except exc.NoResultFound:
            flash('{0} or {1} not found'.format(category_name, item_name))
            return redirect(url_for('show_catalog'))

        return __render_template_with_state('editItem.html',
                                            categories=categories,
                                            category=category,
                                            item=item)


@app.route('/catalog/items/<string:item_name>/delete', methods=['GET', 'POST'])
def delete_item(item_name):
    if 'user_id' not in login_session:
        flash('Please login to delete an Item!')
        return redirect(url_for('show_catalog'))

    try:
        item = session.query(Item).filter_by(title=item_name).one()
    except exc.NoResultFound:
        flash('{} not found'.format(item_name))
        return redirect(url_for('show_catalog'))

    if item.user_id != login_session['user_id']:
        flash('You are not authorized to delete item {}'
              .format(item_name))

    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash('Item {0} deleted successfully !'.format(item.title))
        return redirect(url_for('show_catalog'))
    else:
        return __render_template_with_state("deleteItem.html", item=item)


@app.route('/catalog/json')
def catalog_json():
    categories = session.query(Category).all()
    return jsonify(Categories=[c.serialize for c in categories])


@app.route('/catalog/<string:category_name>/json')
def category_json(category_name):
    try:
        category = session\
            .query(Category)\
            .filter_by(name=category_name)\
            .one()
    except exc.NoResultFound:
        return jsonify(Error='Category {0} not found'
                       .format(category_name))

    return jsonify(Categories=category.serialize)


@app.route('/catalog/<string:category_name>/<string:item_name>/json')
def item_json(category_name, item_name):
    try:
        category = session.query(Category).filter_by(name=category_name).one()
        item = session.query(Item).filter_by(title=item_name).one()
    except exc.NoResultFound:
        return jsonify(
            Error='Item or Category not found')

    if item.category_id != category.id:
        return jsonify(Error='Item {0} does not belong to Category {1}'
                       .format(item_name, category_name))

    return jsonify(Categories=item.serialize)


if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000, threaded=False)
