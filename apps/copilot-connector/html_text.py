# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Zamiana HTML na zwykly tekst.

Plane zwraca opis zadania (i tresc komentarzy) wylacznie jako HTML
(pola 'description_html' / 'comment_html'). Ten modul jest wspolny dla
serwisu synchronizujacego (sync_service.py) i serwera MCP (plane_mcp_server.py).
Nie ma zadnych zaleznosci poza biblioteka standardowa.
"""
import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """Bloki (p, li, h1...) rozdziela nowa linia, komorki tabeli - odstepem; pomija <script>/<style>."""
    BLOCK_TAGS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote", "pre", "hr"}
    CELL_TAGS = {"td", "th"}
    SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        elif tag in self.CELL_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(html):
    """Zwraca czysty tekst z fragmentu HTML ('' dla pustego wejscia lub pustego akapitu)."""
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()
