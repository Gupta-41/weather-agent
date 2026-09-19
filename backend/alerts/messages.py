"""Alert wording, by language.

Alerts are rendered from templates rather than written by the LLM. A severe
weather warning should say exactly the same thing every time it fires, and it
should still render if the Anthropic API is down — neither is true of a
generated sentence. Languages we haven't translated fall back to English.
"""

from backend.languages import normalize

SEVERITY_LABELS = {
    "en": {"advisory": "Advisory", "watch": "Watch", "warning": "Warning"},
    "hi": {"advisory": "सूचना", "watch": "चेतावनी", "warning": "गंभीर चेतावनी"},
    "te": {"advisory": "సూచన", "watch": "హెచ్చరిక", "warning": "తీవ్ర హెచ్చరిక"},
}

TEMPLATES = {
    "en": {
        "heavy_rain": (
            "Heavy rain expected in {location} on {date}",
            "About {value} {unit} of rain is forecast. Expect waterlogging on low roads and slower travel.",
        ),
        "very_heavy_rain": (
            "Very heavy rain expected in {location} on {date}",
            "About {value} {unit} of rain is forecast. Avoid low-lying areas and underpasses, and keep a charged phone.",
        ),
        "extremely_heavy_rain": (
            "Extremely heavy rain expected in {location} on {date}",
            "About {value} {unit} of rain is forecast. Flooding is likely. Stay indoors and follow local authority instructions.",
        ),
        "heat": (
            "Hot day in {location} on {date}",
            "The high is around {value}{unit}. Drink water often and stay out of direct sun between 11am and 4pm.",
        ),
        "severe_heat": (
            "Severe heat in {location} on {date}",
            "The high is around {value}{unit}. Avoid outdoor work at midday and check on elderly neighbours and outdoor workers.",
        ),
        "cold": (
            "Cold night in {location} on {date}",
            "The low is around {value}{unit}. Keep livestock covered and protect young seedlings.",
        ),
        "severe_cold": (
            "Severe cold in {location} on {date}",
            "The low is around {value}{unit}. Cold wave conditions are likely overnight. Limit early-morning exposure.",
        ),
        "strong_wind": (
            "Strong wind in {location} on {date}",
            "Gusts up to {value} {unit}. Secure loose sheeting, hoardings and rooftop items.",
        ),
        "gale": (
            "Gale-force wind in {location} on {date}",
            "Gusts up to {value} {unit}. Standing crops and temporary structures are at risk. Avoid parking under trees.",
        ),
        "storm_wind": (
            "Storm-force wind in {location} on {date}",
            "Gusts up to {value} {unit}. Stay indoors and away from windows. Expect power interruptions.",
        ),
        "thunderstorm": (
            "Thunderstorm expected in {location} on {date}",
            "Lightning is likely. Move indoors when you hear thunder and stay off open ground and rooftops.",
        ),
        "hailstorm": (
            "Thunderstorm with hail in {location} on {date}",
            "Hail can damage crops, vehicles and roofing. Move vehicles under cover and keep livestock sheltered.",
        ),
    },
    "hi": {
        "heavy_rain": (
            "{date} को {location} में भारी बारिश की संभावना",
            "लगभग {value} {unit} बारिश का अनुमान है। निचली सड़कों पर पानी भर सकता है और यातायात धीमा रहेगा।",
        ),
        "very_heavy_rain": (
            "{date} को {location} में बहुत भारी बारिश की संभावना",
            "लगभग {value} {unit} बारिश का अनुमान है। निचले इलाकों और अंडरपास से बचें और फ़ोन चार्ज रखें।",
        ),
        "extremely_heavy_rain": (
            "{date} को {location} में अत्यधिक भारी बारिश की संभावना",
            "लगभग {value} {unit} बारिश का अनुमान है। बाढ़ की आशंका है। घर के अंदर रहें और प्रशासन के निर्देश मानें।",
        ),
        "heat": (
            "{date} को {location} में गर्म दिन",
            "अधिकतम तापमान लगभग {value}{unit} रहेगा। पानी पीते रहें और सुबह 11 से शाम 4 बजे तक धूप से बचें।",
        ),
        "severe_heat": (
            "{date} को {location} में भीषण गर्मी",
            "अधिकतम तापमान लगभग {value}{unit} रहेगा। दोपहर में बाहर काम न करें और बुज़ुर्गों तथा बाहर काम करने वालों का ध्यान रखें।",
        ),
        "cold": (
            "{date} को {location} में ठंडी रात",
            "न्यूनतम तापमान लगभग {value}{unit} रहेगा। पशुओं को ढककर रखें और छोटे पौधों की रक्षा करें।",
        ),
        "severe_cold": (
            "{date} को {location} में भीषण ठंड",
            "न्यूनतम तापमान लगभग {value}{unit} रहेगा। रात में शीतलहर की आशंका है। सुबह जल्दी बाहर निकलने से बचें।",
        ),
        "strong_wind": (
            "{date} को {location} में तेज़ हवा",
            "हवा की गति {value} {unit} तक। ढीली चादरें, होर्डिंग और छत का सामान बाँधकर रखें।",
        ),
        "gale": (
            "{date} को {location} में आँधी जैसी हवा",
            "हवा की गति {value} {unit} तक। खड़ी फ़सल और अस्थायी ढाँचों को ख़तरा है। पेड़ों के नीचे वाहन न खड़े करें।",
        ),
        "storm_wind": (
            "{date} को {location} में तूफ़ानी हवा",
            "हवा की गति {value} {unit} तक। घर के अंदर और खिड़कियों से दूर रहें। बिजली जा सकती है।",
        ),
        "thunderstorm": (
            "{date} को {location} में आंधी-तूफ़ान की संभावना",
            "बिजली गिरने की आशंका है। गरज सुनते ही अंदर आ जाएँ और खुले मैदान व छतों से दूर रहें।",
        ),
        "hailstorm": (
            "{date} को {location} में ओलावृष्टि के साथ तूफ़ान",
            "ओले फ़सल, वाहन और छत को नुक़सान पहुँचा सकते हैं। वाहन ढककर रखें और पशुओं को आश्रय में रखें।",
        ),
    },
    "te": {
        "heavy_rain": (
            "{date}న {location}లో భారీ వర్షం అవకాశం",
            "సుమారు {value} {unit} వర్షపాతం అంచనా. లోతట్టు రోడ్లపై నీరు నిలిచి ప్రయాణం నెమ్మదిస్తుంది.",
        ),
        "very_heavy_rain": (
            "{date}న {location}లో అతి భారీ వర్షం అవకాశం",
            "సుమారు {value} {unit} వర్షపాతం అంచనా. లోతట్టు ప్రాంతాలు, అండర్‌పాస్‌లను తప్పించుకోండి, ఫోన్ ఛార్జ్‌లో ఉంచుకోండి.",
        ),
        "extremely_heavy_rain": (
            "{date}న {location}లో అత్యధిక భారీ వర్షం అవకాశం",
            "సుమారు {value} {unit} వర్షపాతం అంచనా. వరద ముప్పు ఉంది. ఇంట్లోనే ఉండి అధికారుల సూచనలు పాటించండి.",
        ),
        "heat": (
            "{date}న {location}లో వేడి రోజు",
            "గరిష్ఠ ఉష్ణోగ్రత సుమారు {value}{unit}. తరచూ నీరు తాగండి, ఉదయం 11 నుంచి సాయంత్రం 4 వరకు ఎండలో తిరగవద్దు.",
        ),
        "severe_heat": (
            "{date}న {location}లో తీవ్ర వడగాడ్పులు",
            "గరిష్ఠ ఉష్ణోగ్రత సుమారు {value}{unit}. మధ్యాహ్నం బయట పని చేయవద్దు, వృద్ధులను, బయట పనిచేసేవారిని గమనించండి.",
        ),
        "cold": (
            "{date}న {location}లో చల్లని రాత్రి",
            "కనిష్ఠ ఉష్ణోగ్రత సుమారు {value}{unit}. పశువులను కప్పి ఉంచండి, లేత మొక్కలను కాపాడండి.",
        ),
        "severe_cold": (
            "{date}న {location}లో తీవ్ర చలి",
            "కనిష్ఠ ఉష్ణోగ్రత సుమారు {value}{unit}. రాత్రి చలిగాలుల అవకాశం. తెల్లవారుజామున బయటికి వెళ్లడం తగ్గించండి.",
        ),
        "strong_wind": (
            "{date}న {location}లో బలమైన గాలులు",
            "గాలి వేగం {value} {unit} వరకు. వదులుగా ఉన్న రేకులు, హోర్డింగ్‌లు, పైకప్పు వస్తువులను కట్టి ఉంచండి.",
        ),
        "gale": (
            "{date}న {location}లో పెనుగాలులు",
            "గాలి వేగం {value} {unit} వరకు. నిలువు పంటలకు, తాత్కాలిక నిర్మాణాలకు ముప్పు. చెట్ల కింద వాహనాలు నిలపవద్దు.",
        ),
        "storm_wind": (
            "{date}న {location}లో తుఫాను గాలులు",
            "గాలి వేగం {value} {unit} వరకు. ఇంట్లోనే ఉండి కిటికీలకు దూరంగా ఉండండి. విద్యుత్ అంతరాయం ఉండవచ్చు.",
        ),
        "thunderstorm": (
            "{date}న {location}లో ఉరుములతో కూడిన వర్షం",
            "పిడుగుల ప్రమాదం ఉంది. ఉరుము వినిపించగానే లోపలికి రండి, బయలు ప్రదేశాలు, మిద్దెలపై ఉండవద్దు.",
        ),
        "hailstorm": (
            "{date}న {location}లో వడగళ్ల వాన",
            "వడగళ్లు పంటలకు, వాహనాలకు, పైకప్పులకు నష్టం కలిగిస్తాయి. వాహనాలను నీడలో ఉంచండి, పశువులను లోపల ఉంచండి.",
        ),
    },
}


def render(alert: dict, language: str = "en") -> dict:
    """Add headline, advice and a severity label to an alert, in one language."""
    code = normalize(language)
    strings = TEMPLATES.get(code) or TEMPLATES["en"]
    headline, advice = strings.get(alert["code"]) or TEMPLATES["en"].get(
        alert["code"], ("Weather alert for {location} on {date}", "")
    )

    fields = {
        "location": alert.get("location") or "your saved location",
        "date": alert.get("date") or "",
        "value": alert.get("value"),
        "unit": alert.get("unit") or "",
    }
    labels = SEVERITY_LABELS.get(code) or SEVERITY_LABELS["en"]

    return {
        **alert,
        "language": code,
        "severity_label": labels.get(alert["severity"], alert["severity"]),
        "headline": headline.format(**fields),
        "advice": advice.format(**fields),
    }


def render_all(alerts: list[dict], language: str = "en") -> list[dict]:
    return [render(a, language) for a in alerts]
