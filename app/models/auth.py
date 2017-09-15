from functools import wraps

from app.models.user import get_user_id, create_user
from flask import Flask, render_template, url_for, request, redirect, jsonify, Blueprint
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

auth = Blueprint('auth', __name__, template_folder='templates')

# Google Client ID
CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']


def login_required(func):
    @wraps(func)  # this requires an import
    def wrapper():
        if 'username' not in login_session:
            return redirect('login')
        else:
            func()

    return wrapper


@auth.route('/gconnect', methods=['POST', ])
def gconnect():
    """
    Gathers data from Google Sign In API and places it inside a session variable.
    """
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
    return output


@auth.route('/fbconnect', methods=['POST', ])
def fbconnect():
    """
    Gathers data from Facebook Sign In API and places it inside a session variable.
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

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

    return output


@auth.route('/login')
def show_login():
    """
    Renders the login page.
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@auth.route('/logout')
def gdisconnect():
    """
    Check if the existing login is Google or Facebook based. Then,
    revokes the access token and delete login_session variables.
    """
    if login_session['provider'] == 'google':
        # Only disconnect a connected user
        access_token = login_session.get('access_token')
        if access_token is None:
            response = make_response(
                json.dumps('Current user not connected.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

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
