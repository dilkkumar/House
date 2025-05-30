from flask import Flask, render_template, request, url_for, redirect, session, flash
import joblib
import numpy as np
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load the trained model
model = joblib.load('house_price_model.pkl')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['house_price']
users_collection = db['users']

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
        # Get form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = users_collection.find_one({'$or': [{'username': username}, {'email': email}]})
        
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))
        
        # Hash password (using default method)
        hashed_password = generate_password_hash(password)
        
        # Insert new user
        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password
        })
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        
        # Find user in database
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            # Create session
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
    
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
        sqft_living = float(request.form['sqft_living'])
        bedrooms = int(request.form['bedrooms'])
        bathrooms = float(request.form['bathrooms'])
        floors = float(request.form['floors'])
        sqft_lot = float(request.form['sqft_lot'])
        sqft_above = float(request.form['sqft_above'])
        sqft_basement = float(request.form['sqft_basement'])

        # Create a numpy array for the input features
        input_data = np.array([[sqft_living, bedrooms, bathrooms, floors, sqft_lot, sqft_above, sqft_basement]])
        
        # Get the prediction
        prediction = model.predict(input_data)

        return render_template('index.html', prediction_text=f'Predicted House Price: ${round(prediction[0], 2)}')

if __name__ == '__main__':
    app.run(debug=True)