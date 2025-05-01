import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.datasets import make_classification
from imblearn.over_sampling import SMOTE
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Generate a synthetic dataset and train the model
def train_model():
    # Generating a synthetic dataset
    X, Y = make_classification(n_samples=10000, n_features=30, n_informative=10, n_redundant=10, 
                               n_clusters_per_class=1, weights=[0.99], flip_y=0, random_state=42)

    # Converting to DataFrame for easier manipulation
    data = pd.DataFrame(X)
    data['Class'] = Y

    # Data preprocessing
    X = data.drop(['Class'], axis=1)
    Y = data['Class']

    # Standardizing the features
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # Splitting the data into training and testing sets
    xTrain, xTest, yTrain, yTest = train_test_split(X, Y, test_size=0.3, random_state=42)

    # Handle imbalance using SMOTE
    smote = SMOTE()
    xTrain_resampled, yTrain_resampled = smote.fit_resample(xTrain, yTrain)

    # Train the model
    model = RandomForestClassifier(random_state=42)
    model.fit(xTrain_resampled, yTrain_resampled)

    return model, scaler

# Train the model and scaler when the app starts
model, scaler = train_model()

# User registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()

    flash('Registration successful! You can now log in.', 'success')
    return redirect(url_for('login_page'))

# User login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user is None:
        flash('Username not registered.', 'danger')
        return redirect(url_for('login_page'))
    
    if check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = username  # Store username in session
        flash('Login successful!', 'success')
        return redirect(url_for('fraud_detection'))  # Redirect to the fraud detection page
    else:
        flash('Invalid username or password', 'danger')
        return redirect(url_for('login_page'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)  # Remove username from session
    flash('You have been logged out.', 'success')
    return redirect(url_for('login_page'))

# Define the login page route
@app.route('/login_page')
def login_page():
    return render_template('login.html')

# Define the registration page route
@app.route('/register_page')
def register_page():
    return render_template('register.html')

# Define the fraud detection route
@app.route('/fraud_detection')
def fraud_detection():
    if 'user_id' in session:
        username = session['username']  # Get username from session
        return render_template('fraud_detection.html', username=username)  # Render the fraud detection page with username
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login_page'))  # Redirect to login if not logged in

# Define the predict route
@app.route('/predict', methods=['POST'])
def predict():
    data = request.form['features']  # Get the features from the textarea
    # Split the input string into a list of floats
    transaction = np.array([float(x) for x in data.split(',')])
    
    # Check if the input has exactly 30 features
    if len(transaction) != 30:
        return jsonify(result="Error: Please enter exactly 30 features.")

    transaction_scaled = scaler.transform([transaction])  # Scale the input transaction
    prediction = model.predict(transaction_scaled)  # Make prediction
    result = "Fraudulent" if prediction[0] == 1 else "Not Fraudulent"
    return jsonify(result=result)

# Change password route
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' in session:
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, session['user_id']))
        conn.commit()
        conn.close()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('fraud_detection'))
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login_page'))

# Redirect to login page on root URL
@app.route('/')
def index():
    return redirect(url_for('login_page'))  # Redirect to the login page

if __name__ == '__main__':
    app.run(debug=True)