#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер чата Алисы через браузер. Чистая реализация с нуля.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = "https://alice.yandex.ru"

# Селекторы — если сломается, смотри в DevTools
INPUT_SEL = "textarea, [contenteditable='true'], [placeholder*='Спросите']"
BUBBLE_SEL = ".AliceTextBubbleAnimated"
STABLE_MS = 2000
POLL_MS = 300


def _type_and_send(page, text: str) -> None:
    """Вставляет текст в поле ввода и отправляет."""
    js = """
    (text) => {
        const el = document.querySelector("textarea, [contenteditable='true'], [placeholder*='Спросите']");
        if (!el) return false;
        el.focus();
        if (el.tagName === "TEXTAREA") {
            el.value = text;
            el.dispatchEvent(new Event("input", { bubbles: true }));
        } else {
            const r = document.createRange();
            r.selectNodeContents(el);
            r.collapse(true);
            const s = window.getSelection();
            s.removeAllRanges();
            s.addRange(r);
            document.execCommand("insertText", false, text);
        }
        return true;
    }
    """
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(600)

    if not page.evaluate(js, text):
        vp = page.viewport_size
        page.mouse.click(vp["width"] // 2, vp["height"] - 80)
        page.wait_for_timeout(200)
        page.keyboard.type(text, delay=20)

    page.wait_for_timeout(100)
    page.keyboard.press("Enter")


def _wait_response_in_page(page, prev_text: str, timeout_ms: int = 120000) -> str:
    """
    Вся логика ожидания — в JS на странице.
    Ждёт появления текста в последнем пузыре, отличного от prev_text,
    и его стабилизации. Возвращает Promise — Playwright дождётся.
    """
    return page.evaluate(
        """
    (args) => {
        const { prevText, timeoutMs, stableMs, pollMs } = args;
        return new Promise((resolve) => {
            let lastSeen = "";
            let stableCount = 0;
            const stableTicks = Math.ceil(stableMs / pollMs);

            const check = () => {
                const bubbles = document.querySelectorAll(".AliceTextBubbleAnimated");
                if (!bubbles.length) return;
                const last = bubbles[bubbles.length - 1];
                const text = last.innerText.trim();
                if (!text) return;
                if (text === prevText) return;
                if (text === lastSeen) {
                    stableCount++;
                    if (stableCount >= stableTicks) {
                        clearInterval(iv);
                        clearTimeout(tm);
                        resolve(text);
                    }
                } else {
                    lastSeen = text;
                    stableCount = 0;
                }
            };

            const iv = setInterval(check, pollMs);
            const tm = setTimeout(() => {
                clearInterval(iv);
                resolve(lastSeen || "Таймаут: ответ не появился.");
            }, timeoutMs);
        });
    }
    """,
        {
            "prevText": prev_text,
            "timeoutMs": timeout_ms,
            "stableMs": STABLE_MS,
            "pollMs": POLL_MS,
        },
    )


def _get_last_bubble_text(page) -> str:
    """Текст последнего пузыря Алисы."""
    js = """
    () => {
        const bubbles = document.querySelectorAll(".AliceTextBubbleAnimated");
        return bubbles.length ? bubbles[bubbles.length - 1].innerText.trim() : "";
    }
    """
    return page.evaluate(js) or ""


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
