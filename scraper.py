import os
import json
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# Bot olarak algılanmamak için gerçek bir tarayıcı kimliği kullanıyoruz
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def fetch_bubilet():
    events = []
    print("Bubilet Antalya sayfası taranıyor...")
    
    url = "https://www.bubilet.com.tr/antalya"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Sitedeki tüm potansiyel bilet/etkinlik linklerini bul (Sonu 'bileti' veya 'konseri' ile bitenler vs.)
        # Bubilet'te etkinlik detay linkleri genellikle bu formattadır
        event_links = soup.find_all("a", href=True)
        
        seen_titles = set()
        
        for idx, link_tag in enumerate(event_links):
            href = link_tag['href']
            
            # Linkin bir etkinlik sayfası olup olmadığını kontrol et
            if "/antalya/" in href and href != "/antalya":
                
                # Etkinlik başlığını linkin içindeki metinden veya 'title' özelliğinden al
                title = link_tag.get_text(strip=True)
                if not title:
                    title = link_tag.get('title', '').strip()
                
                # Başlık çok kısaysa (örn. sadece "Bilet Al" yazıyorsa) atla
                if len(title) < 5:
                    continue
                    
                # Aynı etkinliği iki kere eklememek için kontrol
                clean_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
                if clean_title in seen_titles:
                    continue
                seen_titles.add(clean_title)

                # Tam URL'yi oluştur
                full_url = href if href.startswith("http") else "https://www.bubilet.com.tr" + href

                # YAZILARI TARAYARAK SINIFLANDIRMA (KATEGORİZASYON)
                title_lower = title.lower()
                category = "Konser & Sahne" # Varsayılan kategori
                
                if "stand up" in title_lower or "komedi" in title_lower or "baturay" in title_lower or "doğu demirkol" in title_lower:
                    category = "Stand-Up & Komedi"
                elif "tiyatro" in title_lower or "oyun" in title_lower or "meyhanesi" in title_lower:
                    category = "Tiyatro"
                elif "parti" in title_lower or "festival" in title_lower or "90'lar" in title_lower:
                    category = "Parti & Festival"
                elif "atölye" in title_lower or "workshop" in title_lower:
                    category = "Atölye & Eğitim"

                # Mekan tespiti (Bubilet'te başlığın içinde veya linkin yanında geçebilir, şimdilik Antalya Sahneleri)
                venue = "Antalya Sahneleri (Detaylar linkte)"
                if "Açıkhava" in title:
                    venue = "Antalya Açıkhava"
                elif "Türkan Şoray" in title:
                    venue = "Türkan Şoray Kültür Merkezi"
                elif "AKM" in title:
                    venue = "Antalya AKM"

                # Örnek Tarih (Gerçek tarih sayfa içine girildiğinde yazar, listelemede genel tarih atıyoruz)
                start_date = datetime.now().strftime("%Y-%m-%dT20:00:00")
                end_date = datetime.now().strftime("%Y-%m-%dT22:30:00")

                events.append({
                    "id": f"bubilet-{idx}",
                    "title": title,
                    "category": category,
                    "venue": venue,
                    "district": "Antalya",
                    "start": start_date,
                    "end": end_date,
                    "price": "Bilet Fiyatlarını Gör",
                    "ticket_url": full_url,
                    "description": f"{title} etkinliği hakkında daha fazla bilgi, saatler ve bilet satın alma ekranı için aşağıdaki butona tıklayın.",
                    "source": "Bubilet"
                })
                
    except Exception as e:
        print(f"Bubilet kazıma sırasında hata: {e}")
        
    return events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    # Apple Takvim için ICS dosyası oluşturma fonksiyonu
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
        desc = f"{ev['description']}\\n\\nBilet Linki: {ev['ticket_url']}"
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
    # Sadece Bubilet verilerini çekiyoruz
    all_events = fetch_bubilet()
    
    print(f"İşlem Tamamlandı: Toplam {len(all_events)} adet etkinlik Bubilet'ten başarıyla çekildi.")

    # 1. HTML panelin için JSON veritabanını kaydet
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # 2. Telefonun için Apple Takvim dosyasını kaydet
    generate_ics(all_events)

if __name__ == "__main__":
    main()
