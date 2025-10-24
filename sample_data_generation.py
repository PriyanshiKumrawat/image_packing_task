import os
import random
from PIL import Image, ImageDraw

def generate_sample_images(output_dir="input_images", count=10):
    os.makedirs(output_dir, exist_ok=True)

    for i in range(count):
        # random width and height between 100 and 400 pixels
        w, h = random.randint(100, 400), random.randint(100, 400)

        # create transparent background
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # random color
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            255
        )

        # random shape type
        shape_type = random.choice(["rectangle", "ellipse"])

        if shape_type == "rectangle":
            draw.rectangle(
                [random.randint(0, w//4), random.randint(0, h//4),
                 random.randint(w//2, w), random.randint(h//2, h)],
                fill=color
            )
        else:
            draw.ellipse(
                [random.randint(0, w//4), random.randint(0, h//4),
                 random.randint(w//2, w), random.randint(h//2, h)],
                fill=color
            )

        # save image
        img.save(os.path.join(output_dir, f"sample_{i+1}.png"))

    print(f"✅ Generated {count} sample images in '{output_dir}/'")

if __name__ == "__main__":
    generate_sample_images()
