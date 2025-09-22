from flask import Flask, render_template, request, redirect, url_for, session, flash
import config
import mysql.connector as connector
from werkzeug.utils import secure_filename
import os
from ultralytics import YOLO
import bcrypt
from collections import Counter
from dotenv import load_dotenv

# Load .env (optional, for DB credentials if needed)
load_dotenv()

app = Flask(__name__)
# Hardcoded secret key
app.secret_key = "220838d7b8826c175083b8a1d69f801fa936bda827d8c2acb569809c088d5396"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_IMAGE = os.path.join(STATIC_DIR, "uploaded_image.jpg")
DETECTED_IMAGE = os.path.join(STATIC_DIR, "detected_image.jpg")

# Ensure static folder exists
os.makedirs(STATIC_DIR, exist_ok=True)

# Database connection
def connect_to_db():
    try:
        connection = connector.connect(**config.mysql_credentials)
        return connection
    except connector.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Home
@app.route('/')
def home():
    return render_template('index.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        email = request.form.get('email')
        vehicle_id = request.form.get('vehicleId')
        contact_number = request.form.get('phoneNumber')
        address = request.form.get('address')
        car_brand = request.form.get('carBrand')
        model = request.form.get('carModel')

        if not all([name, password, email, vehicle_id, contact_number, address, car_brand, model]):
            flash("All fields are required!", "error")
            return render_template('signup.html')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        connection = connect_to_db()
        if connection:
            try:
                with connection.cursor() as cursor:
                    query = '''
                    INSERT INTO user_info (name, password, email, vehicle_id, contact_number, address, car_brand, model)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    '''
                    cursor.execute(query, (name, hashed_password, email, vehicle_id, contact_number, address, car_brand, model))
                    connection.commit()

                session['user_email'] = email  # log in user immediately
                flash("Signup successful!", "success")
                return redirect(url_for('dashboard'))

            except connector.IntegrityError as e:
                if 'Duplicate entry' in str(e):
                    flash("Email already exists. Please use a different email.", "error")
                else:
                    flash("An error occurred while signing up. Please try again.", "error")
            except connector.Error as e:
                print(f"Error executing query: {e}")
                flash("An error occurred while signing up. Please try again.", "error")
        else:
            flash("Database connection failed. Please try again later.", "error")

    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required!", "error")
            return render_template('login.html')

        connection = connect_to_db()
        if connection:
            try:
                with connection.cursor() as cursor:
                    query = "SELECT password FROM user_info WHERE email = %s"
                    cursor.execute(query, (email,))
                    result = cursor.fetchone()
                    if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
                        session['user_email'] = email
                        flash("Login successful!", "success")
                        return redirect(url_for('dashboard'))
                    else:
                        flash("Invalid email or password.", "error")
            except connector.Error as e:
                print(f"Error executing query: {e}")
                flash("An error occurred during login. Please try again.", "error")
        else:
            flash("Database connection failed. Please try again later.", "error")

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Load YOLO model
model_path = os.path.join(MODELS_DIR, "best.pt")
model = YOLO(model_path)

# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
        flash('You need to log in to access the dashboard.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            flash('Please upload an image.', 'error')
            return render_template('dashboard.html')

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            flash('Invalid file type. Please upload an image.', 'error')
            return render_template('dashboard.html')

        # Save uploaded image
        file.save(UPLOAD_IMAGE)

        # Predict using YOLO
        result = model(UPLOAD_IMAGE)
        detected_objects = result[0].boxes
        class_ids = [box.cls.item() for box in detected_objects]
        class_counts = Counter(class_ids)

        # Save detection image
        result[0].save(DETECTED_IMAGE)

        # Fetch part prices
        part_prices = get_part_prices(session['user_email'], class_counts)
        return render_template('estimator.html',  # <- updated template name
                               original_image='uploaded_image.jpg',
                               detected_image='detected_image.jpg',
                               part_prices=part_prices)

    return render_template('dashboard.html')

# Get part prices
def get_part_prices(email, class_counts):
    connection = connect_to_db()
    if connection:
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT car_brand, model FROM user_info WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                if not user_data:
                    return {}
                car_brand = user_data['car_brand']
                car_model = user_data['model']

                prices = {}
                for class_id, count in class_counts.items():
                    part_name = get_part_name_from_id(class_id)
                    if part_name:
                        cursor.execute(
                            "SELECT price FROM car_models WHERE brand = %s AND model = %s AND part = %s",
                            (car_brand, car_model, part_name)
                        )
                        price_data = cursor.fetchone()
                        if price_data:
                            price_per_part = price_data['price']
                            total_price = price_per_part * count
                            prices[part_name] = {'count': count, 'price': price_per_part, 'total': total_price}
                return prices
        except connector.Error as e:
            print(f"Error executing query: {e}")
            return {}
    return {}

# Map class IDs to part names
def get_part_name_from_id(class_id):
    class_names = ['Bonnet', 'Bumper', 'Dickey', 'Door', 'Fender', 'Light', 'Windshield']
    if 0 <= class_id < len(class_names):
        return class_names[int(class_id)]
    return None

if __name__ == '__main__':
    app.run(debug=True)
