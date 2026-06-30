# 🚀 JoshRenamer

> Smart file renaming tool that maps files to structured data using timestamp matching.

JoshRenamer is a Python-based desktop application that automates batch file renaming by matching files to external TXT/CSV data using time proximity logic.

Built with a modern GUI using CustomTkinter, the tool provides real-time preview, validation checks, and safe execution.

---

## ✨ Features

- 📂 Load structured TXT/CSV data
- 📁 Select multiple files for batch processing
- 🔍 Smart timestamp-based matching
- 📊 Live preview using a modern table UI
- ⚠️ Validation system (duplicates, mismatches, missing files)
- 🔁 Reset functionality for quick reuse
- 💬 Clean UI feedback with modern message boxes

---

## 🧠 Core Idea

JoshRenamer matches files to data entries by comparing timestamps:

- Extracts time from filenames  
- Extracts time from dataset (TXT/CSV)  
- Finds the closest match  
- Renames files accordingly  

---

## 🛠️ Tech Stack

- Python 3
- CustomTkinter (UI)
- CTkTable (table rendering)
- CTkMessagebox (user feedback)
- CSV module (data parsing)
- OS module (file operations)

---

## 📸 Preview

> *(Add screenshots here later — highly recommended)*

---

## ⚙️ Installation

```bash
pip install customtkinter
pip install CTkTable
pip install CTkMessagebox
