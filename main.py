from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from forms import ProductForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os
import stripe

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

tags = ["Avante-garde", "Y2K", "80s", "Allesandro", "Tech", "Monocrhome", "Ready-to-wear", "Video Game", "activism", "absurdity", "camp"]
promo_codes = ["WIN10", "NEW64", "APPLEBEE12", "DISCOUNT77"]

login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    img_url = db.Column(db.Text, nullable=False)
    vid_url = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    tags = db.Column(db.Text, nullable=True)
    designer = db.Column(db.Text, nullable=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'))
    cart = db.relationship('Cart', backref='user', uselist=False, foreign_keys=[cart_id])

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('CartItem', backref='cart', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


# with app.app_context():
#     db.create_all()

@app.route("/")
def home():
    products = Product.query.all()[::-1][:4]
    return render_template("index.html", products=products)

@app.route("/add-product", methods=["POST", "GET"])
def admin():
    form = ProductForm()

    if form.validate_on_submit():

        new_product = Product(
            name=form.name.data,
            description=form.description.data,
            img_url=form.img_url.data,
            vid_url=form.vid_url.data,
            price=form.price.data,
            designer=form.designer.data,
            tags=form.tags.data
        )

        db.session.add(new_product)
        db.session.commit()
        flash("Product added succesfully", "sucess")
        return redirect(url_for('admin'))


    return render_template("admin.html", form=form)

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    # Check if the user has a cart
    if current_user.is_authenticated:

        if not current_user.cart:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.commit()

            current_user.cart = cart
            db.session.commit()

        # Create a new CartItem and associate it with the user's cart
        cart_item = CartItem(cart_id=current_user.cart.id,
                             product_id=product.id,
                             quantity=1)

        db.session.add(cart_item)
        db.session.commit()

        flash("Product added to cart", "success")
        return redirect(url_for('show_product', id=product.id))

    else:
        flash("You must be logged in to add to your cart", "error")
        return redirect(url_for('show_product', id=product.id))

@app.route("/discover")
def all_products():
    filter_tag = request.args.get('filter')
    products = Product.query.all()

    if filter_tag:
        # Filter products based on the selected tag
        filtered_products = [product for product in products if filter_tag.lower() in product.tags]
    else:
        filtered_products = products

    return render_template("discover.html", products=filtered_products, tags=tags, filter_tag=filter_tag)


@app.route("/newsletter")
def subscribe():
    return render_template("newsletter.html")

@app.route("/login-page", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password_attempt = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(pwhash=user.password, password=password_attempt):
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash("Incorrect credentials.", "eror")
        else:
            flash("Incorrect credentials.", "error")

    return render_template("login.html")

@app.route("/create-account", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        password = request.form.get("password")
        name = request.form.get("name")
        email = request.form.get("email")

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('home'))

    return render_template("signup.html")

@app.route("/log-out")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/product-page/<int:id>")
def show_product(id):
    product = Product.query.get(id)
    product_tags = product.tags.split(",") if product.tags else []

    # Get the selected tags from the query parameters
    selected_tags = request.args.getlist("tag")

    # Check if any tags are selected
    if selected_tags:
        # Filter the product tags based on the selected tags
        product_tags = [tag for tag in product_tags if tag in selected_tags]

    return render_template("product.html", product=product, product_tags=product_tags, selected_tags=selected_tags)

@app.route("/checkout", methods=["GET", "POST"])
def buy_now():

    cart_items = CartItem.query.filter_by(cart_id=current_user.cart_id).all()
    cart_products = [Product.query.get(item.product_id) for item in cart_items]
    num_items = len(cart_products)
    discount = None
    promo = None

    total_cost = 0
    for product in cart_products:
        total_cost += product.price

    if request.method == "POST":

        promo = request.form.get("promo_code")
        if promo in promo_codes:
            discount = total_cost * 0.1
            total_cost -= discount

        return redirect(url_for("buy_now", discount=discount))

    return render_template("checkout.html", products=cart_products, total=total_cost, num_items=num_items, discount=discount, promo=promo)


@app.route("/shopping-cart", methods=["GET", "POST"])
def cart():
    cart_items = CartItem.query.filter_by(cart_id=current_user.cart_id).all()
    cart_products = [Product.query.get(item.product_id) for item in cart_items]
    num_items = len(cart_products)
    total_cost = 0
    for product in cart_products:
        total_cost += product.price

    return render_template("cart.html", products=cart_products, total=total_cost, num_items=num_items)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
