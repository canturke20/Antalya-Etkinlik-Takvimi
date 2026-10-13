import os
import json
import re
from datetime import datetime, timedelta

# Kategori Havuzu
CATEGORIES = {
    "KONSER": "Konser",
    "TIYATRO": "Tiyatro",
    "STANDUP": "Stand-Up & Komedi",
    "ATOLYE": "Atölye & Workshop",
    "KARIYER": "Kariyer & Öğrenci",
    "SIRKET_IS": "Şirket & İş Zirveleri",
    "TEKNOLOJI": "Teknoloji & Girişimcilik",
    "PARTI": "Parti & Gece Hayatı",
    "DOGA_SPOR": "Doğa & Spor",
    "GASTRONOMI_SERGI": "Sergi & Gastronomi",
    "SOSYAL": "Sosyal Kulüpler & Buluşmalar"
}

def fetch_events_from_sources():
    events = [
        {
            "id": "ant-kar-01",
            "title": "Akdeniz Kariyer Zirvesi '26",
            "category": CATEGORIES["KARIYER"],
            "venue": "Akdeniz Üniversitesi Atatürk Konferans Salonu",
            "district": "Konyaaltı",
            "start": "2026-10-20T10:00:00",
            "end": "2026-10-20T17:30:00",
            "price": "Ücretsiz (Kayıt Zorunlu)",
            "ticket_url": "https://kariyer.akdeniz.edu.tr",
            "description": "50+ kurumsal şirketin İK yöneticileri ile mülakat simülasyonları ve staj fırsatları.",
            "source": "Akdeniz Üniversitesi"
        },
        {
            "id": "ant-tek-01",
            "title": "Antalya Tech & AI Meetup: Yapay Zeka ile Ürün Geliştirme",
            "category": CATEGORIES["TEKNOLOJI"],
            "venue": "Antalya Teknokent Ar-Ge Binası",
            "district": "Konyaaltı",
            "start": "2026-10-22T18:30:00",
            "end": "2026-10-22T21:00:00",
            "price": "Ücretsiz",
            "ticket_url": "https://meetup.com/antalya-tech",
            "description": "Yazılımcılar ve girişimciler için networking buluşması ve sunumlar.",
            "source": "Meetup"
        },
        {
            "id": "ant-sir-01",
            "title": "Uluslararası Turizm & Otelcilik Yatırımları Kongresi",
            "category": CATEGORIES["SIRKET_IS"],
            "venue": "ANFAŞ Fuar Merkezi",
            "district": "Aksu",
            "start": "2026-10-24T09:30:00",
            "end": "2026-10-25T18:00:00",
            "price": "Kurumsal Kayıt",
            "ticket_url": "https://anfas.com.tr",
            "description": "Bölgesel B2B yatırım ve iş ortaklığı zirvesi.",
            "source": "ANFAŞ"
        },
        {
            "id": "ant-par-01",
            "title": "Kaleiçi Rooftop Sunset & Electronic Music",
            "category": CATEGORIES["PARTI"],
            "venue": "Kaleiçi Secret Garden",
            "district": "Muratpaşa",
            "start": "2026-10-24T21:00:00",
            "end": "2026-10-25T03:00:00",
            "price": "350 TL",
            "ticket_url": "https://biletino.com",
            "description": "Gün batımı sonrası yerli ve yabancı DJ performansları.",
            "source": "Biletino"
        },
        {
            "id": "ant-kon-01",
            "title": "Antalya Devlet Senfoni Orkestrası - Film Müzikleri Konseri",
            "category": CATEGORIES["KONSER"],
            "venue": "AKM Aspendos Salonu",
            "district": "Muratpaşa",
            "start": "2026-10-23T20:30:00",
            "end": "2026-10-23T22:30:00",
            "price": "150 TL - 350 TL",
            "ticket_url": "https://biletinial.com",
            "description": "Klasik sinema başyapıtlarının müzikleri canlı orkestra yorumuyla.",
            "source": "Biletinial"
        },
        {
            "id": "ant-tiy-01",
            "title": "Açık Hava Tiyatrosu: Zengin Mutfağı",
            "category": CATEGORIES["TIYATRO"],
            "venue": "Konyaaltı Açıkhava Tiyatrosu",
            "district": "Konyaaltı",
            "start": "2026-10-26T20:30:00",
            "end": "2026-10-26T22:45:00",
            "price": "400 TL - 800 TL",
            "ticket_url": "https://biletix.com",
            "description": "Şener Şen ve usta oyuncu kadrosuyla tiyatro akşamı.",
            "source": "Biletix"
        },
        {
            "id": "ant-std-01",
            "title": "Kaan Sekban Saçmalar Stand-Up",
            "category": CATEGORIES["STANDUP"],
            "venue": "Türkan Şoray Kültür Merkezi",
            "district": "Muratpaşa",
            "start": "2026-10-27T20:30:00",
            "end": "2026-10-27T22:30:00",
            "price": "350 TL - 650 TL",
            "ticket_url": "https://bubilet.com.tr",
            "description": "Tek kişilik komedi gösterisi.",
            "source": "Bubilet"
        },
        {
            "id": "ant-atl-01",
            "title": "Seramik ve Kupa Yapım Atölyesi",
            "category": CATEGORIES["ATOLYE"],
            "venue": "Antalya Sanat Çiftliği",
            "district": "Muratpaşa",
            "start": "2026-10-28T14:00:00",
            "end": "2026-10-28T17:00:00",
            "price": "450 TL",
            "ticket_url": "https://biletinial.com",
            "description": "Çamur şekillendirme ve seramik teknikleri çalışması.",
            "source": "Biletinial"
        },
        {
            "id": "ant-dog-01",
            "title": "Geyikbayırı Tırmanış & Doğa Yürüyüşü",
            "category": CATEGORIES["DOGA_SPOR"],
            "venue": "Geyikbayırı Kamp Alanı",
            "district": "Konyaaltı",
            "start": "2026-11-01T09:00:00",
            "end": "2026-11-01T16:00:00",
            "price": "Ücretsiz",
            "ticket_url": "https://meetup.com/antalya-outdoor",
            "description": "Başlangıç tırmanışları ve Likya Yolu patika yürüyüşü.",
            "source": "Outdoor Kulübü"
        },
        {
            "id": "ant-gas-01",
            "title": "GastroAntalya Lezzet & Narenciye Tadım Günleri",
            "category": CATEGORIES["GASTRONOMI_SERGI"],
            "venue": "Cam Piramit",
            "district": "Muratpaşa",
            "start": "2026-11-06T11:00:00",
            "end": "2026-11-08T19:00:00",
            "price": "Giriş Serbest",
            "ticket_url": "https://antalya.bel.tr",
            "description": "Yerel lezzetler ve narenciye atölyeleri.",
            "source": "Antalya BB"
        },
        {
            "id": "ant-sos-01",
            "title": "Antalya Language Exchange & Board Games",
            "category": CATEGORIES["SOSYAL"],
            "venue": "Old Town Pub Kaleiçi",
            "district": "Muratpaşa",
            "start": "2026-10-21T19:30:00",
            "end": "2026-10-21T23:00:00",
            "price": "Ücretsiz",
            "ticket_url": "https://meetup.com",
            "description": "Yabancı dil pratik akşamı ve masa oyunları.",
            "source": "Meetup"
        }
    ]
    return events

def generate_ics(events, output_path="antalya_etkinlikler.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Antalya Etkinlik Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:🌴 Antalya Etkinlikleri (Canlı)",
        "X-WR-TIMEZONE:Europe/Istanbul"
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    for ev in events:
        start_dt = datetime.fromisoformat(ev["start"]).strftime("%Y%m%dT%H%M%S")
        end_dt = datetime.fromisoformat(ev["end"]).strftime("%Y%m%dT%H%M%S")
        desc = f"{ev['description']}\\n\\nKategori: {ev['category']}\\nMekan: {ev['venue']}\\nFiyat: {ev['price']}\\nLink: {ev['ticket_url']}"
        
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{ev['id']}@antalya-etkinlikler.local",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{start_dt}",
            f"DTEND:{end_dt}",
            f"SUMMARY:[{ev['category']}] {ev['title']}",
            f"LOCATION:{ev['venue']}, {ev['district']}, Antalya",
            f"DESCRIPTION:{desc}",
            f"URL:{ev['ticket_url']}",
            f"CATEGORIES:{ev['category']}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))

def generate_html_portal(events, output_path="index.html"):
    cats = sorted(list(set(ev["category"] for ev in events)))
    districts = sorted(list(set(ev["district"] for ev in events)))
    events_json = json.dumps(events, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antalya Canlı Etkinlik Paneli</title>
    <style>
        :root {{ --bg: #090d16; --surface: #131c2e; --primary: #38bdf8; --accent: #f59e0b; --text: #f8fafc; --muted: #94a3b8; --border: #23324d; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 24px 16px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }}
        .btn-apple {{ background: #fff; color: #000; padding: 10px 18px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 14px; }}
        .filters {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
        .filter-item {{ display: flex; flex-direction: column; gap: 6px; }}
        .filter-item label {{ font-size: 12px; font-weight: 700; color: var(--muted); }}
        .filter-item input, .filter-item select {{ background: var(--bg); color: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; font-size: 14px; outline: none; }}
        .chips {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 20px; }}
        .chip {{ padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; background: var(--surface); color: var(--muted); cursor: pointer; border: 1px solid var(--border); white-space: nowrap; }}
        .chip.active {{ background: var(--primary); color: #000; border-color: var(--primary); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }}
        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }}
        .tag {{ font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 4px; background: rgba(56, 189, 248, 0.15); color: var(--primary); display: inline-block; margin-bottom: 8px; }}
        .title {{ font-size: 17px; font-weight: 700; margin-bottom: 6px; line-height: 1.3; }}
        .desc {{ font-size: 13px; color: var(--muted); margin-bottom: 12px; line-height: 1.4; }}
        .meta {{ border-top: 1px dashed var(--border); padding-top: 10px; font-size: 13px; display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }}
        .actions {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 12px; font-size: 13px; }}
        .actions a {{ color: var(--primary); text-decoration: none; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1 style="font-size:24px;">🌴 Antalya Canlı Etkinlik Paneli</h1>
                <p style="color:var(--muted); font-size:14px;">Kariyer, Parti, Konser, Tiyatro, Zirveler ve Atölyeler</p>
            </div>
            <a href="antalya_etkinlikler.ics" download="antalya_etkinlikler.ics" class="btn-apple"> Apple Takvime Aktar (.ics)</a>
        </header>

        <div class="filters">
            <div class="filter-item">
                <label>Arama</label>
                <input type="text" id="searchInput" placeholder="Etkinlik veya mekan...">
            </div>
            <div class="filter-item">
                <label>İlçe</label>
                <select id="districtFilter">
                    <option value="ALL">Tüm İlçeler</option>
                    {"".join(f'<option value="{d}">{d}</option>' for d in districts)}
                </select>
            </div>
            <div class="filter-item">
                <label>Başlangıç Tarihi</label>
                <input type="date" id="dateFilter">
            </div>
        </div>

        <div class="chips" id="chips">
            <div class="chip active" data-cat="ALL">Tümü</div>
            {"".join(f'<div class="chip" data-cat="{c}">{c}</div>' for c in cats)}
        </div>

        <div class="grid" id="grid"></div>
    </div>

    <script>
        const events = {events_json};
        let activeCat = "ALL";

        function formatDate(str) {{
            return new Date(str).toLocaleDateString('tr-TR', {{ weekday: 'short', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }});
        }}

        function getGoogleUrl(ev) {{
            const s = ev.start.replace(/[-:]/g, "");
            const e = ev.end.replace(/[-:]/g, "");
            return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${{encodeURIComponent(ev.title)}}&dates=${{s}}/${{e}}&details=${{encodeURIComponent(ev.description + "\\n" + ev.ticket_url)}}&location=${{encodeURIComponent(ev.venue)}}`;
        }}

        function render() {{
            const search = document.getElementById("searchInput").value.toLowerCase();
            const district = document.getElementById("districtFilter").value;
            const dateVal = document.getElementById("dateFilter").value;
            const grid = document.getElementById("grid");

            let filtered = events.filter(ev => {{
                const matchCat = activeCat === "ALL" || ev.category === activeCat;
                const matchDist = district === "ALL" || ev.district === district;
                const matchSearch = ev.title.toLowerCase().includes(search) || ev.venue.toLowerCase().includes(search);
                const matchDate = !dateVal || new Date(ev.start) >= new Date(dateVal);
                return matchCat && matchDist && matchSearch && matchDate;
            }});

            grid.innerHTML = filtered.map(ev => `
                <div class="card">
                    <div>
                        <span class="tag">${{ev.category}}</span>
                        <div class="title">${{ev.title}}</div>
                        <div class="desc">${{ev.description}}</div>
                        <div class="meta">
                            <div>📅 ${{formatDate(ev.start)}}</div>
                            <div>📍 ${{ev.venue}} (${{ev.district}})</div>
                            <div>🏷️ <b style="color:var(--accent);">${{ev.price}}</b></div>
                        </div>
                    </div>
                    <div class="actions">
                        <a href="${{getGoogleUrl(ev)}}" target="_blank">+ Google Takvim</a>
                        <a href="${{ev.ticket_url}}" target="_blank">Kayıt / Bilet ↗</a>
                    </div>
                </div>
            `).join("");
        }}

        document.getElementById("searchInput").addEventListener("input", render);
        document.getElementById("districtFilter").addEventListener("change", render);
        document.getElementById("dateFilter").addEventListener("change", render);
        document.querySelectorAll(".chip").forEach(c => {{
            c.addEventListener("click", () => {{
                document.querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
                c.classList.add("active");
                activeCat = c.getAttribute("data-cat");
                render();
            }});
        }});
        render();
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    evs = fetch_events_from_sources()
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(evs, f, ensure_ascii=False, indent=2)
    generate_ics(evs)
    generate_html_portal(evs)
    print("Tamamlandı: events.json, antalya_etkinlikler.ics ve index.html hazır!")

