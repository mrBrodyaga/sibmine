# Miner Management API

Небольшое REST API-приложение на Flask для управления майнерами (ASIC/GPU) с хранением данных в SQLite.  
Поддерживаются операции создания, чтения, обновления и удаления майнеров, а также загрузка тестовых данных.

## Стек

- Python 3.11+
- [Flask](https://flask.palletsprojects.com/)
- SQLite (локальный файл `database.db`)
- Утилита управления зависимостями [`uv`](https://github.com/astral-sh/uv) **или** стандартный `pip`

---

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/mrBrodyaga/sibmine.git miner-api
cd miner-api
```

## Вариант 1: установка через `uv`

### 2. Создать виртуальное окружение и установить зависимости

Если `uv` ещё не установлен:

```bash
pip install uv
```

Далее в директории проекта:

```bash
uv venv .venv
source .venv/bin/activate        # Linux/macOS
# или
# .venv\Scripts\activate         # Windows PowerShell / cmd

uv pip install -r requirements.txt
```

### 3. Запуск приложения

```bash
uv run python main.py
# или, если виртуальное окружение уже активировано:
python main.py
```

По умолчанию приложение поднимается на:

```text
http://0.0.0.0:5000
```

При первом запуске:

- будет создан файл базы данных `database.db` в корне проекта;
- будет создана таблица `miners` (функция `init_db()` вызывается при старте).

---

## Вариант 2: установка через `pip`

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# или
# .venv\Scripts\activate         # Windows PowerShell / cmd
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
python main.py
```

Дальше всё аналогично: приложение доступно на `http://0.0.0.0:5000`, БД создаётся автоматически.

---

### 5. Загрузка тестовых данных

**POST** `/miners/load-sample-data`

Перезаливает таблицу `miners` набором заранее подготовленных примеров.

⚠️ Важно: перед вставкой тестовых данных выполняется:

```sql
DELETE FROM miners
```

То есть **все существующие записи будут удалены**.

Пример запроса:

```bash
curl -X POST http://localhost:5000/miners/load-sample-data
```

Пример ответа:

```json
{
  "message": "10 тестовые майнеры успешно загружены",
  "miners_added": 10,
  "stats": {
    "active": 5,
    "offline": 2,
    "maintenance": 2,
    "error": 1
  }
}
```

---

## Структура базы данных

Используется одна таблица: `miners`.

Поля:

- `id` — целое, первичный ключ, автоинкремент;
- `miner_name` — имя майнера (строка, уникальное, обязательное);
- `model` — модель устройства (обязательное);
- `algorithm` — алгоритм майнинга (например, `SHA-256`, `Ethash`, `Scrypt`) (обязательное);
- `hashrate` — хешрейт (вещественное число, обязательное);
- `power_consumption` — потребление мощности в ваттах (целое, опционально);
- `status` — статус майнера:
  - допустимые значения: `active`, `offline`, `maintenance`, `error`;
  - по умолчанию: `active`;
- `location` — расположение устройства (строка, опционально);
- `ip_address` — IP-адрес майнера (строка, опционально);
- `last_seen` — время последнего обновления / активности (по умолчанию `CURRENT_TIMESTAMP`, автоматически обновляется при `UPDATE`);
- `created_at` — время создания записи (по умолчанию `CURRENT_TIMESTAMP`).

Ограничения:

- `UNIQUE(miner_name)` — два майнера с одинаковым именем создать нельзя.

---

## API

Все ответы — в формате JSON.

Базовый URL:

```text
http://<host>:5000
```

По умолчанию: `http://localhost:5000`.

Доступные статусы майнеров:

```text
active, offline, maintenance, error
```

---

### 1. Создание майнера

**POST** `/miners`

Создаёт новую запись о майнере.

Обязательные поля: `miner_name`, `model`, `algorithm`, `hashrate`.  
Остальные поля опциональны.

Пример запроса (curl):

```bash
curl -X POST http://localhost:5000/miners \
  -H "Content-Type: application/json" \
  -d '{
    "miner_name": "ASIC_Main_1",
    "model": "Antminer S19j Pro",
    "algorithm": "SHA-256",
    "hashrate": 100.0,
    "power_consumption": 3050,
    "status": "active",
    "location": "Data Center A - Rack 1",
    "ip_address": "192.168.1.100"
  }'
```

Пример успешного ответа (201):

```json
{
  "message": "Майнер успешно создан",
  "miner": {
    "id": 1,
    "miner_name": "ASIC_Main_1",
    "model": "Antminer S19j Pro",
    "algorithm": "SHA-256",
    "hashrate": 100.0,
    "power_consumption": 3050,
    "status": "active",
    "location": "Data Center A - Rack 1",
    "ip_address": "192.168.1.100",
    "last_seen": "2025-01-01 12:00:00",
    "created_at": "2025-01-01 12:00:00"
  }
}
```

Возможные ошибки:

- `400` — отсутствует обязательное поле;
- `400` — некорректный статус (`status` не входит в список допустимых);
- `400` — майнер с таким `miner_name` уже существует;
- `500` — любая другая ошибка сервера.

---

### 2. Получение списка майнеров

**GET** `/miners`

Возвращает список всех майнеров.

Пример запроса:

```bash
curl http://localhost:5000/miners
```

Пример ответа:

```json
{
  "count": 3,
  "miners": [
    { "...": "..." },
    { "...": "..." },
    { "...": "..." }
  ]
}
```

---

### 3. Обновление майнера

**PUT** `/miners/<id>`

Обновляет поля майнера с указанным `id`.  
Передавать можно **любой поднабор** полей — обновятся только те, которые присутствуют в JSON.  
Поле `status`, если передано, также валидируется по списку допустимых значений.

Дополнительно: при любом обновлении автоматически обновляется поле `last_seen` (`CURRENT_TIMESTAMP`).

Пример запроса:

```bash
curl -X PUT http://localhost:5000/miners/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "maintenance",
    "location": "Data Center A - Repair"
  }'
```

Пример успешного ответа:

```json
{
  "message": "Майнер успешно обновлен",
  "miner": {
    "id": 1,
    "miner_name": "ASIC_Main_1",
    "model": "Antminer S19j Pro",
    "algorithm": "SHA-256",
    "hashrate": 100.0,
    "power_consumption": 3050,
    "status": "maintenance",
    "location": "Data Center A - Repair",
    "ip_address": "192.168.1.100",
    "last_seen": "2025-01-01 13:00:00",
    "created_at": "2025-01-01 12:00:00"
  }
}
```

Возможные ошибки:

- `400` — нет данных для обновления;
- `400` — некорректный статус;
- `400` — майнер с таким `miner_name` уже существует (если пытаемся сменить имя на уже занятое);
- `404` — майнер с таким `id` не найден;
- `500` — ошибка сервера.

---

### 4. Удаление майнера

**DELETE** `/miners/<id>`

Удаляет майнер с указанным `id`.  
В ответе возвращаются данные удалённого майнера.

Пример:

```bash
curl -X DELETE http://localhost:5000/miners/1
```

Пример успешного ответа:

```json
{
  "message": "Майнер успешно удален",
  "deleted_miner": {
    "id": 1,
    "miner_name": "ASIC_Main_1",
    "model": "Antminer S19j Pro",
    "algorithm": "SHA-256",
    "hashrate": 100.0,
    "power_consumption": 3050,
    "status": "maintenance",
    "location": "Data Center A - Repair",
    "ip_address": "192.168.1.100",
    "last_seen": "2025-01-01 13:00:00",
    "created_at": "2025-01-01 12:00:00"
  }
}
```

Ошибки:

- `404` — майнер с таким `id` не найден;
- `500` — ошибка сервера.

---

## Обработка ошибок

Во всех эндпоинтах API возвращает JSON с полем `error` в случае проблем, например:

```json
{
  "error": "Майнер не найден"
}
```

Коды ответа:

- `200` — успешный запрос (GET, PUT, DELETE, POST sample data);
- `201` — успешное создание ресурса (POST /miners);
- `400` — ошибка валидации входных данных;
- `404` — ресурс не найден;
- `500` — внутренняя ошибка сервера.

---

## Разработка

Приложение запускается в режиме `debug=True`, что удобно при разработке:

```python
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

При необходимости можно изменить порт и параметры запуска в `main.py`.
