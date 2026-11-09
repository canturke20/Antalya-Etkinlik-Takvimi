import os
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def fetch_bubilet():
    events = []
    print("Bubilet güvenlik duvarı aşılıyor (Proxy ile)...")
    
    # GitHub'ın Amerika IP'sini gizlemek ve bot engelini aşmak için proxy servisi kullanıyoruz
    url = "https://api.allorigins.win/get?url=https://www.bubilet.com.tr/antalya"
    
    try:
        response = requests.get(url, timeout=20)
        data = response.json()
        html_content = data.get("contents", "")
        
        soup = BeautifulSoup(html_content, "html.parser")
        links = soup.find_all("a", href=True)
        seen_titles = set()
        
        for tag in links:
            href = tag['href']
            
            # Etkinlik linklerini ayırt etme (Gereksiz menü ve iletişim sayfalarını çöpe at)
            href_lower = href.lower()
            is_event_link = ("/antalya/" in href_lower or "/etkinlik/" in href_lower)
            is_junk = any(x in href_lower for x in ["hakkimizda", "iletisim", "kvkk", "giris", "sepet", "uye-ol", "kategori", "mekan", "sss"])
            
            # Sadece /antalya ana sayfa linkiyse atla
            if len(href.split("/")) < 4:
                is_event_link = False
            
            if is_event_link and not is_junk:
                full_url = href if href.startswith("http") else "https://www.bubilet.com.tr" + href
                
                # 1. Aşama: Başlığı ve Fırsat Yazısını Kazı
                title = ""
                if tag.get("title"):
                    title = tag.get("title")
                
                if not title:
                    header = tag.find(["h2", "h3", "h4", "h5", "strong"])
                    if header:
                        title = header.get_text(strip=True)
                
                if not title:
                    img = tag.find("img")
                    if img and img.get("alt"):
                        title = img.get("alt")
                
                if not title:
                    title = tag.get_text(strip=True)
                    
                # Yazıyı temizle ve kısa başlıklı buton metinlerini atla
                title = re.sub(r'\s+', ' ', title).strip()
                if len(title) < 6 or "Bilet Al" in title or "İncele" in title:
                    continue
                    
                # Aynı fırsatı listeye 2 kez eklememek için filtrele
                clean_t = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
                if clean_t in seen_titles:
                    continue
                seen_titles.add(clean_t)
                
                # 2. Aşama: Yazıların İçindeki Kelimelere Göre Kategoriye Ayır (Senin İstediğin Şablon)
                category = "Konser & Sahne"
                tl = title.lower()
                if any(x in tl for x in ["stand up", "komedi", "baturay", "demirkol", "gösteri", "talk"]):
                    category = "Stand-Up & Komedi"
                elif any(x in tl for x in ["tiyatro", "oyun", "meyhanesi", "kumpanya", "müzikali"]):
                    category = "Tiyatro"
                elif any(x in tl for x in ["parti", "festival", "party", "90'lar", "dj"]):
                    category = "Parti & Festival"
                elif any(x in tl for x in ["atölye", "workshop", "eğitim"]):
                    category = "Atölye & Eğitim"
                    
                events.append({
                    "id": f"bubilet-{len(events)}",
                    "title": title,
                    "category": category,
                    "venue": "Antalya (Detaylar Linkte)",
                    "district": "Antalya",
                    "start": datetime.now().strftime("%Y-%m-%dT20:00:00"),
                    "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
                    "price": "Fırsatı İncele",
                    "ticket_url": full_url,
                    "description": f"Fırsat: {title}. Sayfaya gidip detayları okumak ve bilet almak için yandaki butona tıkla.",
                    "source": "Bubilet"
                })
                
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        
    return events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Etkinlik Firsatlari//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:🌴 Bubilet Fırsatları",
        "X-WR-TIMEZONE:Europe/Istanbul"
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for ev in events:
        s_dt = ev["start"].replace("-", "").replace(":", "")
        e_dt = ev["end"].replace("-", "").replace(":", "")
        desc = f"{ev['description']}\\n\\nSayfaya Git: {ev['ticket_url']}"
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
    events = fetch_bubilet()
    print(f"Başarılı: Toplam {len(events)} gerçek etkinlik yakalandı.")
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    generate_ics(events)

if __name__ == "__main__":
    main()
