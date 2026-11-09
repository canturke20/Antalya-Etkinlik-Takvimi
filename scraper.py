import os
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9"
}

def fetch_biletix_antalya():
    """Biletix Antalya RSS akışından doğrudan gerçek ve bilet satışı aktif etkinlikleri çeker."""
    events = []
    url = "https://www.biletix.com/rss/all/TURKIYE/tr?city=Antalya"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for idx, item in enumerate(root.findall(".//item")):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                
                if not title or not link:
                    continue

                # Kategori ayrıştırma
                cat = "Konser & Sahne"
                t_lower = (title + " " + desc).lower()
                if "stand-up" in t_lower or "stand up" in t_lower or "komedi" in t_lower:
                    cat = "Stand-Up & Komedi"
                elif "tiyatro" in t_lower or "oyun" in t_lower:
                    cat = "Tiyatro"
                elif "parti" in t_lower or "festival" in t_lower or "dance" in t_lower:
                    cat = "Parti & Festival"
                elif "spor" in t_lower or "maç" in t_lower:
                    cat = "Spor"

                # Tarih ayrıştırma (varsayılan bugün/akşam)
                start_iso = datetime.now().strftime("%Y-%m-%dT20:00:00")
                if pub_date:
                    try:
                        # RFC 822 format örneği: 'Wed, 02 Oct 2026 18:00:00 GMT'
                        clean_dt = pub_date[:25].strip()
                        dt = datetime.strptime(clean_dt, "%a, %d %b %Y %H:%M:%S")
                        start_iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        pass

                events.append({
                    "id": f"btx-{idx}",
                    "title": title.strip(),
                    "category": cat,
                    "venue": "Antalya",
                    "district": "Muratpaşa / Konyaaltı",
                    "start": start_iso,
                    "end": start_iso,
                    "price": "Biletix Sayfasında",
                    "ticket_url": link.strip(),
                    "description": re.sub(r'<[^>]+>', '', desc).strip()[:200] if desc else f"{title} - Biletix Antalya etkinliği.",
                    "source": "Biletix"
                })
    except Exception as e:
        print(f"Biletix RSS hatası: {e}")
    return events

def fetch_bubilet_antalya():
    """Bubilet Antalya sayfasından gerçek etkinlikleri kazır."""
    events = []
    url = "https://www.bubilet.com.tr/antalya"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select(".event-card, .event-item, article")
            for idx, card in enumerate(cards):
                title_el = card.select_one("h3, .title, .event-title")
                link_el = card.select_one("a[href]")
                venue_el = card.select_one(".venue, .location, .place")
                
                if title_el and link_el:
                    title = title_el.get_text(strip=True)
                    link = link_el["href"]
                    if not link.startswith("http"):
                        link = "https://www.bubilet.com.tr" + link
                    
                    venue = venue_el.get_text(strip=True) if venue_el else "Antalya"
                    
                    cat = "Konser & Sahne"
                    t_lower = title.lower()
                    if "stand up" in t_lower or "komedi" in t_lower:
                        cat = "Stand-Up & Komedi"
                    elif "tiyatro" in t_lower:
                        cat = "Tiyatro"
                    elif "parti" in t_lower:
                        cat = "Parti & Gece Hayatı"

                    events.append({
                        "id": f"bub-{idx}",
                        "title": title,
                        "category": cat,
                        "venue": venue,
                        "district": "Antalya",
                        "start": datetime.now().strftime("%Y-%m-%dT20:30:00"),
                        "end": datetime.now().strftime("%Y-%m-%dT23:00:00"),
                        "price": "Bubilet Sayfasında",
                        "ticket_url": link,
                        "description": f"{title} detayları ve biletleri için tıklayın.",
                        "source": "Bubilet"
                    })
    except Exception as e:
        print(f"Bubilet hatası: {e}")
    return events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Gercek Etkinlik Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:🌴 Antalya Etkinlikleri",
        "X-WR-TIMEZONE:Europe/Istanbul"
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for ev in events:
        s_dt = ev["start"].replace("-", "").replace(":", "")
        e_dt = ev["end"].replace("-", "").replace(":", "")
        desc = f"{ev['description']}\\n\\nBilet: {ev['ticket_url']}"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{ev['id']}@antalya-canli",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{s_dt}",
            f"DTEND:{e_dt}",
            f"SUMMARY:[{ev['category']}] {ev['title']}",
            f"LOCATION:{ev['venue']}, Antalya",
            f"DESCRIPTION:{desc}",
            f"URL:{ev['ticket_url']}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))

def main():
    all_events = []
    
    # 1. Biletix Gerçek Verileri
    bx_events = fetch_biletix_antalya()
    all_events.extend(bx_events)
    
    # 2. Bubilet Gerçek Verileri
    bu_events = fetch_bubilet_antalya()
    all_events.extend(bu_events)
    
    # Mükerrer etkinlikleri temizle
    unique_events = []
    seen_titles = set()
    for ev in all_events:
        clean_name = re.sub(r'[^a-zA-Z0-9çğıöşüÇĞİÖŞÜ]', '', ev['title'].lower())
        if clean_name not in seen_titles:
            seen_titles.add(clean_name)
            unique_events.append(ev)

    print(f"Toplam {len(unique_events)} adet gerçek etkinlik bulundu.")

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    generate_ics(unique_events, "antalya_etkinlikler.ics")

if __name__ == "__main__":
    main()
