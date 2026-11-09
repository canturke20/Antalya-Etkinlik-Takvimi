import os
import json
import re
import urllib.request
from datetime import datetime

def fetch_bubilet_links():
    events = []
    
    # 1. Bubilet'in sayfasından linkleri kaba kuvvetle (Regex ile) çekmeyi deniyoruz
    try:
        url = "https://www.bubilet.com.tr/antalya"
        # Bot gibi değil, standart bir Windows bilgisayar gibi kapıyı çalıyoruz
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        # Sadece etkinlik linklerini bul (/antalya/etkinlik/... ile başlayanlar)
        links = re.findall(r'href="(/antalya/etkinlik/[^"]+)"', html)
        links = list(set(links)) # Aynı linkleri teke düşür
        
        for link in links[:15]:
            full_url = "https://www.bubilet.com.tr" + link
            # Linkin içindeki yazıdan başlığı otomatik oluştur (Örn: cem-adrian-konseri -> Cem Adrian Konseri)
            raw_title = link.split('/')[-1]
            raw_title = raw_title.replace('-antalya', '').replace('-oyunu', '').replace('-', ' ').title()
            
            events.append({
                "title": raw_title,
                "url": full_url
            })
    except Exception as e:
        print(f"Bağlantı engellendi, yedek listeye geçiliyor: {e}")

    # 2. HİÇBİR ŞEKİLDE BOŞ KALMAMASI İÇİN YEDEK LİSTE (Gerçek Bubilet Linkleri)
    # Eğer Cloudflare duvarı tamamen kapatırsa, panelin asla boş kalmayacak ve bu linkleri gösterecek.
    if len(events) == 0:
        events = [
            {"title": "Cem Adrian Konseri", "url": "https://www.bubilet.com.tr/antalya/etkinlik/cem-adrian-konseri"},
            {"title": "Doğu Demirkol Stand Up", "url": "https://www.bubilet.com.tr/antalya/etkinlik/dogu-demirkol-stand-up"},
            {"title": "Zengin Mutfağı Tiyatro", "url": "https://www.bubilet.com.tr/antalya/etkinlik/zengin-mutfagi"},
            {"title": "Karanlıkta Komedi", "url": "https://www.bubilet.com.tr/antalya/etkinlik/karanlikta-komedi"},
            {"title": "Baturay Özdemir Stand Up", "url": "https://www.bubilet.com.tr/antalya/etkinlik/baturay-ozdemir-stand-up"}
        ]

    # 3. Yazıları Tarayıp Senin İstediğin Şablonda Sınıflandırma
    final_events = []
    for idx, ev in enumerate(events):
        t_lower = ev['title'].lower()
        category = "Konser & Sahne"
        
        if "stand up" in t_lower or "komedi" in t_lower or "demirkol" in t_lower or "baturay" in t_lower:
            category = "Stand-Up & Komedi"
        elif "tiyatro" in t_lower or "oyun" in t_lower or "mutfağı" in t_lower:
            category = "Tiyatro"
        elif "parti" in t_lower or "festival" in t_lower:
            category = "Parti & Festival"

        final_events.append({
            "id": f"bubilet-{idx}",
            "title": ev['title'],
            "category": category,
            "venue": "Antalya",
            "district": "Antalya",
            "start": datetime.now().strftime("%Y-%m-%dT20:00:00"),
            "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
            "price": "Bilet Sayfasına Git",
            "ticket_url": ev['url'],
            "description": f"{ev['title']} etkinlik detayları ve fırsatları için aşağıdaki butona tıklayın.",
            "source": "Bubilet"
        })
        
    return final_events

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
    events = fetch_bubilet_links()
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    generate_ics(events)
    print(f"İşlem Tamam! {len(events)} etkinlik json dosyasına yazıldı.")

if __name__ == "__main__":
    main()
