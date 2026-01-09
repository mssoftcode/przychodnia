import requests
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)

# Model Pacjenta
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    # Relacja do wizyt
    appointments = db.relationship('Appointment', back_populates='patient', cascade='all, delete-orphan')


# Model Wizyty
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)  # Klucz obcy do pacjenta
    doctor_id = db.Column(db.Integer, nullable=False)
    doctor_name = db.Column(db.String(50), nullable=False)
    doctor_surname = db.Column(db.String(50), nullable=False)
    doctor_specialty = db.Column(db.String(100), nullable=False)
    appointment_date = db.Column(db.String(50), nullable=False)
    
    # Relacja z pacjentem
    patient = db.relationship('Patient', back_populates='appointments')



@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        
        # Wysyłamy zapytanie do mikroserwisu rejestracja, aby sprawdzić pacjenta
        response = requests.get(f'http://127.0.0.1:5002/get_patient/{name}')
        
        if response.status_code == 200:
            patient_data = response.json()
            if patient_data and password == patient_data.get("password"):  # Sprawdzanie hasła
                session['patient_id'] = patient_data["id"]
                session['patient_name'] = patient_data["name"]
                session['patient_surname'] = patient_data["surname"]
                session['patient_password'] = patient_data["password"]
                return redirect('/appointments')
            else:
                return "Nieprawidłowe dane logowania, spróbuj ponownie!"
        else:
            return "Nie znaleziono pacjenta, spróbuj ponownie!"

    return render_template('login.html')

# Strona umówienia wizyty
@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'patient_id' not in session:
        return redirect(url_for('login'))  # Jeśli pacjent nie jest zalogowany, przekieruj do logowania

    print(f"Pacjent w sesji: {session.get('patient_id')}, {session.get('patient_name')}")
    print(f"Sesja pacjenta: {session}")

    # Pobieranie dostępnych lekarzy z mikroserwisu rejestracji
    response = requests.get('http://127.0.0.1:5002/get_doctors')
    doctors = response.json() if response.status_code == 200 else []  # Lista lekarzy

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']  # Wybór lekarza
        appointment_date = request.form['appointment_date']  # Data wizyty

        # Pobieranie danych wybranego lekarza
        doctor = next((doc for doc in doctors if doc['id'] == int(doctor_id)), None)

        # Walidacja, czy dane zostały wysłane
        if not doctor_id or not appointment_date:
            return "Wszystkie pola są wymagane!", 400


        # **Sprawdzamy, czy pacjent istnieje w bazie danych**
        patient = db.session.get(Patient, session.get('patient_id'))
        print(patient)
        if not patient:
            # Jeśli pacjent nie istnieje w bazie, tworzymy nowego pacjenta
            patient_name = session.get('patient_name')
            patient_surname = session.get('patient_surname')
            patient_password = session.get('patient_password')
            patient = Patient(name=patient_name, surname=patient_surname, password=patient_password)

            try:
                db.session.add(patient)
                db.session.commit()  # Zapisujemy pacjenta do bazy danych
                session['patient_id'] = patient.id  # Zaktualizuj ID pacjenta w sesji
                print(f"Nowy pacjent zapisany do bazy! ID: {patient.id}")
            except Exception as e:
                db.session.rollback()
                flash(f"Coś poszło nie tak przy zapisie pacjenta: {str(e)}")
                return redirect(url_for('appointments'))



        # Tworzenie nowej wizyty w bazie danych
        new_appointment = Appointment(
            patient_id=session.get('patient_id'),  # ID pacjenta z sesji
            doctor_id=doctor['id'],
            doctor_name=doctor['name'],
            doctor_surname=doctor['surname'],
            doctor_specialty=doctor['specialty'],
            appointment_date=appointment_date
        )

        # Zapisanie wizyty do bazy danych
        try:
            db.session.add(new_appointment)
            db.session.commit()

            # Debugowanie: Sprawdź, czy wizyta została zapisana
            saved_appointment = Appointment.query.filter_by(patient_id=session.get('patient_id')).order_by(Appointment.id.desc()).first()
            if saved_appointment:
                print(f"Wizyta zapisana w bazie! ID: {saved_appointment.id}, Data: {saved_appointment.appointment_date}")
            else:
                print("Wizyta nie została zapisana w bazie.")

            # Debugowanie: Sprawdzamy, czy sesja zawiera dane pacjenta
            print(f"Po zapisaniu wizyty pacjent w sesji: {session.get('patient_id')}")

            print("Wizyta została pomyślnie umówiona!")
            return redirect('/view_appointments')  # Po zapisaniu wizyty, przekierowanie do widoku wizyt
        except Exception as e:
            db.session.rollback()
            flash(f"Coś poszło nie tak: {str(e)}")
            return redirect(url_for('appointments'))

    return render_template('appointments.html', doctors=doctors)

@app.route('/view_appointments')
def view_appointments():
    print(f"Pacjent ID z sesji: {session.get('patient_id')}")
    if 'patient_id' not in session:
        return redirect(url_for('login'))  # Jeśli pacjent nie jest zalogowany, przekieruj do logowania
    
    # Pobierz pacjenta na podstawie ID z sesji
    # patient = Patient.query.get(session['patient_id'])
    patient = db.session.get(Patient, session['patient_id'])
    patient_full_name = session['patient_name'] + ' ' + session['patient_surname']
    # Debugowanie: Sprawdzamy, czy pacjent_id jest w sesji
    print(f"Pacjent ID z sesji: {session.get('patient_id')}")
    
    patient_exists = Patient.query.filter_by(id=session.get('patient_id')).first()
    if not patient_exists:
        print("Pacjent nie istnieje w bazie danych!")



    # Debugowanie: Sprawdzamy, czy pacjent został znaleziony w bazie danych
    if not patient:
        print(f"Nie znaleziono pacjenta o ID {session['patient_id']} w bazie danych!")
        return "Nie znaleziono wizyt pacjenta", 404
    
    # Debugowanie: Sprawdzamy, jakie wizyty są przypisane do pacjenta
    print(f"Znaleziono pacjenta: {patient.name} {patient.surname}")
    appointments = patient.appointments  # Wizyty pacjenta


    appointments_with_recommendations = []

    for appointment in appointments:
        response = requests.get(f'http://127.0.0.1:5004/get_recommendations_by_appointment_id/{appointment.id}')
        recommendations = response.json() if response.status_code == 200 else []

        appointments_with_recommendations.append({
            "appointment": appointment,
            "recommendations": recommendations
        })

    return render_template('view_appointments.html', appointments_with_recommendations=appointments_with_recommendations, patient_full_name=patient_full_name)



# Endpoint do pobrania appointments
@app.route('/get_appointments', methods=['GET'])
def get_appointments():

    doctor_id = request.args.get('doctor_id')  # Pobierz parametr doctor_id z zapytania

    if doctor_id:
        appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()  # Filtrowanie wizyt po doctor_id
    else:
        appointments = Appointment.query.all()  # Jeśli nie podano doctor_id, zwróć wszystkie wizyty

    # Jeśli są lekarze w bazie danych
    if appointments:
        appointments_list = [
            {
                "id": appointment.id,
                "patient_id": appointment.patient_id,
                "doctor_id": appointment.doctor_id,
                "doctor_name": appointment.doctor_name,
                "doctor_surname": appointment.doctor_surname,
                "doctor_specialty": appointment.doctor_specialty,
                "appointment_date": appointment.appointment_date
            }
            for appointment in appointments
        ]
        return jsonify(appointments_list), 200
    else:
        return jsonify({"message": "Brak wizyt w systemie"}), 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy bazę danych, jeśli jeszcze nie istnieje
    app.run(debug=True, port=5003)  # Uruchom na porcie 5003
