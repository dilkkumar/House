from flask import Flask, render_template, request, url_for, redirect, session, flash
import joblib
import numpy as np
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure, OperationFailure

# Load environment variables
load_dotenv()

# Load the trained model
model = joblib.load('house_price_model.pkl')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# MongoDB Atlas configuration
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME', 'house_price_prediction')

class MongoDBManager:
    def __init__(self):
        self.client = None
        self.db = None
        
    def connect(self):
        try:
            self.client = MongoClient(
                MONGODB_URI,
                connectTimeoutMS=30000,
                socketTimeoutMS=None,
                maxPoolSize=50,
                retryWrites=True,
                w="majority"
            )
            # Verify the connection
            self.client.admin.command('ping')
            self.db = self.client[DB_NAME]
            
            # Create indexes if they don't exist
            self.db.users.create_index([('username', 1)], unique=True)
            self.db.users.create_index([('email', 1)], unique=True)
            
            print("Successfully connected to MongoDB Atlas!")
            return True
        except ConnectionFailure as e:
            print(f"Connection failed: {e}")
            return False
        except OperationFailure as e:
            print(f"Operation failed: {e}")
            return False

# Initialize MongoDB connection
mongodb = MongoDBManager()
if not mongodb.connect():
    raise RuntimeError("Failed to connect to MongoDB Atlas")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/service')
@login_required
def service():
    return render_template('service.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            # Check if user already exists
            existing_user = mongodb.db.users.find_one({
                '$or': [
                    {'username': username},
                    {'email': email}
                ]
            })
            
            if existing_user:
                flash('Username or email already exists.', 'danger')
                return redirect(url_for('register'))
            
            # Hash password
            hashed_password = generate_password_hash(password)
            
            # Insert new user
            result = mongodb.db.users.insert_one({
                'username': username,
                'email': email,
                'password': hashed_password
            })
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            print(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            password = request.form['password']
            
            # Find user in database
            user = mongodb.db.users.find_one({'username': username})
            
            if user and check_password_hash(user['password'], password):
                # Create session
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password.', 'danger')
        
        except Exception as e:
            print(f"Error during login: {e}")
            flash('An error occurred during login. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if request.method == 'POST':
        try:
            sqft_living = float(request.form['sqft_living'])
            bedrooms = int(request.form['bedrooms'])
            bathrooms = float(request.form['bathrooms'])
            floors = float(request.form['floors'])
            sqft_lot = float(request.form['sqft_lot'])
            sqft_above = float(request.form['sqft_above'])
            sqft_basement = float(request.form['sqft_basement'])

            # Create a numpy array for the input features
            input_data = np.array([[
                sqft_living, bedrooms, bathrooms, floors, 
                sqft_lot, sqft_above, sqft_basement
            ]])
            
            # Get the prediction
            prediction = model.predict(input_data)

            return render_template(
                'index.html',
                prediction_text=f'Predicted House Price: ${round(prediction[0], 2)}'
            )
        
        except Exception as e:
            print(f"Error during prediction: {e}")
            flash('An error occurred during prediction. Please check your inputs.', 'danger')
            return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)