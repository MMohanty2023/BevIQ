# BevIQ Project - VS Code Quick Setup

## 1. Codex se logout

VS Code mein Codex panel kholkar account/profile menu par click karo aur **Sign out / Log out** select karo.

Agar option na mile:

1. `Ctrl + Shift + P` dabao.
2. Search karo: `Codex: Sign Out` ya `Codex: Logout`.
3. Command select karke confirm karo.

Menu ka naam Codex extension version ke hisaab se thoda alag ho sakta hai.

## 2. Project VS Code mein open karo

VS Code terminal mein:

```powershell
cd "C:\Users\ANUVAB MOHANTY\Downloads\beverage_db\beverage_db"
code .
```

## 3. Python environment activate karo

Project mein `.venv` already hai:

```powershell
.\.venv\Scripts\Activate.ps1
```

Agar environment nahi bana ho:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 4. Required imports/dependencies install karo

Har package manually import/install karne ki zarurat nahi. `requirements.txt` se install karo:

```powershell
python -m pip install -r requirements.txt
```

Main packages ka use:

- `Flask`: web app/API
- `pandas`: CSV aur table data
- `mysql-connector-python`: MySQL connection
- `openpyxl`: Excel files
- `pypdf`: PDF reading
- `python-docx`: DOCX reading
- `pytesseract` + `Pillow`: image OCR
- `rapidfuzz`: product/brand similarity
- `requests`: local Ollama API

Python standard-library imports jaise `os`, `io`, `pathlib`, `csv`, `sqlite3`, `re`, `json`, `uuid` alag se install nahi karne padte.

## 5. Project run karo

Recommended command:

```powershell
python run.py
```

Browser mein kholo:

```text
http://127.0.0.1:5000
```

`run.py` pehle local SQLite database/vector index check ya build karta hai, phir Flask app start karta hai.

## 6. Optional settings

- MySQL primary database hai; default target `127.0.0.1:3306` hai. Apna MySQL password `.env` mein `MYSQL_PASSWORD` ke roop mein set karo; port alag ho to `MYSQL_PORT` set karo. MySQL unavailable hone par SQLite fallback chalta hai.
- Database/document features bina Ollama ke chal sakte hain. Normal open-ended chat ke liye Ollama install karke `ollama run llama3.2` chalao; chat local hi rehti hai.
- `.env` mein passwords/settings rakho, lekin `.env` ko GitHub par upload mat karo.

## 7. Common commands

```powershell
python run.py
python -m pytest
deactivate
```

## One-line summary

Activate `.venv` -> `pip install -r requirements.txt` -> `python run.py` -> browser mein `http://127.0.0.1:5000` open karo.
