import json
import unittest

from crawl_weread import extract_initial_book_info


class InitialBookInfoTests(unittest.TestCase):
    def test_runtime_mutation_does_not_replace_response_metadata(self):
        info = {
            "title": "亲密关系（第8版）",
            "author": "[美]罗兰·米勒",
            "cover": "https://example.com/correct-cover.jpg",
            "publisher": "人民邮电出版社有限公司",
        }
        state = json.dumps({"reader": {"bookInfo": info}}, ensure_ascii=False)
        html = (
            '<script>window.__INITIAL_STATE__ = ' + state + ';</script>'
            '<script>window.__INITIAL_STATE__.reader.bookInfo.cover = '
            '"https://example.com/wrong-cover.jpg";'
            'window.__INITIAL_STATE__.reader.bookInfo.publisher = "wrong";</script>'
        )
        self.assertEqual(extract_initial_book_info(html), info)

    def test_accepts_escaped_strings_and_trailing_javascript(self):
        info = {"title": '书名中的 "引号" 与括号 }', "cover": "https://example.com/a.jpg"}
        html = 'window.__INITIAL_STATE__=\n' + json.dumps({"reader": {"bookInfo": info}}) + ';window.ready=true;'
        self.assertEqual(extract_initial_book_info(html), info)

    def test_missing_or_invalid_state_returns_empty_info(self):
        for html in (
            '<title>没有初始状态</title>',
            'window.__INITIAL_STATE__ = invalid;',
            'window.__INITIAL_STATE__ = null;',
            'window.__INITIAL_STATE__ = [];',
            'window.__INITIAL_STATE__ = {};',
            'window.__INITIAL_STATE__ = {"reader": null};',
            'window.__INITIAL_STATE__ = {"reader": {"bookInfo": []}};',
        ):
            with self.subTest(html=html):
                self.assertEqual(extract_initial_book_info(html), {})


if __name__ == "__main__":
    unittest.main()
