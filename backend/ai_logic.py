import random
import math
import re

# ── Multilingual Definitions for 8 Coastal Target Languages ────────────────────
# en (English), hi (Hindi), ta (Tamil), ml (Malayalam),
# bn (Bengali), or (Odia), gu (Gujarati), kok (Konkani)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "ml": "Malayalam",
    "bn": "Bengali",
    "or": "Odia",
    "gu": "Gujarati",
    "kok": "Konkani"
}

# Unicode Script Ranges
SCRIPT_PATTERNS = [
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),       # Tamil
    ("ml", re.compile(r"[\u0D00-\u0D7F]")),       # Malayalam
    ("bn", re.compile(r"[\u0980-\u09FF]")),       # Bengali
    ("or", re.compile(r"[\u0B00-\u0B7F]")),       # Odia
    ("gu", re.compile(r"[\u0A80-\u0AFF]")),       # Gujarati
    ("hi_or_kok", re.compile(r"[\u0900-\u097F]")), # Devanagari (Hindi / Konkani)
]

# Distinctive Konkani markers in Devanagari & Latin
KONKANI_MARKERS = [
    "न्हंय", "उदक", "झाड", "वाडळ", "ल्हारां", "सुटका", "आदार", "तात्पुरतो", "गोंय",
    "बुडता", "दुयेन्स", "रोगोत", "आसा", "जाय", "व्हड", "हांगा", "कसलें", "वाटाव", "दॉक्टर",
    "nhay", "udak", "aadar", "soddi", "bachav", "voiz", "asa", "zay", "vhad"
]

# Transliterated Romanized Keyword Cues
ROMANIZED_CUES = {
    "hi": ["madad", "bachao", "pani", "chot", "toofan", "baadh", "doob", "sahayata", "bache", "ghayal"],
    "ta": ["kaapathunga", "thanni", "vellam", "udhavi", "alaigal", "maruthuvam", "kaapadu", "sikkitom"],
    "ml": ["sahayam", "vellappokkam", "rakshikuka", "kurungi", "chikitsa", "thiramaala"],
    "bn": ["banya", "jol", "sahajjo", "uddhar", "daktar", "bachao"],
    "or": ["sahajya", "banya", "uddhar", "pani", "daktara"],
    "gu": ["madad", "bachavo", "poor", "vavazodu", "paani", "lohi"],
    "kok": ["nhay", "udak", "aadar", "soddi", "bachav", "voiz", "dondo"]
}

# Multilingual Category Keywords for SOS Classification
MULTILINGUAL_SOS_KEYWORDS = {
    "Tsunami": {
        "en": ["tsunami", "wave", "ocean surge", "sea wave", "earthquake", "tidal wave"],
        "hi": ["सुनामी", "लहर", "समुद्र", "समुद्री लहर", "भूकंप", "लहरें"],
        "ta": ["சுனாமி", "அலை", "கடல்", "நில அதிர்வு", "ஆழிப்பேரலை", "அலைகள்"],
        "ml": ["സുനാമി", "തിരമാല", "കടൽ", "ഭൂകമ്പം"],
        "bn": ["সুনামি", "ঢেউ", "সমুদ্র", "ভূমিকম্প"],
        "or": ["ସୁନାମୀ", "ଢେଉ", "ସମୁଦ୍ର", "ଭୂମିକମ୍ପ"],
        "gu": ["સુનામી", "મોજા", "દરિયો", "ધરતીકંપ"],
        "kok": ["सुनामी", "ल्हार", "दर्या", "भूंयकांप", "ल्हारां"]
    },
    "Medical": {
        "en": ["medical", "doctor", "hurt", "bleeding", "ambulance", "hospital", "injury", "pregnant", "pain", "unconscious"],
        "hi": ["चिकित्सा", "डॉक्टर", "चोट", "खून", "अस्पताल", "घायल", "दवा", "एंबुलेंस", "दर्द", "बेहोश"],
        "ta": ["மருத்துவம்", "மருத்துவர்", "காயம்", "ரத்தம்", "ஆஸ்பத்திரி", "ஆம்புலன்ஸ்", "வலி", "மருந்து", "உயிருக்கு"],
        "ml": ["ചികിത്സ", "ഡോക്ടർ", "പരുക്ക്", "രക്തം", "ആശുപത്രി", "ആംബുലൻസ്", "വേദന"],
        "bn": ["চিকিৎসা", "ডাক্তার", "আহত", "রক্ত", "হাসপাতাল", "অ্যাম্বুলেন্স", "ব্যথা"],
        "or": ["ଚିକିତ୍ସା", "ଡାକ୍ତର", "ରକ୍ତ", "ହସ୍ପିଟାଲ", "ଆହତ", "ଆମ୍ବୁଲାନ୍ସ", "ଯନ୍ତ୍ରଣା"],
        "gu": ["તબીબી", "ડોક્ટર", "ઈજા", "લોહી", "હોસ્પિટલ", "એમ્બ્યુલન્સ", "દર્દ"],
        "kok": ["वैजकी", "दॉक्टर", "इजा", "रोगोत", "रगत", "दुख", "दुयेन्स", "अस्पताल", "हॉस्पिटल", "रुग्णवाहिका"]
    },
    "Flood": {
        "en": ["flood", "water", "drowning", "submerged", "river overflow", "inundation", "water level rising"],
        "hi": ["बाढ़", "पानी", "डूब", "जलभराव", "सैलाब", "नदी", "डूबा", "जलमग्न", "डूबना"],
        "ta": ["வெள்ளம்", "தண்ணீர்", "மூழ்குகிறது", "ஆறு", "வெள்ளப்பெருக்கு", "நீர்", "மூழ்கியது"],
        "ml": ["വെള്ളപ്പൊക്കം", "വെള്ളം", "മുങ്ങി", "നദി", "കവിഞ്ഞൊഴുകുന്നു"],
        "bn": ["বন্যা", "জল", "ডুবে", "নদী", "প্লাবিত", "জলমগ্ন"],
        "or": ["ବନ୍ୟା", "ପାଣି", "ବୁଡ଼ିବା", "ନଦୀ", "ଜଳମଗ୍ନ"],
        "gu": ["પૂર", "પાણી", "ડૂબી", "નદી", "જળબંબાકાર", "પૂરગ્રસ્ત"],
        "kok": ["हुंवार", "उदक", "बुडता", "न्हंय", "न्हंयेक"]
    },
    "Evacuation": {
        "en": ["evacuate", "stuck", "trapped", "rescue", "help", "stranded", "sos", "save us", "danger", "collapse"],
        "hi": ["बचाव", "फंसे", "मदद", "सहायता", "सुरक्षित", "निकासी", "संकट", "फंसा", "बचाओ", "मकान गिरा"],
        "ta": ["வெளியேறு", "சிக்கி", "மீட்பு", "உதவி", "காப்பாற்று", "சிக்கிக்கொண்டோம்", "அபாயம்", "காப்பாத்துங்கள்"],
        "ml": ["രക്ഷിക്കുക", "കുടുങ്ങി", "സহായം", "ഒഴിപ്പിക്കൽ", "രക്ഷാപ്രവർത്തനം", "അപകടം"],
        "bn": ["উদ্ধার", "আটকে", "সাহায্য", "স্থানান্তর", "বাঁচাও", "বিপদ"],
        "or": ["ଉଦ୍ଧାର", "ଫସି", "ସାହାଯ୍ୟ", "ସ୍ଥାନାନ୍ତର", "ବଞ୍ଚାଅ", "ବିପଦ"],
        "gu": ["બચાવો", "ફસાયેલા", "મદદ", "સ્થળાંતર", "સહાય", "જોખમ"],
        "kok": ["सुटका", "आदार", "मदत", "वाटाव", "संकट", "फाशी"]
    }
}

def detect_language(text: str) -> str:
    """
    Detects language of input text across the 8 target coastal languages.
    Uses Unicode script inspection, vocabulary markers, and Romanized cues.
    Defaults to 'en' (English).
    """
    if not text or not text.strip():
        return "en"

    # 1. Check Indic Unicode Scripts
    for lang_code, pattern in SCRIPT_PATTERNS:
        if pattern.search(text):
            if lang_code == "hi_or_kok":
                # Distinguish Konkani vs Hindi
                text_lower = text.lower()
                if any(m in text_lower for m in KONKANI_MARKERS):
                    return "kok"
                return "hi"
            return lang_code

    # 2. Check Romanized / Transliterated keywords for coastal languages
    text_lower = text.lower()
    for lang_code, cues in ROMANIZED_CUES.items():
        if any(re.search(rf"\b{re.escape(cue)}\b", text_lower) for cue in cues):
            return lang_code

    # 3. Default fallback
    return "en"

def analyze_multilingual_voice_sos(transcript: str) -> dict:
    """
    Analyzes an emergency voice SOS transcript in any of the 8 coastal languages.
    Performs language detection, category categorization, and severity scoring.
    """
    detected_lang = detect_language(transcript)
    text_lower = transcript.lower()

    category = "General"
    severity = 50
    matched_keyword = None

    # Priority ranking: Tsunami (100) > Medical (95) > Evacuation (90) > Flood (85)
    category_order = [
        ("Tsunami", 100),
        ("Medical", 95),
        ("Flood", 85),
        ("Evacuation", 90)
    ]

    for cat_name, base_sev in category_order:
        lang_dict = MULTILINGUAL_SOS_KEYWORDS.get(cat_name, {})
        # Search all languages in dictionary to catch mixed language speech (e.g. Hindi + English)
        for lang, kw_list in lang_dict.items():
            for kw in kw_list:
                if kw in text_lower:
                    category = cat_name
                    severity = base_sev
                    matched_keyword = kw
                    break
            if matched_keyword:
                break
        if matched_keyword:
            break

    # Add slight heuristic jitter (-3 to +3) capped at 100
    jitter = random.randint(-3, 3)
    final_severity = max(10, min(100, severity + jitter))

    return {
        "language": detected_lang,
        "language_name": LANGUAGE_NAMES.get(detected_lang, "English"),
        "category": category,
        "severity": final_severity,
        "matched_keyword": matched_keyword
    }

def calculate_risk_score(text: str, location: str) -> int:
    """
    Advanced heuristic-based model to assign a risk score.
    Higher scores mean higher priority for authorities.
    Now supports all 8 coastal languages.
    """
    text_lower = text.lower()
    score = 0

    # Life-threatening keywords across languages
    p1_keywords = [
        "tsunami", "cyclone", "flood", "drowning", "sos", "emergency", "earthquake",
        "सुनामी", "चक्रवात", "बाढ़", "डूब", "சுனாமி", "சூறாவளி", "வெள்ளம்", "വെള്ളപ്പൊക്കം",
        "ঘূর্ণিঝড়", "বন্যা", "ବାତ୍ୟା", "ବନ୍ୟା", "વાવાઝોડું", "પૂર", "हुंवार"
    ]
    for kw in p1_keywords:
        if kw in text_lower:
            score += 40
            break

    # Priority 2: Significant Threat (30-60 pts)
    p2_keywords = [
        "storm", "oil spill", "pollution", "hazard", "blocked", "bridge collapse",
        "तूफान", "प्रदूषण", "புயல்", "மாசு", "കൊടുങ്കാറ്റ്", "ঝড়", "ଜଳମଗ୍ନ", "તોફાન"
    ]
    for kw in p2_keywords:
        if kw in text_lower:
            score += 20
            break

    # Priority 3: Environmental Anomaly (10-30 pts)
    p3_keywords = [
        "algal bloom", "waste", "trash", "erosion", "beach", "tide",
        "समुद्र", "कचरा", "கடற்கரை", "தீரம்", "তীর", "କୂଳ", "કાંઠો", "दर्या"
    ]
    for kw in p3_keywords:
        if kw in text_lower:
            score += 10
            break

    if "beach" in text_lower or "shore" in text_lower or "coast" in text_lower or "समुद्र" in text_lower or "கடல்" in text_lower:
        score += 5

    return min(score, 100)

def calculate_aid_priority(needs: str, description: str) -> tuple[str, int]:
    """
    Determines urgency level and validation score for humanitarian aid.
    Returns: (Urgency_Label, Score_0_100)
    """
    text_lower = (needs + " " + description).lower()
    score = 0
    
    # Base prioritization based on 'needs' category
    if "medical" in needs.lower() or "rescue" in needs.lower():
        score += 50
    elif "food" in needs.lower() or "water" in needs.lower():
        score += 30
    elif "shelter" in needs.lower():
        score += 20
        
    # Keyword analysis (Accumulative)
    # High Priority Keywords (Critical Life Threat)
    high_keywords = ["rescue", "trapped", "bleeding", "medical", "drowning", "ambulance", "stuck", "baby", "elderly", "pregnant", "critical"]
    for kw in high_keywords:
        if kw in text_lower:
            score += 15
            
    # Medium Priority Keywords (Essential/Health)
    med_keywords = ["food", "water", "shelter", "medicine", "fever", "electricity", "supply", "hungry", "sick"]
    for kw in med_keywords:
        if kw in text_lower:
            score += 10
            
    # Length/Detail bonus (Real requests often explain more, but spam can be short)
    if len(description) > 20: 
        score += 5
        
    # Cap score at 100
    score = min(score, 100)
    
    # Determine Label based on Score
    if score >= 70:
        return "High", score
    elif score >= 40:
        return "Medium", score
    else:
        return "Low", score

def generate_heatmap_data():
    """
    Generates a global dataset approximating world coastlines.
    Simulates global satellite monitoring data.
    """
    points = []
    
    def add_line(start_lat, start_lon, end_lat, end_lon, steps, intensity_base, jitter=1.0):
        for i in range(steps):
            t = i / steps
            lat = start_lat * (1 - t) + end_lat * t
            lon = start_lon * (1 - t) + end_lon * t
            
            # Jitter to make it look less like a straight line
            lat += random.uniform(-jitter, jitter)
            lon += random.uniform(-jitter, jitter)
            
            # Intensity fluctuation
            intensity = max(0.1, min(1.0, intensity_base + random.uniform(-0.3, 0.3)))
            points.append([lat, lon, intensity])
            
    # Major Global Coastlines Approximations
    
    # 1. Americas West Coast (Alaska to Chile)
    # High risk in North (Storms) and Central (Hurricanes)
    add_line(60, -140, 30, -120, 40, 0.4)
    add_line(30, -120, 10, -90, 30, 0.7) # Central America (High)
    add_line(10, -90, -50, -75, 60, 0.5)

    # 2. Americas East Coast (Canada to Argentina)
    add_line(50, -60, 25, -80, 40, 0.5) # North Atlantic
    add_line(25, -80, 10, -75, 20, 0.9) # Caribbean (Very High Risk)
    add_line(10, -60, -40, -60, 50, 0.4) 

    # 3. Africa West Coast
    add_line(35, -10, 5, 5, 40, 0.3)
    add_line(5, 5, -34, 18, 50, 0.4)

    # 4. Africa East Coast
    add_line(-34, 25, 12, 50, 50, 0.6) # Cyclone zone

    # 5. Europe/Asia South Coast (Mediterranean -> India -> SE Asia)
    add_line(36, -5, 40, 25, 30, 0.3) # Med
    add_line(25, 60, 10, 75, 20, 0.7) # Arabian Sea
    add_line(10, 75, 20, 90, 20, 0.8) # Bay of Bengal (High)
    add_line(20, 90, 10, 105, 20, 0.7)
    add_line(10, 105, 35, 140, 40, 0.9) # Japan/SE Asia (Pacific Ring - High)

    # 6. Australia
    add_line(-20, 115, -35, 115, 20, 0.4) # West
    add_line(-35, 115, -35, 150, 30, 0.5) # South
    add_line(-35, 150, -10, 140, 30, 0.6) # East
    
    return points

def generate_dynamic_alerts():
    """
    Simulates real-time AI detection of threats.
    Returns a list of alert dictionaries.
    """
    base_threats = [
        {"loc": "Mumbai Coast", "lat": 19.0760, "lon": 72.8777, "type": "Cyclone", "title": "Cyclonic Swell Warning"},
        {"loc": "North Goa", "lat": 15.2993, "lon": 74.1240, "type": "Pollution", "title": "Algal Bloom Alert"},
        {"loc": "Coastal Kerala", "lat": 9.9312, "lon": 76.2673, "type": "Weather", "title": "Heavy Rainfall Advisory"},
        {"loc": "Chennai", "lat": 13.0827, "lon": 80.2707, "type": "Tsunami", "title": "Seismic Activity Alert"},
        {"loc": "Puri", "lat": 19.8135, "lon": 85.8312, "type": "Weather", "title": "High Tide Warning"},
        {"loc": "Gujarat Coast (Surat)", "lat": 21.1702, "lon": 72.8311, "type": "Flood", "title": "Tapi River Surge Alert"},
        {"loc": "Surat Beach (Dumas)", "lat": 21.0688, "lon": 72.7231, "type": "Weather", "title": "High Wind Alert"},
        {"loc": "Andaman", "lat": 11.7401, "lon": 92.6586, "type": "Storm", "title": "Tropical Storm Watch"}
    ]

    alerts_data = []
    # detailed messages
    messages = {
        "Cyclone": "Significant cyclonic activity detected. High waves expected.",
        "Pollution": "Harmful substance detected in water. Avoid contact.",
        "Weather": "Extreme weather conditions forecast for next 24 hours.",
        "Tsunami": "Undersea earthquake detected. Monitor coastal sirens.",
        "Oil Spill": "Satellite imagery confirms oil slick. Containment teams notified.",
        "Storm": "Tropical storm forming. Fishermen return to shore.",
        "Flood": "River levels rising rapidly due to upstream discharge. Evacuate low-lying areas."
    }

    # Randomly select 4-6 threats (increased slightly to ensure Surat likely appears or we can force it)
    active_threats = random.sample(base_threats, k=random.randint(4, 7))

    for t in active_threats:
        # Jitter location slightly
        lat_jitter = t["lat"] + random.uniform(-0.05, 0.05)
        lon_jitter = t["lon"] + random.uniform(-0.05, 0.05)
        
        # Random severity
        severity = random.choice(["High", "Medium", "Low"])
        
        # Simulated Source for "Integrated" feel
        sources = ["Sentinel-1 Satellite", "Coastal Buoy Sensor", "MetDept Radar", "Community Report", "IoT Network"]
        source = random.choice(sources)
        
        alerts_data.append({
            "location": t["loc"],
            "lat": lat_jitter,
            "lon": lon_jitter,
            "title": t["title"],
            "message": messages.get(t["type"], "Anomaly detected."),
            "severity": severity,
            "alert_type": t["type"],
            "source": source
        })
        
    return alerts_data
