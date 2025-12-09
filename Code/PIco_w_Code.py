import board 
import busio
import displayio
import terminalio
from digitalio import DigitalInOut, Direction
from adafruit_display_text import label
from fourwire import FourWire
from adafruit_st7789 import ST7789
import time
import keypad  # for matrix keypad

displayio.release_displays()

# ========= DISPLAY SETUP =========
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19)
tft_cs = board.GP17
tft_dc = board.GP16
tft_rst = board.GP20

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = ST7789(display_bus, rotation=270, width=240, height=135, rowstart=40, colstart=53)

# ========= UI =========
splash = displayio.Group()
display.root_group = splash

bg_bitmap = displayio.Bitmap(display.width, display.height, 2)
bg_palette = displayio.Palette(2)
bg_palette[0] = 0x000000  # black
bg_palette[1] = 0x111111  # alternate for flash
bg_tilegrid = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
splash.append(bg_tilegrid)

status_label = label.Label(terminalio.FONT, text="Status: Off", color=0x00FF00)
detect_label = label.Label(terminalio.FONT, text="Detection: Null", color=0x00FF00)
group1 = displayio.Group(scale=2, x=10, y=40)
group2 = displayio.Group(scale=2, x=10, y=80)
group1.append(status_label)
group2.append(detect_label)
splash.append(group1)
splash.append(group2)

motion_bitmap = displayio.Bitmap(display.width, 10, 1)
motion_palette = displayio.Palette(1)
motion_palette[0] = 0x00FF00
motion_tile = displayio.TileGrid(motion_bitmap, pixel_shader=motion_palette, x=0, y=0)
splash.append(motion_tile)
motion_tile.hidden = True

display.refresh()

# ========= SENSOR =========
sensor = DigitalInOut(board.GP21)
sensor.direction = Direction.INPUT
sensor.pull = None  # PIR is inverted, no pull

# ========= UART =========
uart = busio.UART(board.GP0, board.GP1, baudrate=115200, timeout=0.1)

# ========= KEYPAD =========
rows = [board.GP2, board.GP3, board.GP4, board.GP5]
cols = [board.GP6, board.GP7, board.GP8, board.GP9]
key_map = [
    ["1","2","3","A"],
    ["4","5","6","B"],
    ["7","8","9","C"],
    ["*","0","#","D"]
]
flat_keys = [k for row in key_map for k in row]  # flatten for key_number indexing
keypad_matrix = keypad.KeyMatrix(rows, cols, columns_to_anodes=False)

# ========= STATE =========
motion_active = False
sent_sleep = False
last_motion_time = 0
unknown_count = 0
password_mode = False
password_attempts = 0
entered_password = ""
PASSWORD = "220044"
SLEEP_DELAY = 5  # seconds after no motion to send "S"

def set_status_off():
    status_label.text = "Status: Off"
    detect_label.text = "Detection: Null"
    display.refresh()

def set_status_on(name):
    status_label.text = "Status: On"
    detect_label.text = "Detection: " + name
    if name == "Anas":
        status_label.color = 0x1E90FF
        detect_label.color = 0x1E90FF
    elif name == "Marawan":
        status_label.color = 0xFFA500
        detect_label.color = 0xFFA500
    display.refresh()

def show_password_prompt():
    status_label.text = "Enter Password"
    detect_label.text = ""
    display.refresh()

def check_password():
    global entered_password, password_attempts, password_mode
    if entered_password == PASSWORD:
        status_label.text = "Access Granted"
        detect_label.text = ""
        password_mode = False
    else:
        password_attempts += 1
        if password_attempts >= 2:
            status_label.text = "Access Denied"
            detect_label.text = ""
            password_mode = False
        else:
            show_password_prompt()
    entered_password = ""
    display.refresh()

# ========= MAIN LOOP =========
while True:
    now = time.monotonic()

    # ----- MOTION HANDLING (PIR inverted) -----
    if not sensor.value:  # motion detected
        last_motion_time = now
        if not motion_active:
            motion_active = True
            sent_sleep = False
            uart.write(b"M")
            time.sleep(0.05)
            uart.write(b"X")
            motion_tile.hidden = False
        display.refresh()
    else:  # no motion
        motion_tile.hidden = True
        if motion_active and (now - last_motion_time >= SLEEP_DELAY):
            motion_active = False
            if not sent_sleep:
                uart.write(b"S")
                set_status_off()
                sent_sleep = True
        display.refresh()

    # ----- UART FACE DETECTION -----
    data = uart.read(64)
    if data:
        try:
            msg = data.decode('utf-8').strip()
            for c in msg:
                if password_mode:
                    continue  # ignore face detection during password entry
                if c == "A":
                    set_status_on("Anas")
                    unknown_count = 0
                elif c == "M":
                    set_status_on("Marawan")
                    unknown_count = 0
                elif c == "U":
                    unknown_count += 1
                    detect_label.text = "Detection: Unknown"
                    status_label.text = "Status: Off"
                    display.refresh()
                    if unknown_count >= 3:
                        password_mode = True
                        password_attempts = 0
                        entered_password = ""
                        show_password_prompt()
                        unknown_count = 0
        except UnicodeError:
            print("Received non-UTF8 data:", data)

    # ----- KEYPAD PASSWORD ENTRY -----
    if password_mode:
        key_event = keypad_matrix.events.get()
        while key_event:
            if key_event.pressed:
                key = flat_keys[key_event.key_number]
                if key in "0123456789":
                    entered_password += key
                    detect_label.text = "*" * len(entered_password)
                    display.refresh()
                    if len(entered_password) >= len(PASSWORD):
                        check_password()
            key_event = keypad_matrix.events.get()

    time.sleep(0.05)

