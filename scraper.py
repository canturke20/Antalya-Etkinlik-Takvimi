import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_bubilet_playwright():
    events = []
    print("Gerçek tarayıcı (Chrome) başlatılıyor...")

    with sync_playwright() as p:
        # Arka planda başsız (görünmez) bir tarayıcı aç
        browser = p.chromium.launch(headless=True)
        # Cloudflare'in bot olduğumuzu anlamaması için normal bir bilgisayar kimliği veriyoruz
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        try:
            print("Bubilet Antalya sayfasına gidiliyor ve Cloudflare aşılıyor...")
            # Siteye git ve tüm JavaScript/Cloudflare engellerinin yüklenip bitmesini bekle
            page.goto("https://www.bubilet.com.tr/antalya", timeout=60000, wait_until="networkidle")
            
            # Sayfa tamamen yüklendi, artık HTML içindeki tüm linkleri alabiliriz
            link_elements = page.query_selector_all("a[href]")
            seen_titles = set()
            
            for el in link_elements:
                href = el.get_attribute("href") or ""
                
                # Sadece etkinlik linklerini filtrele, gereksiz iletişim/sepet sayfalarını atla
                href_lower = href.lower()
                is_event_link = ("/antalya/" in href_lower or "/etkinlik/" in href_lower)
                is_junk = any(x in href_lower for x in ["hakkimizda", "iletisim", "kvkk", "giris", "sepet", "uye-ol", "kategori", "mekan", "sss"])
                
                if len(href.split("/")) < 4:
                    is_event_link = False
                    
                if is_event_link and not is_junk:
                    full_url = href if href.startswith("http") else "https://www.bubilet.com.tr" + href
                    
                    # Başlığı al
                    title = el.get_attribute("title") or ""
                    if not title:
                        title = el.inner_text().strip()
                        
                    title = re.sub(r'\s+', ' ', title).strip()
                    if len(title) < 6 or "Bilet Al" in title or "İncele" in title:
                        continue
                        
                    # Aynı etkinliği bir daha ekleme
                    clean_t = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
                    if clean_t in seen_titles:
                        continue
                    seen_titles.add(clean_t)
                    
                    # SENİN İSTEDİĞİN ŞABLON: Kelimelere göre kategoriye ayırma
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
                        "venue": "Antalya",
                        "district": "Antalya",
                        "start": datetime.now().strftime("%Y-%m-%dT20:00:00"),
                        "end": datetime.now().strftime("%Y-%m-%dT22:30:00"),
                        "price": "Fırsatı İncele",
                        "ticket_url": full_url,
                        "description": f"Fırsat: {title}. Etkinlik detayları ve bilet sayfasına gitmek için yandaki butona tıklayın.",
                        "source": "Bubilet"
                    })
        except Exception as e:
            print(f"Tarayıcı hatası: {e}")
        finally:
            browser.close()
            
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
    events = fetch_bubilet_playwright()
    print(f"Başarılı: Toplam {len(events)} gerçek etkinlik tarayıcı ile yakalandı.")
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    generate_ics(events)

if __name__ == "__main__":
    main()
