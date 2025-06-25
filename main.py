from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests
import tkintermapview
from bs4 import BeautifulSoup

# dane logowania
USER_CREDENTIALS = {"admin": "admin123"}

PRESET_STORES = [
    ("SuperMarket Centrum", "Warszawa, Marszałkowska 99", 52.2297, 21.0122),
    ("Fresh Market Północ", "Gdańsk, Długa 1", 54.3480, 18.6466),
    ("Eko-Sklep Południe", "Kraków, Rynek Główny 12", 50.0619, 19.9373),
]

PL_CENTER = (52.2297, 21.0122)

# geokodowanie
def nominatim_geocode(query: str) -> tuple[float, float] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": "ShopManagerApp/1.1 (kontakt@example.com)"}
    try:
        data = requests.get(url, params=params, headers=headers, timeout=6).json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def wikigeocode(city: str) -> tuple[float, float]:
    try:
        html = requests.get(f"https://pl.wikipedia.org/wiki/{city.strip()}", timeout=6).text
        soup = BeautifulSoup(html, "html.parser")
        lat = soup.select('.latitude')[1].text.replace(',', '.')
        lon = soup.select('.longitude')[1].text.replace(',', '.')
        return float(lat), float(lon)
    except Exception:
        return PL_CENTER






# zostawiam

if __name__ == "__main__":
    login_window = tk.Tk()
    login_window.title("Logowanie do Systemu")
    login_window.geometry("400x200")

    tk.Label(login_window, text="Nazwa użytkownika:").pack(pady=5)
    username_entry = tk.Entry(login_window);
    username_entry.pack()
    tk.Label(login_window, text="Hasło:").pack(pady=5)
    password_entry = tk.Entry(login_window, show="*"); password_entry.pack()
    tk.Button(login_window, text="Zaloguj", command=attempt_login).pack(pady=20)
    login_window.mainloop()
