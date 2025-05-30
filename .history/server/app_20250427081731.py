from flask import Flask, jsonify, request, Blueprint
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restful import Api
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Profile, Content, Category, Subscription, ContentSubscription, Wishlist, Comment, Like, Notification, Share
from datetime import timedelta

app = Flask(__name__)

# ========== CONFIGURATION ==========

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moringa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '4bfbece877bc4c6a9276b4f9f0203a45d722bbfd02728c7d823438120c8b5c91'
app.config['JWT_SECRET_KEY'] = 'd9cbf61a59b0c1e24e9fc62547c3d524c97a35d7e283c902835de5d61b126bde'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=10)

# ========== INITIALIZE EXTENSIONS ==========

db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])
api = Api(app)
jwt = JWTManager(app)

# ========== BLUEPRINT ==========

resources_bp = Blueprint('resources', __name__)




#
# ========== AUTH ROUTES ==========

@resources_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        hashed_password = generate_password_hash(data['password'], method='sha256')
        user = User(email=data['email'], password=hashed_password)
        user.assign_role()
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@resources_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    return jsonify({"error": "Invalid credentials"}), 401

# ========== PROFILE ROUTES ==========

@resources_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=current_user).first()
    if profile:
        return jsonify(profile.to_dict()), 200
    return jsonify({"message": "Profile not found"}), 404

@resources_bp.route('/profile', methods=['POST'])
@jwt_required()
def create_profile():
    data = request.get_json()
    current_user = get_jwt_identity()
    if Profile.query.filter_by(user_id=current_user).first():
        return jsonify({"message": "Profile already exists"}), 400
    profile = Profile(user_id=current_user, bio=data.get('bio'), profile_picture=data.get('profile_picture'), website=data.get('website'))
    db.session.add(profile)
    db.session.commit()
    return jsonify(profile.to_dict()), 201

@resources_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    data = request.get_json()
    current_user = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=current_user).first()
    if not profile:
        return jsonify({"message": "Profile not found"}), 404
    profile.bio = data.get('bio', profile.bio)
    profile.profile_picture = data.get('profile_picture', profile.profile_picture)
    profile.website = data.get('website', profile.website)
    db.session.commit()
    return jsonify(profile.to_dict()), 200

@resources_bp.route('/profile', methods=['DELETE'])
@jwt_required()
def delete_profile():
    current_user = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=current_user).first()
    if not profile:
        return jsonify({"message": "Profile not found"}), 404
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"message": "Profile deleted"}), 200

# ========== CONTENT ROUTES ==========

@resources_bp.route('/content', methods=['POST'])
@jwt_required()
def create_content():
    data = request.get_json()
    user_id = get_jwt_identity()

    content_type = data.get("content_type")
    if not content_type:
        return jsonify({"message": "content_type is required"}), 400

    content = Content(
        title=data.get("title"),
        body=data.get("body"),
        content_type=content_type,
        category_id=data.get("category_id"),
        author_id=user_id
    )

    db.session.add(content)
    db.session.commit()
    return jsonify(content.to_dict()), 201

@resources_bp.route('/content', methods=['GET'])
def get_all_content():
    content = Content.query.all()
    return jsonify([c.to_dict() for c in content]), 200

@resources_bp.route('/content/<int:content_id>', methods=['GET'])
def get_content_by_id(content_id):
    content = Content.query.get_or_404(content_id)
    return jsonify(content.to_dict()), 200

@resources_bp.route('/content/<int:content_id>', methods=['PATCH'])
@jwt_required()
def update_content(content_id):
    content = Content.query.get_or_404(content_id)
    data = request.get_json()
    for key, value in data.items():
        setattr(content, key, value)
    db.session.commit()
    return jsonify(content.to_dict()), 200

@resources_bp.route('/content/<int:content_id>', methods=['DELETE'])
@jwt_required()
def delete_content(content_id):
    content = Content.query.get_or_404(content_id)
    db.session.delete(content)
    db.session.commit()
    return '', 204

# ========== CATEGORY ROUTES ==========

@resources_bp.route('/categories', methods=['GET'])
def get_categories():
    return jsonify([c.to_dict() for c in Category.query.all()]), 200

@resources_bp.route('/categories', methods=['POST'])
@jwt_required()
def add_category():
    data = request.get_json()
    if 'name' not in data:
        return jsonify({"error": "Category name is required"}), 400
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({"message": "Category already exists"}), 400

    category = Category(name=data['name'])
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201

# ========== SUBSCRIPTION ROUTES ==========

@resources_bp.route('/subscribe/category/<int:category_id>', methods=['POST'])
@jwt_required()
def subscribe_category(category_id):
    current_user = get_jwt_identity()
    subscription = Subscription(user_id=current_user, category_id=category_id)
    db.session.add(subscription)
    db.session.commit()
    return jsonify(subscription.to_dict()), 201

@resources_bp.route('/subscribe/content/<int:content_id>', methods=['POST'])
@jwt_required()
def subscribe_content(content_id):
    current_user = get_jwt_identity()
    subscription = ContentSubscription(user_id=current_user, content_id=content_id)
    db.session.add(subscription)
    db.session.commit()
    return jsonify(subscription.to_dict()), 201

# ========== WISHLIST ROUTE ==========

@resources_bp.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    data = request.get_json()
    current_user = get_jwt_identity()
    wishlist = Wishlist(user_id=current_user, content_id=data['content_id'])
    db.session.add(wishlist)
    db.session.commit()
    return jsonify(wishlist.to_dict()), 201

# ========== COMMENT ROUTE ==========

@resources_bp.route('/comment', methods=['POST'])
@jwt_required()
def post_comment():
    data = request.get_json()
    current_user = get_jwt_identity()
    comment = Comment(user_id=current_user, content_id=data['content_id'], text=data['text'])
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201

# ========== LIKE ROUTE ==========

@resources_bp.route('/content/<int:content_id>/like', methods=['POST', 'DELETE'])
@jwt_required()
def toggle_like(content_id):
    current_user = get_jwt_identity()  # Get the current user from the JWT token
    like = Like.query.filter_by(user_id=current_user, content_id=content_id).first()

    if request.method == 'POST':
        if like:
            return jsonify({"message": "Already liked"}), 400
        like = Like(user_id=current_user, content_id=content_id)
        db.session.add(like)
        db.session.commit()

        # Return updated like count
        like_count = Like.query.filter_by(content_id=content_id).count()
        return jsonify({"message": "Liked successfully", "like_count": like_count}), 201

    elif request.method == 'DELETE':
        if not like:
            return jsonify({"message": "Like not found"}), 404
        db.session.delete(like)
        db.session.commit()

        # Return updated like count
        like_count = Like.query.filter_by(content_id=content_id).count()
        return jsonify({"message": "Unliked successfully", "like_count": like_count}), 200
# ========== SHARE ROUTE ==========

@resources_bp.route('/share', methods=['POST'])
@jwt_required()
def share_content():
    data = request.get_json()
    current_user = get_jwt_identity()
    share = Share(user_id=current_user, content_id=data['content_id'])
    db.session.add(share)
    db.session.commit()
    return jsonify(share.to_dict()), 201

# ========== NOTIFICATION ROUTE ==========

@resources_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user = get_jwt_identity()
    notifications = Notification.query.filter_by(user_id=current_user).all()
    return jsonify([n.to_dict() for n in notifications]), 200

# ========== HOME ROUTE ==========

@resources_bp.route('/')
def home():
    return jsonify({"message": "Welcome to the Moringa Social Media Platform!"})

# ========== REGISTER BLUEPRINT ==========

app.register_blueprint(resources_bp, url_prefix='/api')

# ========== CREATE TABLES ==========

with app.app_context():
    db.create_all()

# ========== RUN APP ==========

if __name__ == '__main__':
    app.run(debug=True)
