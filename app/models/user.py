from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CatalogItem, User


engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# User Helper Functions
def create_user(login_session):
    """
    Create a new user in the database.
    """
    new_user = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_info(user_id):
    """
    Returns an User object based on a given user_id
    """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    """
    Returns an User object based on a given email
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except BaseException:
        return None
