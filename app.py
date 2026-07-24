from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# 1. Konfigurasi Koneksi Database
db_url = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_LMGqD79goEWS@ep-muddy-butterfly-azxyk7tu-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
)

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODEL DATABASE
# ==========================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone or ""
        }

class Product(db.Model):
    __tablename__ = 'products'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255), default='plant_1.png')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": float(self.price),
            "stock": self.stock,
            "description": self.description,
            "image": self.image
        }

# ==========================================
# ENDPOINT / ROUTES
# ==========================================

# --- AUTH & USER ENDPOINTS ---

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({"error": "Semua kolom harus diisi!"}), 400
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "Email sudah terdaftar!"}), 400
        
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "message": "Registrasi berhasil!",
            "user": new_user.to_dict()
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            return jsonify({
                "message": "Login Berhasil",
                "user": user.to_dict()
            }), 200
        else:
            return jsonify({"error": "Email atau password salah!"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>', methods=['GET', 'PUT'])
def manage_user(user_id):
    # Menggunakan db.session.get untuk standar SQLAlchemy 2.0
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "Pengguna tidak ditemukan"}), 404

    if request.method == 'GET':
        return jsonify(user.to_dict()), 200

    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_email = data.get('email', user.email)

            # Cek jika email diubah dan email baru ternyata sudah dipakai user lain
            if new_email != user.email:
                existing_email = User.query.filter_by(email=new_email).first()
                if existing_email:
                    return jsonify({"error": "Email sudah digunakan oleh pengguna lain!"}), 400

            user.name = data.get('name', user.name)
            user.email = new_email
            user.phone = data.get('phone', user.phone)

            db.session.commit()
            return jsonify({
                "message": "Profil berhasil diperbarui",
                "user": user.to_dict()
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

# --- PRODUCT ENDPOINTS ---

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        category_filter = request.args.get('category')
        
        if category_filter and category_filter != 'Semua':
            products = Product.query.filter_by(category=category_filter).all()
        else:
            products = Product.query.all()
            
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint Produk Unggulan (Mengambil 6 produk pertama)
@app.route('/api/products/featured', methods=['GET'])
def get_featured_products():
    try:
        products = Product.query.limit(6).all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint Produk Populer (Mengambil 6 produk berikutnya)
@app.route('/api/products/popular', methods=['GET'])
def get_popular_products():
    try:
        products = Product.query.offset(6).limit(6).all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)