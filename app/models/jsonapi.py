
# API Endpoint
@app.route('/catalog.json/')
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


@app.route('/catalog.json/<item_name>')
def jsonapi_item(item_name):
    """
    Implements a JSON endpoint that serves the same information as displayed in the
    HTML endpoints for an arbitrary item in the catalog.
    """
    item = session.query(CatalogItem).filter_by(name=item_name).one()
    return jsonify(item.serialize)

