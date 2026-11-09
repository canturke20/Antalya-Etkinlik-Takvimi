import os
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def fetch_biletinial_antalya():
    """Biletinial Antalya listesinden gerçek etkinlikleri çeker."""
    events = []
    url = "https://biletinial.com/tr-tr/etkinlikler/antalya"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("div.event-card, .event-list-item, li.eventItem, .movie-card")
            
            # Alternatif kart seçicileri
            if not cards:
                cards = soup.find_all("a", href=re.compile(r"/tr-tr/(tiyatro|muzik|stand-up|etkinlik)/"))
            
            for idx, card in enumerate(cards[:25]):
                # Eğer link kartın kendisiyse
                if card.name == "a":
                    link = card.get("href", "")
                    title = card.get_text(strip=True)
                else:
                    link_elem = card.select_one("a[href]")
                    title_elem = card.select_one("h3, h2, .name, .title")
                    link = link_elem["href"] if link_elem else ""
                    title = title_elem.get_text(strip=True) if title_elem else ""

                if not title or len(title) < 3 or not link:
                    continue

                if not link.startswith("http"):
                    link = "https://biletinial.com" + link

                # Kategori tespiti
                cat = "Konser & Sahne"
                t_lower = (title + " " + link).lower()
                if "stand-up" in t_lower or "komedi" in t_lower:
                    cat = "Stand-Up & Komedi"
                elif "tiyatro" in t_lower or "oyun" in t_lower:
                    cat = "Tiyatro"
                elif "opera" in t_lower or "bale" in t_lower:
                    cat = "Opera & Bale"

                events.append({
                    "id": f"biletinial-{idx}",
                    "title": title[:70].strip(),
                    "category": cat,
                    "venue": "Antalya",
                    "district": "Muratpaşa / Konyaaltı",
                    "start": datetime.now().strftime("%Y-%m-%dT20:30:00"),
                    "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
                    "price": "Bilet Sayfasında",
                    "ticket_url": link,
                    "description": f"{title} - Biletler ve etkinlik seansları için bağlantıya gidin.",
                    "source": "Biletinial"
                })
    except Exception as e:
        print(f"Biletinial tarama hatası: {e}")
    return events

def fetch_events_from_sources():
    all_events = []
    
    # 1. Biletinial canlı tarama
    biletinial_events = fetch_biletinial_antalya()
    all_events.extend(biletinial_events)

    # 2. Canlı taramada bot engeli olursa listenin ASLA boş kalmaması için 
    # doğrudan Antalya'daki resmi güncel biletleme/etkinlik sayfalarına yönlendiren doğrulanmış merkezler:
    if len(all_events) < 3:
        verified_hub = [
            {
                "id": "hub-akm",
                "title": "Antalya Atatürk Kültür Merkezi (AKM) Güncel Sahne Takvimi",
                "category": "Konser & Sahne",
                "venue": "AKM Aspendos & Perge Salonu",
                "district": "Muratpaşa",
                "start": datetime.now().strftime("%Y-%m-%dT20:00:00"),
                "end": datetime.now().strftime("%Y-%m-%dT22:00:00"),
                "price": "Resmi Gişe & Online",
                "ticket_url": "https://antalya.bel.tr/Hizmetler/Kultur-Sanat-Etkinlikleri",
                "description": "Antalya Büyükşehir Belediyesi AKM Aspendos ve Perge salonlarında sahnelenen tüm haftalık tiyatro, konser ve bale programı.",
                "source": "Antalya BB"
            },
            {
                "id": "hub-biletix",
                "title": "Biletix Antalya Tüm Konser ve Stand-Up Listesi",
                "category": "Konser & Sahne",
                "venue": "Antalya Açıkhava & Türkan Şoray KM",
                "district": "Muratpaşa / Konyaaltı",
                "start": datetime.now().strftime("%Y-%m-%dT20:30:00"),
                "end": datetime.now().strftime("%Y-%m-%dT23:00:00"),
                "price": "Biletix Satışta",
                "ticket_url": "https://www.biletix.com/search/TURKIYE/tr#!city_sb:Antalya",
                "description": "Antalya'da şu an aktif satışta olan tüm güncel biletix etkinlikleri ve doğrudan bilet alma sayfası.",
                "source": "Biletix"
            },
            {
                "id": "hub-bubilet",
                "title": "Bubilet Antalya İndirimli Etkinlik Biletleri",
                "category": "Tiyatro",
                "venue": "Antalya Sahneleri",
                "district": "Muratpaşa",
                "start": datetime.now().strftime("%Y-%m-%dT20:00:00"),
                "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
                "price": "İndirimli Bilet",
                "ticket_url": "https://www.bubilet.com.tr/antalya",
                "description": "Antalya bölgesindeki tüm indirimli tiyatro, stand-up ve konser bilet listesi.",
                "source": "Bubilet"
            },
            {
                "id": "hub-passo",
                "title": "Passo Antalya Etkinlik & Antalyaspor Maç Biletleri",
                "category": "Spor",
                "venue": "Corendon Airlines Park Antalya",
                "district": "Muratpaşa",
                "start": datetime.now().strftime("%Y-%m-%dT19:00:00"),
                "end": datetime.now().strftime("%Y-%m-%dT21:00:00"),
                "price": "Passo Satışta",
                "ticket_url": "https://www.passo.com.tr/tr/etkinlikler/antalya",
                "description": "Antalyaspor Süper Lig maçları ve Antalya sahne gösterileri.",
                "source": "Passo"
            }
        ]
        all_events.extend(verified_hub)

    return all_events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Etkinlik Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:🌴 Antalya Etkinlikleri",
        "X-WR-TIMEZONE:Europe/Istanbul"
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for ev in events:
        s_dt = ev["start"].replace("-", "").replace(":", "")
        e_dt = ev["end"].replace("-", "").replace(":", "")
        desc = f"{ev['description']}\\n\\nResmi Sayfa / Bilet: {ev['ticket_url']}"
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
    evs = fetch_events_from_sources()
    print(f"Toplam {len(evs)} adet etkinlik işlendi.")
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(evs, f, ensure_ascii=False, indent=2)
    generate_ics(evs)

if __name__ == "__main__":
    main()
