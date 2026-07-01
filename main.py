import os
import sys
import csv
from typing import Optional
from datetime import datetime
from tkinter import filedialog
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from CTkTable import *
from PIL import Image

# --- Global Variables ---
names = []
files = []
pairs = []

logs_window: Optional[ctk.CTkToplevel] = None
logs_textbox: Optional[ctk.CTkTextbox] = None

#filepath = 'data.csv'
ctk.set_appearance_mode("dark")
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS #type: ignore
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
# --- Logic Functions ---

def parse_line(line: str):
    reader = csv.reader([line])
    row = next(reader)
    
    if not row or not row[0].strip():
        return None
    if len(row) < 11:
        return None
        
    value = row[0].strip()
    parts = value.split('_')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        name = row[0].strip()
        start_time = row[8].strip()
        duration = row[10].strip()
        try:
            h, m, s = duration.split(":")
            total_duration = int(h) * 3600 + int(m) * 60 + int(s)
        except ValueError:
            return None
        return (name, start_time, total_duration)
    return None
   
def load_names_from_txt(filepath):
    names = []
    failures = []
    try:
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                result = parse_line(line)
                if result:
                    names.append(result)
    except Exception as e:
        failures.append(str(e))
    return names, failures

def extract_datetime_from_filename(filename):
    try:
        parts = filename.split("Time_")
        time_part = parts[1].split("file")[0]
        time_str = time_part.replace("_", ":")
        parts_date = filename.split("Date_")[1].split("Time_")[0]
        d, mo, y = parts_date.split("_")
        h, mi, s = time_str.split(":")
        return datetime(int("20" + y), int(mo), int(d), int(h), int(mi), int(s)).timestamp()
    except (IndexError, ValueError):
        return None

def extract_datetime_from_csv(csv_time):
    try:
        date_part = csv_time.split(" ")[0]
        time_part = csv_time.split(" ")[1]
        d, mo, y = date_part.split("/")
        h, mi, s = time_part.split(":")
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s)).timestamp()
    except (IndexError, ValueError):
        return None


def build_pairs(parsed_entries, files):
    pairs = []
    remaining = []
    for entry in parsed_entries:
        ts = extract_datetime_from_csv(entry[1])
        if ts is not None:
            remaining.append((entry, ts))
    for file in files:
        filename = os.path.basename(file)
        file_seconds = extract_datetime_from_filename(filename)
        if file_seconds is None:
            pairs.append((file, "NO_MATCH_FOUND"))
            continue
        if not remaining:
            pairs.append((file, "NO_MATCH_FOUND"))
            continue
        extension = os.path.splitext(file)[1]

        closest = min(remaining, key=lambda pair: abs(pair[1] - file_seconds))
        entry, ts = closest
        diff = abs(ts - file_seconds)

        if diff > 300:
            file_seconds_12h = file_seconds + 43200
            closest_12h = min(remaining, key=lambda pair: abs(pair[1] - file_seconds_12h))
            entry_12h, ts_12h = closest_12h
            diff_12h = abs(ts_12h - file_seconds_12h)

            if diff_12h <= 300:
                new_filename = entry_12h[0] + extension
                pairs.append((file, new_filename))
                remaining.remove(closest_12h)
                continue
            
            # no match found — check duration
            if entry[2] <= 4:        
                continue
            
            pairs.append((file, "NO_MATCH_FOUND"))
            continue

        new_filename = entry[0] + extension
        pairs.append((file, new_filename))
        remaining.remove(closest)
    return pairs

def validate_pairs(names, files, pairs):
    warnings = []
    valid_pairs = [p for p in pairs if p[1] != "NO_MATCH_FOUND"]
    new_filenames = [p[1] for p in valid_pairs]
    if len(valid_pairs) != len(files) - len([p for p in pairs if p[1] == "NO_MATCH_FOUND"]):
        warnings.append(f"מספר שמות: {len(names)} \n לא תואם למספר הקבצים: {len(files)}")
    if len(new_filenames) != len(set(new_filenames)):
        warnings.append("קבצים כפולים נמצאו")
    for pair in pairs:
        if not os.path.exists(pair[0]):
            warnings.append(f"{pair[0]} does not exist")
    no_matches = [pair[0] for pair in pairs if pair[1] == "NO_MATCH_FOUND"]
    if no_matches:
        warnings.append(f"{len(no_matches)} files had no matching CSV entry")
    return warnings



def execute_rename(pairs):
    successes = []
    failures = []
    for pair in pairs:
        old_path = pair[0]
        new_filename = pair[1]
        folder = os.path.dirname(old_path)
        new_path = os.path.join(folder, new_filename)
        if os.path.exists(new_path):
            failures.append(f"{new_filename} already exists - skipped")
            continue   
        try:
            os.rename(old_path, new_path)
            successes.append(new_filename)
        except Exception as e:
            failures.append(str(e))
    return successes, failures

# --- UI Functions ---

def update_buttons():
    if names and files:
        btn_preview.configure(state="normal")
        btn_rename.configure(state="normal")
        btn_reset.configure(state="normal")
    else:
        btn_preview.configure(state="disabled")
        btn_rename.configure(state="disabled")
        btn_reset.configure(state="disabled")
def load_txt():
    global names
    try:
        filepath = filedialog.askopenfilename(title="Select an TXT file", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filepath:
            names, failures = load_names_from_txt(filepath)
            if failures:
                CTkMessagebox(title="Load Error", message="\n".join(failures), icon="warning")

            update_buttons()
            update_status()
    except Exception as e:
        CTkMessagebox(title="Error", message=f"Something went wrong:\n{e}", icon="cancel")
       # empty_label.configure(text=f"TXT File: {len(names)} names loaded")

def select_files():
    global files
    selected = filedialog.askopenfilenames(title="Select an MP3 files", filetypes=[("Audio Files", "*.mp3"), ("All Files", "*.*")])
    if selected:
        files = list(selected)
        update_buttons()
        update_status()

def update_status():
    txt_status = f"TXT File: {len(names)} names loaded" if names else "TXT File: Not loaded"
    files_status = f"MP3 Files: {len(files)} selected" if files else "MP3 Files: 0 selected"
    print(names)
    ready_status = "✔ Ready to preview" if names and files else "Waiting for input..."

    empty_label.configure(text=f"{txt_status}\n{files_status}\n\n{ready_status}")
    
    

def preview():
    global pairs, table
    try:

        pairs = build_pairs(names, files)

        table_values = [["Original Filename", "New Filename"]]

        for old_path, new_name in pairs:
            table_values.append([os.path.basename(old_path), new_name])

        table.destroy()
        
        empty_label.configure(text="")
        table = CTkTable(
            master=table_container,
            width=15,
            values=table_values,
            colors=["#27435e", "#1d344a"],
            header_color="#4653ab",
            corner_radius=20
        )
        
        table.pack(pady=4, padx=5, fill="both", expand=True)
    except Exception as e:
        CTkMessagebox(title="Error", message=f"Something went wrong:\n{e}", icon="cancel")


    
    
def rename():
    try:
        warnings = validate_pairs(names, files, pairs)
        if warnings:
            print(warnings)
            CTkMessagebox(
        title="Warning",
        message="\n".join(warnings),
        icon="warning"
    )
            return
        successes, failures = execute_rename(pairs)
        if successes:
            CTkMessagebox(
        title="Success",
        message=f"Renamed {len(successes)} files",
        icon="check",
        option_1="Thanks!"
    )
        
        if failures:
            CTkMessagebox(
        title="Rename Errors",
        message="\n".join(failures),
        icon="warning"
    )
        logs_message("=== Rename Failure")
        for failure in failures:
                logs_message(f"[FAILED] {failure}")
        logs_message("==================\n")
        print(successes, failures)

    except Exception as e:
        logs_message(f"[CRITICAL ERROR] Something went wrong: {e}")
        CTkMessagebox(title="Error", message=f"Something went wrong:\n{e}", icon="cancel")


def reset():
    global names, files, pairs, table
    names.clear()
    files.clear()
    pairs.clear()

    
    table.destroy()
    table = CTkTable(master=table_container, width=15, colors=["#25415c", "#1d344a"], values=[[]], corner_radius=12)
    table.pack(pady=14, padx=14, fill="both", expand=True)

    empty_label.configure(text="No files loaded yet\nLoad a TXT file and select files to preview")
    btn_preview.configure(state="disabled")
    btn_rename.configure(state="disabled")
    btn_reset.configure(state="disabled")


def logs_message(message: str):
    global logs_window, logs_textbox

    # 1. אם החלון לא קיים או נסגר על ידי המשתמש - ניצור אותו מחדש כאן
    if logs_window is None or not logs_window.winfo_exists():
        logs_window = ctk.CTkToplevel(app)
        logs_window.title("Console Logs & Errors")
        logs_window.geometry("500x300")
        logs_window.attributes("-topmost", True)

        # יצירת התיבה ישירות בתוך החלון החדש
        logs_textbox = ctk.CTkTextbox(logs_window, width=480, height=280, font=("Consolas", 12))
        logs_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        logs_textbox.configure(state="disabled")
        
        # מכריח את ה-UI להתרענן ולהיבנות פיזית בזיכרון
        logs_window.update()

    # 2. הזרקת הטקסט - מתבצעת רק אחרי שאנחנו בטוחים ב-100% שהרכיב קיים
    if logs_textbox is not None:
        logs_textbox.configure(state="normal")
        logs_textbox.insert("end", message + "\n")
        logs_textbox.configure(state="disabled")
        logs_textbox.see("end")  # גלילה אוטומטית לסוף הטקסט

# --- UI Layout ---

app = ctk.CTk()
app.iconbitmap("police.png")
app.title("JoshRenamer")
app.geometry("1280x720")


app.configure(fg_color="#1c3554")

# רק grid על app
app.grid_columnconfigure(0, weight=0)   # sidebar
app.grid_columnconfigure(1, weight=1)   # main
app.grid_rowconfigure(0, weight=1)

sidebar = ctk.CTkFrame(app, width=180, fg_color="#2c4f70", corner_radius=0)
sidebar.grid(row=0, column=0, sticky="ns")
sidebar.grid_propagate(False)

main = ctk.CTkFrame(app, fg_color="#1c3554")
main.grid(row=0, column=1, sticky="nsew")

your_img_path = resource_path("police.png")

my_image = ctk.CTkImage(
    light_image=Image.open(your_img_path),
    dark_image=Image.open(your_img_path),
    size=(50, 50)
)

# test button for error
def test_error_trigger():
    mock_failures = [
        "קובץ 'photo.jpg' נעול על ידי תוכנה אחרת",
        "אין הרשאות כתיבה לתיקייה C:/Protected",
        "השם החדש מכיל תווים לא חוקיים (?, *, :)"
    ]
    
    logs_message("=== RENAME FAILURES (TEST) ===")
    for failure in mock_failures:
        logs_message(f"[FAILED] {failure}")
    logs_message("=======================\n")

# יצירת כפתור זמני בנאבר להרצת הטסט
btn_test = ctk.CTkButton(sidebar, text="בדיקת שגיאות (Test)", fg_color="red", command=test_error_trigger)
#btn_test.grid(row=5, column=5, sticky="ns")

logo = ctk.CTkLabel(sidebar, image=my_image, text="")
logo.pack(side="top", pady=(18, 14))

btn_load_txt = ctk.CTkButton(sidebar, text="Load TXT File", command=load_txt, width=140, height=38, hover_color="#3a92d9", font=("Arial", 14))
btn_load_txt.pack(padx=20, pady=8)

btn_select_files = ctk.CTkButton(sidebar, text="Select Files", command=select_files, width=140, height=38, hover_color="#3a92d9", font=("Arial", 14))
btn_select_files.pack(padx=20, pady=8)

btn_preview = ctk.CTkButton(sidebar, text="Preview", command=preview, width=140, height=38, hover_color="#3a92d9", font=("Arial", 14))
btn_preview.pack(padx=20, pady=8)
btn_preview.configure(state="disabled")

btn_rename = ctk.CTkButton(sidebar, text="Rename Files", command=rename, width=140, height=40, hover_color="#28b463", font=("Arial", 14, "bold"))
btn_rename.pack(padx=20, pady=(8, 14))
btn_rename.configure(state="disabled")


btn_reset = ctk.CTkButton(sidebar, text="Reset", command=reset, width=140, height=36, fg_color="#b03a48", hover_color="#c44555", font=("Arial", 13,"bold"))
btn_reset.pack(side="bottom", pady=24, padx=20)
btn_rename.configure(state="disabled")

# header בתוך main

btn_logs = ctk.CTkButton(sidebar, text="Logs", command=logs_message("החלון נפתח לבד"))

header = ctk.CTkFrame(main, fg_color="#1c3554")
header.pack(fill="x", padx=10, pady=10)


title = ctk.CTkLabel(header, text="JoshRenamer", font=("Arial", 28, "bold"), text_color="white")
title.pack(anchor="n", padx=16, pady=(12, 4))

steps = ctk.CTkLabel(
    header,
    text="1. Load TXT → 2. Select Files → 3. Preview → 4. Rename",
    font=("Arial", 13),
    text_color="#bfc9d4"
)
steps.pack(anchor="n", padx=16, pady=(0, 12))


# table בתוך table_container
table_container = ctk.CTkScrollableFrame(main, fg_color="#406e9c", corner_radius=14)
table_container.pack(fill="both", expand=True, padx=10, pady=(0, 5))

empty_label = ctk.CTkLabel(
    table_container,
    text="No files loaded yet\nLoad a TXT file and select files to preview",
    font=("Arial", 16),
    text_color="#bfc9d4",
    justify="center"
)
empty_label.pack(anchor="n", padx=16, pady=(12, 6))

table_values = [[]]
table = CTkTable(master=table_container, width=15, colors=["#25415c", "#1d344a"], values=table_values, corner_radius=12)
table.pack(pady=14, padx=14, fill="both", expand=True)



app.mainloop()
