import sqlite3
from flask import Flask, g, request, jsonify


app = Flask(__name__)
DATABASE = 'database.db'

# Соединения с БД
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Возвращаем словари вместо кортежей
        db.row_factory = sqlite3.Row
    return db

# Закрытие соединения при завершении
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Создание таблицы майнеров
def init_db():
    with app.app_context():
        db = get_db()
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS miners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                miner_name TEXT NOT NULL,
                model TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                hashrate REAL NOT NULL,
                power_consumption INTEGER,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'offline', 'maintenance', 'error')),
                location TEXT,
                ip_address TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(miner_name)
            )
        ''')
        
        db.commit()


VALID_STATUSES = ['active', 'offline', 'maintenance', 'error']


# Создание нового майнера
@app.route('/miners', methods=['POST'])
def create_miner():
    data = request.get_json()
    
    # Валидация обязательных полей
    required_fields = ['miner_name', 'model', 'algorithm', 'hashrate']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Отсутствует обязательное поле: {field}'}), 400
    
    # Валидация статуса
    if data.get('status') and data['status'] not in VALID_STATUSES:
        return jsonify({'error': f'Invalid status. Must be one of: {VALID_STATUSES}'}), 400
    
    try:
        db = get_db()
        cursor = db.execute('''
            INSERT INTO miners 
            (miner_name, model, algorithm, hashrate, power_consumption, status, location, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['miner_name'],
            data['model'],
            data['algorithm'],
            data['hashrate'],
            data.get('power_consumption'),
            data.get('status', 'active'),
            data.get('location'),
            data.get('ip_address')
        ))
        db.commit()
        
        # Получаем созданный майнер
        new_miner = db.execute(
            'SELECT * FROM miners WHERE id = ?', 
            (cursor.lastrowid,)
        ).fetchone()
        
        return jsonify({
            'message': 'Майнер успешно создан',
            'miner': dict(new_miner)
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Майнер с таким именем уже существует'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# Получение всех майнеров
@app.route('/miners', methods=['GET'])
def get_all_miners():
    try:
        db = get_db()
        
        cursor = db.execute('SELECT * FROM miners ORDER BY id')
        miners = cursor.fetchall()
        
        return jsonify({
            'count': len(miners),
            'miners': [dict(miner) for miner in miners]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# UPDATE - Обновление майнера
@app.route('/miners/<int:miner_id>', methods=['PUT'])
def update_miner(miner_id):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Данные для обновления не предоставлены'}), 400
    
    # Валидация статуса
    if data.get('status') and data['status'] not in VALID_STATUSES:
        return jsonify({'error': f'Некорректный статус. Допустимые значения: {VALID_STATUSES}'}), 400
    
    try:
        db = get_db()
        
        # Проверяем существование майнера
        cursor = db.execute('SELECT id FROM miners WHERE id = ?', (miner_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Майнер не найден'}), 404
        
        # Формируем SQL запрос динамически на основе переданных полей
        update_fields = []
        values = []
        
        for field in ['miner_name', 'model', 'algorithm', 'hashrate', 'power_consumption', 'status', 'location', 'ip_address']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        if not update_fields:
            return jsonify({'error': 'Нет полей для обновления'}), 400
        
        # Добавляем обновление времени последнего seen
        update_fields.append("last_seen = CURRENT_TIMESTAMP")
        values.append(miner_id)
        
        query = f'UPDATE miners SET {", ".join(update_fields)} WHERE id = ?'
        
        cursor = db.execute(query, values)
        db.commit()
        
        # Возвращаем обновленный майнер
        updated_miner = db.execute(
            'SELECT * FROM miners WHERE id = ?', 
            (miner_id,)
        ).fetchone()
        
        return jsonify({
            'message': 'Майнер успешно обновлен',
            'miner': dict(updated_miner)
        })
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Майнер с таким именем уже существует'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# DELETE - Удаление майнера
@app.route('/miners/<int:miner_id>', methods=['DELETE'])
def delete_miner(miner_id):
    try:
        db = get_db()
        
        # Сначала получаем информацию о майнере для ответа
        miner = db.execute('SELECT * FROM miners WHERE id = ?', (miner_id,)).fetchone()
        
        if not miner:
            return jsonify({'error': 'Майнер не найден'}), 404
        
        # Удаляем майнер
        cursor = db.execute('DELETE FROM miners WHERE id = ?', (miner_id,))
        db.commit()
        
        return jsonify({
            'message': 'Майнер успешно удален',
            'deleted_miner': dict(miner)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    

@app.route('/miners/load-sample-data', methods=['POST'])
def load_sample_data():
    sample_miners = [
        {
            'miner_name': 'ASIC_Main_1',
            'model': 'Antminer S19j Pro',
            'algorithm': 'SHA-256',
            'hashrate': 100.0,
            'power_consumption': 3050,
            'status': 'active',
            'location': 'Data Center A - Rack 1',
            'ip_address': '192.168.1.100'
        },
        {
            'miner_name': 'ASIC_Main_2',
            'model': 'Antminer S19 XP',
            'algorithm': 'SHA-256',
            'hashrate': 140.0,
            'power_consumption': 3010,
            'status': 'active',
            'location': 'Data Center A - Rack 1',
            'ip_address': '192.168.1.101'
        },
        {
            'miner_name': 'ASIC_Backup_1',
            'model': 'Antminer S19',
            'algorithm': 'SHA-256',
            'hashrate': 95.0,
            'power_consumption': 3250,
            'status': 'maintenance',
            'location': 'Data Center A - Rack 2',
            'ip_address': '192.168.1.102'
        },
        {
            'miner_name': 'ASIC_Backup_2',
            'model': 'Whatsminer M50',
            'algorithm': 'SHA-256',
            'hashrate': 112.0,
            'power_consumption': 3276,
            'status': 'active',
            'location': 'Data Center A - Rack 2',
            'ip_address': '192.168.1.103'
        },
        {
            'miner_name': 'GPU_Rig_1',
            'model': 'NVIDIA RTX 3080',
            'algorithm': 'Ethash',
            'hashrate': 0.1,
            'power_consumption': 320,
            'status': 'active',
            'location': 'Office - Mining Rig 1',
            'ip_address': '192.168.1.200'
        },
        {
            'miner_name': 'GPU_Rig_2',
            'model': 'NVIDIA RTX 3090',
            'algorithm': 'Ethash',
            'hashrate': 0.12,
            'power_consumption': 350,
            'status': 'offline',
            'location': 'Office - Mining Rig 1',
            'ip_address': '192.168.1.201'
        },
        {
            'miner_name': 'ASIC_Old_1',
            'model': 'Antminer S9',
            'algorithm': 'SHA-256',
            'hashrate': 14.0,
            'power_consumption': 1320,
            'status': 'offline',
            'location': 'Warehouse - Storage',
            'ip_address': '192.168.1.150'
        },
        {
            'miner_name': 'ASIC_Litecoin_1',
            'model': 'Antminer L7',
            'algorithm': 'Scrypt',
            'hashrate': 9.5,
            'power_consumption': 3425,
            'status': 'active',
            'location': 'Data Center B - Rack 3',
            'ip_address': '192.168.2.100'
        },
        {
            'miner_name': 'ASIC_Error_1',
            'model': 'Antminer S17',
            'algorithm': 'SHA-256',
            'hashrate': 56.0,
            'power_consumption': 2385,
            'status': 'error',
            'location': 'Data Center A - Repair',
            'ip_address': '192.168.1.250'
        },
        {
            'miner_name': 'GPU_Rig_3',
            'model': 'AMD RX 6800 XT',
            'algorithm': 'Ethash',
            'hashrate': 0.064,
            'power_consumption': 280,
            'status': 'maintenance',
            'location': 'Office - Mining Rig 2',
            'ip_address': '192.168.1.202'
        }
    ]
    
    try:
        db = get_db()
        
        # Очищаем существующие данные перед загрузкой
        db.execute('DELETE FROM miners')
        
        for miner_data in sample_miners:
            db.execute('''
                INSERT INTO miners 
                (miner_name, model, algorithm, hashrate, power_consumption, status, location, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                miner_data['miner_name'],
                miner_data['model'], 
                miner_data['algorithm'],
                miner_data['hashrate'],
                miner_data['power_consumption'],
                miner_data['status'],
                miner_data['location'],
                miner_data['ip_address']
            ))
        db.commit()
        
        return jsonify({
            'message': f'{len(sample_miners)} тестовые майнеры успешно загружены',
            'miners_added': len(sample_miners),
            'stats': {
                'active': len([m for m in sample_miners if m['status'] == 'active']),
                'offline': len([m for m in sample_miners if m['status'] == 'offline']),
                'maintenance': len([m for m in sample_miners if m['status'] == 'maintenance']),
                'error': len([m for m in sample_miners if m['status'] == 'error'])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)