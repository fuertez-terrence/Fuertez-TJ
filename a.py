import pygame
import json
import os
import sys
from collections import deque
from datetime import datetime

pygame.init()

WIDTH, HEIGHT = 1100, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Campus Lost-and-Found Management System")

WHITE = (255, 255, 255)
BG = (241, 245, 249)
NAVY = (30, 58, 138)
BLUE = (37, 99, 235)
GREEN = (5, 150, 105)
RED = (220, 38, 38)
PURPLE = (124, 58, 237)
DARK = (30, 41, 59)
GRAY = (100, 116, 139)
LIGHT = (226, 232, 240)

font = pygame.font.SysFont("arial", 17)
small_font = pygame.font.SysFont("arial", 14)
title_font = pygame.font.SysFont("arial", 27, bold=True)
big_font = pygame.font.SysFont("arial", 28, bold=True)

DATA_FILE = "items.json"


class LostAndFoundSystem:

    def __init__(self):
        self.items = {}
        self.claim_queue = deque()
        self.next_id = 1
        self.load_data()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            self.save_data()
            return

        try:
            with open(DATA_FILE, "r") as file:
                data = json.load(file)

            self.items = data.get("items", {})
            self.claim_queue = deque(data.get("claims", []))
            self.next_id = data.get("next_id", 1)

        except (json.JSONDecodeError, OSError, TypeError):
            self.items = {}
            self.claim_queue = deque()
            self.next_id = 1

    def save_data(self):
        data = {
            "items": self.items,
            "claims": list(self.claim_queue),
            "next_id": self.next_id
        }

        with open(DATA_FILE, "w") as file:
            json.dump(data, file, indent=4)

    def add_item(self, name, location, kind):
        if not name.strip() or not location.strip():
            raise ValueError("Complete all fields.")

        if kind not in ("Lost", "Found"):
            raise ValueError("Invalid item type.")

        item_id = f"IT{self.next_id:04d}"

        self.items[item_id] = {
            "item_id": item_id,
            "name": name.strip(),
            "location": location.strip(),
            "report_type": kind,
            "status": kind,
            "date_reported": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        self.next_id += 1
        self.save_data()
        return item_id

    def search_item(self, keyword):
        keyword = keyword.lower().strip()

        if not keyword:
            return []

        results = []

        for item_id, item in self.items.items():
            values = [
                item_id,
                item["name"],
                item["location"],
                item["status"]
            ]

            if any(keyword in str(value).lower() for value in values):
                results.append(item)

        return results

    def get_items(self, sorted_items=False):
        records = list(self.items.values())

        if sorted_items:
            records.sort(key=lambda x: x["name"].lower())

        return records

    def submit_claim(self, item_id, claimant, contact):
        if item_id not in self.items:
            raise ValueError("Item not found.")

        if not claimant.strip() or not contact.strip():
            raise ValueError("Complete claimant details.")

        if self.items[item_id]["status"] != "Found":
            raise ValueError("Item is not available.")

        if any(c["item_id"] == item_id for c in self.claim_queue):
            raise ValueError("Claim already pending.")

        self.claim_queue.append({
            "item_id": item_id,
            "claimant": claimant,
            "contact": contact,
            "date_submitted": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        self.save_data()

    def process_claim(self):
        if not self.claim_queue:
            return "No pending claims."

        claim = self.claim_queue.popleft()
        item_id = claim["item_id"]

        if item_id not in self.items:
            self.save_data()
            return "Item no longer exists."

        item = self.items[item_id]

        if item["status"] != "Found":
            self.save_data()
            return "Item is unavailable."

        item["status"] = "Claimed"
        item["claimed_by"] = claim["claimant"]
        item["claim_contact"] = claim["contact"]

        self.save_data()

        return "Claim approved: " + claim["claimant"]

    def delete_item(self, item_id):
        if item_id not in self.items:
            return False

        del self.items[item_id]

        self.claim_queue = deque(
            c for c in self.claim_queue
            if c["item_id"] != item_id
        )

        self.save_data()
        return True


system = LostAndFoundSystem()

buttons = []
inputs = {}
input_values = {}
active_input = None
page = "Dashboard"
search_text = ""
notification = ""
sorted_mode = False
scroll = 0
selected_item = None


def draw_text(text, x, y, color=DARK, font_obj=font):
    image = font_obj.render(str(text), True, color)
    screen.blit(image, (x, y))


def button(text, x, y, w, h, color, action):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, color, rect, border_radius=7)
    draw_text(text, x + 12, y + 11, WHITE, small_font)
    buttons.append((rect, action))


def input_box(key, label, x, y, w=400):
    draw_text(label, x, y, DARK, small_font)
    rect = pygame.Rect(x, y + 23, w, 39)

    pygame.draw.rect(screen, WHITE, rect, border_radius=5)
    pygame.draw.rect(screen, LIGHT, rect, 1, border_radius=5)

    value = input_values.get(key, "")
    draw_text(value, x + 10, y + 32, DARK, small_font)

    inputs[key] = rect


def header():
    pygame.draw.rect(screen, NAVY, (0, 0, WIDTH, 85))
    draw_text("CAMPUS LOST-AND-FOUND", 25, 17, WHITE, title_font)
    draw_text("Item and Claim Management System", 28, 52,
              (219, 234, 254), small_font)


def sidebar():
    pygame.draw.rect(screen, WHITE, (0, 85, 205, HEIGHT - 85))

    menu = [
        ("Dashboard", "Dashboard"),
        ("Report Item", "Report"),
        ("Search Items", "Search"),
        ("Manage Items", "Manage"),
        ("Claims", "Claims")
    ]

    for i, (label, target) in enumerate(menu):
        color = BLUE if page == target else DARK
        button(label, 15, 120 + i * 60, 175, 43, color,
               lambda p=target: change_page(p))


def change_page(target):
    global page, input_values, search_text, scroll, active_input
    page = target
    input_values = {}
    search_text = ""
    scroll = 0
    active_input = None


def dashboard():
    draw_text("Dashboard Overview", 235, 115, DARK, title_font)

    items = list(system.items.values())

    stats = [
        ("Total Items", len(items), BLUE),
        ("Found Items", sum(i["status"] == "Found" for i in items), GREEN),
        ("Lost Items", sum(i["status"] == "Lost" for i in items), RED),
        ("Pending Claims", len(system.claim_queue), PURPLE)
    ]

    for i, (label, value, color) in enumerate(stats):
        x = 235 + i * 205
        rect = pygame.Rect(x, 170, 185, 115)
        pygame.draw.rect(screen, WHITE, rect, border_radius=10)
        draw_text(label, x + 15, 188, GRAY, small_font)
        draw_text(value, x + 15, 220, color, big_font)

    draw_text("Recent Registered Items", 235, 325, DARK, title_font)

    draw_table(system.get_items()[-7:], 355)


def report_page():
    draw_text("Report Lost or Found Item", 235, 115, DARK, title_font)

    fields = [
        ("name", "Item Name"),
        ("location", "Location")
    ]

    for i, (key, label) in enumerate(fields):
        input_box(key, label, 250, 180 + i * 100)

    draw_text("Report Type", 250, 415, DARK, small_font)

    button("LOST", 250, 440, 110, 40, RED,
           lambda: save_item("Lost"))

    button("FOUND", 375, 440, 110, 40, GREEN,
           lambda: save_item("Found"))


def save_item(kind):
    global notification

    try:
        item_id = system.add_item(
            input_values.get("name", ""),
            input_values.get("location", ""),
            kind
        )

        notification = "Item saved successfully: " + item_id
        change_page("Manage")

    except ValueError as error:
        notification = str(error)


def search_page():
    global search_text

    draw_text("Search Items", 235, 115, DARK, title_font)

    input_box("search", "Search by ID, name or location",
              250, 160, 440)

    button("SEARCH", 710, 183, 110, 40, BLUE,
           perform_search)

    button("SHOW ALL", 835, 183, 110, 40, GRAY,
           lambda: change_page("Manage"))

    if search_text:
        draw_table(system.search_item(search_text), 255)


def perform_search():
    global search_text, notification

    search_text = input_values.get("search", "").strip()

    if not search_text:
        notification = "Enter a search keyword."
    elif not system.search_item(search_text):
        notification = "No matching items found."


def draw_table(records, start_y):
    headers = ["ID", "NAME", "LOCATION", "STATUS"]

    x_positions = [240, 370, 600, 830]

    for x, label in zip(x_positions, headers):
        draw_text(label, x, start_y, GRAY, small_font)

    pygame.draw.line(screen, LIGHT,
                     (235, start_y + 27), (1050, start_y + 27), 2)

    for i, item in enumerate(records):
        y = start_y + 42 + i * 42

        pygame.draw.rect(
            screen,
            WHITE,
            (235, y - 5, 830, 35),
            border_radius=4
        )

        values = [
            item["item_id"],
            item["name"][:22],
            item["location"][:25],
            item["status"]
        ]

        for x, value in zip(x_positions, values):
            color = GREEN if value == "Found" else (
                RED if value == "Lost" else DARK
            )
            draw_text(value, x, y, color, small_font)

        rect = pygame.Rect(235, y - 5, 830, 35)
        buttons.append((rect, lambda item_id=item["item_id"]:
                        select_item(item_id)))


def select_item(item_id):
    global selected_item, notification
    selected_item = item_id
    notification = "Selected: " + item_id


def manage_page():
    global sorted_mode

    draw_text("Manage Items", 235, 115, DARK, title_font)

    button("SORT A-Z", 235, 165, 110, 40, GREEN,
           sort_items)

    button("DELETE SELECTED", 360, 165, 160, 40, RED,
           delete_selected)

    button("REFRESH", 535, 165, 110, 40, BLUE,
           lambda: change_page("Manage"))

    draw_text("Click an item row to select it.", 665, 180,
              GRAY, small_font)

    draw_table(system.get_items(sorted_mode), 230)


def sort_items():
    global sorted_mode, notification
    sorted_mode = not sorted_mode
    notification = "Items sorted alphabetically."


def delete_selected():
    global notification

    if not selected_item:
        notification = "Select an item first."
        return

    if system.delete_item(selected_item):
        notification = "Item deleted."
    else:
        notification = "Item not found."

    change_page("Manage")


def claims_page():
    draw_text("Claim Management", 235, 115, DARK, title_font)

    button("SUBMIT CLAIM", 235, 165, 140, 42, GREEN,
           lambda: change_page("Submit"))

    button("PROCESS NEXT", 390, 165, 145, 42, PURPLE,
           process_claim)

    draw_text("Pending Requests (FIFO)", 235, 235,
              DARK, title_font)

    claims = list(system.claim_queue)

    for i, claim in enumerate(claims):
        y = 285 + i * 48

        pygame.draw.rect(
            screen,
            WHITE,
            (235, y, 800, 38),
            border_radius=5
        )

        draw_text(
            f"{i + 1}. {claim['item_id']} - "
            f"{claim['claimant']} - {claim['contact']}",
            250, y + 10, DARK, small_font
        )

    if not claims:
        draw_text("No pending claims.", 250, 290, GRAY)


def submit_page():
    draw_text("Submit Claim Request", 235, 115,
              DARK, title_font)

    fields = [
        ("item_id", "Item ID"),
        ("claimant", "Claimant Name"),
        ("contact", "Contact Information")
    ]

    for i, (key, label) in enumerate(fields):
        input_box(key, label, 250, 180 + i * 100)

    button("SUBMIT REQUEST", 250, 510, 180, 45,
           GREEN, submit_claim)

    button("BACK", 450, 510, 110, 45,
           GRAY, lambda: change_page("Claims"))


def submit_claim():
    global notification

    try:
        system.submit_claim(
            input_values.get("item_id", "").strip().upper(),
            input_values.get("claimant", ""),
            input_values.get("contact", "")
        )

        notification = "Claim request added to queue."
        change_page("Claims")

    except ValueError as error:
        notification = str(error)


def process_claim():
    global notification
    notification = system.process_claim()


def draw_notification():
    if notification:
        pygame.draw.rect(screen, NAVY, (225, 655, 850, 42),
                         border_radius=5)
        draw_text(notification[:100], 240, 668,
                  WHITE, small_font)


def draw():
    global buttons, inputs

    screen.fill(BG)
    buttons = []
    inputs = {}

    header()
    sidebar()

    if page == "Dashboard":
        dashboard()
    elif page == "Report":
        report_page()
    elif page == "Search":
        search_page()
    elif page == "Manage":
        manage_page()
    elif page == "Claims":
        claims_page()
    elif page == "Submit":
        submit_page()

    draw_notification()

    pygame.display.flip()


running = True
clock = pygame.time.Clock()

while running:
    draw()

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            system.save_data()
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                active_input = None

                for key, rect in inputs.items():
                    if rect.collidepoint(event.pos):
                        active_input = key
                        break

                for rect, action in reversed(buttons):
                    if rect.collidepoint(event.pos):
                        action()
                        break

        elif event.type == pygame.KEYDOWN:
            if active_input:
                if event.key == pygame.K_BACKSPACE:
                    input_values[active_input] = input_values.get(
                        active_input, ""
                    )[:-1]

                elif event.key == pygame.K_RETURN:
                    active_input = None

                elif event.unicode.isprintable():
                    input_values[active_input] = (
                        input_values.get(active_input, "")
                        + event.unicode
                    )

    clock.tick(30)

pygame.quit()
sys.exit()