#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Чат с нейросетью через alice.yandex.ru.
Простой вывод текста, без обработки блоков.
"""

import colorama

from alice_browser import ChatSession

colorama.init()

# Режим: True = браузер в фоне, False = видно окно
HEADLESS = True
USER_COLOR = colorama.Fore.CYAN      # голубой — твоё сообщение
ALICE_COLOR = colorama.Fore.YELLOW   # жёлтый — ответ Алисы
RESET = colorama.Style.RESET_ALL


def chat():
    """Цикл переписки: вводишь — получаешь ответ. Чат один, история сохраняется."""
    print("Alice (alice.yandex.ru). Выход: пустая строка или Ctrl+C\n")

    with ChatSession(headless=HEADLESS) as session:
        while True:
            try:
                print(USER_COLOR, end="")
                text = input("> ").strip()
                print(RESET, end="")
            except (KeyboardInterrupt, EOFError):
                print("\nПока.")
                break

            if not text:
                break

            print("Жду ответ...")
            response = session.send(text)
            print(f"{ALICE_COLOR}{response}{RESET}")
            print()


if __name__ == "__main__":
    chat()
