import json
import sqlalchemy
import sqlalchemy as sq
from models import User, User_Words, Words, Base
from sqlalchemy.orm import sessionmaker

# 1 - удаление всего из базы; 2 - создание новой базы
def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


#Создание адреса базы данных
DSN = input("Введитк DNS: ")
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
            "words": Words
        }[record.get('model')]
        session.add(model(**record.get('fields')))
    session.commit()