import requests
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///doctor_service.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, nullable=False)
    doctor_id = db.Column(db.Integer, nullable=False)
    patient_id = db.Column(db.Integer, nullable=False)
    recommendation = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Recommendation {self.id} for Appointment {self.appointment_id}>"




@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        
        # Wysyłanie zapytania do mikroserwisu rejestracji lekarzy, aby sprawdzić lekarza
        response = requests.get(f'http://127.0.0.1:5002/get_doctors')  # Pobieramy wszystkich lekarzy

        if response.status_code == 200:
            doctors_data = response.json()

            # Wyszukiwanie lekarza w odpowiedzi
            doctor = next((doc for doc in doctors_data if doc['name'] == name), None)

            # Sprawdzanie, czy lekarz istnieje i czy hasło jest poprawne
            if doctor and doctor['password'] == password:
                session['doctor_id'] = doctor['id']
                session['doctor_name'] = doctor['name']
                session['doctor_surname'] = doctor['surname']
                session['doctor_specialty'] = doctor['specialty']
                return redirect('/appointments')
            else:
                return "Nieprawidłowe dane logowania, spróbuj ponownie!"
        else:
            return "Nie znaleziono danych o lekarzach!"

    return render_template('login.html')


@app.route('/appointments')
def appointments():
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    doctor_id = session['doctor_id']

    # Pobieramy wizyty przypisane do lekarza
    response = requests.get(f'http://127.0.0.1:5003/get_appointments', params={'doctor_id': doctor_id})

    if response.status_code != 200:
        return "Brak wizyt w systemie.", 404

    appointments_data = response.json()  # Pobieramy wizyty

    # Pobieramy wszystkie rekomendacje z bazy danych
    all_recommendations = Recommendation.query.all()

    # Tworzymy mapowanie rekomendacji po patient_id
    recommendations_by_patient = {}
    for rec in all_recommendations:
        if rec.patient_id not in recommendations_by_patient:
            recommendations_by_patient[rec.patient_id] = []
        recommendations_by_patient[rec.patient_id].append(rec.recommendation)

    # Przetwarzamy każdą wizytę
    for appointment in appointments_data:
        # Pobieramy pacjenta po ID
        patient_response = requests.get(f'http://127.0.0.1:5002/get_patient_by_id/{appointment["patient_id"]}')
        if patient_response.status_code == 200:
            patient_data = patient_response.json()
            appointment['patient_name'] = patient_data['name']
            appointment['patient_surname'] = patient_data['surname']
            appointment['patient_age'] = patient_data.get('age', 'brak')
        else:
            appointment['patient_name'] = "Nie znaleziono"
            appointment['patient_surname'] = "Nie znaleziono"

        # Tylko rekomendacje tego pacjenta
        appointment['recommendations'] = recommendations_by_patient.get(appointment['patient_id'], [])

    return render_template('appointments.html', appointments=appointments_data, doctor_name=session['doctor_name'], doctor_surname=session['doctor_surname'], doctor_specialty=session['doctor_specialty'])



@app.route('/appointments/<int:appointment_id>/recommendation', methods=['GET', 'POST'])
def add_recommendation(appointment_id):
    if 'doctor_id' not in session:
        return redirect(url_for('login'))  # Jeśli lekarz nie jest zalogowany, przekieruj do logowania

    doctor_id = session['doctor_id']

    # Pobieramy wizyty przypisane do lekarza przez API
    response = requests.get(f'http://127.0.0.1:5003/get_appointments', params={'doctor_id': doctor_id})

    if response.status_code == 200:
        appointments_data = response.json()  # Pobieramy wizyty
        # Szukamy wizyty na podstawie appointment_id
        appointment = next((app for app in appointments_data if app['id'] == appointment_id), None)
        
        if not appointment:
            return "Wizyta nie istnieje", 404  # Jeśli wizyta nie istnieje, zwróć błąd
    else:
        return "Nie udało się pobrać wizyt z mikroserwisu.", 500

    patient_id = appointment['patient_id']  # Pobieramy patient_id z wizyty

    if request.method == 'POST':
        recommendation_text = request.form['recommendation']  # Pobieramy rekomendację z formularza
        
        # Walidacja, czy rekomendacja jest wpisana
        if not recommendation_text:
            return "Rekomendacja nie może być pusta!", 400

        # Tworzenie obiektu rekomendacji
        new_recommendation = Recommendation(
            appointment_id=appointment_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            recommendation= "[" + session.get('doctor_specialty') + "] " + recommendation_text  # Specajlizacja + Tekst rekomendacji
        )

        # Zapisanie rekomendacji w bazie danych
        try:
            db.session.add(new_recommendation)
            db.session.commit()
            print(f"Rekomendacja zapisana dla wizyty {appointment_id} przez lekarza {doctor_id}")
            return redirect(url_for('appointments'))  # Po zapisaniu rekomendacji, wracamy do listy wizyt
        except Exception as e:
            db.session.rollback()
            print(f"Coś poszło nie tak: {str(e)}")
            return redirect(url_for('appointments'))
    
    # else:
    #     return "Brak wizyt w systemie.", 404

    return render_template('add_recommendation.html', appointment=appointment)




@app.route('/get_recommendations_by_appointment_id/<int:appointment_id>', methods=['GET'])
def get_recommendations_by_appointment_id(appointment_id):
    
    recommendations = Recommendation.query.filter_by(appointment_id=appointment_id).all()

    if recommendations:
        return jsonify([
            {
                "id": rec.id,
                "appointment_id": rec.appointment_id,
                "doctor_id": rec.doctor_id,
                "patient_id": rec.patient_id,
                "recommendation": rec.recommendation
            }
            for rec in recommendations
        ]), 200
    else:
        return jsonify({"message": "Brak zaleceń dla tej wizyty"}), 404





if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy bazę danych, jeśli jeszcze nie istnieje
    app.run(debug=True, port=5004)  # Uruchom mikroserwis dla lekarza na porcie 5004