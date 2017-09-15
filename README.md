# Catalog App #

Source code for Udacity Project: Build an Item Catalog Application.

The application provides a list of items within a variety of categories as well as provide a user registration and authentication system. Registered users have the ability to post, edit and delete their own items.

### Run the project ###
* Clone this repository
* Install all dependencies: pip install -r requirements.txt
* Add your own Facebook and Google ClientID and Secret Key to the following files:
    * fb_client_secret.json
    * client_secret.json
* Run the project.py file: python project.py

### Screenshot ###
![Alt text](https://raw.githubusercontent.com/jonathanfmachado/udacity-item-catalog-app/master/thumbnail.png)

## API ##
### JSON ###
Examples:

**http://localhost:8000/catalog.json/<item_name>**

Returns the details of a given <item_name>
```javascript
{
  "cat_id": 1,
  "description": "Long description",
  "id": 1,
  "name": "Stick"
}
```

**http://localhost:8000/catalog.json/**

Returns all Categories and Items from the database
```javascript
[
  {
    "id": 1,
    "items": [
      {
        "cat_id": 1,
        "description": "Long description",
        "id": 1,
        "name": "Stick"
      },
      {
        "cat_id": 1,
        "description": "",
        "id": 4,
        "name": "Shinguards"
      }
    ],
    "name": "Soccer"
  },
  {
    "id": 4,
    "items": [],
    "name": "Frisbee"
  },
  {
    "id": 5,
    "items": [
      {
        "cat_id": 5,
        "description": "",
        "id": 2,
        "name": "Goggles"
      },
      {
        "cat_id": 5,
        "description": "",
        "id": 3,
        "name": "Snowboard"
      }
    ],
    "name": "Snowboarding"
  }
]
```
