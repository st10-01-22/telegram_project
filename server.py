import telebot
from map import get_map_cell
from wikipediaapi import Wikipedia
from config import BOT_TOKEN, API_KEY
import requests

# Создаём бота
bot = telebot.TeleBot(BOT_TOKEN)
# Настройка языка википедии
wiki = Wikipedia('ru')
# Настройка размера лабиринта
cols, rows = 8, 8

# Клавиатура для лабиринта
keyboard = telebot.types.InlineKeyboardMarkup()
keyboard.row(telebot.types.InlineKeyboardButton('←', callback_data='left'),
             telebot.types.InlineKeyboardButton('↑', callback_data='up'),
             telebot.types.InlineKeyboardButton('↓', callback_data='down'),
             telebot.types.InlineKeyboardButton('→', callback_data='right'))

# Место хранения сгенерированных лабиринтов
maps = {}

# Функция отрисовки карты лабиринта
def get_map_str(map_cell, player):
    map_str = ""
    for y in range(rows * 2 - 1):
        for x in range(cols * 2 - 1):
            if map_cell[x + y * (cols * 2 - 1)]:
                map_str += "⬛"
            elif (x, y) == player:
                map_str += "🔴"
            else:
                map_str += "⬜"
        map_str += "\n"

    return map_str


# Функция для получения адреса пользователя
@bot.message_handler(content_types=["location"])
def location(message):
    if message.location is not None:
        coord = str(message.location.longitude) + ',' + str(message.location.latitude)
        r = requests.get('https://geocode-maps.yandex.ru/1.x/?apikey=' + API_KEY + '&format=json&geocode=' + coord)

        if len(r.json()['response']['GeoObjectCollection']['featureMember']) > 0:
            address = r.json()['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
                'GeocoderMetaData']['text']
            bot.send_message(message.chat.id, 'Ваш адрес:\n{}'.format(address))
        else:
            bot.send_message(message.chat.id, 'Не удалось получить Ваш адрес')


# Функция начала игры
@bot.message_handler(commands=['play'])
def play_message(message):
    map_cell = get_map_cell(cols, rows)

    user_data = {
        'map': map_cell,
        'x': 0,
        'y': 0
    }

    maps[message.chat.id] = user_data

    bot.send_message(message.from_user.id, get_map_str(map_cell, (0, 0)), reply_markup=keyboard)


# Функция управления игрой
@bot.callback_query_handler(func=lambda call: True)
def callback_func(query):
    user_data = maps[query.message.chat.id]
    new_x, new_y = user_data['x'], user_data['y']

    if query.data == 'left':
        new_x -= 1
    if query.data == 'right':
        new_x += 1
    if query.data == 'up':
        new_y -= 1
    if query.data == 'down':
        new_y += 1

    if new_x < 0 or new_x > 2 * cols - 2 or new_y < 0 or new_y > rows * 2 - 2:
        return None
    if user_data['map'][new_x + new_y * (cols * 2 - 1)]:
        return None

    user_data['x'], user_data['y'] = new_x, new_y

    if new_x == cols * 2 - 2 and new_y == rows * 2 - 2:
        bot.edit_message_text(chat_id=query.message.chat.id,
                              message_id=query.message.id,
                              text="Вы выиграли")
        return None

    bot.edit_message_text(chat_id=query.message.chat.id,
                          message_id=query.message.id,
                          text=get_map_str(user_data['map'], (new_x, new_y)),
                          reply_markup=keyboard)


# Фукнция пересыла ответа википедии пользователю
def send_long_message(chat_id, text):
    while len(text) > 4096:
        bot.send_message(chat_id, text[0:4096])
        text = text[4096::]

    bot.send_message(chat_id, text)


# Стартовая функция
@bot.message_handler(commands=['help', 'start'])
def handle_command(message):
    bot.send_message(message.chat.id, f"Приветствую, {message.from_user.username}")
    bot.send_message(message.chat.id, "На данный момент я умею три вещи:")
    bot.send_message(message.chat.id, "1) Ты можешь прислать мне любое слово и дам тебе информацию о нём из википедии")
    bot.send_message(message.chat.id, "2) Если ты скинешь мне свою геолокацию, я смогу сказать тебе твой точный адрес")
    bot.send_message(message.chat.id, "3) Напиши /play чтобы сыграть в миниигру")


# Функция проверки, есть ли вообще информация на википедии
@bot.message_handler(content_types=["text"])
def handle_message(message):
    page = wiki.page(message.text)
    if page.exists():
        send_long_message(message.chat.id, page.summary)
    else:
        bot.send_message(message.chat.id, 'Nothing found')


if __name__ == '__main__':
    bot.polling(True)
