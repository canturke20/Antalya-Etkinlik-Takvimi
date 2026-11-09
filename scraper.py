"""Antalya etkinliklerini Bubilet ve Biletinial sayfalarından toplar.

İki site de listeyi sunucu HTML'i olarak basıyor. Her etkinliğin kendi
sayfasındaki schema.org Event kaydı tarih, mekan ve fiyatı veriyor.
Sıfır etkinlik çıkarsa mevcut events.json ve ICS dosyasına dokunulmaz.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

IST = ZoneInfo("Europe/Istanbul")
MIN_EVENTS = 8
DETAIL_WORKERS = 6
ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(ROOT, "events.json")
ICS_PATH = os.path.join(ROOT, "antalya_etkinlikler.ics")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

BUBILET_TAGS = {
    "stand-up": "Stand-Up",
    "tiyatro": "Tiyatro",
    "festival": "Festival",
    "cocuk-aktiviteleri": "Çocuk",
    "elektronik-muzik": "Parti & Festival",
    "eglence": "Eğlence",
    "konser": "Konser",
}
TAG_PRIORITY = list(BUBILET_TAGS)

BILETINIAL_LISTS = [
    ("https://biletinial.com/tr-tr/tiyatro/antalya", "Tiyatro"),
    ("https://biletinial.com/tr-tr/muzik/antalya", "Konser"),
    ("https://biletinial.com/tr-tr/opera-bale/antalya", "Opera & Bale"),
    ("https://biletinial.com/tr-tr/etkinlik/antalya", "Etkinlik"),
]

DISTRICTS = [
    "Muratpaşa",
    "Konyaaltı",
    "Döşemealtı",
    "Kepez",
    "Alanya",
    "Manavgat",
    "Kaleiçi",
    "Aksu",
    "Serik",
    "Kemer",
    "Lara",
]


class FetchError(RuntimeError):
    pass


def looks_blocked(html: str) -> bool:
    head = html[:4000].lower()
    return any(
        marker in head
        for marker in (
            "just a moment",
            "cf-browser-verification",
            "attention required",
            "/cdn-cgi/challenge-platform",
            "cf-mitigated",
        )
    )


class HtmlClient:
    def __init__(self) -> None:
        self._local = threading.local()
        self._browser = None
        self._playwright = None
        self._page = None
        self._browser_lock = threading.Lock()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(HEADERS)
            self._local.session = session
        return session

    def get(self, url: str, required: bool = False) -> str | None:
        last = "yanıt yok"
        for attempt in range(3):
            try:
                response = self._session().get(url, timeout=30)
                if response.status_code == 200 and not looks_blocked(response.text):
                    return response.text
                last = f"HTTP {response.status_code}"
                if response.status_code in (403, 429, 503) or looks_blocked(response.text):
                    break
            except requests.RequestException as exc:
                last = str(exc)
            time.sleep(0.8 + attempt)
        print(f"  istek engellendi, tarayıcı deneniyor: {url} ({last})")
        html = self._browser_get(url)
        if html:
            return html
        if required:
            raise FetchError(f"sayfa alınamadı: {url} ({last})")
        print(f"  atlandı: {url} ({last})")
        return None

    def _browser_get(self, url: str) -> str | None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  Playwright yüklü değil, tarayıcı yedeği kullanılamadı.")
            return None
        with self._browser_lock:
            try:
                if self._page is None:
                    self._playwright = sync_playwright().start()
                    self._browser = self._playwright.chromium.launch(headless=True)
                    context = self._browser.new_context(
                        user_agent=HEADERS["User-Agent"],
                        locale="tr-TR",
                    )
                    self._page = context.new_page()
                self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    self._page.wait_for_selector(
                        "a[href*='etkinlik'], script[type='application/ld+json']",
                        timeout=12000,
                    )
                except Exception:
                    pass
                html = self._page.content()
            except Exception as exc:
                print(f"  tarayıcı hatası: {exc}")
                return None
        if looks_blocked(html):
            return None
        return html


def json_ld_blocks(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            found.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return found


def walk_types(payload, type_name: str) -> list[dict]:
    items = []

    def visit(node) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child)
            return
        if not isinstance(node, dict):
            return
        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if type_name in types:
            items.append(node)
        for key in ("@graph", "itemListElement"):
            if key in node:
                visit(node[key])

    visit(payload)
    return items


def parse_dt(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed


def clean_text(value: str, limit: int = 280) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def price_from_offers(offers) -> str:
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return ""
    low = offers.get("lowPrice", offers.get("price"))
    high = offers.get("highPrice")
    try:
        low_n = int(round(float(str(low).replace(",", "."))))
    except (TypeError, ValueError):
        return ""
    if high not in (None, "", low):
        try:
            high_n = int(round(float(str(high).replace(",", "."))))
        except (TypeError, ValueError):
            high_n = low_n
        if high_n != low_n:
            return f"{low_n}–{high_n} TL"
    return f"{low_n} TL"


def district_of(*parts: str) -> str:
    blob = " ".join(part for part in parts if part)
    lowered = blob.lower()
    for name in DISTRICTS:
        if name.lower() in lowered:
            return name
    return "Antalya"


def refine_category(title: str, category: str) -> str:
    folded = title.casefold()
    if any(word in folded for word in ("stand-up", "stand up", "standup")):
        return "Stand-Up"
    if any(word in folded for word in ("atölye", "atolye", "workshop")):
        return "Atölye"
    if any(word in folded for word in ("kariyer", "zirve", "kongre")):
        return "Kariyer"
    return category


def upcoming(start: datetime) -> bool:
    return start.astimezone(IST) >= datetime.now(IST) - timedelta(hours=6)


def event_record(
    *,
    source: str,
    slug: str,
    title: str,
    category: str,
    venue: str,
    start: datetime,
    end: datetime | None,
    price: str,
    ticket_url: str,
    description: str,
    image: str,
    address: str = "",
) -> dict:
    start_local = start.astimezone(IST)
    if end is None or end <= start:
        end = start + timedelta(hours=2)
    end_local = end.astimezone(IST)
    stamp = start_local.strftime("%Y%m%dT%H%M")
    return {
        "id": f"{source.lower()}-{slug}-{stamp}",
        "title": title,
        "category": refine_category(title, category),
        "venue": venue or "Antalya",
        "district": district_of(venue, address),
        "start": start_local.isoformat(timespec="minutes"),
        "end": end_local.isoformat(timespec="minutes"),
        "price": price or "Bilet sayfasında",
        "ticket_url": ticket_url,
        "description": description or title,
        "image": image or "",
        "source": source,
    }


def first_image(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("url") or ""
    if isinstance(value, str) and value.startswith("http"):
        return value
    return ""


def bubilet_category(blocks, slug_hint: str) -> str:
    found = set()
    for block in blocks:
        for crumb in walk_types(block, "BreadcrumbList"):
            elements = crumb.get("itemListElement") or []
            for element in elements:
                url = ""
                if isinstance(element, dict):
                    url = str(element.get("item") or "")
                for tag in BUBILET_TAGS:
                    if f"/etiket/{tag}" in url:
                        found.add(tag)
    for tag in TAG_PRIORITY:
        if tag in found:
            return BUBILET_TAGS[tag]
    return slug_hint or "Etkinlik"


def is_antalya(location: dict, venue_hint: str = "") -> bool:
    if not isinstance(location, dict):
        return False
    address = location.get("address") or {}
    if isinstance(address, str):
        address_text = address
    elif isinstance(address, dict):
        address_text = " ".join(
            str(address.get(key) or "")
            for key in ("addressLocality", "addressRegion", "streetAddress")
        )
    else:
        address_text = ""
    blob = f"{location.get('name') or ''} {address_text}".lower()
    if "antalya" in blob:
        return True
    hint = (venue_hint or "").strip().lower()
    name = str(location.get("name") or "").strip().lower()
    return bool(hint and name and (hint in name or name in hint))


def address_text(location: dict) -> str:
    address = location.get("address") if isinstance(location, dict) else None
    if isinstance(address, dict):
        return str(address.get("streetAddress") or "")
    if isinstance(address, str):
        return address
    return ""


def fetch_bubilet(client: HtmlClient) -> list[dict]:
    print("Bubilet listeleri okunuyor...")
    pages = [("https://www.bubilet.com.tr/antalya", "")]
    pages.extend(
        (f"https://www.bubilet.com.tr/antalya/etiket/{tag}", category)
        for tag, category in BUBILET_TAGS.items()
    )
    slugs: dict[str, str] = {}
    for url, category in pages:
        html = client.get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.select('a[href*="/antalya/etkinlik/"]'):
            href = (anchor.get("href") or "").split("?")[0]
            match = re.search(r"/antalya/etkinlik/([^/]+)/?$", href)
            if not match:
                continue
            slug = match.group(1)
            slugs.setdefault(slug, category)
    print(f"  {len(slugs)} Bubilet etkinlik sayfası bulundu.")
    if not slugs:
        return []

    def load(item: tuple[str, str]) -> list[dict]:
        slug, hinted = item
        url = f"https://www.bubilet.com.tr/antalya/etkinlik/{slug}"
        html = client.get(url)
        if not html:
            return []
        blocks = json_ld_blocks(html)
        category = bubilet_category(blocks, hinted)
        records = []
        for block in blocks:
            for raw in walk_types(block, "Event"):
                start = parse_dt(raw.get("startDate"))
                if start is None or not upcoming(start):
                    continue
                location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
                venue = str(location.get("name") or "Antalya")
                title = clean_text(str(raw.get("name") or slug), limit=160)
                records.append(
                    event_record(
                        source="Bubilet",
                        slug=slug.strip("-") or slug,
                        title=title,
                        category=category,
                        venue=venue,
                        start=start,
                        end=parse_dt(raw.get("endDate")),
                        price=price_from_offers(raw.get("offers")),
                        ticket_url=url,
                        description=clean_text(str(raw.get("description") or title)),
                        image=first_image(raw.get("image")),
                        address=address_text(location),
                    )
                )
        return records

    events = []
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        futures = [pool.submit(load, item) for item in slugs.items()]
        for future in as_completed(futures):
            try:
                events.extend(future.result())
            except Exception as exc:
                print(f"  Bubilet sayfa hatası: {exc}")
    print(f"  Bubilet: {len(events)} seans.")
    return events


def biletinial_links(client: HtmlClient) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for list_url, category in BILETINIAL_LISTS:
        html = client.get(list_url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("li.hpv2-event-card"):
            anchor = card.select_one("a[href]")
            if anchor is None:
                continue
            href = anchor.get("href") or ""
            match = re.search(r"/tr-tr/[a-z0-9\-]+/([a-z0-9\-]+)/?$", href)
            if not match or match.group(1) == "antalya":
                continue
            path = href if href.startswith("/") else "/" + href
            url = "https://biletinial.com" + path.split("?")[0]
            venue_node = card.select_one("address span:last-child")
            price_node = card.select_one(".hpv2-event-card__price strong")
            title = clean_text(anchor.get("title") or anchor.get_text(" ", strip=True), limit=160)
            found.setdefault(
                url,
                {
                    "title": title,
                    "category": category,
                    "venue": clean_text(venue_node.get_text(" ", strip=True) if venue_node else "", limit=120),
                    "price": clean_text(price_node.get_text(" ", strip=True) if price_node else "", limit=40).replace("₺", "").strip(),
                },
            )
    return found


def fetch_biletinial(client: HtmlClient) -> list[dict]:
    print("Biletinial listeleri okunuyor...")
    links = biletinial_links(client)
    print(f"  {len(links)} Biletinial etkinlik sayfası bulundu.")
    if not links:
        return []

    def load(item: tuple[str, dict]) -> list[dict]:
        url, hint = item
        html = client.get(url)
        if not html:
            return []
        slug = url.rstrip("/").split("/")[-1]
        records = []
        seen_starts = set()
        for block in json_ld_blocks(html):
            for raw in walk_types(block, "Event"):
                location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
                if not is_antalya(location, hint["venue"]):
                    continue
                start = parse_dt(raw.get("startDate"))
                if start is None or not upcoming(start):
                    continue
                key = start.astimezone(IST).strftime("%Y%m%dT%H%M")
                if key in seen_starts:
                    continue
                seen_starts.add(key)
                price = price_from_offers(raw.get("offers"))
                if not price and hint["price"]:
                    digits = re.sub(r"[^\d]", "", hint["price"])
                    price = f"{int(digits)} TL" if digits else ""
                venue = str(location.get("name") or hint["venue"] or "Antalya")
                title = clean_text(str(raw.get("name") or hint["title"]), limit=160)
                records.append(
                    event_record(
                        source="Biletinial",
                        slug=slug,
                        title=title,
                        category=hint["category"],
                        venue=venue,
                        start=start,
                        end=parse_dt(raw.get("endDate")),
                        price=price,
                        ticket_url=url,
                        description=clean_text(str(raw.get("description") or title)),
                        image=first_image(raw.get("image")),
                        address=address_text(location),
                    )
                )
        return records

    events = []
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        futures = [pool.submit(load, item) for item in links.items()]
        for future in as_completed(futures):
            try:
                events.extend(future.result())
            except Exception as exc:
                print(f"  Biletinial sayfa hatası: {exc}")
    print(f"  Biletinial: {len(events)} seans.")
    return events


def dedupe(events: list[dict]) -> list[dict]:
    unique = {}
    for event in events:
        unique.setdefault(event["id"], event)
    ordered = sorted(unique.values(), key=lambda event: (event["start"], event["title"]))
    return ordered


def ics_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def fold_ics_line(line: str) -> str:
    raw = line.encode("utf-8")
    parts = []
    first = True
    while raw:
        limit = 75 if first else 74
        if len(raw) <= limit:
            parts.append(raw.decode("utf-8"))
            break
        cut = limit
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        if cut <= 0:
            cut = limit
        parts.append(raw[:cut].decode("utf-8"))
        raw = raw[cut:]
        first = False
    return "\r\n ".join(parts)


def ics_stamp(value: str) -> str:
    parsed = datetime.fromisoformat(value).astimezone(IST)
    return parsed.strftime("%Y%m%dT%H%M%S")


def generate_ics(events: list[dict]) -> str:
    now_stamp = datetime.now(IST).strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Etkinlik Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Antalya Etkinlikleri",
        "X-WR-TIMEZONE:Europe/Istanbul",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Istanbul",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0300",
        "TZOFFSETTO:+0300",
        "TZNAME:+03",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]
    for event in events:
        description = (
            f"{event['description']}\\n\\n"
            f"Fiyat: {event['price']}\\n"
            f"Bilet: {event['ticket_url']}"
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{event['id']}@antalya-etkinlik",
                f"DTSTAMP;TZID=Europe/Istanbul:{now_stamp}",
                f"DTSTART;TZID=Europe/Istanbul:{ics_stamp(event['start'])}",
                f"DTEND;TZID=Europe/Istanbul:{ics_stamp(event['end'])}",
                f"SUMMARY:{ics_escape('[' + event['category'] + '] ' + event['title'])}",
                f"LOCATION:{ics_escape(event['venue'] + ', ' + event['district'])}",
                f"DESCRIPTION:{description}",
                f"URL:{event['ticket_url']}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ics_line(line) for line in lines) + "\r\n"


def write_outputs(events: list[dict], source_counts: dict[str, int]) -> None:
    payload = {
        "generated_at": datetime.now(IST).isoformat(timespec="minutes"),
        "sources": source_counts,
        "events": events,
    }
    json_tmp = JSON_PATH + ".tmp"
    ics_tmp = ICS_PATH + ".tmp"
    with open(json_tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with open(ics_tmp, "w", encoding="utf-8", newline="") as handle:
        handle.write(generate_ics(events))
    os.replace(json_tmp, JSON_PATH)
    os.replace(ics_tmp, ICS_PATH)


def main() -> int:
    client = HtmlClient()
    try:
        grouped = {
            "Bubilet": fetch_bubilet(client),
            "Biletinial": fetch_biletinial(client),
        }
    finally:
        client.close()

    events = dedupe([event for batch in grouped.values() for event in batch])
    counts = {name: len(batch) for name, batch in grouped.items()}
    print(f"Toplam benzersiz seans: {len(events)} ({counts})")
    if len(events) < MIN_EVENTS:
        print(
            "Yeterli etkinlik toplanamadı. Mevcut takvim dosyaları değiştirilmedi.",
            file=sys.stderr,
        )
        return 1
    write_outputs(events, counts)
    print(f"Yazıldı: {JSON_PATH}")
    print(f"Yazıldı: {ICS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
