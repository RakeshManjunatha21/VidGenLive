import streamlit as st
import time
import json
import os
from openai import OpenAI
import openai
import narration
import images
import video
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

# Load settings from a JSON file
caption_settings = {}
with open("settings.json") as f:
    caption_settings = json.load(f)

# Initialize a unique short ID only once per session
if "short_id" not in st.session_state:
    st.session_state.short_id = str(int(time.time()))
    st.session_state.basedir = os.path.join("shorts", st.session_state.short_id)
    
    # Create a directory for the shorts if it doesn't exist
    if not os.path.exists(st.session_state.basedir):
        os.makedirs(st.session_state.basedir)

# Title and description
st.markdown("<h1 style='text-align: center; color: #2b5876;'>AI-Powered Video Generation for Product Marketing</h1>", unsafe_allow_html=True)

# Sidebar for choosing mode
option = st.sidebar.selectbox("Choose Mode", ("Generate From Script"))

STYLE = ['Informative', 'Formal', 'Humorous or Witty', 'Inspirational', 'Friendly', 'Curious', 'Optimistic',
         'Pessimistic', 'Casual', 'Conversational', 'Thought Leadership']

if "theme_submitted" not in st.session_state:
    st.session_state.theme_submitted = False
if "theme" not in st.session_state:
    st.session_state.theme = ""
if "style" not in st.session_state:
    st.session_state.style = STYLE[0]
if "video_generated" not in st.session_state:
    st.session_state.video_generated = False

# Function to handle "Generate From Script" mode
if option == "Generate From Script":

    # Handle theme input and submission
    if not st.session_state.theme_submitted:
        st.session_state.theme = st.text_input("Enter the script theme for your marketing video", st.session_state.theme)
        st.session_state.style = st.selectbox("Choose Style", STYLE)
        video_length = st.slider("Select Video Length (seconds)", 1, 260, 120)

        if st.button("Set Theme and Style"):
            if st.session_state.theme:
                st.session_state.theme_submitted = True
                # st.experimental_rerun()  # Rerun the app to show editable theme
    else:
        # Once the theme is submitted, display editable theme and allow further editing
        st.markdown("<h3 style='color: #2b5876;'>Editable Script:</h3>", unsafe_allow_html=True)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a YouTube short narration generator. You generate 30 seconds to 1 minute of narration. The shorts you create have a background that fades from image to image as the narration is going on.

        You will need to generate descriptions of images for each of the sentences in the short. They will be passed to an AI image generator. DO NOT IN ANY CIRCUMSTANCES use names of celebrities or people in the image descriptions. It is illegal to generate images of celebrities. Only describe persons without their names. Do not reference any real person or group in the image descriptions. Don't mention the female figure or other sexual content in the images because they are not allowed.

        You are however allowed to use any content, including real names in the narration. Only image descriptions are restricted.

        Note that the narration will be fed into a text-to-speech engine, so don't use special characters.

        Respond with a pair of an image description in square brackets and a narration below it. Both of them should be on their own lines, as follows:

        ###

        [Description of a background image]

        Narrator: "One sentence of narration"

        [Description of a background image]

        Narrator: "One sentence of narration"

        [Description of a background image]

        Narrator: "One sentence of narration"

        ###

        The short should be 6 sentences maximum.

        You should add a description of a fitting background image in between all of the narrations. It will later be used to generate an image with AI.
        """
                },
                {
                    "role": "user",
                    "content": f"Create a YouTube short narration based on the following source material:\n\n{st.session_state.theme} consider the following style while generating: {st.session_state.style}"
                }
            ]
        )

        response_text = response.choices[0].message.content
        response_text = response_text.replace("’", "'").replace("`", "'").replace("…", "...").replace("“", '"').replace("”", '"')

        # editable_theme = st.text_area("Edit script: ", response_text)
        editable_theme = st.text_area("Edit script: ", response_text, height=300)

        # Submit edited theme button
        if st.button("Submit Edited Script"):
            status_text = st.empty()
            with open(os.path.join(st.session_state.basedir, "response.txt"), "w") as f:
                f.write(editable_theme)  # Save the edited theme
            
            data, narrations = narration.parse(editable_theme)
            with open(os.path.join(st.session_state.basedir, "data.json"), "w") as f:
                json.dump(data, f, ensure_ascii=False)
            
            with st.spinner('Generating narration...'):
                narration.create(data, os.path.join(st.session_state.basedir, "narrations"))

            with st.spinner('Generating images...'):
                images.create_from_data(data, os.path.join(st.session_state.basedir, "images"))

            image_dir = os.path.join(st.session_state.basedir   , "images")
            if os.path.exists(image_dir):
                image_files = os.listdir(image_dir)
                cols = st.columns(3)  # Create 3 columns to display images side by side
                for idx, image_file in enumerate(image_files):
                    image_path = os.path.join(image_dir, image_file)
                    img = Image.open(image_path)
                    cols[idx % 3].image(img, caption=image_file)

            with st.spinner('Generating video...'):
                video.create(narrations, st.session_state.basedir, "short.avi", caption_settings)
                
            st.text(f"DONE! Here's your video:")
            st.video(os.path.join(st.session_state.basedir, "with_narration.mp4"))
    
elif option == "Generate From Images":
    # Initialize session states for theme and submission
    if "theme_submitted" not in st.session_state:
        st.session_state.theme_submitted = False
    if "theme" not in st.session_state:
        st.session_state.theme = ""

    uploaded_files = st.file_uploader("Upload Images for Video", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)
    if uploaded_files:
        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            image_path = os.path.join(st.session_state.basedir, "images")
            os.makedirs(image_path, exist_ok=True)
            # Open the image file
            image = Image.open(uploaded_file)         
            # Set the new file name
            new_filename = f"image_{idx}.webp"         
            # Define the full path to save the image
            save_path = os.path.join(image_path, new_filename)           
            # Save the image
            image.save(save_path)

    # Handle theme input and submission
    if not st.session_state.theme_submitted:
        # Text input for theme
        st.session_state.theme = st.text_input("Enter the script theme for your marketing video", st.session_state.theme)
        st.session_state.style = st.selectbox("Choose Style", STYLE)
        video_length = st.slider("Select Video Length (seconds)", 1, 260, 120)

        if st.button("Set Theme and Style"):
            if st.session_state.theme:
                st.session_state.theme_submitted = True
                # st.experimental_rerun()  # Rerun the app to show editable theme
    else:
        # Once the theme is submitted, display editable theme and allow further editing
        st.write("Editable Script:")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a YouTube short narration generator. You generate 30 seconds to 1 minute of narration. The shorts you create have a background that fades from image to image as the narration is going on.

        You will need to generate descriptions of images for each of the sentences in the short. They will be passed to an AI image generator. DO NOT IN ANY CIRCUMSTANCES use names of celebrities or people in the image descriptions. It is illegal to generate images of celebrities. Only describe persons without their names. Do not reference any real person or group in the image descriptions. Don't mention the female figure or other sexual content in the images because they are not allowed.

        You are however allowed to use any content, including real names in the narration. Only image descriptions are restricted.

        Note that the narration will be fed into a text-to-speech engine, so don't use special characters.

        Respond with a pair of an image description in square brackets and a narration below it. Both of them should be on their own lines, as follows:

        ###

        [Description of a background image]

        Narrator: "One sentence of narration"

        [Description of a background image]

        Narrator: "One sentence of narration"

        [Description of a background image]

        Narrator: "One sentence of narration"

        ###

        The short should be 6 sentences maximum.

        You should add a description of a fitting background image in between all of the narrations. It will later be used to generate an image with AI.
        """
                },
                {
                    "role": "user",
                    "content": f"Create a YouTube short narration based on the following source material:\n\n{st.session_state.theme} consider the following style while generating: {st.session_state.style}"
                }
            ]
        )

        response_text = response.choices[0].message.content
        response_text = response_text.replace("’", "'").replace("`", "'").replace("…", "...").replace("“", '"').replace("”", '"')

        editable_theme = st.text_area("Edit script: ", response_text)

        # Submit edited theme button
        if st.button("Submit Edited Theme"):
            status_text = st.empty()
            with open(os.path.join(st.session_state.basedir, "response.txt"), "w") as f:
                f.write(editable_theme) 
            
            data, narrations = narration.parse(editable_theme)
            with open(os.path.join(st.session_state.basedir, "data.json"), "w") as f:
                json.dump(data, f, ensure_ascii=False)
            
            with st.spinner('Generating narration...'):
                narration.create(data, os.path.join(st.session_state.basedir, "narrations"))

            # with st.spinner('Generating images...'):
            #     images.create_from_data(data, os.path.join(st.session_state.basedir, "images"))

            with st.spinner('Displaying Uploaded images...'):
                # Display images from 'shorts' folder
                image_dir = os.path.join(st.session_state.basedir, "images")
                if os.path.exists(image_dir):
                    cols = st.columns(3)  # Create 3 columns to display images side by side
                    for idx, image_file in enumerate(os.listdir(image_dir)):
                        image_path = os.path.join(image_dir, image_file)
                        img = Image.open(image_path)
                        cols[idx % 3].image(img, caption=image_file)

            with st.spinner('Generating video...'):
                video.create(narrations, st.session_state.basedir, "short.avi", caption_settings)
                
            st.text(f"DONE! Here's your video:")
            st.video(os.path.join(st.session_state.basedir, "with_narration.mp4"))
