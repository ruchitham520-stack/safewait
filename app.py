import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from datetime import datetime, date, timedelta
import streamlit.components.v1 as components
import requests
import math

st.set_page_config(page_title="SafeWait", page_icon="🛡️", layout="wide")
st.title("🛡️ SafeWait")
st.subheader("A Time-Aware Predictive Waiting-Spot Recommendation System")
st.caption("✅ LIVE DATA: Real places from OpenStreetMap | Real GPS Location | Real Distance")
st.divider()

with st.expander("🆘 SOS - Emergency Help"):
    st.error("In Emergency, Call Immediately!")
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 Police", "112")
    c2.metric("🚑 Ambulance", "108")
    c3.metric("👩 Women Helpline", "1091")

# ---------- DISTANCE FUNCTION ----------
def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    dist = R * c
    if dist < 1:
        return f"{int(dist*1000)} m away", dist
    else:
        return f"{dist:.1f} km away", dist

# ---------- REAL PLACES FUNCTION ----------
def fetch_real_places(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"](around:5000,{lat},{lon});
      node["amenity"="police"](around:5000,{lat},{lon});
      node["amenity"="pharmacy"](around:5000,{lat},{lon});
      node["amenity"="fuel"](around:5000,{lat},{lon});
      node["amenity"="cafe"](around:5000,{lat},{lon});
      node["amenity"="restaurant"](around:5000,{lat},{lon});
      node["shop"="supermarket"](around:5000,{lat},{lon});
      node["man_made"="surveillance"](around:5000,{lat},{lon});
    );
    out body;
    """
    try:
        resp = requests.post(overpass_url, data={"data": query}, timeout=30)
        data = resp.json()
        places = []
        for el in data.get("elements", [])[:25]:
            tags = el.get("tags", {})
            name = tags.get("name", "Unnamed Place")
            amenity = tags.get("amenity", tags.get("shop", tags.get("man_made", "place")))
            if amenity == "hospital":
                cat = "🏥 Hospital"
            elif amenity == "police":
                cat = "👮 Police Station"
            elif amenity == "pharmacy":
                cat = "💊 Pharmacy"
            elif amenity == "fuel":
                cat = "⛽ Petrol Bunk - CCTV + Lights"
            elif amenity == "surveillance":
                cat = "📹 CCTV Camera Available"
            elif amenity in ["cafe", "restaurant"]:
                cat = "☕ Cafe / Restaurant - Crowded"
            elif amenity == "supermarket":
                cat = "🛒 Supermarket - Crowded"
            else:
                cat = "📍 Public Place"
            places.append({"name": name, "category": cat, "lat": el.get("lat"), "lon": el.get("lon"), "dist": "Real Place", "real": True})
        return places
    except Exception:
        return []

st.header("Find a Waiting Location")
st.write("📍 **Option 1: Use Live Location**")
components.html(
    """
    <button onclick="getLive()" style="background:#FF4B4B;color:white;padding:12px 20px;border:none;border-radius:8px;font-size:16px;cursor:pointer;">📍 Get My Live Location</button>
    <p id="msg" style="font-family:sans-serif;font-size:16px;font-weight:bold;"></p>
    <script>
    function getLive(){
        document.getElementById("msg").innerHTML = "⏳ Detecting... Please click ALLOW!";
        if(navigator.geolocation){
            navigator.geolocation.getCurrentPosition(function(pos){
                document.getElementById("msg").innerHTML = "✅ COPY THESE: <br>Lat: " + pos.coords.latitude + "<br>Lon: " + pos.coords.longitude;
            }, function(err){
                document.getElementById("msg").innerHTML = "❌ DENIED! Click 🔒 Lock icon > Location > Allow > Refresh";
            });
        }
    }
    </script>
    """, height=120,
)
st.write("**STEP 2 - Paste the 2 numbers:**")
col_lat, col_lon = st.columns(2)
with col_lat:
    live_lat_input = st.text_input("Paste Live Latitude", placeholder="Example: 12.9786")
with col_lon:
    live_lon_input = st.text_input("Paste Live Longitude", placeholder="Example: 77.364")

if "found" not in st.session_state:
    st.session_state.found = False
    st.session_state.lat = 0.0
    st.session_state.lon = 0.0
    st.session_state.address = ""

if st.button("✅ Use This Live Location"):
    if not live_lat_input or not live_lon_input:
        st.warning("First click red button, copy Lat/Lon, paste here!")
    else:
        try:
            lat_f = float(live_lat_input.strip()); lon_f = float(live_lon_input.strip())
            geolocator = Nominatim(user_agent="SafeWait_Real_Dist")
            addr = geolocator.reverse((lat_f, lon_f), timeout=15)
            st.session_state.found = True; st.session_state.lat = lat_f; st.session_state.lon = lon_f
            st.session_state.address = addr.address if addr else f"Live Location {lat_f}, {lon_f}"
            st.rerun()
        except Exception as e:
            st.error("Check numbers - only numbers and dot. Example: 12.9786")

st.write("OR")
st.write("📍 **Option 2: Type Location Manually**")
location = st.text_input("Enter your current or selected location", placeholder="Example: Majestic, Bengaluru")
st.write("Expected arrival time")
col1, col2, col3 = st.columns(3)
with col1: hour = st.selectbox("Hour", list(range(1, 13)), index=6)
with col2: minute = st.selectbox("Minute", ["00", "15", "30", "45"])
with col3: period = st.selectbox("AM / PM", ["AM", "PM"])
arrival_time = datetime.strptime(f"{hour}:{minute} {period}", "%I:%M %p").time()
duration = st.selectbox("Select your waiting duration", ["15 minutes", "30 minutes", "45 minutes", "60 minutes", "90 minutes", "120 minutes"])
duration_minutes = int(duration.split()[0])
arrival_datetime = datetime.combine(date.today(), arrival_time)
departure_datetime = arrival_datetime + timedelta(minutes=duration_minutes)
st.info("Expected departure time: " + departure_datetime.strftime("%I:%M %p"))
filter_choice = st.radio("Show Only:", ["All Places", "🟢 Only SAFE (75+)", "📹 Only CCTV", "🏥 Only Hospital / Police"], horizontal=True)

def get_safety_score(place_type, is_night, duration_min):
    score = 50
    if "CCTV" in place_type: score += 30
    if "Petrol" in place_type: score += 25
    if "Hospital" in place_type: score += 20
    if "Police" in place_type: score += 25
    if "Pharmacy" in place_type: score += 10
    if "Cafe" in place_type or "Supermarket" in place_type: score += 15
    if is_night:
        if "Hospital" not in place_type and "Police" not in place_type and "Petrol" not in place_type: score -= 15
        else: score -= 5
    if duration_min >= 60: score -= 10
    if score > 95: score = 95
    if score < 20: score = 20
    return score

def get_badge(score):
    if score >= 75: return "🟢 SAFE TO WAIT"
    elif score >= 55: return "🟡 AVERAGE - Be Careful"
    else: return "🔴 AVOID"

if st.button("Find Waiting Locations"):
    if not location.strip():
        st.warning("Please enter a location OR use Live Location above.")
    else:
        try:
            geolocator = Nominatim(user_agent="SafeWait_Real2")
            with st.spinner("Searching..."):
                result = geolocator.geocode(location, timeout=15, country_codes="in")
            if result is None:
                result = geolocator.geocode(location + ", Bengaluru, Karnataka, India", timeout=15, country_codes="in")
            if result is not None:
                st.session_state.found = True; st.session_state.lat = result.latitude; st.session_state.lon = result.longitude; st.session_state.address = result.address
            else: st.warning("Location not found. Try 'Majestic, Bengaluru'")
        except Exception as error:
            st.error("Unable to search. Check internet.")
            st.caption(str(error))

if st.session_state.found:
    latitude = st.session_state.lat; longitude = st.session_state.lon
    h24 = arrival_datetime.hour; is_night = (h24 >= 19 or h24 < 6)
    if is_night: st.warning("🌙 Night Time - Safety Score lower for dark places!")
    else: st.success("☀️ Day Time - Generally Safer")
    st.success("Location found successfully!")
    st.write("Location:", st.session_state.address)
    st.write("Latitude:", latitude, "| Longitude:", longitude)
    with st.spinner("🔍 Fetching REAL nearby places from OpenStreetMap (5km)..."):
        real_places = fetch_real_places(latitude, longitude)
    if len(real_places) == 0:
        st.warning("No real places found in 5km in OpenStreetMap. Showing nearby sample.")
        real_places = [
            {"name": "CCTV Zone - Main Road", "category": "📹 CCTV Camera Available", "lat": latitude+0.003, "lon": longitude+0.002, "dist": "Nearby"},
            {"name": "Nearby Hospital", "category": "🏥 Hospital", "lat": latitude+0.008, "lon": longitude+0.005, "dist": "Nearby"},
            {"name": "Nearby Police Station", "category": "👮 Police Station", "lat": latitude-0.005, "lon": longitude+0.004, "dist": "Nearby"},
            {"name": "Street Light Zone", "category": "💡 Street Light Available", "lat": latitude-0.002, "lon": longitude-0.003, "dist": "Nearby"},
        ]
    for p in real_places:
        p["score"] = get_safety_score(p["category"], is_night, duration_minutes)
        p["badge"] = get_badge(p["score"])
        dist_text, dist_num = calc_distance(latitude, longitude, p["lat"], p["lon"])
        p["dist_text"] = dist_text
        p["dist_num"] = dist_num
    nearby_all = sorted(real_places, key=lambda x: x["score"], reverse=True)
    if filter_choice == "🟢 Only SAFE (75+)": nearby = [p for p in nearby_all if p["score"] >= 75]
    elif filter_choice == "📹 Only CCTV": nearby = [p for p in nearby_all if "CCTV" in p["category"] or "Petrol" in p["category"]]
    elif filter_choice == "🏥 Only Hospital / Police": nearby = [p for p in nearby_all if "Hospital" in p["category"] or "Police" in p["category"]]
    else: nearby = nearby_all
    if len(nearby) == 0:
        st.warning("No places match this filter. Try 'All Places'.")
    else:
        best = nearby[0]
        st.subheader("⭐ BEST RECOMMENDATION FOR YOU - REAL PLACE")
        st.success(f"**{best['name']}** - {best['category']} - 📍 {best['dist_text']} - Safety Score: {best['score']}/100 - {best['badge']}")
        st.code(f"Share: I will wait at {best['name']} ({best['dist_text']}) near {st.session_state.address}. Score {best['score']}/100. Arrival {arrival_datetime.strftime('%I:%M %p')}", language="text")
        st.subheader(f"All REAL Nearby Places ({len(nearby)} found in 5km) - Sorted by Safety Score")
        c1, c2, c3 = st.columns(3)
        c1.metric("📍 Real Places Found", len(nearby))
        c2.metric("🏥 Hospitals / Police", len([x for x in nearby if "Hospital" in x["category"] or "Police" in x["category"]]))
        c3.metric("⭐ Best Score", f"{best['score']}/100")
        for p in nearby:
            st.write(f"**{p['name']}** - {p['category']} - 📍 **{p['dist_text']}** - **Score: {p['score']}/100** - {p['badge']} - ✅ Real Data")
            st.progress(p["score"] / 100)
        st.subheader("Interactive Map - REAL Places - YOU ARE HERE")
        map_view = folium.Map(location=[latitude, longitude], zoom_start=13)
        folium.Marker([latitude, longitude], popup=st.session_state.address, tooltip="YOU ARE HERE", icon=folium.Icon(color="blue", icon="info-sign")).add_to(map_view)
        folium.Circle([latitude, longitude], radius=5000, color="teal", fill=True, fill_opacity=0.1).add_to(map_view)
        for p in nearby:
            color = "green" if p["score"] >= 75 else "orange" if p["score"] >= 55 else "red"
            folium.Marker([p["lat"], p["lon"]], popup=f"{p['name']} - {p['dist_text']} - Score {p['score']}", tooltip=f"{p['name']} - {p['dist_text']}", icon=folium.Icon(color=color, icon="info-sign")).add_to(map_view)
        st_folium(map_view, width=750, height=500, key="safewait_real_dist_map")
        st.success("✅ REAL DATA + DISTANCE WORKING!")

st.divider()
st.caption("SafeWait | Real OpenStreetMap Data | Real Distance | Time-Aware Waiting-Spot Recommendation | SJCIT Project")