# tradingview_scraper/auth.py
import os, json, base64, re, requests
from typing import Optional, Dict
from dotenv import load_dotenv
load_dotenv()

class TradingViewAuth:
    def __init__(self):
        self.cookie = os.getenv("TRADINGVIEW_COOKIE")
        self.url   = os.getenv("TRADINGVIEW_CHART_URL")
        self.ua    = os.getenv("TRADINGVIEW_USER_AGENT",
                                "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0")
        self._token: Optional[str] = None

    def get_token(self) -> str:
        if self._token and not self._is_expired(self._token):
            return self._token
        if not self.cookie:
            raise ValueError("TRADINGVIEW_COOKIE not set")
        self._token = self._extract()
        return self._token

    def refresh(self) -> str:
        self._token = None
        return self.get_token()

    def _extract(self) -> str:
        hdr = {
            "Cookie": self.cookie,
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Priority": "u=0, i",
            "Te": "trailers"
        }
        r = requests.get(self.url, headers=hdr, timeout=30)
        r.raise_for_status()
        for t in re.findall(r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+', r.text):
            if self._verify_jwt(t):
                return t
        raise ValueError("No valid JWT found with provided cookies")

    @staticmethod
    def _verify_jwt(token: str) -> bool:
        try:
            h, p, _ = token.split('.')
            h += '=' * (-len(h) % 4)
            p += '=' * (-len(p) % 4)
            header = json.loads(base64.urlsafe_b64decode(h))
            payload = json.loads(base64.urlsafe_b64decode(p))
            return 'alg' in header and 'typ' in header
        except Exception:
            return False

    @staticmethod
    def _is_expired(token: str) -> bool:
        try:
            payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
            exp = payload.get('exp')
            return exp is None or exp < int(__import__('time').time())
        except Exception:
            return True