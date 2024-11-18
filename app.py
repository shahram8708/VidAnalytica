from flask import Flask, render_template, request, jsonify
import os
import moviepy.editor as mp
import speech_recognition as sr
import requests
import logging
import markdown

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=API_Key"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = os.path.join('uploads', file.filename)
    file.save(filename)

    video = mp.VideoFileClip(filename)
    audio_path = os.path.join('uploads', 'audio.wav')
    video.audio.write_audiofile(audio_path)

    text = transcribe_audio(audio_path)

    custom_input = request.form.get('customInput', '')
    gemini_response = generate_story(text, custom_input)
    
    if gemini_response and 'candidates' in gemini_response:
        story_content = extract_story_content(gemini_response)
        if story_content:
            markdown_content = markdown.markdown(story_content)
            return jsonify({'summary': markdown_content})

    return jsonify({'error': 'Failed to generate response. Please try again.'}), 500

def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)

    with audio_file as source:
        audio = recognizer.record(source)
    
    try:
        transcript = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        transcript = "Could not understand the audio"
    except sr.RequestError as e:
        transcript = f"Could not request results; {e}"

    return transcript

def generate_story(text, custom_input):
    prompt = f"{custom_input} {text}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    response = requests.post(API_ENDPOINT, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def extract_story_content(response):
    candidates = response.get('candidates', [])
    if candidates:
        content = candidates[0].get('content', {})
        if content:
            parts = content.get('parts', [])
            if parts:
                return parts[0].get('text', '')
    return None

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)
