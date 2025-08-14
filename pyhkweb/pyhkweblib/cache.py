from flask_caching import Cache

# This is imported and initialized in pyhkweb.py, and is imported and
# used in pyhk_blueprint.py.  
# https://stackoverflow.com/questions/11020170/using-flask-extensions-in-flask-blueprints
cache = Cache()
