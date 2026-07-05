import os
import sys
import csv
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from CTkTable import CTkTable
from PIL import Image

MATCH_TOLERANCE = 300      # max seconds between a csv entry and a file timestamp
HALF_DAY = 43200           # 12hour clock, so PM files 12h off
NO_MATCH = "NO_MATCH_FOUND"

HELP_STEPS = [
    (" TXT לפתוח את הקובץ ", "תלחץ 'לטעון קובץ טקסט' ותבחר את הקובץ דאטא שהורדת מהמערכת, " "\nהסטטוס למטה מראה כמה קבצים יש בקובץ טקסט", "help_load_txt.png"),
    ("תבחר את ההקלטות ", "תלחץ 'בחר קבצים' ותבחר את הקבצי שמע שאתה רוצה לשנות את שמם" "\nאתה יכול לבחור כמה קבצים במקביל", "help_select_files.png"),
    ("סקירה של ההשוואות", "תלחץ 'הצג השוואות' בשביל לראות איזה שם יקבל כל קובץ\n" "שורות שבצבע אדום לא נמצא מקביל אליהן בטבלה והתוכנה תדלג עליהן\n", "help_preview.png"),
    ("Rename", "תלחץ שנה שם של הקבצים ולאחר מכן אישור, אם משהו לא עובר נכון\n" " אתה תראה את השגיאה", "help_rename.png"),
]
ctk.set_appearance_mode("dark")
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def parse_line(line: str):
    reader = csv.reader([line])
    row = next(reader, None)
    if not row or not row[0].strip() or len(row) < 11:
        return None
    name = row[0].strip()
    parts = name.split("_")
    if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit()):
        return None
    start_time = row[8].strip()
    try:
        h, m, s = row[10].strip().split(":")
        duration = int(h) * 3600 + int(m) * 60 + int(s)
    except ValueError:
        return None
    return (name, start_time, duration)

def load_names_from_txt(filepath):
    entries = []
    failures = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                parsed = parse_line(line)
                if parsed:
                    entries.append(parsed)
    except Exception as e:
        failures.append(str(e))
    return entries, failures

def extract_datetime_from_filename(filename):
    try:
        time_part = filename.split("Time_")[1].split("file")[0]
        h, mi, s = time_part.replace("_", ":").split(":")
        date_part = filename.split("Date_")[1].split("Time_")[0]
        d, mo, y = date_part.split("_")
        return datetime(int("20" + y), int(mo), int(d), int(h), int(mi), int(s)).timestamp()
    except (IndexError, ValueError):
        return None

def extract_datetime_from_csv(csv_time):
    #CSV times look like 'DD/MM/YYYY HH:MM:SS'.
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
        file_seconds = extract_datetime_from_filename(os.path.basename(file))
        if file_seconds is None or not remaining:
            pairs.append((file, NO_MATCH))
            continue

        extension = os.path.splitext(file)[1]
        closest = min(remaining, key=lambda item: abs(item[1] - file_seconds))
        if abs(closest[1] - file_seconds) <= MATCH_TOLERANCE:
            pairs.append((file, closest[0][0] + extension))
            remaining.remove(closest)
            continue

        # retry with a 12h shift
        shifted = file_seconds + HALF_DAY
        closest_12h = min(remaining, key=lambda item: abs(item[1] - shifted))
        if abs(closest_12h[1] - shifted) <= MATCH_TOLERANCE:
            pairs.append((file, closest_12h[0][0] + extension))
            remaining.remove(closest_12h)
            continue
        pairs.append((file, NO_MATCH))
    return pairs

def validate_pairs(names, files, pairs):
    warnings = []
    matched = [p for p in pairs if p[1] != NO_MATCH]
    unmatched = [p for p in pairs if p[1] == NO_MATCH]
    if len(pairs) != len(files):
        warnings.append("Preview is out of date - run Preview again before renaming")
    if unmatched:
        warnings.append(f"{len(unmatched)} files had no matching csv entry and will be skipped")

    targets = [p[1] for p in matched]
    if len(targets) != len(set(targets)):
        warnings.append("Duplicate target names - only the first of each will be renamed")

    for old_path, new_name in matched:
        if not os.path.exists(old_path):
            warnings.append(f"Missing source file: {os.path.basename(old_path)}")
        elif os.path.exists(os.path.join(os.path.dirname(old_path), new_name)):
            warnings.append(f"{new_name} already exists in the folder")
    return warnings

def execute_rename(pairs):
    successes = []
    failures = []
    for old_path, new_name in pairs:
        if new_name == NO_MATCH:
            continue
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if os.path.exists(new_path):
            failures.append(f"{new_name} already exists - skipped")
            continue
        try:
            os.rename(old_path, new_path)
            successes.append(new_name)
        except OSError as e:
            failures.append(f"{os.path.basename(old_path)}: {e}")
    return successes, failures

class RenamerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JoshRenamer")
        self.geometry("1280x720")
        self.minsize(1080, 720)
        self.configure(fg_color="#152538")
        self.entries = []
        self.files = []
        self.pairs = []
        self.log_lines = []
        self.logs_window = None
        self.logs_textbox = None
        self.table = None
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.set_icon()
        self.sidebar()
        self.build_main()
        self.refresh_ui()
        self.log("App started")

    def report_callback_exception(self, exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
        self.log(f"[ERROR] {exc_type.__name__}: {exc_value}")
        CTkMessagebox(title="Unexpected Error",
                      message=f"{exc_type.__name__}: {exc_value}",
                      icon="cancel")

    def set_icon(self):
        try:
            self.icon = tk.PhotoImage(file=resource_path("logo.png"))
            self.iconphoto(True, self.icon)
        except tk.TclError:
            pass

    def load_logo(self):
        path = resource_path("logo.png")
        if not os.path.exists(path):
            return None
        img = Image.open(path)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(52, 52))

    def sidebar_button(self, parent, text, command):
        btn = ctk.CTkButton(parent, text=text, command=command, width=160, height=38, corner_radius=8, fg_color="#3579b8", hover_color="#4a94d6", font=("Segoe UI", 13))
        btn.pack(padx=20, pady=10)
        return btn

    def sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, fg_color="#1e3450", corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        logo = self.load_logo()
        if logo:
            ctk.CTkLabel(sidebar, image=logo, text="").pack(pady=(24, 6))
        ctk.CTkLabel(sidebar, text="JoshRenamer", font=("Segoe UI", 17), text_color="#e8eef5").pack()
        ctk.CTkLabel(sidebar, text="Batch renamer for call recordings", font=("Segoe UI", 11), text_color="#9db1c6", wraplength=170, justify="center").pack(pady=(2, 16))
        self.btn_load_txt = self.sidebar_button(sidebar, "Load TXT", self.load_txt)
        self.btn_select_files = self.sidebar_button(sidebar, "Select Files", self.select_files)
        ctk.CTkFrame(sidebar, height=1, fg_color="#2c4b6e").pack(fill="x", padx=20, pady=10)
        self.btn_preview = self.sidebar_button(sidebar, "Preview", self.preview)
        self.btn_rename = ctk.CTkButton(sidebar, text="Rename Files", command=self.rename, width=160, height=40, corner_radius=8, fg_color="#2e9e5b", hover_color="#36b568", font=("Segoe UI", 14, "bold"))
        self.btn_rename.pack(padx=20, pady=(40, 6))
        self.btn_logs = ctk.CTkButton(sidebar, text="Logs", command=self.open_logs, width=160, height=32, corner_radius=8, fg_color="transparent", hover_color="#28466a", border_width=1, border_color="#2c4b6e", text_color="#9db1c6", font=("Segoe UI", 12))
        self.btn_logs.pack(padx=20, pady=40)
        self.btn_reset = ctk.CTkButton(sidebar, text="Reset", command=self.reset, width=160, height=34, corner_radius=8, fg_color="#a8433f", hover_color="#bd5450", font=("Segoe UI", 13, "bold"))
        self.btn_reset.pack(side="bottom", pady=22, padx=20)
        self.btn_help = ctk.CTkButton(sidebar, text="Help", command=self.open_help_window, width=160, height=34, corner_radius=8, fg_color="#3579b8", font=("Segoe UI", 13, "bold"))
        self.btn_help.pack(side="bottom", pady=22, padx=20)
    def build_main(self):
        main = ctk.CTkFrame(self, fg_color="#152538")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(main, fg_color="#152538")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        ctk.CTkLabel(header, text="Rename Recordings", font=("Segoe UI", 24, "bold"), text_color="#e8eef5").pack(anchor="w")
        ctk.CTkLabel(header, text="Load TXT  ->  Select Files  ->  Preview  ->  Rename", font=("Segoe UI", 12), text_color="#9db1c6").pack(anchor="w", pady=(2, 0))

        self.table_container = ctk.CTkScrollableFrame(main, fg_color="#1a2f49", corner_radius=12)
        self.table_container.grid(row=1, column=0, sticky="nsew", padx=18, pady=(4, 8))

        self.empty_label = ctk.CTkLabel(self.table_container, text="Nothing here yet.\nLoad a TXT file and select recordings, then hit Preview.", font=("Segoe UI", 15), text_color="#9db1c6", justify="center")
        self.empty_label.pack(pady=60)

        status_bar = ctk.CTkFrame(main, fg_color="#1e3450", corner_radius=10)
        status_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        self.status_label = ctk.CTkLabel(status_bar, text="", font=("Segoe UI", 12), text_color="#9db1c6")
        self.status_label.pack(side="left", padx=14, pady=8)
        self.match_label = ctk.CTkLabel(status_bar, text="", font=("Segoe UI", 12), text_color="#9db1c6")
        self.match_label.pack(side="right", padx=14, pady=8)

    def refresh_ui(self):
        has_input = bool(self.entries and self.files)
        self.btn_preview.configure(state="normal" if has_input else "disabled")
        can_rename = any(p[1] != NO_MATCH for p in self.pairs)
        self.btn_rename.configure(state="normal" if can_rename else "disabled")

        has_anything = bool(self.entries or self.files or self.pairs)
        self.btn_reset.configure(state="normal" if has_anything else "disabled")

        txt_part = f"{len(self.entries)} names loaded" if self.entries else "no TXT loaded"
        files_part = f"{len(self.files)} files selected" if self.files else "no files selected"
        self.status_label.configure(text=f"{txt_part}   ·   {files_part}")

        if self.pairs:
            matched = sum(1 for p in self.pairs if p[1] != NO_MATCH)
            unmatched = len(self.pairs) - matched
            text = f"{matched} matched"
            if unmatched:
                text += f", {unmatched} unmatched"
            self.match_label.configure(text=text)
        else:
            self.match_label.configure(text="")

    def clear_table(self):
        if self.table is not None:
            self.table.destroy()
            self.table = None
        self.empty_label.configure(
            text="Nothing here yet.\nLoad a TXT file and select recordings, then hit Preview.")
        if not self.empty_label.winfo_manager():
            self.empty_label.pack(pady=60)

    def show_pairs_table(self):
        if self.table is not None:
            self.table.destroy()
        self.empty_label.pack_forget()

        values = [["Original Filename", "New Filename"]]
        for old_path, new_name in self.pairs:
            display = new_name if new_name != NO_MATCH else "no match found"
            values.append([os.path.basename(old_path), display])

        self.table = CTkTable(master=self.table_container, values=values, colors=["#223f5e", "#1c3350"], header_color="#2d5f8f", text_color="#e8eef5", font=("Segoe UI", 12), corner_radius=10)
        self.table.pack(fill="both", expand=True, padx=8, pady=8)

        for i, (_, new_name) in enumerate(self.pairs, start=1):
            if new_name == NO_MATCH:
                self.table.edit_row(i, text_color="#f0a8a2")


    def load_txt(self):
        path = filedialog.askopenfilename(
            title="Select the call log (TXT)",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path:
            return

        entries, failures = load_names_from_txt(path)
        self.entries = entries
        self.pairs = []
        self.clear_table()

        if failures:
            CTkMessagebox(title="Load Error", message="\n".join(failures), icon="warning")
            self.log(f"Failed reading {os.path.basename(path)}: " + "; ".join(failures))
        elif not entries:
            CTkMessagebox(title="Nothing Loaded", message="No valid entries were found in that file.", icon="warning")
            self.log(f"No valid entries in {os.path.basename(path)}")
        else:
            self.log(f"Loaded {len(entries)} entries from {os.path.basename(path)}")
        self.refresh_ui()

    def select_files(self):
        selected = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[("MP3 Files", "*.mp3"),("WAV Audio", "*.wav"), ("All Files", "*.*")])
        if not selected:
            return

        self.files = list(selected)
        self.pairs = []
        self.clear_table()
        self.log(f"Selected {len(self.files)} files")
        self.refresh_ui()

    def preview(self):
        self.pairs = build_pairs(self.entries, self.files)
        self.show_pairs_table()
        matched = sum(1 for p in self.pairs if p[1] != NO_MATCH)
        self.log(f"Preview: {matched}/{len(self.pairs)} files matched")
        self.refresh_ui()

    def rename(self):
        warnings = validate_pairs(self.entries, self.files, self.pairs)
        matched = [p for p in self.pairs if p[1] != NO_MATCH]

        message = f"About to rename {len(matched)} file(s)."
        if warnings:
            message += "\n\n" + "\n".join(warnings)
        box = CTkMessagebox(title="Confirm Rename", message=message, icon="question", option_1="Cancel", option_2="Rename")
        if box.get() != "Rename":
            return

        successes, failures = execute_rename(self.pairs)
        self.log(f"Renamed {len(successes)} file(s), {len(failures)} failure(s)")
        for failure in failures:
            self.log(f"  [FAILED] {failure}")

        if failures:
            CTkMessagebox(title="Finished With Errors", message=f"Renamed {len(successes)} files, {len(failures)} failed.\n" "See Logs for details.", icon="warning")
            self.open_logs()
        elif successes:
            CTkMessagebox(title="Done", message=f"Renamed {len(successes)} files.",
                          icon="check", option_1="Nice")

        # the old paths are gone after a rename, so the selection is stale
        self.files = []
        self.pairs = []
        self.clear_table()
        self.empty_label.configure(text="Batch complete.\nSelect the next set of files whenever you're ready.")
        self.refresh_ui()

    def reset(self):
        self.entries = []
        self.files = []
        self.pairs = []
        self.clear_table()
        self.log("Reset")
        self.refresh_ui()

    def log(self, message: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_lines.append(line)
        if self.logs_textbox is not None and self.logs_textbox.winfo_exists():
            self.logs_textbox.configure(state="normal")
            self.logs_textbox.insert("end", line + "\n")
            self.logs_textbox.configure(state="disabled")
            self.logs_textbox.see("end")

    def open_logs(self):
        if self.logs_window is not None and self.logs_window.winfo_exists():
            self.logs_window.deiconify()
            self.logs_window.lift()
            self.logs_window.focus()
            return

        self.logs_window = ctk.CTkToplevel(self)
        self.logs_window.title("Logs")
        self.logs_window.geometry("560x320")
        self.logs_window.attributes("-topmost", True)

        self.logs_textbox = ctk.CTkTextbox(self.logs_window, font=("Consolas", 12))
        self.logs_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        if self.log_lines:
            self.logs_textbox.insert("end", "\n".join(self.log_lines) + "\n")
            self.logs_textbox.see("end")
        self.logs_textbox.configure(state="disabled")

    def load_help_image(self, image_name, display_width=700):
        path = resource_path(os.path.join("help", image_name))
        if not os.path.exists(path):
            return None
        img = Image.open(path)
        w, h = img.size
        return ctk.CTkImage(light_image=img, dark_image=img, size=(display_width, int(h * display_width / w)))

    def open_help_window(self):
        self.help_window = ctk.CTkToplevel(self)
        self.help_window.title("Help")
        self.help_window.geometry("960x520")
        
        self.help_window.after(200, lambda: self.help_window.focus())
    
        frame = ctk.CTkScrollableFrame(self.help_window, fg_color="#152538")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="How to use JoshRenamer", font=("Segoe UI", 20, "bold"), text_color="#e8eef5").pack(anchor="w", padx=8, pady=(6, 14))
        for i, (step_title, description, image_name) in enumerate(HELP_STEPS, start=1):
            card = ctk.CTkFrame(frame, fg_color="#1a2f49", corner_radius=12)
            card.pack(fill="x", padx=8, pady=(0, 14))
 
            ctk.CTkLabel(card, text=f"{i}.  {step_title}", font=("Segoe UI", 15, "bold"), text_color="#e8eef5").pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=description, font=("Segoe UI", 12), text_color="#9db1c6", wraplength=520, justify="left").pack(anchor="w", padx=14, pady=(0, 10))
 
            image = self.load_help_image(image_name)
            if image:
                ctk.CTkLabel(card, image=image, text="").pack(padx=14, pady=(0, 14))
            else:
                ctk.CTkLabel(card, text=f"Screenshot missing: help/{image_name}", font=("Segoe UI", 11, "italic"), text_color="#9db1c6").pack(anchor="w", padx=14, pady=(0, 12))

def main():
    app = RenamerApp()
    app.mainloop()






    

if __name__ == "__main__":
    main()
