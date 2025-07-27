
"""
wikiscrape.py – minimal, polite Wikipedia text extractor
--------------------------------------------------------

Usage
-----
>>> from wikiscrape import get_article_text
>>> text = get_article_text("Albert Einstein", lang="en")
>>> print(text[:800], "…")

You can also process a whole list safely:

>>> from wikiscrape import batch_fetch
>>> results = batch_fetch([("en", "Albert Einstein"),
...                        ("de", "Quantenmechanik")])
"""

from __future__ import annotations
import random, time, re, html
from typing import Iterable, List, Tuple, Dict

import requests
import certifi
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# 1.  CONFIGURATION
# ----------------------------------------------------------------------

USER_AGENT = "WikipediaTextBot/1.0 (example@example.com)"
DEFAULT_SLEEP = (0.75, 1.25)             # polite random delay in seconds
TIMEOUT      = 15                        # request timeout

# Headings after which we CUT the article
STOP_HEADINGS = {
    "en": (
        "references", "citations", "sources", "notes",
        "bibliography", "further reading",
        "external links", "see also",
    ),
    "de": (
        "einzelnachweise", "literatur",
        "quellen", "anmerkungen",
        "weblinks", "siehe auch",
    ),
}

# ----------------------------------------------------------------------
# 2.  MAIN PUBLIC API
# ----------------------------------------------------------------------

def get_article_text(title: str,
                     lang: str = "en",
                     wait_range: Tuple[float, float] = DEFAULT_SLEEP,
                     min_chars: int = 1000,
                     max_chars: int = 100_000
                     ) -> str:
    """
    Return the main text of a Wikipedia article (plain text, no refs/see-also).

    Raises:
        ValueError  – page does not exist
        RuntimeError – network / API errors
    """
    def _good(txt: str) -> bool:
        return bool(txt) and len(txt) >= min_chars

    tried: set[str] = set()         # ← keep titles we’ve actually fetched

    def _try(t: str) -> str | None:
        """Fetch once; remember the canonical form we tried."""
        key = t.casefold()           # simple normalisation
        if key in tried:
            return None              # already gave it a go
        
        txt = _api_extract(t, lang)
        if _good(txt):
            tried.add(key)
            return txt[:max_chars]
        
        return None


    if wait_range:                 # be polite – delay *before* the request
        time.sleep(random.uniform(*wait_range))

    # 1) original title
    text = _try(title)
    if text: return text

    # 2) try English → target-lang langlinks
    if lang != "en":
        for alt in _translate_titles(title, "en", lang):
            text = _try(alt)
            if text: return text

    # 3) best-match search in the target language
    alt = _search_best_match(title, lang)
    if alt and alt.lower() != title.lower():
        text = _try(alt)
        if text: return text

     # 4) HTML scrape
    text = _html_extract(title, lang)
    if _good(text):
        return text[:max_chars]

     
    # nothing met the threshold
    print(f"Skipping ‘{title}’ ({lang}): has < {min_chars} chars or is missing")
    return ''
    # raise ValueError(f"‘{title}’ ({lang}) has < {min_chars} chars or is missing")



def batch_fetch(articles: Iterable[Tuple[str, str]],
                wait_range: Tuple[float, float] = DEFAULT_SLEEP
                ) -> Dict[Tuple[str, str], str]:
    """
    Fetch many articles safely.  `articles` is an iterable of (lang, title).
    Returns a dict mapping (lang, title) ➜ article_text (or '' if failed).
    """
    out = {}
    for lang, title in articles:
        try:
            out[(lang, title)] = get_article_text(title, lang, wait_range)
        except Exception as exc:
            print(f"[warn] {title} ({lang}): {exc}")
            out[(lang, title)] = ""
    return out

# ----------------------------------------------------------------------
# 3.  HELPERS
# ----------------------------------------------------------------------

API_ENDPOINT = "https://{lang}.wikipedia.org/w/api.php"
HEADERS      = {"User-Agent": USER_AGENT}

CUT_REGEX_CACHE: Dict[str, re.Pattern] = {}

def _build_cut_regex(lang: str) -> re.Pattern:
    """compile and memoise CUT regex for the language."""
    if lang in CUT_REGEX_CACHE:
        return CUT_REGEX_CACHE[lang]

    stops = "|".join(re.escape(h) for h in STOP_HEADINGS[lang])
    pat = (
        r"\n==\s*(?:" + stops + r")\s*==.*"  # match from heading to EOF
    )
    CUT_REGEX_CACHE[lang] = re.compile(pat, re.IGNORECASE | re.DOTALL)
    return CUT_REGEX_CACHE[lang]


def _api_extract(title: str, lang: str) -> str:
    """Primary path – MediaWiki Extracts API (plain text)."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "exsectionformat": "plain",   # headings like '== Heading =='
        "redirects": 1,
        "titles": title,
    }
    try:
        r = requests.get(API_ENDPOINT.format(lang=lang),
                         params=params, headers=HEADERS,
                         verify=False,      #certifi.where(),
                         timeout=TIMEOUT)
        r.raise_for_status()
        pages = r.json()["query"]["pages"]
        page = next(iter(pages.values()))
        text = page.get("extract", "")
    except Exception as exc:
        raise RuntimeError(f"API error: {exc}") from exc

    # strip trailing unwanted sections
    regex = _build_cut_regex(lang)
    text = regex.sub("", text)
    return text.strip()


def _html_extract(title: str, lang: str) -> str:
    """Fallback – download the HTML and strip tags."""
    url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
    try:
        r = requests.get(url, headers=HEADERS,
                         verify=False,      #certifi.where(),
                         timeout=TIMEOUT)
        r.raise_for_status()

    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            return ""          # treat as “article missing”
        raise RuntimeError(f"HTML fetch error: {exc}") from exc


    soup = BeautifulSoup(r.content, "html.parser")
    content = soup.find("div", class_="mw-parser-output")
    if not content:
        return ""

    paragraphs = []
    for elem in content.children:
        if elem.name == "h2":                       # reached a top-level heading
            span = elem.find("span", class_="mw-headline")
            if span and span.text.strip().lower() in STOP_HEADINGS[lang]:
                break
        if elem.name == "p":
            paragraphs.append(elem.get_text(" ", strip=True))

    return "\n\n".join(paragraphs).strip()

# ----------------------------------------------------------------------
#  NEW  • TITLE TRANSLATION VIA LANGLINKS
# ----------------------------------------------------------------------

def _translate_titles(title: str,
                      source_lang: str,
                      target_lang: str) -> list[str]:
    """
    Return *all* titles in `target_lang` that correspond to `title`
    in `source_lang`, ordered as returned by the API.
    """
    if source_lang == target_lang:
        return [title]

    params = {
        "action": "query",
        "format": "json",
        "prop": "langlinks",
        "titles": title,
        "redirects": 1,
        "lllang": target_lang,
        "lllimit": "max",          # <- get them all
    }
    r = requests.get(API_ENDPOINT.format(lang=source_lang),
                     params=params, headers=HEADERS,
                     verify=False,      #certifi.where(),
                     timeout=TIMEOUT)
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    links = next(iter(pages.values())).get("langlinks", [])
    return [link["*"] for link in links]          # just the titles



def _search_best_match(query: str, lang: str, num_hits=1) -> str | None:
        params = {
            "action": "query", "format": "json",
            "list": "search", "srsearch": query, "srlimit": num_hits,
        }
        r = requests.get(API_ENDPOINT.format(lang=lang),
                        params=params, headers=HEADERS,
                        verify=False,      #certifi.where(),
                        timeout=TIMEOUT)
        r.raise_for_status()
        hits = r.json()["query"]["search"]
        return hits[0]["title"] if hits else None





# ----------------------------------------------------------------------
# 4.  LITTLE SELF-TEST (run “python wikiscrape.py”)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    for lang, title in [("en", "Python (programming language)"),
                        ("de", "Albert Einstein")]:
        print("=" * 60)
        print(f"{title} ({lang})\n")
        print(get_article_text(title, lang)[:800], "…\n")





# # FINAL
# # import ssl
# # ssl._create_default_https_context = ssl._create_unverified_context

# # import os
# # os.environ['PYTHONHTTPSVERIFY'] = '0'

# import wikipediaapi
# from typing import Optional, Dict, List
# import re


# class WikipediaExtractor:
#     def __init__(self, language: str = 'en', user_agent: str = 'WikipediaExtractor/1.0'):
#         """Initialize Wikipedia API extractor."""

#         self.wiki = wikipediaapi.Wikipedia(
#             language=language,
#             extract_format=wikipediaapi.ExtractFormat.WIKI,
#             user_agent=user_agent,
#         )

#         self.exclude_sections = {
#             'References', 'External links', 'Further reading', 'See also',
#             'Notes', 'Bibliography', 'Sources', 'Citations', 'Literature',
#             'Footnotes', 'Works cited', 'Additional references'
#         }

#     def _clean_text(self, text: str) -> str:
#         """Remove extra whitespace and clean up text."""
#         text = re.sub(r'\s+', ' ', text)
#         return text.strip()

#     def _extract_section_content(self, section) -> List[str]:
#         """Recursively extract content from a section and its subsections."""
#         content = []

#         # Skip excluded sections
#         if section.title in self.exclude_sections:
#             return content

#         # Add the section's own text if it exists
#         if section.text.strip():
#             content.append(section.text)

#         # Recursively process subsections
#         for subsection in section.sections:
#             content.extend(self._extract_section_content(subsection))

#         return content

#     def _get_main_content(self, page) -> str:
#         """Extract content from the page including all nested sections."""
#         # Start with the summary
#         main_content = [page.summary]

#         # Process each top-level section
#         for section in page.sections:
#             content = self._extract_section_content(section)
#             main_content.extend(content)

#         return '\n\n'.join(main_content)

#     def extract_article(self, title: str, language: Optional[str] = None) -> Dict:
#         """Extract article content using the Wikipedia API."""
#         # Rest of the implementation remains the same
#         if title.startswith('http'):
#             title = title.split('/wiki/')[-1].replace('_', ' ')

#         if language:
#             self.wiki = wikipediaapi.Wikipedia(
#                 language=language,
#                 extract_format=wikipediaapi.ExtractFormat.WIKI,
#                 user_agent=self.wiki.user_agent
#             )

#         page = self.wiki.page(title)

#         if not page.exists():
#             raise ValueError(f"Article '{title}' does not exist in {self.wiki.language} Wikipedia")

#         main_content = self._get_main_content(page)
#         categories = list(page.categories.keys())
#         is_disambiguation = (
#             'disambiguation' in page.title.lower() or
#             any('disambiguation' in cat.lower() for cat in categories)
#         )

#         return {
#             'title': page.title,
#             'text': self._clean_text(main_content),
#             'language': self.wiki.language,
#             'url': page.fullurl,
#             'length': len(main_content),
#             'is_disambiguation': is_disambiguation
#         }

# # Example usage function
# def get_wikipedia_content(title_or_url: str, language: str = 'en') -> Optional[Dict]:
#     try:
#         extractor = WikipediaExtractor(language=language)
#         return extractor.extract_article(title_or_url)
#     except Exception as e:
#         print(f"Error: {str(e)}")
#         return None