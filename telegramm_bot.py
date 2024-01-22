import json
import random
from table_starter import*
from sqlalchemy.sql import func
from sqlalchemy import and_
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup


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
    trach = []
    q = session.query(Words).all()
    for i in q:
        trach.append(((list(str(i).split(", ")))[0]))
    if a in trach:
        trach.remove(a)
    others = random.sample(trach, 4)  # брать из БД
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
    userStep[cid] = 1
    if message.text == Command.DELETE_WORD:
        msg = bot.send_message(cid, "Введите слово на английском языке для удаления")
        bot.register_next_step_handler(msg, user_answer_del)
    
def user_answer_del(message):
    vision = []
    vision_all = []
    cid = message.chat.id
    name_del = message.text
    if name_del == "Дальше ⏭":
        create_cards(message)
    elif name_del == "Добавить слово ➕":
        add_word(message)
    elif name_del == "Удалить слово🔙":
        delete_word(message)
        return
    else:
        word = session.query(Words).filter_by(word=name_del).first()
        user = session.query(User).filter_by(name=cid).first()
        q = session.query(Words).filter_by(is_public=True).all()
        for i in q:
            vision.append(((list(str(i).split(", ")))[0]))
        q1 = session.query(Words).join(User_Words).join(User).filter(and_(User.name == cid, User.name == User_Words.user_id, Words.id == User_Words.words_id, Words.is_public == False)).all()
        for i in q1:
            vision_all.append(((list(str(i).split(", ")))[0]))
        if name_del in vision:
            bot.send_message(cid, "Это слово не подлежит удалению")
            create_cards(message)
        elif name_del in vision_all:
            q = session.query(User_Words).filter_by(user_id=user.name, words_id=word.id).first()
            session.delete(q)
            session.commit()
            create_cards(message)
        else:
            bot.send_message(cid, "Это слово не находится в Вашем списке")
            create_cards(message)

#Добавление слова в базу для соответствующего ID
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    if message.text == Command.ADD_WORD:
        msg = bot.send_message(cid, "Введите слово на английском языке")
        bot.register_next_step_handler(msg, user_answer)

new_word_list = []

def user_answer(message):
    cid = message.chat.id
    name = message.text
    vision = []
    vision_all = []
    if name == "Дальше ⏭":
        create_cards(message)
    elif name == "Добавить слово ➕":
        add_word(message)
    elif name == "Удалить слово🔙":
        delete_word(message)
        return
    else:
        print(name)
        word = session.query(Words).filter_by(word=name).first()
        user = session.query(User).filter_by(name=cid).first()
        q = session.query(Words).filter_by(is_public=True).all()
        for i in q:
            vision.append(((list(str(i).split(", ")))[0]))
        q1 = session.query(Words).join(User_Words).join(User).filter(and_(User.name == User_Words.user_id, Words.id == User_Words.words_id, Words.is_public == False)).all()
        for i in q1:
            vision_all.append(((list(str(i).split(", ")))[0]))
        name_x = name
        name_x_del = list(name_x)
        name_x_del.pop(-1)
        print(vision)
        print(vision_all)
        bild = ("".join(name_x_del))
        if name in vision or bild in vision:
            bot.send_message(cid, "Это слово уже есть в базовом списке")
            create_cards(message)
        elif name in vision_all:
            bot.send_message(cid, "Это слово Вы уже добавляли")
            create_cards(message)
        else:
            new_word_list.append(name)
            msg = bot.send_message(cid, "Введите перевод")
            bot.register_next_step_handler(msg, user_answer2)
        

def user_answer2(message):
    all_false = []
    cid = message.chat.id
    name = message.text
    if name == "Дальше ⏭":
        create_cards(message)
    elif name == "Добавить слово ➕":
        add_word(message)
    elif name == "Удалить слово🔙":
        delete_word(message)
        return new_word_list.clear()
    else:
        print(name)
        q1 = session.query(Words).filter_by(is_public=False).all()
        for i in q1:
            all_false.append(i)
        new_word_list.append(name)
        a = new_word_list[0]
        b = name # сохранить в БД
        if a in all_false:
            q = session.query(Words).filter(Words.word == new_word_list[0]).all()
            for i in q:
                new_id = (i.id)
                u_w4 = User_Words(user_id = cid, words_id = new_id)
                session.add(u_w4)
                session.commit()
                create_cards(message)
        else:
            try:
                wr1 = Words(word = a, translation = b, is_public = False)
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
            bot.reply_to(message, f'Добавлено слово {a} с переводом {b} ')
            create_cards(message)
       

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
