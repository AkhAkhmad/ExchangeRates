# Импорт необходимых библиотек
import asyncio
import websockets
import json
import ssl
import logging
import pika
from fastapi import FastAPI, WebSocket, Request
from redis import StrictRedis
from sqlalchemy import create_engine
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

# Подключение к БД
DATABASE_URL = "postgresql://user:password@db:5432/database"
engine = create_engine(DATABASE_URL)

# Создание подключения к серверу RabbitMQ
# pika.BlockingConnection: Это класс, который реализует блокирующее подключение к Rabbit
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq')
)

# Создание подключения к серверу Redis
redis_data = StrictRedis(host="redis", port=6379, db=0)

# Создание экземпляра приложения FastAPI
app = FastAPI()

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename='logs.log', filemode='w',
                    format="%(asctime)s %(levelname)s %(message)s")

# Создание экземпляра Jinja2Templates для работы с HTML-шаблонами
templates = Jinja2Templates(directory="templates")

# Глобальная переменная для хранения типа источника данных
TYPE = ''


# Функция для получения данных о курсах валют
async def get_courses():
    global TYPE
    """
    Асинхронная функция для получения данных о курсах валют.
    Функция подключается к веб-сокетам двух различных источников данных (Bitfinex и Binance) и получает данные.
    Если происходит исключение, оно логируется, и функция переключается на другой источник данных.
    """

    # Создание контекста SSL для подключения к веб-сокетам
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Попытка подключения к веб-сокетам Binance
    try:
        async with websockets.connect(f"wss://stream.binance.com:9443/ws/!miniTicker@arr",
                                      ssl=ssl_context) as websocket:
            # Установка типа источника данных
            TYPE = 'binance'
            while True:
                # Получение данных от веб-сокета
                response = await websocket.recv()
                return json.loads(response)
    except Exception as e:
        # Логирование исключений
        try:
            logging.error(e, exc_info=True)
            # Попытка подключения к веб-сокетам Bitfinex в случае ошибки с Binance
            async with websockets.connect('wss://api-pub.bitfinex.com/ws/2', ssl=ssl_context) as websocket:
                # Установка типа источника данных
                TYPE = 'bitfinex'
                lst = ['btcrub', 'btcusdt', 'btc_usd', 'ethrub', 'ethusdt', 'eth_usd', 'usdttrcrub', 'usdttrcusdt',
                       'usdtercrub', 'usdtercusdt']
                for i in lst:
                    # Отправка запроса на подписку на канал ticker для каждого символа в списке
                    await websocket.send(json.dumps({"event": "subscribe", "channel": "ticker", "symbol": i}))

                while True:
                    # Получение данных от веб-сокета
                    response = await websocket.recv()
                    return json.loads(response)
        except Exception as e:
            # Логирование исключений
            logging.error(e, exc_info=True)


# Маршрут WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Маршрут WebSocket, который принимает подключения, отправляет данные, полученные от веб-сокета, и логирует отправленные данные.
    """
    global TYPE
    # Получение данных о курсах валют
    data = await get_courses()
    # Принятие подключения к WebSocket
    await websocket.accept()
    lst = ['btcrub', 'btcusdt', 'btc_usd', 'ethrub', 'ethusdt', 'eth_usd', 'usdttrcrub', 'usdttrcusdt', 'usdtercrub',
           'usdtercusdt']
    while True:
        courses = []
        for i in data:
            # Проверка, содержит ли полученный символ один из интересующих нас символов
            if i.get('s').lower() in lst:
                # Формирование направления и значения курса
                direction = i.get('s').upper().replace("USDT", "-USD").replace("RUB", "-RUB")
                value = float(i.get('c'))
                # Добавление информации о курсе в список
                courses.append({"direction": direction, "value": value})
        # Формирование результата
        result = {"exchanger": TYPE, "courses": courses}
        # Отправка результата через WebSocket
        await websocket.send_text(json.dumps(result))
        # Задержка в 5 секунд перед следующим запросом
        await asyncio.sleep(5)


# API GET
@app.get("/courses", response_class=HTMLResponse)
async def read_courses(request: Request):
    """
    API GET, который возвращает HTML-ответ с использованием шаблона Jinja2.
    """
    return templates.TemplateResponse("button_redirect.html", {"request": request})
