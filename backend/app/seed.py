import os
from urllib.parse import quote_plus
from sqlalchemy import select

from .models import Destination

DATA = [
    (
        "jaipur",
        "Jaipur",
        "Rajasthan",
        "North",
        "The Pink City: forts, palaces and bazaars.",
        "Amer Fort, City Palace and Hawa Mahal sit within a short drive. Evenings suit the old-city bazaars.",
        "Oct–Mar",
        26.9124,
        75.7873,
        ["heritage", "fort", "culture", "food"],
    ),
    (
        "varanasi",
        "Varanasi",
        "Uttar Pradesh",
        "North",
        "Ancient ghats on the Ganga.",
        "Dawn boat rides and the evening Ganga aarti at Dashashwamedh Ghat define a visit.",
        "Oct–Mar",
        25.3176,
        82.9739,
        ["spiritual", "culture", "river"],
    ),
    (
        "leh-ladakh",
        "Leh–Ladakh",
        "Ladakh",
        "North",
        "High-altitude desert, monasteries and passes.",
        "Acclimatise for two days in Leh. Pangong Lake and Nubra Valley are the classic loop.",
        "Jun–Sep",
        34.1526,
        77.5771,
        ["mountain", "trek", "adventure", "monastery"],
    ),
    (
        "munnar",
        "Munnar",
        "Kerala",
        "South",
        "Tea-covered hills in the Western Ghats.",
        "Walk the tea estates, visit Eravikulam National Park and stay in a plantation homestay.",
        "Sep–Mar",
        10.0889,
        77.0595,
        ["hills", "nature", "tea", "wildlife"],
    ),
    (
        "hampi",
        "Hampi",
        "Karnataka",
        "South",
        "Boulder-strewn ruins of Vijayanagara.",
        "Cycle between Virupaksha Temple, Vittala Temple and the Royal Enclosure at sunrise.",
        "Oct–Feb",
        15.335,
        76.46,
        ["heritage", "temple", "culture", "trek"],
    ),
    (
        "goa",
        "Goa",
        "Goa",
        "West",
        "Beaches, Portuguese quarters and nightlife.",
        "North Goa for beach parties, South Goa for quiet shores; Old Goa for churches.",
        "Nov–Feb",
        15.2993,
        74.124,
        ["beach", "food", "nightlife"],
    ),
    (
        "kaziranga",
        "Kaziranga",
        "Assam",
        "Northeast",
        "Home of the one-horned rhinoceros.",
        "Take jeep and elephant-back safaris at first light in the Brahmaputra floodplain.",
        "Nov–Apr",
        26.5775,
        93.1711,
        ["wildlife", "nature", "safari"],
    ),
    (
        "sundarbans",
        "Sundarbans",
        "West Bengal",
        "East",
        "Largest mangrove delta on Earth.",
        "Boat safaris through tidal creeks to spot birds, crocodiles and, with luck, a Bengal tiger.",
        "Oct–Mar",
        21.9497,
        89.1833,
        ["wildlife", "nature", "river", "safari"],
    ),
    (
        "rishikesh",
        "Rishikesh",
        "Uttarakhand",
        "North",
        "Yoga capital and white-water rafting on the Ganga.",
        "Raft the Ganga rapids, join an ashram yoga class, and cross the Laxman Jhula.",
        "Sep–Jun",
        30.0869,
        78.2676,
        ["adventure", "spiritual", "river", "mountain"],
    ),
    (
        "khajuraho",
        "Khajuraho",
        "Madhya Pradesh",
        "Central",
        "UNESCO temples with intricate sculpture.",
        "The Western Group temples are best seen in morning light; the sound-and-light show runs nightly.",
        "Oct–Mar",
        24.8318,
        79.9199,
        ["heritage", "temple", "culture"],
    ),
]

AID = os.getenv("BOOKING_AID", "")  # your Booking.com affiliate id (optional for now)


def stay_link(name: str, state: str) -> str:
    url = f"https://www.booking.com/searchresults.html?ss={quote_plus(f'{name}, {state}, India')}"
    return url + (f"&aid={AID}" if AID else "")


def seed(db):
    # 1) Repair old rows that still have the fake placeholder link.
    #    This MUST run before the early return below.
    old = db.scalars(
        select(Destination).where(Destination.affiliate_url.like("%example.com%"))
    ).all()
    for d in old:
        d.affiliate_url = stay_link(d.name, d.state)
    if old:
        db.commit()

    # 2) Insert the sample places only into an empty database.
    if db.scalar(select(Destination.id).limit(1)):
        return
    for slug, name, state, region, summary, desc, season, lat, lng, tags in DATA:
        db.add(
            Destination(
                slug=slug,
                name=name,
                state=state,
                region=region,
                summary=summary,
                description=desc,
                best_season=season,
                lat=lat,
                lng=lng,
                tags=tags,
                affiliate_url=stay_link(name, state),
            )
        )
    db.commit()
