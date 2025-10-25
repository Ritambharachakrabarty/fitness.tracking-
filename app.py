# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

DATABASE = 'fitness_tracker.db'

def get_db():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database schema.
    Using 'CREATE TABLE IF NOT EXISTS' is safe to run every time.
    """
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                duration INTEGER NOT NULL,
                calories INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL,
                target_value INTEGER NOT NULL,
                deadline TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                food_name TEXT NOT NULL,
                calories INTEGER NOT NULL,
                protein INTEGER DEFAULT 0,
                carbs INTEGER DEFAULT 0,
                fats INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS calorie_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                daily_goal INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("Database tables ensured to exist.")

# --- All API Endpoints (no changes needed here) ---

@app.route('/api/workouts', methods=['GET'])
def get_workouts():
    with get_db() as conn:
        workouts = conn.execute('SELECT * FROM workouts ORDER BY date DESC, created_at DESC').fetchall()
        return jsonify([dict(w) for w in workouts])

@app.route('/api/workouts', methods=['POST'])
def add_workout():
    try:
        data = request.json
        with get_db() as conn:
            cursor = conn.execute('INSERT INTO workouts (date, type, duration, calories, notes) VALUES (?, ?, ?, ?, ?)',(data['date'], data['type'], data['duration'], data['calories'], data.get('notes', '')))
            conn.commit()
            return jsonify({'id': cursor.lastrowid, 'message': 'Workout added successfully'}), 201
    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid or missing data in request'}), 400

@app.route('/api/workouts/<int:workout_id>', methods=['DELETE'])
def delete_workout(workout_id):
    with get_db() as conn:
        conn.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
        conn.commit()
        return jsonify({'message': 'Workout deleted successfully'})

@app.route('/api/meals', methods=['GET'])
def get_meals():
    date = request.args.get('date')
    with get_db() as conn:
        if date:
            meals = conn.execute('SELECT * FROM meals WHERE date = ? ORDER BY created_at DESC', (date,)).fetchall()
        else:
            meals = conn.execute('SELECT * FROM meals ORDER BY date DESC, created_at DESC LIMIT 50').fetchall()
        return jsonify([dict(m) for m in meals])

@app.route('/api/meals', methods=['POST'])
def add_meal():
    try:
        data = request.json
        with get_db() as conn:
            cursor = conn.execute('INSERT INTO meals (date, meal_type, food_name, calories, protein, carbs, fats, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (data['date'], data['meal_type'], data['food_name'], data['calories'], data.get('protein', 0), data.get('carbs', 0), data.get('fats', 0), data.get('notes', '')))
            conn.commit()
            return jsonify({'id': cursor.lastrowid, 'message': 'Meal added successfully'}), 201
    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid or missing data in request'}), 400

@app.route('/api/meals/<int:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    with get_db() as conn:
        conn.execute('DELETE FROM meals WHERE id = ?', (meal_id,))
        conn.commit()
        return jsonify({'message': 'Meal deleted successfully'})

@app.route('/api/meals/daily/<date>', methods=['GET'])
def get_daily_meals(date):
    with get_db() as conn:
        meals = conn.execute('SELECT * FROM meals WHERE date = ? ORDER BY created_at ASC', (date,)).fetchall()
        totals = conn.execute('''SELECT SUM(calories) as calories, SUM(protein) as protein, SUM(carbs) as carbs, SUM(fats) as fats FROM meals WHERE date = ?''', (date,)).fetchone()
        return jsonify({'meals': [dict(m) for m in meals],'totals': {'calories': totals['calories'] or 0, 'protein': totals['protein'] or 0, 'carbs': totals['carbs'] or 0, 'fats': totals['fats'] or 0}})

@app.route('/api/calorie-goals/<date>', methods=['GET'])
def get_calorie_goal(date):
    with get_db() as conn:
        goal = conn.execute('SELECT * FROM calorie_goals WHERE date = ?', (date,)).fetchone()
        return jsonify(dict(goal) if goal else None)

@app.route('/api/calorie-goals', methods=['POST'])
def set_calorie_goal():
    try:
        data = request.json
        with get_db() as conn:
            conn.execute('INSERT OR REPLACE INTO calorie_goals (date, daily_goal) VALUES (?, ?)', (data['date'], data['daily_goal']))
            conn.commit()
            return jsonify({'message': 'Calorie goal set successfully'}), 201
    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid or missing data in request'}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as conn:
        total_workouts = conn.execute('SELECT COUNT(*) as count FROM workouts').fetchone()['count']
        total_calories_burned = conn.execute('SELECT SUM(calories) as total FROM workouts').fetchone()['total'] or 0
        total_duration = conn.execute('SELECT SUM(duration) as total FROM workouts').fetchone()['total'] or 0
        total_calories_consumed = conn.execute('SELECT SUM(calories) as total FROM meals').fetchone()['total'] or 0
        return jsonify({'total_workouts': total_workouts, 'total_calories_burned': total_calories_burned, 'total_duration': total_duration, 'total_calories_consumed': total_calories_consumed, 'net_calories': total_calories_consumed - total_calories_burned})

@app.route('/api/goals', methods=['GET'])
def get_goals():
    with get_db() as conn:
        goals = conn.execute('SELECT * FROM goals ORDER BY created_at DESC').fetchall()
        return jsonify([dict(g) for g in goals])

@app.route('/api/goals', methods=['POST'])
def add_goal():
    try:
        data = request.json
        with get_db() as conn:
            cursor = conn.execute('INSERT INTO goals (goal_type, target_value, deadline) VALUES (?, ?, ?)', (data['goal_type'], data['target_value'], data.get('deadline', None)))
            conn.commit()
            return jsonify({'id': cursor.lastrowid, 'message': 'Goal added successfully'}), 201
    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid or missing data in request'}), 400

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    with get_db() as conn:
        conn.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
        conn.commit()
        return jsonify({'message': 'Goal deleted successfully'})

# --- CORRECTED STARTUP LOGIC ---
from flask import send_from_directory

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')
    
if __name__ == '__main__':
    init_db()  # Call this every time to ensure tables exist

    app.run(debug=True, port=5000)

