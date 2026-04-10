import os
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from base.models import Property, PropertyImage

def populate_property_images():
    # Modern house image URLs from Unsplash
    image_pool = [
        "https://picsum.photos/800/600?random=1",
        "https://picsum.photos/800/600?random=2",
        "https://picsum.photos/800/600?random=3",
        "https://picsum.photos/800/600?random=4",
        "https://picsum.photos/800/600?random=5",
        "https://picsum.photos/800/600?random=6",
        "https://picsum.photos/800/600?random=7",
        "https://picsum.photos/800/600?random=8",
    ]

    properties = Property.objects.all()
    print(f"Found {properties.count()} properties. Starting population...")

    for prop in properties:
        # Check if property already has images to avoid duplicates
        if prop.images.count() >= 3:
            print(f"Skipping {prop.title} (already has gallery)")
            continue

        # Each property gets 3 random images from the pool
        import random
        selected_urls = random.sample(image_pool, 3)

        print(f"Populating gallery for: {prop.title}")
        for i, url in enumerate(selected_urls):
            try:
                # Download image
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    img_temp = NamedTemporaryFile(delete=True)
                    img_temp.write(response.content)
                    img_temp.flush()
                    
                    p_img = PropertyImage(property=prop, order=i+1)
                    p_img.image.save(f"prop_{prop.id}_img_{i}.jpg", File(img_temp), save=True)
                    print(f"  - Added image {i+1}")
                else:
                    print(f"  - Failed to download image {i+1} (Status: {response.status_code})")
            except Exception as e:
                print(f"  - Error on image {i+1}: {e}")

    print("Success! All properties populated.")

if __name__ == "__main__":
    populate_property_images()
