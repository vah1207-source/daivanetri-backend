from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
swe.set_ephe_path('./ephe')
swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHIS = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
NAKSHATRAS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
TITHIS = ["Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashti","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima","Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashti","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"]
YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]
KARANAS = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti","Shakuni","Chatushpada","Naga","Kimstughna"]

class Birth(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    lat: float = 14.61
    lon: float = 74.83

def to_rashi(lon):
    return RASHIS[int(lon // 30)], round(lon % 30, 2)
def to_nakshatra(lon):
    idx = int(lon // 13.3333333)
    pada = int(((lon % 13.3333333) / 13.3333333) * 4) + 1
    return NAKSHATRAS[idx], pada

def get_panchanga(jd):
    sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    moon, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    s_lon, m_lon = sun[0], moon[0]
    diff = (m_lon - s_lon) % 360
    tithi_idx = int(diff // 12)
    yoga_val = (s_lon + m_lon) % 360
    yoga_idx = int(yoga_val // 13.3333333)
    karana_idx = int(diff // 6) % 11
    return {"tithi": TITHIS[tithi_idx], "yoga": YOGAS[yoga_idx], "karana": KARANAS[karana_idx], "paksha": "Shukla Paksha" if tithi_idx < 15 else "Krishna Paksha"}

def get_kp(jd, lat, lon):
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    lagna_lon = ascmc[0]
    nak_idx = int(lagna_lon // 13.3333333)
    lord_map = ["Ketu","Shukra","Surya","Chandra","Kuja","Rahu","Guru","Shani","Budha"]
    star_lord = lord_map[nak_idx % 9]
    rem = (lagna_lon % 13.3333333) / 13.3333333
    sub_idx = int(rem * 9)
    sub_lord = lord_map[(nak_idx + sub_idx) % 9]
    lagna_r, lagna_d = to_rashi(lagna_lon)
    lagna_n, lagna_p = to_nakshatra(lagna_lon)
    return {"lagna_rashi": lagna_r, "lagna_degree": lagna_d, "nakshatra": lagna_n, "pada": lagna_p, "star_lord": star_lord, "sub_lord": sub_lord, "kp_note": "Prashna Kundalige - Sub-Lord mukhya"}

def get_jaimini(grahas_deg):
    filtered = [(g["name"], g["degree_full"]) for g in grahas_deg if g["name"] not in ["Rahu","Ketu"]]
    sorted_g = sorted(filtered, key=lambda x: x[1], reverse=True)
    karaka_names = ["Atmakaraka","Amatyakaraka","Bhratrukaraka","Matrukaraka","Pitrikaraka","Putrakaraka","Gnatikaraka","Darakaraka"]
    result = {}
    for i, (name, deg) in enumerate(sorted_g):
        if i < len(karaka_names):
            result[karaka_names[i]] = name
    return result

@app.get("/")
def home():
    return {"status": "DaivaNetri Backend Working - KP + Jaimini + Panchanga Ready"}

@app.post("/api/kundali")
def kundali(b: Birth):
    jd = swe.julday(b.year, b.month, b.day, b.hour + b.minute/60.0)
    cusps, ascmc = swe.houses(jd, b.lat, b.lon, b'P')
    lagna_lon = ascmc[0]
    lagna_rashi, lagna_deg = to_rashi(lagna_lon)
    lagna_nak, lagna_pada = to_nakshatra(lagna_lon)
    planets = {"Surya": swe.SUN, "Chandra": swe.MOON, "Kuja": swe.MARS, "Budha": swe.MERCURY, "Guru": swe.JUPITER, "Shukra": swe.VENUS, "Shani": swe.SATURN, "Rahu": swe.MEAN_NODE}
    grahas = []
    grahas_deg = []
    moon_lon = 0
    for name, pid in planets.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SPEED)
        lon = res[0]
        if name == "Chandra":
            moon_lon = lon
        if name == "Rahu":
            ketu_lon = (lon + 180) % 360
            kr, kd = to_rashi(lon)
            kn, kp = to_nakshatra(lon)
            grahas.append({"name": "Rahu", "rashi": kr, "degree": kd, "nakshatra": kn, "pada": kp})
            kr2, kd2 = to_rashi(ketu_lon)
            kn2, kp2 = to_nakshatra(ketu_lon)
            grahas.append({"name": "Ketu", "rashi": kr2, "degree": kd2, "nakshatra": kn2, "pada": kp2})
            continue
        r, d = to_rashi(lon)
        n, p = to_nakshatra(lon)
        retro = res[3] < 0
        grahas.append({"name": name, "rashi": r, "degree": d, "nakshatra": n, "pada": p, "retro": retro})
        grahas_deg.append({"name": name, "degree_full": lon})
    janma_rashi, _ = to_rashi(moon_lon)
    janma_nak, janma_pada = to_nakshatra(moon_lon)
    panchanga = get_panchanga(jd)
    kp = get_kp(jd, b.lat, b.lon)
    jaimini = get_jaimini(grahas_deg)
    return {"lagna": {"rashi": lagna_rashi, "degree": lagna_deg, "nakshatra": lagna_nak, "pada": lagna_pada}, "janma_rashi": janma_rashi, "chandra_rashi": janma_rashi, "nakshatra": janma_nak, "pada": janma_pada, "grahas": grahas, "panchanga": panchanga, "kp": kp, "jaimini": jaimini, "source": "Swiss Ephemeris - Lahiri - KP + Jaimini + Panchanga"}
