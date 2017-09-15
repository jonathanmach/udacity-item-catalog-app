
from app.models.auth import login_required, show_login
# Create Anti Forgery State Token
from flask import session as login_session
from functools import wraps
from flask import Flask, render_template, url_for, request, redirect, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CatalogItem, User
from flask import Blueprint

api = Blueprint('api', __name__)


engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# API Endpoint
@api.route('/catalog.json/')
def jsonapi():
    """
    Returns a JSON containg all Categories and its items.
    """
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


@api.route('/catalog.json/<item_name>')
def jsonapi_item(item_name):
    """
    Implements a JSON endpoint that serves the same information as displayed in the
    HTML endpoints for an arbitrary item in the catalog.
    """
    item = session.query(CatalogItem).filter_by(name=item_name).one()
    return jsonify(item.serialize)

