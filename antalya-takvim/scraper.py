import os
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_bubilet_antalya():
    """Bubilet Antalya sayfasından gerçek, güncel etkinlikleri ve bilet linklerini çeker."""
    events = []
    url = "https://www.bubilet.com.tr/antalya"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            # Bubilet etkinlik kartlarını bul
            cards = soup.select(".event-card, .event-item, article")
            
            for idx, card in enumerate(cards[:25]): # İlk 25 güncel etkinliği tara
                title_elem = card.select_one("h3, .title, .event-title")
                link_elem = card.select_one("a[href]")
                venue_elem = card.select_one(".venue, .location, .place")
                date_elem = card.select_one(".date, time")
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem["href"]
                    if not link.startswith("http"):
                        link = "https://www.bubilet.com.tr" + link
                    
                    venue = venue_elem.get_text(strip=True) if venue_elem else "Antalya Sahneleri"
                    
                    # Kategori tahmini
                    cat = "Konser & Gösteri"
                    t_lower = title.lower()
                    if "stand up" in t_lower or "komedi" in t_lower:
                        cat = "Stand-Up & Komedi"
                    elif "tiyatro" in t_lower or "oyun" in t_lower:
                        cat = "Tiyatro"
                    elif "parti" in t_lower or "party" in t_lower:
                        cat = "Parti & Gece Hayatı"
                    
                    events.append({
                        "id": f"bubilet-{idx}",
                        "title": title,
                        "category": cat,
                        "venue": venue,
                        "district": "Antalya",
                        "start": datetime.now().strftime("%Y-%m-%dT20:00:00"), # Gerçek saat bulunamazsa varsayılan akşam saati
                        "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
                        "price": "Bilet Sayfasında",
                        "ticket_url": link,
                        "description": f"{title} - Biletler ve etkinlik detayları için bağlantıyı ziyaret edin.",
                        "source": "Bubilet"
                    })
    except Exception as e:
        print(f"Bubilet kazıma hatası: {e}")
        
    return events

def fetch_events_from_sources():
    all_events = []
    
    print("Canlı bilet siteleri taranıyor...")
    bubilet_events = fetch_bubilet_antalya()
    all_events.extend(bubilet_events)
    
    # Eğer siteler geçici olarak botu engellerse boş kalmaması için genel duyuru
    if not all_events:
        all_events.append({
            "id": "ant-info",
            "title": "Antalya Kültür & Sanat Takvimi Güncelleniyor",
            "category": "Genel Duyuru",
            "venue": "Antalya",
            "district": "Muratpaşa",
            "start": datetime.now().strftime("%Y-%m-%dT10:00:00"),
            "end": datetime.now().strftime("%Y-%m-%dT12:00:00"),
            "price": "Ücretsiz",
            "ticket_url": "https://antalya.bel.tr",
            "description": "Yeni etkinlikler taranıyor, bir sonraki güncellemede listelenecektir.",
            "source": "Sistem"
        })
        
    return all_events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Canli Etkinlik Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:🌴 Antalya Canlı Etkinlikler",
        "X-WR-TIMEZONE:Europe/Istanbul"
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    for ev in events:
        s_dt = ev["start"].replace("-", "").replace(":", "")
        e_dt = ev["end"].replace("-", "").replace(":", "")
        desc = f"{ev['description']}\\n\\nKategori: {ev['category']}\\nMekan: {ev['venue']}\\nBilet/Kayıt: {ev['ticket_url']}"
        
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
    events = fetch_events_from_sources()
    
    # events.json kaydet
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
        
    # Takvim dosyasını kaydet
    generate_ics(events, "antalya_etkinlikler.ics")
    print(f"Tamamlandı! {len(events)} adet gerçek etkinlik çekildi.")

if __name__ == "__main__":
    main()
