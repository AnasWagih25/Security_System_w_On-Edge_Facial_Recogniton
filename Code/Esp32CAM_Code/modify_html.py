#!/usr/bin/env python3
"""
Script to decompress HTML from camera_index.h, add auto-update script tag, and recompress it.
"""

import gzip
import re

def extract_gzip_data_from_header(header_file, array_name):
    """Extract gzipped data from C header file array."""
    with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the array definition - match across multiple lines
    pattern = rf'const uint8_t {array_name}\[\] = \{{(.*?)\}};'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Error: Could not find array {array_name} in {header_file}")
        return None
    
    # Extract hex values - match 0x followed by 2 hex digits
    hex_values = re.findall(r'0x([0-9A-Fa-f]{2})', match.group(1))
    if not hex_values:
        print(f"Error: Could not extract hex values from {array_name}")
        return None
    
    # Convert to bytes
    gzip_data = bytes([int(h, 16) for h in hex_values])
    return gzip_data

def decompress_html(gzip_data):
    """Decompress gzipped HTML."""
    try:
        return gzip.decompress(gzip_data)
    except Exception as e:
        print(f"Error decompressing: {e}")
        return None

def add_script_tag(html_content):
    """Add script tag to HTML before </body> or </html>."""
    html_str = html_content.decode('utf-8', errors='ignore')
    script_tag = '<script src="/autoupdate.js"></script>'
    
    # Check if already exists
    if '/autoupdate.js' in html_str:
        print("  Script tag already exists, skipping...")
        return html_content
    
    # Try to insert before </body>
    if '</body>' in html_str:
        html_str = html_str.replace('</body>', f'{script_tag}\n</body>', 1)
        print("  Added script tag before </body>")
    # If no </body>, try before </html>
    elif '</html>' in html_str:
        html_str = html_str.replace('</html>', f'{script_tag}\n</html>', 1)
        print("  Added script tag before </html>")
    # If neither, append at the end
    else:
        html_str = html_str + '\n' + script_tag
        print("  Added script tag at end of file")
    
    return html_str.encode('utf-8')

def compress_html(html_data):
    """Compress HTML to gzip format."""
    return gzip.compress(html_data, compresslevel=9)

def format_as_c_array(data):
    """Format binary data as C array body (just the hex values)."""
    lines = []
    # Write bytes in hex format, 16 per line
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_values = ', '.join([f'0x{b:02X}' for b in chunk])
        if i + 16 < len(data):
            lines.append(f' {hex_values},')
        else:
            lines.append(f' {hex_values}')
    return '\n'.join(lines)

def update_header_file(header_file, array_name, array_len_name, new_data):
    """Update the array in the header file with new data."""
    with open(header_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the array definition - we need to match the entire array including the opening brace
    # Pattern: const uint8_t array_name[] = { ... };
    pattern = rf'(const uint8_t {re.escape(array_name)}\[\] = \{{)(.*?)(\}};)'
    
    def replacer(match):
        # Replace the array body with new hex values
        new_array_body = format_as_c_array(new_data)
        return match.group(1) + '\n' + new_array_body + '\n' + match.group(3)
    
    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    
    if new_content == content:
        print(f"  WARNING: Pattern replacement failed for {array_name}")
        return False
    
    # Update the length define
    len_pattern = rf'#define {re.escape(array_len_name)} \d+'
    new_content = re.sub(len_pattern, f'#define {array_len_name} {len(new_data)}', new_content)
    
    with open(header_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  Updated {array_name} (new size: {len(new_data)} bytes)")
    return True

def verify_script_tag(header_file, array_name):
    """Verify that the script tag was actually added."""
    gzip_data = extract_gzip_data_from_header(header_file, array_name)
    if gzip_data:
        html_data = decompress_html(gzip_data)
        if html_data:
            html_str = html_data.decode('utf-8', errors='ignore')
            if '/autoupdate.js' in html_str:
                print(f"  ✓ Verified: Script tag found in {array_name}")
                return True
            else:
                print(f"  ✗ ERROR: Script tag NOT found in {array_name}")
                return False
    return False

def main():
    header_file = 'camera_index.h'
    
    # Process OV2640 HTML
    print("Processing index_ov2640_html_gz...")
    gzip_data_2640 = extract_gzip_data_from_header(header_file, 'index_ov2640_html_gz')
    if gzip_data_2640:
        print(f"  Extracted {len(gzip_data_2640)} bytes of gzipped data")
        html_data_2640 = decompress_html(gzip_data_2640)
        if html_data_2640:
            print(f"  Decompressed to {len(html_data_2640)} bytes")
            html_data_2640 = add_script_tag(html_data_2640)
            new_gzip_2640 = compress_html(html_data_2640)
            if update_header_file(header_file, 'index_ov2640_html_gz', 'index_ov2640_html_gz_len', new_gzip_2640):
                verify_script_tag(header_file, 'index_ov2640_html_gz')
            print("✓ Updated index_ov2640_html_gz\n")
    
    # Process OV3660 HTML
    print("Processing index_ov3660_html_gz...")
    gzip_data_3660 = extract_gzip_data_from_header(header_file, 'index_ov3660_html_gz')
    if gzip_data_3660:
        print(f"  Extracted {len(gzip_data_3660)} bytes of gzipped data")
        html_data_3660 = decompress_html(gzip_data_3660)
        if html_data_3660:
            print(f"  Decompressed to {len(html_data_3660)} bytes")
            html_data_3660 = add_script_tag(html_data_3660)
            new_gzip_3660 = compress_html(html_data_3660)
            if update_header_file(header_file, 'index_ov3660_html_gz', 'index_ov3660_html_gz_len', new_gzip_3660):
                verify_script_tag(header_file, 'index_ov3660_html_gz')
            print("✓ Updated index_ov3660_html_gz\n")
    
    print("Done! The HTML files have been updated with the auto-update script tag.")
    print("Recompile and upload to your ESP32.")

if __name__ == '__main__':
    main()
