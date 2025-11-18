"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Favorite, Planet, People
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()

    name = data.get('name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')

    if not name or last_name:
        return jsonify({"error": "Name and Last Name are required."}), 400
    if not email or password:
        return jsonify({"errror": "Email and password are required."}), 400
    
    user_exists = User.query.filter_by(email=email).first()
    if user_exists:
        return jsonify({"error": "User alredy exists."}), 400
    
    new_user = User(
        name=name,
        last_name=last_name,
        email=email,
        password=password    
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User create succesfully."}, new_user.serialize()), 201

@app.route('/user/favorites', methods=['GET'])
def get_user_favorites():
    user_id = request.args.get('user_id')    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not finded."}),404
    
    favorites = Favorite.query.filter_by(user_id=user_id).all()
    if not favorites:
        return jsonify({"msg": "Favorites not founded in this user."}), 404
    
    result = []
    for fav in favorites:
        if fav.planet_id and fav.planet:
            result.append({
                "id":fav.id,
                "type": "planet",
                "planet": fav.planet.serialize()
            })
        elif fav.people_id and fav.people:
            result.append({
                "id":fav.id,
                "type": "people",
                "people": fav.people.serialize()
            })
        
    return jsonify(result), 200

@app.route('/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(planet_id):
    user_id = request.args.get('user_id')    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not finded."}),404
    
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"msg": "Planet id not founded."}), 404
    favorite_exists = Favorite.query.filter_by(
        user_id=user_id,
        planet_id=planet_id 
    ).first()
    if favorite_exists:
        return jsonify({"msg": "Planet already in favorites."}), 409
    
    new_favorite = Favorite(
        user_id=user_id,
        planet_id=planet_id,
        people_id=None
    )

    db.session.add(new_favorite)
    db.session.commit()

    return jsonify({
        "msg": "Planet added to favorites.",
        "favorite": new_favorite.serialize()
    }), 201

@app.route('/favorite/people/<int:people_id>')
def add_favorite_people(people_id):
    user_id = request.args.get('user_id')    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not finded."}),404
    
    people = People.query.get(people_id)
    if not people:
        return jsonify ({"msg": "People id not founded."}), 404
    
    favorite_exists = Favorite.query.filter_by(
        user_id=user_id,
        people_id=people_id
    ).first()
    if favorite_exists:
        return jsonify({"msg": "People already in favorites"}), 409
    
    new_favorite = Favorite(
        user_id=user_id,
        planet_id=None,
        people_id=people_id
    )
    db.session.add(new_favorite)
    db.session.commit()

@app.route('/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(planet_id):
    user_id = request.args.get('user_id')    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not finded."}),404
    
    favorite = Favorite.query.filter_by(
        user_id=user_id,
        planet_id=planet_id
    ).first()

    if not favorite:
        return jsonify({"msg": "Not planet founded in this user favorites."}), 404
    
    db.session.delete(favorite)
    db.session.commit()

    return jsonify({"msg": "Planet deleted succesfully."}), 200

@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_people(people_id):
    user_id = request.args.get('user_id')    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not finded."}),404
    
    favorite = Favorite.query.filter_by(
        user_id=user_id,
        people_id=people_id
    ).first()

    if not favorite:
        return jsonify({"msg": "People not founded in this user favorites."}), 404
    
    db.session.delete(favorite)
    db.session.commit()

    return jsonify({"msg": "People deleted succesfully."}), 200

#----------------People Routes----------------

@app.route('/people', methods=['GET'])
def get_all_people():
    peoples = People.query.all()
    peoples_serialized = [people.serialize() for people in peoples]
    
    if peoples_serialized:
        return jsonify(peoples_serialized), 200
    else:
        return jsonify({"msg": "Peoples dosn't exists."}), 404


@app.route('/people/<int:people_id>', methods=['GET'])
def get_person_by_id(people_id):
    people = People.query.get(people_id)
    if people:
        return jsonify(people.serialize()), 200
    else:
        return jsonify({"msg": "People id not founded."}), 404


#----------------------Planets Routes----------------

@app.route('/planets', methods=['GET'])
def get_all_planets():
    planets = Planet.query.all()
    planets_serialized = [planet.serialize() for planet in planets]
    if planets_serialized:
        return jsonify(planets_serialized), 200
    else:
        return jsonify({"msg": "Planets dosn't exists."}), 404


@app.route('/planets/<int:planet_id>', methods=['GET'])
def get_planet_by_id(planet_id):
    planet = Planet.query.get(planet_id)
    if planet:
        return jsonify(planet.serialize()), 200
    else:
        return jsonify({"msg": "Planet id not founded"}), 404


# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
