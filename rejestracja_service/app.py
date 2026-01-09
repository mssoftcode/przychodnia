from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask import Flask, request, jsonify


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)

# Model Pacjenta
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    contact = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Model Lekarza
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)


# Strona główna
@app.route('/')
def home():
    patients = Patient.query.all()  # Pobierz wszystkich pacjentów
    doctors = Doctor.query.all()    # Pobierz wszystkich lekarzy
    return render_template('index.html', patients=patients, doctors=doctors)

# Dodanie pacjenta
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        age = request.form['age']
        contact = request.form['contact']
        password = f"{request.form['name']}{request.form['surname']}{request.form['age']}"

        new_patient = Patient(name=name, surname=surname, age=age, contact=contact, password=password)
        db.session.add(new_patient)
        db.session.commit()

        return redirect('/')

    return render_template('add_patient.html')

# Edytowanie pacjenta
@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    patient = Patient.query.get_or_404(id)
    
    if request.method == 'POST':
        patient.name = request.form['name']
        patient.surname = request.form['surname']
        patient.age = request.form['age']
        patient.contact = request.form['contact']
        
        db.session.commit()
        return redirect('/')

    return render_template('edit_patient.html', patient=patient)

# Dodanie lekarza
@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        specialty = request.form['specialty']
        password = f"{request.form['name']}{request.form['surname']}{request.form['specialty']}"

        new_doctor = Doctor(name=name, surname=surname, specialty=specialty, password=password)
        db.session.add(new_doctor)
        db.session.commit()

        return redirect('/')

    return render_template('add_doctor.html')

# Edytowanie lekarza
@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    
    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.surname = request.form['surname']
        doctor.specialty = request.form['specialty']
        
        db.session.commit()
        return redirect('/')

    return render_template('edit_doctor.html', doctor=doctor)

# Endpoint do pobrania pacjenta po imieniu (do logowania)
@app.route('/get_patient/<name>', methods=['GET'])
def get_patient(name):
    patient = Patient.query.filter_by(name=name).first()
    
    if patient:
        return jsonify({
            "id": patient.id,
            "name": patient.name,
            "surname": patient.surname,
            "password": patient.password
        }), 200
    else:
        return jsonify({"message": "Pacjent nie znaleziony"}), 404


# Endpoint do pobrania pacjenta po ID
@app.route('/get_patient_by_id/<int:patient_id>', methods=['GET'])
def get_patient_by_id(patient_id):
    patient = Patient.query.filter_by(id=patient_id).first()
    
    if patient:
        return jsonify({
            "id": patient.id,
            "name": patient.name,
            "surname": patient.surname,
            "age": patient.age,
            "password": patient.password
        }), 200
    else:
        return jsonify({"message": "Pacjent nie znaleziony"}), 404




# Endpoint do pobrania lekarzy
@app.route('/get_doctors', methods=['GET'])
def get_doctors():
    doctors = Doctor.query.all()  # Pobieramy wszystkich lekarzy z bazy danych
    
    # Jeśli są lekarze w bazie danych
    if doctors:
        doctors_list = [
            {
                "id": doctor.id,
                "name": doctor.name,
                "surname": doctor.surname,
                "specialty": doctor.specialty,
                "password": doctor.password
            }
            for doctor in doctors
        ]
        return jsonify(doctors_list), 200
    else:
        return jsonify({"message": "Brak lekarzy w systemie"}), 404



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy bazę danych, jeśli jeszcze nie istnieje
    app.run(debug=True, port=5002)  # Uruchom na porcie 5002
