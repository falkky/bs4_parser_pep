# Проект сбора информации о Python
## Описание
Скрипт парсит сайт python.org и собирает информацию о версиях Python, PEP, скачивает документацию
## Как запустить проект
Клонировать репозиторий
```
git clone git@github.com:falkky/bs4_parser_pep.git
```
Перейти в каталог проекта
```
cd bs4_parser_pep
```
Создать и активировать виртуальное окружение
```
python3 -m venv venv
```
```
. venv/bin/activate
```
Перейти в каталог src и запустить main.py с ключем -h для вывода возможных аргументов запуска парсера
```
cd src
```
```
python3 main.py -h
```
Пример запуска парсера в режиме сбора информации о PEP и сохранения в csv
```
python3 main.py pep -o file
```
## Используемые технологии
* Python 3.11
* Beautifulsoup4
* requests-cache
* argparse
* logging
* prettytable
* tqdm
## Автор
Andrew Stepanov https://github.com/falkky
