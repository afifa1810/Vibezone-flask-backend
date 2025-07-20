from dotenv import load_dotenv

load_dotenv()
import requests
from flask import Flask, request, jsonify
from deepface import DeepFace
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # Replace with your actual API key

def get_youtube_songs(query, max_total=20):
    songs = []
    search_query = f"{query} trending songs"

    for region in ['IN', 'PK']:
        # Step 1: Search for videos
        search_url = 'https://www.googleapis.com/youtube/v3/search'
        search_params = {
            'part': 'snippet',
            'q': search_query,
            'key': YOUTUBE_API_KEY,
            'type': 'video',
            'maxResults': max_total,
            'regionCode': region
        }

        search_response = requests.get(search_url, params=search_params)
        if search_response.status_code != 200:
            continue

        search_data = search_response.json()
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]

        # Step 2: Filter only music category videos (categoryId = 10)
        if not video_ids:
            continue

        videos_url = 'https://www.googleapis.com/youtube/v3/videos'
        videos_params = {
            'part': 'snippet',
            'id': ','.join(video_ids),
            'key': YOUTUBE_API_KEY
        }

        videos_response = requests.get(videos_url, params=videos_params)
        if videos_response.status_code != 200:
            continue

        videos_data = videos_response.json()
        for item in videos_data.get('items', []):
            if item['snippet'].get('categoryId') == '10':  # Only music videos
                video_id = item['id']
                song_title = item['snippet']['title']
                song_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                songs.append({
                    'title': song_title,
                    'url': song_url,
                    'thumbnail': thumbnail_url
                })

    # Remove duplicates
    seen_urls = set()
    unique_songs = []
    for song in songs:
        if song['url'] not in seen_urls:
            unique_songs.append(song)
            seen_urls.add(song['url'])

    return unique_songs[:max_total]

@app.route('/detect_mood', methods=['POST'])
def detect_mood():
    print("📡 Request received on /detect_mood")

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded in form-data'}), 400

    image = request.files['image']
    print("✅ Image received:", image.filename)

    # Save image
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)
    print("💾 Image saved at:", image_path)

    try:
        print("🔍 Analyzing image with DeepFace...")
        result = DeepFace.analyze(img_path=image_path, actions=['emotion'])
        emotion = result[0]['dominant_emotion']
        print("😊 Detected emotion:", emotion)

        songs = get_youtube_songs(emotion, max_total=15)
        print("🎶 Songs fetched:", len(songs))

        return jsonify({'mood': emotion, 'songs': songs})

    except Exception as e:
        print("❌ DeepFace error:", str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
