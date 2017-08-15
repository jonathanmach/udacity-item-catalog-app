from flask import Flask, render_template, url_for, request, redirect, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CatalogItem, User
# Create Anti Forgery State Token
from flask import session as login_session
import random
import string
# GConnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
from flask import make_response

app = Flask(__name__)

# Google Client ID
CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# User Helper Functions
def create_user(login_session):
    new_user = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except BaseException:
        return None


def populate_database():
    session.add(Category(name="Soccer"))
    session.add(Category(name="Basketball"))
    session.add(Category(name="Baseball"))
    session.add(Category(name="Frisbee"))
    session.add(Category(name="Snowboarding"))
    session.add(Category(name="Rock Climbing"))
    session.add(Category(name="Skating"))
    session.add(Category(name="Hockey"))
    session.commit()


@app.route('/gconnect', methods=['POST', ])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
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
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
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
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # Retrieve User Info
    user_id = get_user_id(login_session['email'])
    if not user_id:
        login_session['user_id'] = create_user(login_session)
    else:
        login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    # flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/fbconnect', methods=['POST', ])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secret.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secret.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?' \
          'grant_type=fb_exchange_token&client_id=%s&' \
          'client_secret=%s&fb_exchange_token=%s' % (app_id,
                                                     app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    '''
    Due to the formatting for the result from the server token exchange we
    have to split the token first on commas and select the first index which
    gives us the key : value for the server access token then we split it on
    colons to pull out the actual token value     and replace the remaining
    quotes with nothing so that it can be used directly in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?' \
          'access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?' \
          'access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    # flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/login')
def show_login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout')
def gdisconnect():
    if login_session['provider'] == 'google':
        # Only disconnect a connected user
        access_token = login_session.get('access_token')
        if access_token is None:
            print 'Access Token is None'
            response = make_response(
                json.dumps('Current user not connected.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        print 'In gdisconnect access token is %s', access_token
        print 'User name is: '
        print login_session['username']

        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        # Execute HTTP GET request to revoke the current token
        url = 'https://accounts.google.com/o/oauth2/revoke?' \
              'token=%s' % access_token
        h = httplib2.Http()
        result = h.request(url, 'GET')[0]
        if result['status'] == '200':
            response = make_response(
                json.dumps('Successfully disconnected.'), 200)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            response = make_response(
                json.dumps(
                    'Failed to revoke token for given user.',
                    400))
            response.headers['Content-Type'] = 'application/json'
            return response

    if login_session['provider'] == 'facebook':
        facebook_id = login_session['facebook_id']
        # The access token must me included to successfully logout
        access_token = login_session['access_token']
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
            facebook_id, access_token)
        h = httplib2.Http()
        result = h.request(url, 'DELETE')[1]
        del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        return "you have been logged out"


@app.route('/')
def main():
    """Returns all categories and items"""
    cat = session.query(Category).all()
    items = session.query(CatalogItem).all()
    return render_template(
        'latest.html',
        item_list=items,
        categories=cat,
        login_session=login_session)


# Item details
@app.route('/catalog/<category_name>/<item_name>/')
def catalog(category_name, item_name):
    cat = session.query(Category).all()
    selected_category = session.query(
        Category).filter_by(name=category_name).one()
    item = session.query(CatalogItem).filter_by(
        name=item_name, category_id=selected_category.id).one()
    iscreator = False
    if item.user_id == login_session['user_id']:
        iscreator = True

    return render_template(
        'item-details.html',
        categories=cat,
        item=item,
        login_session=login_session,
        iscreator=iscreator)


# Items from specific Category
@app.route('/catalog/<category_name>/items/')
def catalog_items(category_name):
    cat = session.query(Category).all()
    selected_category = session.query(
        Category).filter_by(name=category_name).one()
    items = session.query(CatalogItem).filter_by(
        category_id=selected_category.id)
    return render_template(
        'category-items.html',
        item_list=items,
        categories=cat,
        category_name=category_name,
        login_session=login_session)


# Update an item
@app.route('/catalog/<item_name>/edit/', methods=['GET', 'POST'])
def edit_item(item_name):
    if 'username' not in login_session:
        return redirect(url_for('show_login'))

    if request.method == 'POST':
        item = session.query(CatalogItem).filter_by(name=item_name).one()
        # Get posted values
        title = request.form['title']
        description = request.form['description']
        category_id = request.form['category_id']

        # Set new values
        item.name = title
        item.description = description
        item.category_id = category_id
        session.add(item)
        session.commit()

        return redirect(
            url_for(
                'catalog',
                category_name=item.category.name,
                item_name=item.name,
            ))

    else:
        cat = session.query(Category).all()
        item = session.query(CatalogItem).filter_by(name=item_name).one()
        if item.user_id != login_session['user_id']:
            return 'Not allowed'
        return render_template(
            'edit-item.html',
            item=item,
            categories=cat,
            login_session=login_session)


# Add a new item
@app.route('/catalog/add_item/', methods=['GET', 'POST'])
def add_item():
    if 'username' not in login_session:
        return redirect(url_for('show_login'))

    if request.method == 'POST':
        # Get posted values
        title = request.form['title']
        description = request.form['description']
        category_id = request.form['category_id']

        # Create new item
        new_item = CatalogItem(
            name=title,
            description=description,
            category_id=category_id,
            user_id=login_session['user_id'])
        session.add(new_item)
        session.commit()

        return redirect(
            url_for(
                'catalog_items',
                category_name=new_item.category.name))

    else:
        cat = session.query(Category).all()
        return render_template(
            'add-item.html',
            categories=cat,
            login_session=login_session)


# Delete an existing item
@app.route('/catalog/<item_name>/delete/', methods=['GET', 'POST'])
def delete_item(item_name):
    if 'username' not in login_session:
        return redirect(url_for('show_login'))

    cat = session.query(Category).all()
    item = session.query(CatalogItem).filter_by(name=item_name).one()
    if item.user_id != login_session['user_id']:
        return 'Not allowed'

    if request.method == 'POST':
        cat_name = item.category.name
        session.delete(item)
        session.commit()
        return redirect(url_for('catalog_items', category_name=cat_name))
    else:
        return render_template(
            'delete-item.html',
            item=item,
            categories=cat,
            login_session=login_session)


# API Endpoint
@app.route('/catalog.json/')
def jsonapi():
    all_cat = session.query(Category).all()
    json_response = []
    for i in all_cat:
        cat = i.serialize
        all_items = session.query(CatalogItem).filter_by(category_id=i.id)
        items = []
        for x in all_items:
            items.append(x.serialize)
        cat['items'] = items
        json_response.append(cat)
    return jsonify(json_response)


if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
