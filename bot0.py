import json
import os
import random
import black
import isort
import redis
import requests
import telebot

from telebot import types

token = '5656126747:AAHvjNJF4blQ8Ji5lDufF91B0qDOw5P0xQc'

bot = telebot.TeleBot(token)

koeficienti = {}  # будем в основном использовать на этапе с конвертацией, для коэффициентов

url = 'https://www.cbr-xml-daily.ru/daily_json.js'  # записываем в переменную url API центрабанка

response = requests.get(url).json()  # преобразуем полученные из ссылки данные в словарь

USD = response['Valute']['USD']['Value']  # Из api центрабанка достали стоимость доллара в рублях
koeficienti[11] = USD

EUR = response['Valute']['EUR']['Value']  # Из api центрабанка достали стоимость евро в рублях
koeficienti[0] = EUR

CNY = response['Valute']['CNY']['Value']  # Из api центрабанка достали стоимость юаней в рублях
koeficienti[1] = CNY

# Задаём коэффициенты перевода из одной валюты в другую
izEURvUSD = int(EUR) / int(USD)
koeficienti[2] = izEURvUSD
izUSDvEUR = int(USD) / int(EUR)
koeficienti[3] = izUSDvEUR
izRUBvUSD = 1 / int(USD)
koeficienti[4] = izRUBvUSD
izRUBvEUR = 1 / int(EUR)
koeficienti[5] = izRUBvEUR
izRUBvCNY = 1 / int(CNY)
koeficienti[6] = izRUBvCNY
izUSDvCNY = int(USD) / int(CNY)
koeficienti[7] = izUSDvCNY
izEURvCNY = int(EUR) / int(CNY)
koeficienti[8] = izEURvCNY
izCNYvUSD = int(CNY) / int(USD)
koeficienti[9] = izCNYvUSD
izCNYvEUR = int(CNY) / int(EUR)
koeficienti[10] = izCNYvEUR

# Вводим все состояния
MAIN_STATE = 'main'
Vvedini = 'vvedeni dannie'
Symiruem = 'idet rasschet'
SYM1 = 'vtoroe rasschitat'
konvertiruem = 'idet konvertaciya'
ADMIN = 'idet administrirovanie'
redis_url = os.environ.get('REDIS_URL')
dict_db = {}

#  Создаём базу данных либо загружаем готовую
if redis_url is None:
    """
    В данной функции мы получаем значения из redis database
    """

    try:
        data = json.load(open('db/data.json', 'r', encoding='utf-8'))  # выводим нашу базу данных

    except:
        data = {
            "states": {},
            "main": {},
            "vvedeni dannie": {},
            "idet rasschet": {},
            "vtoroe rasschitat": {},
            "idet konvertaciya": {},
            "idet administrirovanie": {},
            "sym": {},
            "konvertaciya": {},
            "Admins": {
                "mainadmins": "286770273"
            }
        }


else:
    redis_db = redis.from_url(redis_url)
    raw_data = redis_db.get('data')
    print('Viveodim')

    if raw_data is None:
        data = {
            "states": {},
            "main": {},
            "vvedeni dannie": {},
            "idet rasschet": {},
            "vtoroe rasschitat": {},
            "idet konvertaciya": {},
            "idet administrirovanie": {},
            "sym": {},
            "konvertaciya": {},
            "Admins": {
                "mainadmins": "810391410"
            }
        }

    else:
        data = json.loads(raw_data)  # выводим нашу базу данных
        print('Viveli')

konvertaciya = data['konvertaciya']  # будем использовать на этапе с конвертацией и выводом "квт", для других переменных
sym = data['sym']  # объявляем словарь с суммой


# функция изменения базы данных
def change_data(key, user_id, value):
    """
    В данной функции у нас происходит загрузка данных в redis db
    :param key: столбец базы данных
    :param user_id: id пользователя которму мы что-то меняем
    :param value: новое значение
    :return:
    """
    data[key][user_id] = value

    # проверяем наличие базы данных на редис
    if redis_url is None:  # Обработка базы данных, если нет подключения к редис
        json.dump(data,
                  open('db/data.json', 'w', encoding='utf-8'),
                  indent=2,
                  ensure_ascii=False,
                  )

    else:
        redis_db = redis.from_url(redis_url)
        redis_db.set('data', json.dumps(data))


# диспетчер состояний, используется декоратор message_handler для обработки сообщений
@bot.message_handler(content_types=['text'])
# Обработчик всех состояний
def dispatcher(message):
    """
    В данной функции происходит обработка состояний. Т.е. переход к различным
    функциям нашего бота в зависимости от состояния пользователя
    :param message: принимает на вход сообщение
    :return: ничего не вовращает. Вызывает другие функции
    """

    user_id = str(message.from_user.id)
    # Если словарь с состояниями пустой, то добавляем туда пользователя и присваиваем ему состояние MAIN_STATE
    if str(data['states']) == '{}':
        change_data('states', user_id, MAIN_STATE)

    try:
        print(data['states'][user_id])  # Проверяем наличие пользователя в БД, если его нет в БД, то добавляем его в БД
    except KeyError:
        change_data('states', user_id, MAIN_STATE)

    state = data['states'][user_id]  # Достаём состояния
    print('current state', user_id, state)  # Печатаем текущее состояние в логи

    # Обрабатываем состояния
    if state == MAIN_STATE:
        main_handler(message)

    elif state == Vvedini:
        Trati(message)

    elif state == Symiruem:
        Sym(message)

    elif state == SYM1:
        Sym1(message)

    elif state == konvertiruem:
        Trati2(message)

    elif state == ADMIN:
        adminpanel(message)


# основной обработчик
def main_handler(message):

    """
    В данной функции происходит обработка всех основных команд
    :param message: принимает на вход сообщение
    :return: ничего не возвращает. Вызывает другие функции
    """

    user_id = str(message.from_user.id)  # Объявляем переменную user id
    #  Обрабатываем команды

    if message.text == '/start':
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        btn1 = types.KeyboardButton('/test')
        btn2 = types.KeyboardButton('/help')
        btn3 = types.KeyboardButton('Рассчитать')
        markup.row(btn1, btn2, btn3)
        bot.send_message(message.from_user.id, 'Привет, я могу помочь тебе в подсчете твоих расходов! \nПо команде:'
                                               '\n/help вы узнаете возможности бота'
                                               '\n/test вы получите объяснение работы бота'
                                               '\nНапишите "Рассчитать" чтобы внести свои расходы', reply_markup=markup)

    elif message.text == '/test':
        test(message)

    elif message.text == '/help':
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        btn2 = types.KeyboardButton('/test')
        btn3 = types.KeyboardButton('Рассчитать')
        markup.row(btn2, btn3)
        tekct = 'По команде "Рассчитать" вы вводите свои расходы \nПо команде /test вам будет представлен пример работы бота'
        bot.send_message(message.from_user.id, tekct, reply_markup=markup)
    #  Обрабатываем кнопки

    elif message.text.lower() == 'рассчитать':
        bot.send_message(message.from_user.id, 'Напиши свои расходы (только цифрами!)')
        change_data('states', user_id, Symiruem)
        print(str(data['states'][user_id]))

    elif message.text.lower() == 'траты' or message.text.lower() == 'квт' or message.text.lower() == 'конвертировать':
        bot.send_message(message.from_user.id, 'Вы ещё не ввели свои расходы. Напишите "Рассчитать" чтобы ввести трату')

    elif message.text.lower() == 'админ панель':
        adminpanel(message)
        doadmenki = data['states'][user_id]
        koeficienti[12] = doadmenki
        change_data('states', user_id, ADMIN)
    #  Обрабатывем всё остальное

    else:
        bot.send_message(message.from_user.id, 'Я вас не понял;( \nИспользуйте панель или введите сумму ваших расходов')


#  Панель администратора
def adminpanel(message):
    """
    В данной функции проводятся основные админские манипуляции, такие как:
    Очистка БД, просмотр БД
    :param message: принимает на вход сообщение и обрабатывет его
    :return: отправляет сообщения
    """

    user_id = str(message.from_user.id)
    admins = data["Admins"]["mainadmins"]

    if user_id in admins:
        if message.text.lower() == 'очистить бд':
            bot.send_message(message.from_user.id, 'Идёт очистка базы данных')
            ochistka(message)

        elif message.text.lower() == 'вывод бд':
            tekct0 = 'STATES:  ' + str(data['states']) + 'SYMMI:  ' + str(data['sym']) + 'Informaciya pro konvertaciyu'
            tekct1 = str(data['konvertaciya'])
            tekct = tekct0 + '  ' + tekct1
            bot.send_message(user_id, tekct)

        elif message.text.lower() == 'выход':
            doadmenki = koeficienti[12]
            change_data('states', user_id, doadmenki)
            bot.send_message(user_id, 'Выход выполнен')

        elif message.text.lower() == 'админ панель':
            bot.send_message(user_id, 'Режим администрирования')

        else:
            bot.send_message(user_id, 'Команда не верна')


#  Функция очистки базы данных
def ochistka(message):

    """
    Данная функция выполняет задачу очистки БД. Например в случае неправильного ввода вы можете её почистить

    :param message: принимает сообщение, чтобы из него достать user id
    :return: ничего не возвращает.
    """

    user_id = str(message.from_user.id)
    data['states'] = {}
    data['sym'] = {}
    data['konvertaciya'] = {}

    print(data)
    change_data('states', user_id, ADMIN)
    print(data['states'])


# Пример работы бота
def test(message):

    """
    В данной функции выводится сообщение с разъяснениями для пользователя
    :param message: сообщение также принимается для обработки user_id
    :return: отпраавляет сообщения
    """
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    btn2 = types.KeyboardButton('/help')
    btn3 = types.KeyboardButton('Рассчитать')
    markup.row(btn2, btn3)

    tekct = 'Введите команду "Рассчитать",\nЗатем напишите цифрами сколько вы потратили,\nПосле выбираете валюту,\n'
    tekct1 = 'Далее вы можете посмотреть ваши расходы написав комманду "Траты"\nВам выводится значение в виде:'
    bot.send_message(message.from_user.id, tekct + tekct1)

    primersymmi = random.randrange(1000, 30000)
    primervaluti = random.choice(['Долларов', 'Рублей', 'Евро', 'Юаней'])
    soobchenie = 'Ваши траты составили: ' + str(primersymmi) + ' ' + str(primervaluti)
    bot.send_message(message.from_user.id, soobchenie, reply_markup=markup)


# записывальщик трат
def Sym(message):
    """
    Данная функция является основной в боте и отвечает за запись трат
    :param message: принимает на вход сообщение юзера
    :return: отправляет сообщения
    """

    user_id = str(message.from_user.id)
    state = data['states'][user_id]
    aftercikl = Vvedini  # Переменная, которая позволяет в случае ошибки перезапустить цикл, стандарт: она равна Vvedini

    if state == Symiruem:  # Проверка, что мы правельно попали в функцию
        symma = 0
        cifra = message.text

        try:  # Если всё введено правельно, то прибавляем введёное число к сумме
            symma += int(str(cifra))

        except:  # Если введено что-то помимо числа, то отправляем сообщение о неправельных данных
            bot.send_message(user_id, 'Введите только цифры')
            aftercikl = Symiruem

        if aftercikl == Vvedini:  # Проверка, что не допущены ошибки

            sym[user_id] = symma
            sym["1"] = cifra
            keyboard2 = types.InlineKeyboardMarkup()

            key_eur = types.InlineKeyboardButton(text='В евро', callback_data='eunow')
            keyboard2.add(key_eur)  # добавляем кнопку в клавиатуру

            key_usd = types.InlineKeyboardButton(text='В долларах', callback_data='usnow')
            keyboard2.add(key_usd)

            key_rub = types.InlineKeyboardButton(text='В рублях', callback_data='rubnow')
            keyboard2.add(key_rub)

            key_cny = types.InlineKeyboardButton(text='В юанях', callback_data='cnynow')
            keyboard2.add(key_cny)

            question2 = 'В какой валюте вы тратили деньги?'
            bot.send_message(message.from_user.id, text=question2, reply_markup=keyboard2)

        else:  # Если ошибки допущены, перезапускаем цикл
            change_data('states', user_id, aftercikl)


# записывальщик трат, когда уже была введена трата
def Sym1(message):
    """
    Данная функция также записывает траты, но уже приплюсовывает к старым.
    :param message: принимает на вход message
    :return: ничего не возвращает
    """

    user_id = str(message.from_user.id)
    state = data['states'][user_id]

    try:  # Проверяем, что у нас имеется состояние, которое было до начала выполнения функции
        dosymmi = data['dosymmi']

    except:
        # Если состояние исчезло(к примеру ошибка сервера или утрата БД), то считаем состояние за Vvedini
        dosymmi = Vvedini

    aftercikl = Vvedini

    if state == SYM1:
        symma = int(sym[user_id])
        cifra = message.text

        try:
            symma += int(str(cifra))  # Если всё верно, то сумируем

        except:
            bot.send_message(user_id, 'Введите только цифры')  # Если допущена какая-либо ошибка, то перезапускаем
            aftercikl = SYM1

        if aftercikl == Vvedini:  # Если всё введено нормально, то продолжаем

            sym[user_id] = symma
            sym["1"] = cifra

            markup1 = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)

            btn1 = types.KeyboardButton('Траты')
            btn2 = types.KeyboardButton('Конвертировать')
            btn3 = types.KeyboardButton('Рассчитать')

            markup1.row(btn1, btn2, btn3)

            bot.send_message(message.from_user.id, 'Хорошо, я записал вашу трату.\nВы можете посмотреть ее по команде '
                                                   '"Траты"', reply_markup=markup1)

            if dosymmi == konvertiruem and aftercikl == Vvedini:
                change_data('states', user_id, dosymmi)

        else:  # Если допущена ошибка при вводе суммы, то перезапускаем цикл
            change_data('states', user_id, aftercikl)


#  функция присваивания валюты
def oprvaliuti(call, valuta):
    """
    Данная функция определяет в какой валюте человек тратит деньги
    :param call: принимает запрос от пользователя
    :param valuta: переменная в которую записывается валюта
    :return: присваивает новое значение валюты в бд
    """

    user_id = str(call.from_user.id)
    konvertaciya[user_id + 'valiutatrat'] = valuta


# обработчик клавиатуры
@bot.callback_query_handler(func=lambda call: True)
def valuta(call):
    """
    Данная функция отвечает за обработку клавиатур
    :param call: Значение запроса клавиатуры
    :return:
    """

    user_id = str(call.from_user.id)  # Задаём user_id и state
    state = data['states'][user_id]

    if state == Symiruem:  # Проверка, верно ли состояние

        # объявляем валюту
        if call.data == 'eunow':
            valiuta = 'Евро'
            oprvaliuti(call, valiuta)

        if call.data == 'usnow':
            valiuta = 'Долларах'
            oprvaliuti(call, valiuta)

        if call.data == 'rubnow':
            valiuta = 'Рублях'
            oprvaliuti(call, valiuta)

        if call.data == 'cnynow':
            valiuta = 'Юанях'
            oprvaliuti(call, valiuta)

        # Настраиваем клавиатуру
        markup1 = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        btn1 = types.KeyboardButton('Траты')
        btn2 = types.KeyboardButton('Конвертировать')
        btn3 = types.KeyboardButton('Рассчитать')
        markup1.row(btn1, btn2, btn3)

        bot.send_message(call.message.chat.id, 'Я записал ваши расходы\nУзнать ваши траты и '
                                               'валюту, в которой они находятся вы можете по комманде "Траты" '
                                               '\nВы можете конвертировать ваши расходы в другую валюту написав '
                                               'команду '
                                               '"Конвертировать"', reply_markup=markup1)

        change_data('states', user_id, Vvedini)

        valiutahandler(call)  # вызываем функцию обработки переменной now

    else:
        valiutahandler(call)  # вызываем функцию обработки переменной now

        perevod(call)  # вызываем другой скрипт обработчика


def valiutahandler(call):
    """
    Данная функция отвечает за обработку валюты трат
    :param call: Запрос от пользователя
    :return: изменяет значение валюты в бд
    """

    user_id = str(call.from_user.id)  # Объявляем переменные user_id и valiuta
    valiuta = konvertaciya[user_id + 'valiutatrat']

    # Объявляем переменную now
    if 'Руб' in valiuta:
        now = 'rub'
        konvertaciya[1] = now

    if 'Дол' in valiuta:
        now = 'us'
        konvertaciya[1] = now

    if 'Евр' in valiuta:
        now = 'eu'
        konvertaciya[1] = now

    if 'Юан' in valiuta:
        now = 'cny'
        konvertaciya[1] = now


# обработчик при введённых тратах
def Trati(message):
    """
    Данная функция занимается обработкой вывода трат
    :param message: принимает сообщение пользователя
    :return:
    """

    user_id = str(message.from_user.id)  # Объявляем переменные user_id и valiuta
    valiuta = konvertaciya[user_id + 'valiutatrat']

    if message.text.lower() == 'траты':
        # Вводим стандартные кнопки и стандартную клавиатуру
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        btn1 = types.KeyboardButton('Рассчитать')
        btn2 = types.KeyboardButton('Конвертировать')

        # Если состояние 'konvertiruem', то добавляем дополнительную кнопку с текстом 'квт'
        if str(data['states'][user_id]) == konvertiruem:
            btn3 = types.KeyboardButton('КВТ')
            markup.row(btn1, btn2, btn3)

        # Если другое состояние, то добавляем кнопки к клавиатуре
        else:
            markup.row(btn1, btn2)

        # Объявляем переменную symma и объявляем переменную vivod
        symma = data['sym'][user_id]
        vivod = 'Ваши траты составили: ' + str(symma) + '  ' + 'Вы тратили деньги в ' + valiuta
        bot.send_message(message.from_user.id, vivod, reply_markup=markup)

    elif message.text.lower() == 'рассчитать':

        # Делаем все манипуляции, для возврата к тому же состоянию
        dosymmi = data['states'][user_id]
        data['dosymmi'] = dosymmi
        json.dump(data,
                  open('db/data.json', 'w', encoding='utf-8'),
                  indent=2,
                  ensure_ascii=False,
                  )

        bot.send_message(message.from_user.id, 'Напиши свои расходы (только цифрами!)')
        change_data('states', user_id, SYM1)

    elif message.text.lower() == 'конвертировать':
        konvert(message)

    elif message.text.lower() == 'квт':
        bot.send_message(message.from_user.id, 'Вы ещё не сконвертировали траты')

    else:
        main_handler(message)


#  обработчик при введённых данных и проделанной конвертации
def Trati2(message):
    """
    Данная функция занимается обработкой трат при введённых данных
    :param message: принимает на вход сообщение пользователя
    :return:
    """

    user_id = str(message.from_user.id)

    if message.text.lower() == 'квт':
        konvertirovano = konvertaciya[user_id + 'symma']
        vochtoperevesti = konvertaciya[user_id]

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        btn1 = types.KeyboardButton('Рассчитать')
        btn2 = types.KeyboardButton('Конвертировать')
        btn3 = types.KeyboardButton('Траты')
        markup.row(btn1, btn2, btn3)

        tekct = 'Ваши траты: ' + str(konvertirovano) + ' ' + str(vochtoperevesti)
        bot.send_message(message.from_user.id, tekct, reply_markup=markup)

    else:
        Trati(message)


#  Клавиатура выбора валюты в которую конвертировать
def konvert(message):
    """
    Данная функция создаёт клавиатуры перевода в различные валюты
    :param message: Принимает на вход сообщение
    :return: отправляет сообщение
    """

    # создаём клавиатуру, для определения, в какую валюту переводить
    keyboard = types.InlineKeyboardMarkup()

    key_euro = types.InlineKeyboardButton(text=' Перевести в Евро', callback_data='eu')
    keyboard.add(key_euro)  # добавляем кнопку в клавиатуру

    key_usd = types.InlineKeyboardButton(text='Перевести в Доллары', callback_data='us')
    keyboard.add(key_usd)

    key_rub = types.InlineKeyboardButton(text='Перевести в Рубли', callback_data='rub')
    keyboard.add(key_rub)

    key_cny = types.InlineKeyboardButton(text='Перевести в Юани', callback_data='cny')
    keyboard.add(key_cny)

    question = 'В какую валюту вы хотите конвертировать?'
    bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)


# Конвертатор валют
@bot.callback_query_handler(func=lambda call: True)
def perevod(call):
    """
    Данная функция занимается переводом трат в нужную валюту.
    :param call: проверка на запрос от кнопки
    :return: не возвращает
    """

    user_id = str(call.from_user.id)
    change_data('states', user_id, konvertiruem)
    now = konvertaciya[1]

    # обработчик клавиатуры в которой задаётся, переменная в которую мы переводим
    symma = sym[user_id]
    CNY = koeficienti[1]
    USD = koeficienti[11]
    EUR = koeficienti[0]

    izEURvUSD = koeficienti[2]
    izEURvCNY = koeficienti[8]

    izUSDvEUR = koeficienti[3]
    izUSDvCNY = koeficienti[7]

    izRUBvUSD = koeficienti[4]
    izRUBvEUR = koeficienti[5]
    izRUBvCNY = koeficienti[6]



    izCNYvUSD = koeficienti[9]
    izCNYvEUR = koeficienti[10]

    vochtoperevesti = call.data

    # всё ниже это конвертаторы из одной валюты в другую. Всё точно работает:)
    if vochtoperevesti == "eu" and now == 'eu':
        bot.send_message(call.message.chat.id, 'Ваша валюта уже евро')

    if vochtoperevesti == "rub" and now == 'rub':
        bot.send_message(call.message.chat.id, 'Ваша валюта уже рубли')

    if vochtoperevesti == "us" and now == 'us':
        bot.send_message(call.message.chat.id, 'Ваша валюта уже доллары')

    if vochtoperevesti == 'cny' and now == 'cny':
        bot.send_message(call.message.chat.id, 'Ваша валюта уже юани')

    if vochtoperevesti == 'rub' and now == 'cny':
        konvertirovano = int(symma) * CNY
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_RUB(call)
        messkonvert(call)

    if vochtoperevesti == 'cny' and now == 'rub':
        konvertirovano = int(symma) * izRUBvCNY
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_CNY(call)
        messkonvert(call)

    if vochtoperevesti == 'us' and now == 'cny':
        konvertirovano = int(symma) * izCNYvUSD
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_USD(call)
        messkonvert(call)

    if vochtoperevesti == 'cny' and now == 'eu':
        konvertirovano = int(symma) * izEURvCNY
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_CNY(call)
        messkonvert(call)

    if vochtoperevesti == 'cny' and now == 'us':
        konvertirovano = int(symma) * izUSDvCNY
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_CNY(call)
        messkonvert(call)

    if vochtoperevesti == 'eu' and now == 'cny':
        konvertirovano = int(symma) * izCNYvEUR
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_EUR(call)
        messkonvert(call)

    if vochtoperevesti == 'us' and now == 'rub':
        konvertirovano = int(symma) * izRUBvUSD
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_USD(call)
        messkonvert(call)

    if vochtoperevesti == 'rub' and now == 'us':
        konvertirovano = int(symma) * USD
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_RUB(call)
        messkonvert(call)

    if vochtoperevesti == 'eu' and now == 'rub':
        konvertirovano = int(symma) * izRUBvEUR
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_EUR(call)
        messkonvert(call)

    if vochtoperevesti == 'rub' and now == 'eu':
        konvertirovano = int(symma) * EUR
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_RUB(call)
        messkonvert(call)

    if vochtoperevesti == 'eu' and now == 'us':
        konvertirovano = int(symma) * izUSDvEUR
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_EUR(call)
        messkonvert(call)

    if vochtoperevesti == 'us' and now == 'eu':
        konvertirovano = int(symma) * izEURvUSD
        konvertaciya[user_id + 'symma'] = konvertirovano
        okryglenie(call)
        KonvertV_USD(call)
        messkonvert(call)

    json.dump(data,
              open('db/data.json', 'w', encoding='utf-8'),
              indent=2,
              ensure_ascii=False,
              )


def KonvertV_USD(call):  # функция отправки сообщения при переводе в доллары
    """
    данная
    :param call:
    :return:
    """
    user_id = str(call.message.chat.id)
    bot.send_message(call.message.chat.id, 'Ваши траты в долларах = ' + str(konvertaciya[user_id + 'symma']))
    vochtoperevesti = 'В долларах'
    konvertaciya[user_id] = vochtoperevesti


def KonvertV_CNY(call):  # функция отправки сообщения при переводе в юани
    user_id = str(call.message.chat.id)
    bot.send_message(call.message.chat.id, 'Ваши траты в юанях = ' + str(konvertaciya[user_id + 'symma']))
    vochtoperevesti = 'В юанях'
    konvertaciya[user_id] = vochtoperevesti


def KonvertV_RUB(call):  # функция отправки сообщения при переводе в рубли
    user_id = str(call.message.chat.id)
    bot.send_message(call.message.chat.id, 'Ваши траты в рублях = ' + str(konvertaciya[user_id + 'symma']))
    vochtoperevesti = 'В рублях'
    konvertaciya[user_id] = vochtoperevesti


def KonvertV_EUR(call):  # функция отправки сообщения при переводе в евро
    user_id = str(call.message.chat.id)
    bot.send_message(call.message.chat.id, 'Ваши траты в евро = ' + str(konvertaciya[user_id + 'symma']))
    vochtoperevesti = 'В евро'
    konvertaciya[user_id] = vochtoperevesti


def okryglenie(call):  # Функция округления
    user_id = str(call.from_user.id)
    konvertirovano = konvertaciya[user_id + 'symma']
    konvertirovano = round(konvertirovano, 2)
    konvertaciya[user_id + 'symma'] = konvertirovano


def messkonvert(call):  # функция отправки сообщения, о возможности узнать конвертированную трату :)
    user_id = call.message.chat.id

    markup1 = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Траты')
    btn2 = types.KeyboardButton('КВТ')
    btn3 = types.KeyboardButton('Рассчитать')
    btn4 = types.KeyboardButton('Конвертировать')
    markup1.row(btn1, btn2, btn3, btn4)

    bot.send_message(user_id, 'Вы можете конвертировать расходы, написав комманду '
                              '"КВТ"', reply_markup=markup1)


if __name__ == '__main__':
    bot.polling()
