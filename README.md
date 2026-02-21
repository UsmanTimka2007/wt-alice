# Alice Chat API

Чат с Алисой (alice.yandex.ru) через Python. Парсинг DOM, вывод текста без обработки блоков.

## Установка

```bash
pip install -r requirements.txt
playwright install chromium
```

## Запуск

```bash
python alice_api.py
```

## Селекторы

Если ничего не работает — селекторы устарели. Открой alice.yandex.ru в браузере, F12 → Elements:

1. **input** — поле ввода (textarea или contenteditable)
2. **send** — кнопка отправки (или используем Enter)
3. **assistant_msg** — блок с ответом Алисы (поищи по `data-*`, классам, `role`)

В `alice_browser.py` в словаре `SELECTORS` замени на найденные селекторы.

Отладка: в `alice_api.py` поставь `HEADLESS = False` — окно браузера будет видно.
