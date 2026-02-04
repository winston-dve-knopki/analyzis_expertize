import os
import requests
import base64

url = "https://api.eliza.yandex.net/openai/v1/chat/completions"

with open('image.png', 'rb') as f:
    encoded_image = base64.b64encode(f.read())

payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Что изображено на картинке?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                    }
                }
            ]
        }
    ]
}

headers = {
    "authorization": f"OAuth {os.getenv('ELIZA_TOKEN')}",
    "content-type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())