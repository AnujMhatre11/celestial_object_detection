# ui.py

import streamlit as st
import requests
import base64
import threading
from io import BytesIO
import av  # Required for frame processing
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Celestial Body Scanner")

# --- Thread-Safe Image Container ---
# A lock is needed to safely share the captured frame between the
# webrtc thread and the main streamlit thread.
lock = threading.Lock()
img_container = {"img": None}

# --- Video Processor Class ---
# This class processes frames from the webcam stream.
class PhotoProcessor:
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # Convert the video frame to a PIL Image and store it
        img = frame.to_image()
        with lock:
            img_container["img"] = img
        return frame

# --- Initialize Session State & Callbacks ---
if 'scan_complete' not in st.session_state:
    st.session_state.scan_complete = False
if 'celestial_bodies' not in st.session_state:
    st.session_state.celestial_bodies = []
if 'planet_details' not in st.session_state:
    st.session_state.planet_details = None

def reset_scan():
    st.session_state.scan_complete = False
    st.session_state.celestial_bodies = []
    st.session_state.planet_details = None

# --- UI elements ---
st.title("🪐 Celestial Body Scanner")
st.markdown("Use your camera or upload a photo of a textbook page. I'll identify the celestial bodies, and then you can select one to learn more about it!")

# Define the API endpoints
API_URL_SCAN = "http://127.0.0.1:5000/scan_celestial_body"
API_URL_DETAILS = "http://127.0.0.1:5000/get_planet_details"

# --- Function to process and scan the image ---
def process_and_scan(image_input):
    """Takes a file-like object, sends it to the API, and updates state."""
    with st.spinner("Scanning for celestial bodies... 🔭"):
        try:
            image_bytes = image_input.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            payload = {"imageData": base64_image}
            response = requests.post(API_URL_SCAN, json=payload, timeout=30)

            if response.status_code == 200:
                st.session_state.celestial_bodies = response.json().get("celestial_bodies", [])
                st.session_state.scan_complete = True
            else:
                st.error(f"API Error ({response.status_code}): {response.json().get('error')}")

        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not connect to the API server. Is the Flask app running?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
    st.rerun()

# --- Image Input Tabs ---
tab1, tab2 = st.tabs(["📁 Upload a Photo", "📸 Use Camera"])

with tab1:
    uploaded_image = st.file_uploader(
        "Select a photo from your device",
        type=["png", "jpg", "jpeg"],
        on_change=reset_scan
    )
    if uploaded_image:
        process_and_scan(uploaded_image)

with tab2:
    st.write("Select your camera from the dropdown below and click 'Take Photo'.")
    webrtc_ctx = webrtc_streamer(
        key="camera-select",
        mode=WebRtcMode.SENDONLY,
        video_processor_factory=PhotoProcessor,
        media_stream_constraints={"video": True, "audio": False}, # Ask for video
        async_processing=True,
    )

    if webrtc_ctx.video_processor:
        if st.button("Take Photo"):
            with lock:
                captured_image = img_container["img"]
            
            if captured_image is not None:
                # Convert PIL Image to a file-like bytes object
                buffer = BytesIO()
                captured_image.save(buffer, format="JPEG")
                buffer.seek(0)
                
                reset_scan()
                process_and_scan(buffer)
            else:
                st.warning("No image captured yet. Please wait a moment for the video to start.")

# --- Display Results and Fetch Details ---
if st.session_state.scan_complete:
    # This part of the logic remains unchanged
    if st.session_state.celestial_bodies:
        st.success(f"Scan Complete! Found: {', '.join(st.session_state.celestial_bodies)}")
        selected_planet = st.selectbox(
            "Select a celestial body to learn more:",
            options=[""] + st.session_state.celestial_bodies,
            format_func=lambda x: "Choose an option" if x == "" else x
        )
        if selected_planet:
            with st.spinner(f"Fetching details for {selected_planet}..."):
                # Fetching details logic here...
                try:
                    payload = {"planet_name": selected_planet}
                    response = requests.post(API_URL_DETAILS, json=payload, timeout=20)
                    if response.status_code == 200:
                        st.session_state.planet_details = response.json()
                    else:
                        st.error(f"API Error ({response.status_code}): {response.json().get('error')}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
    else:
        st.info("No celestial bodies were identified in the image.")

    if st.session_state.planet_details:
        details = st.session_state.planet_details
        if details.get('name') == selected_planet:
            st.markdown("---")
            st.header(f"✨ Information about {details.get('name')}")
            st.write(details.get('summary'))
            st.subheader("Data for AR/VR Simulation")
            col1, col2, col3 = st.columns(3)
            col1.metric("Mass (kg)", value=details.get('mass_kg', 'N/A'))
            col2.metric("Mean Radius (km)", value=details.get('radius_km', 'N/A'))
            col3.metric("Axial Rotation", value=details.get('rotation_direction', 'N/A'))

    if st.button("Start Over"):
        reset_scan()
        st.rerun()