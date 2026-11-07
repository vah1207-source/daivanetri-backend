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

@app.get("/")
def home():
    return {"status": "DaivaNetri Backend Working"}

@app.post("/api/kundali")
def kundali(b: Birth):
    jd = swe.julday(b.year, b.month, b.day, b.hour + b.minute/60.0)
    cusps, ascmc = swe.houses(jd, b.lat, b.lon, b'P')
    lagna_lon = ascmc[0]
    lagna_rashi, lagna_deg = to_rashi(lagna_lon)
    lagna_nak, lagna_pada = to_nakshatra(lagna_lon)
    planets = {"Surya": swe.SUN, "Chandra": swe.MOON, "Kuja": swe.MARS, "Budha": swe.MERCURY, "Guru": swe.JUPITER, "Shukra": swe.VENUS, "Shani": swe.SATURN, "Rahu": swe.MEAN_NODE}
    grahas = []
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
    janma_rashi, _ = to_rashi(moon_lon)
    janma_nak, janma_pada = to_nakshatra(moon_lon)
    return {"lagna": {"rashi": lagna_rashi, "degree": lagna_deg, "nakshatra": lagna_nak, "pada": lagna_pada}, "janma_rashi": janma_rashi, "chandra_rashi": janma_rashi, "nakshatra": janma_nak, "pada": janma_pada, "grahas": grahas, "source": "Swiss Ephemeris - Lahiri Ayanamsa"}
