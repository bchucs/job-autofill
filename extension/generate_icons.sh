#!/bin/bash
# Generate PNG icons from SVG

cd "$(dirname "$0")/icons"

# Check if we have a tool to convert SVG to PNG
if command -v rsvg-convert &> /dev/null; then
    rsvg-convert -w 16 -h 16 icon.svg > icon16.png
    rsvg-convert -w 48 -h 48 icon.svg > icon48.png
    rsvg-convert -w 128 -h 128 icon.svg > icon128.png
    echo "Icons generated using rsvg-convert"
elif command -v convert &> /dev/null; then
    convert -background none -resize 16x16 icon.svg icon16.png
    convert -background none -resize 48x48 icon.svg icon48.png
    convert -background none -resize 128x128 icon.svg icon128.png
    echo "Icons generated using ImageMagick"
elif command -v sips &> /dev/null; then
    # macOS - create simple colored icons
    for size in 16 48 128; do
        sips -z $size $size icon.svg --out icon${size}.png 2>/dev/null || true
    done
    echo "Attempted to generate icons using sips"
else
    echo "No SVG converter found. Creating placeholder icons..."
    # Create simple placeholder PNGs using Python
    python3 << 'EOF'
import struct
import zlib

def create_png(width, height, filename):
    # Simple purple gradient PNG
    def make_pixel(x, y, w, h):
        # Gradient from #667eea to #764ba2
        t = (x + y) / (w + h)
        r = int(102 + (118 - 102) * t)
        g = int(126 + (75 - 126) * t)
        b = int(234 + (162 - 234) * t)
        return bytes([r, g, b, 255])

    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            raw_data += make_pixel(x, y, width, height)

    def png_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)

    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw_data, 9)

    with open(filename, 'wb') as f:
        f.write(signature)
        f.write(png_chunk(b'IHDR', ihdr))
        f.write(png_chunk(b'IDAT', idat))
        f.write(png_chunk(b'IEND', b''))

create_png(16, 16, 'icon16.png')
create_png(48, 48, 'icon48.png')
create_png(128, 128, 'icon128.png')
print("Placeholder icons created")
EOF
fi

echo "Done! Icons are in the icons/ directory"
