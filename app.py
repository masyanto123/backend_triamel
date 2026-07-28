from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
# Konfigurasi CORS terbuka agar Flutter Web / Mobile dapat mengakses API
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ==========================================
# 1. KONFIGURASI KONEKSI DATABASE
# ==========================================
db_url = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_LMGqD79goEWS@ep-muddy-butterfly-azxyk7tu-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
)

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mencegah error SSL tertutup di Railway
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True, 
    "pool_recycle": 300,   
}

db = SQLAlchemy(app)

# ==========================================
# 2. MODEL DATABASE
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

class Address(db.Model):
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    label = db.Column(db.String(50), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    full_address = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "recipient_name": self.recipient_name,
            "phone": self.phone,
            "full_address": self.full_address
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

class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    product = db.relationship('Product', backref=db.backref('cart_items', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            "cart_id": self.id,
            "id": self.product_id,
            "name": self.product.name if self.product else "",
            "price": float(self.product.price) if self.product else 0.0,
            "image": self.product.image if self.product else "plant_1.png",
            "quantity": self.quantity,
            "stock": self.product.stock if self.product else 0
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True) # Menggunakan Integer autoincrement standar
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='Menunggu Pembayaran')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "alamat": self.address,
            "metodePembayaran": self.payment_method,
            "total": float(self.total_price),
            "status": self.status,
            "tanggal": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else "",
            "items": [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.product.name if self.product else "",
            "quantity": self.quantity,
            "price": float(self.price)
        }

# ==========================================
# 3. ENDPOINTS / ROUTES
# ==========================================

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
        db.session.rollback()
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
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "Pengguna tidak ditemukan"}), 404

    if request.method == 'GET':
        return jsonify(user.to_dict()), 200

    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_email = data.get('email', user.email)

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

@app.route('/api/products/featured', methods=['GET'])
def get_featured_products():
    try:
        products = Product.query.limit(6).all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/popular', methods=['GET'])
def get_popular_products():
    try:
        products = Product.query.offset(6).limit(6).all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/addresses', methods=['GET'])
def get_user_addresses(user_id):
    try:
        addresses = Address.query.filter_by(user_id=user_id).all()
        return jsonify([addr.to_dict() for addr in addresses]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/addresses', methods=['POST'])
def add_user_address(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "Pengguna tidak ditemukan!"}), 404

        count = Address.query.filter_by(user_id=user_id).count()
        if count >= 3:
            return jsonify({"error": "Kamu sudah mencapai batas maksimal 3 alamat."}), 400

        data = request.get_json()
        label = data.get('label')
        recipient_name = data.get('recipient_name')
        phone = data.get('phone')
        full_address = data.get('full_address')

        if not label or not recipient_name or not phone or not full_address:
            return jsonify({"error": "Semua field alamat wajib diisi!"}), 400

        new_address = Address(
            user_id=user_id,
            label=label,
            recipient_name=recipient_name,
            phone=phone,
            full_address=full_address
        )
        db.session.add(new_address)
        db.session.commit()

        return jsonify({
            "message": "Alamat berhasil ditambahkan!",
            "address": new_address.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/addresses/<int:address_id>', methods=['DELETE'])
def delete_address(address_id):
    try:
        address = db.session.get(Address, address_id)
        if not address:
            return jsonify({"error": "Alamat tidak ditemukan"}), 404

        db.session.delete(address)
        db.session.commit()
        return jsonify({"message": "Alamat berhasil dihapus"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/cart', methods=['GET'])
def get_cart(user_id):
    try:
        cart_items = Cart.query.filter_by(user_id=user_id).all()
        return jsonify([item.to_dict() for item in cart_items]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/<int:user_id>/cart', methods=['POST'])
def add_to_cart(user_id):
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id:
            return jsonify({"error": "Product ID wajib diisi!"}), 400

        existing_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()

        if existing_item:
            existing_item.quantity += quantity
        else:
            new_cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(new_cart_item)

        db.session.commit()
        return jsonify({"message": "Produk berhasil ditambahkan ke keranjang"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ==========================================
# 4. ORDER / PESANAN ENDPOINTS (BARU)
# ==========================================

# Ambil daftar pesanan user
@app.route('/api/user/<int:user_id>/orders', methods=['GET'])
def get_user_orders(user_id):
    try:
        orders = Order.query.filter_by(user_id=user_id).all()
        return jsonify([order.to_dict() for order in orders]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Buat pesanan baru (Checkout)
# Buat pesanan baru (Checkout) dengan Pengurangan Stok Otomatis
@app.route('/api/user/<int:user_id>/orders', methods=['POST'])
def create_order(user_id):
    try:
        data = request.get_json()
        address = data.get('address')
        payment_method = data.get('payment_method')
        total_price = data.get('total_price')
        items = data.get('items', []) # Berisi list produk dari keranjang

        if not address or not payment_method or not total_price or not items:
            return jsonify({"error": "Data pesanan tidak lengkap!"}), 400

        # Simpan ke tabel orders
        new_order = Order(
            user_id=user_id,
            address=address,
            payment_method=payment_method,
            total_price=total_price,
            status='Menunggu Pembayaran'
        )
        db.session.add(new_order)
        db.session.flush() # Agar new_order.id langsung terbentuk

        # Simpan detail item ke tabel order_items DAN potong stok produk
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            price = item.get('price')

            # 1. Cari produk berdasarkan product_id
            product = db.session.get(Product, product_id)
            if not product:
                db.session.rollback()
                return jsonify({"error": f"Produk dengan ID {product_id} tidak ditemukan!"}), 404

            # 2. Validasi Ketersediaan Stok
            if product.stock < quantity:
                db.session.rollback()
                return jsonify({
                    "error": f"Stok untuk produk '{product.name}' tidak mencukupi! Tersisa {product.stock} pcs."
                }), 400

            # 3. KEKURANGAN UTAMA SEBELUMNYA: KURANGI STOK PRODUK DI SINI!
            product.stock -= quantity

            # 4. Simpan ke OrderItem
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product_id,
                quantity=quantity,
                price=price
            )
            db.session.add(order_item)

        # Hapus keranjang user setelah checkout berhasil
        Cart.query.filter_by(user_id=user_id).delete()

        # Simpan semua perubahan (Order + OrderItem + Pengurangan Stok + Hapus Cart) secara Atomic
        db.session.commit()

        return jsonify({
            "message": "Pesanan berhasil dibuat dan stok telah diperbarui!",
            "order": new_order.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)