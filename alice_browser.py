#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер чата Алисы через браузер. Чистая реализация с нуля (без JS-вставок).
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time  # Для измерения времени

URL = "https://alice.yandex.ru"

# Селекторы — если сломается, смотри в DevTools
INPUT_SEL = "textarea, [contenteditable='true'], [placeholder*='Спросите']"
BUBBLE_SEL = ".AliceTextBubbleAnimated"
STABLE_MS = 2000
POLL_MS = 300

def _type_and_send(page, text: str) -> None:
    """Вставляет текст в поле ввода и отправляет."""
    # Прокручиваем вниз
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(600)

    # Ищем поле ввода
    input_field = page.query_selector(INPUT_SEL)
    if not input_field:
        raise Exception("Поле ввода не найдено")

    # Кликаем для фокуса
    input_field.click()
    page.wait_for_timeout(200)

    # Определяем тип элемента и вставляем текст
    tag_name = input_field.evaluate("(el) => el.tagName")
    if tag_name == "TEXTAREA":
        # Для <textarea> используем fill()
        input_field.fill(text)
    else:
        # Для contenteditable используем type()
        page.keyboard.type(text, delay=20)

    page.wait_for_timeout(100)
    # Отправляем, нажимая Enter
    page.keyboard.press("Enter")

def _wait_response_in_page(page, prev_text: str, timeout_ms: int = 120000) -> str:
    """
    Ждёт появления текста в последнем пузыре, отличного от prev_text,
    и его стабилизации.
    """
    start_time = time.time()  # Начало отсчёта общего таймаута
    stable_start_time = None  # Время, когда текст стал стабильным
    last_seen = ""  # Последний увиденный текст

    while (time.time() - start_time) < timeout_ms / 1000:
        # Ждём появления хотя бы одного пузыря
        bubbles = page.query_selector_all(BUBBLE_SEL)
        if not bubbles:
            page.wait_for_timeout(POLL_MS)
            continue

        # Берём последний пузырь
        last_bubble = bubbles[-1]
        text = last_bubble.text_content().strip()

        # Пропускаем пустые пузыри или те, что равны предыдущему тексту
        if not text or text == prev_text:
            page.wait_for_timeout(POLL_MS)
            continue

        if text == last_seen:
            # Текст стабилен, проверяем время стабильности
            if stable_start_time is None:
                stable_start_time = time.time()
            elif (time.time() - stable_start_time) >= STABLE_MS / 1000:
                # Текст стабилен нужное время
                return text
        else:
            # Текст изменился, сбрасываем таймер стабильности
            last_seen = text
            stable_start_time = None

        page.wait_for_timeout(POLL_MS)

    # Таймаут вышел
    return last_seen or "Таймаут: ответ не появился."

def _get_last_bubble_text(page) -> str:
    """Текст последнего пузыря Алисы."""
    bubbles = page.query_selector_all(BUBBLE_SEL)
    if bubbles:
        return bubbles[-1].text_content().strip()
    return ""

class ChatSession:
    """Одна вкладка, один чат, история сохраняется."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._page = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        ctx = self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ru-RU",
        )
        self._page = ctx.new_page()
        self._page.goto(URL, wait_until="networkidle", timeout=30000)
        return self

    def __exit__(self, *args):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def send(self, text: str) -> str:
        try:
            prev = _get_last_bubble_text(self._page)
            _type_and_send(self._page, text)
            return _wait_response_in_page(self._page, prev)
        except PlaywrightTimeout:
            return "Таймаут: страница не ответила."
        except Exception as e:
            return f"Ошибка: {e}"

def ask(text: str, headless: bool = True) -> str:
    """Один запрос (открывает и закрывает браузер)."""
    with ChatSession(headless=headless) as s:
        return s.send(text)

if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if sys.argv[1:] else "Привет!"
    print(ask(msg, headless=False))
