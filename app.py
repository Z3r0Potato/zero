from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reservations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Flash 메시지용
db = SQLAlchemy(app)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    callback_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reservation_id': self.reservation_id,
            'status': self.status,
            'callback_time': self.callback_time.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

@app.route('/')
def index():
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template('index.html', reservations=reservations)

@app.route('/reserve', methods=['GET', 'POST'])
def reserve():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        if phone_number:
            try:
                # 현재 시간으로부터 5분 후를 콜백 시간으로 설정
                callback_time = datetime.now() + timedelta(minutes=5)
                reservation = Reservation(
                    reservation_id=phone_number,
                    status='pending',
                    callback_time=callback_time
                )
                db.session.add(reservation)
                db.session.commit()
                flash('예약이 성공적으로 접수되었습니다.', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash('예약 접수 중 오류가 발생했습니다.', 'error')
    return render_template('reserve.html')

@app.route('/api/webhook/ars-callback', methods=['POST'])
def webhook_callback():
    data = request.get_json()
    
    if not data or 'reservation_id' not in data or 'status' not in data or 'callback_time' not in data:
        return jsonify({'error': '필수 데이터가 누락되었습니다.'}), 400
    
    try:
        callback_time = datetime.strptime(data['callback_time'], '%Y-%m-%d %H:%M:%S')
        reservation = Reservation.query.filter_by(reservation_id=data['reservation_id']).first()
        if reservation:
            reservation.status = data['status']
            reservation.callback_time = callback_time
            db.session.commit()
            return jsonify({'message': '콜백이 성공적으로 처리되었습니다.'}), 200
        return jsonify({'error': '예약을 찾을 수 없습니다.'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 