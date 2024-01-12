import json
import random
import sqlalchemy
import sqlalchemy as sq
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup


#Создание и заполнение базы данных
Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    #id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.Integer, primary_key=True)
    words = relationship("User_Words", backref='users')
    
    def __str__(self):
        return f'{self.name}'


class User_Words(Base):
    __tablename__ = 'user_words'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer(), sq.ForeignKey("user.name"))
    words_id =  sq.Column(sq.Integer(), sq.ForeignKey("words.id"))


class Words(Base):
    __tablename__ = "words"

    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length=160), unique=True)
    translation = sq.Column(sq.String(length=160), unique=True)
    user = relationship("User_Words", backref='wordss')
    
    def __str__(self):
        return f'{self.word}, {self.translation}'


class Trashcan(Base):
    __tablename__ = "trashcan"

    id = sq.Column(sq.Integer, primary_key=True)
    ran = sq.Column(sq.String(length=40), unique=True)
  
    def __str__(self):
        return f'{self.ran}'

# 1 - удаление всего из базы; 2 - создание новой базы
def create_tables(engine):
    #Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


#Создание адреса базы данных
DSN = input("Введите адрес базы данных, например: ")
engine = sqlalchemy.create_engine(DSN)
create_tables(engine)

#Создание сессии
Session = sessionmaker(bind = engine)
session = Session()

# Заполнение базы при первом открытии бота
with open(r"tests_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    for record in data:
        model = {
            "user" : User,
            "words": Words,
            "user_words": User_Words,
            "trashcan": Trashcan,
        }[record.get('model')]
        session.add(model(**record.get('fields')))
    session.commit()

#Запуск бота
print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = input("Введите токен бота: ")
bot = TeleBot(token_bot, state_storage=state_storage, skip_pending=True)
#skip_pending=True - пропускать сообщения, отправленные до запуска бота

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


# Функция, запоминающая пользователя, который еще не нажал 'cards', 'start'
def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


#Ответ при запросе помощи. Текст форматирован с помощью HTML.
@bot.message_handler(commands=['help'])
def send_help(message):
    cid = message.chat.id
    get_user_step(cid)
    ans =  (f'<u><b>Привет, {message.from_user.first_name}! 👋 '
            f'Давай попрактикуемся в английском языке. '
            f'Тренировки можешь проходить в удобном для себя темпе. '
            f'У тебя есть возможность использовать тренажёр, как конструктор, '
            f'и собирать свою собственную базу для обучения. '
            f'Для этого воспрользуйся инструментами:</b></u>\n'
            f'добавить слово ➕,\n'
            f'удалить слово 🔙.\n'
            f'Ну что, начнём ⬇️')
    bot.send_message(cid, ans, parse_mode='html') 

# Создание очередной карточки (слово, его перевод и четыре неправильных перевода)
@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        send_help(message)
        #Дополнение базы данных для последующих открывших бота
        try:
            with open(r"next_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                data[0]['fields'].update({"name": cid})
                for i in range(1, 11):
                    data[i]['fields'].update({"user_id": cid})
                for record in data:
                    model = {
                        "user" : User,
                        "user_words": User_Words
                    }[record.get('model')]
                    session.add(model(**record.get('fields')))
                session.commit()
        except:
            pass
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    #Выбор рандомного слова и перевода для соответствующего ID
    user = session.query(User).filter_by(name = cid).first()
    q = session.query(Words).join(User_Words).filter_by(user_id = user.name).order_by(func.random()).first()
    a = (list(str(q).split(", ")))[0]
    b = (list(str(q).split(", ")))[1]
    session.commit()
    target_word = a  # брать из БД
    translate = b  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    #Четыре рандомных слова из базы
    lis_t = []   
    q = session.query(Trashcan).order_by(func.random()).limit(4).all()
    for i in q:
        lis_t.append((str(i)))
    others = lis_t  # брать из БД
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        a = (data.get('target_word'))  # удалить из БД
        print(a)
        #Удаление отдельного слова. Удаляется слово из очередной карточки.
        user = session.query(User).filter_by(name = cid).first()
        word = session.query(Words).filter_by(word = a).first()
        q = session.query(User_Words).filter_by(user_id=user.name, words_id=word.id).first()
        session.delete(q)
        session.commit()

#Добавление слова в базу для соответствующего ID
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    if message.text == Command.ADD_WORD:
        bot.reply_to(message, 'Введите слово на английском языке и через запятую с пробелом его перевод')
        @bot.message_handler(content_types=['text'])
        def message_input_step(message):
             global text
             text = message.text
             try:
                 a = (list(str(message.text).split(", ")))[0]
                 b = (list(str(message.text).split(", ")))[1] # сохранить в БД
                 bot.reply_to(message, f'Добавлено слово {a} с переаодом {b} ')
             except:
                 pass
             try:
                 wr1 = Words(word = a, translation= b)
                 session.add(wr1)
                 session.commit()
                 q = session.query(Words).filter(Words.word == a).all()
                 for i in q:
                     new_id = (i.id)
                     u_w4 = User_Words(user_id = cid, words_id = new_id)
                     session.add(u_w4)
                     session.commit()
             except:
                 pass
        bot.register_next_step_handler(message, message_input_step)

#Функция выделяет крестом на кнопках неправильные ответы, либо отвечает при правильном.
@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=False)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get('target_word')
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)
# reply_markup=markup - необходим для привязки кнопок к сообщению

bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)

session.close()
