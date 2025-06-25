from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import requests
import tkintermapview
from bs4 import BeautifulSoup


# dane logowania
USER_CREDENTIALS = {"admin": "admin123"}


def verify_login(username: str, password: str) -> bool:
    return USER_CREDENTIALS.get(username.strip()) == password.strip()


def attempt_login() -> None:
    if verify_login(username_entry.get(), password_entry.get()):
        messagebox.showinfo("Logowanie udane", "Zalogowano pomyślnie.")
        login_window.destroy()
        launch_main_app()
    else:
        messagebox.showerror("Błąd logowania", "Nieprawidłowy login lub hasło")

PRESET_STORES = [
    ("SuperMarket Centrum", "Warszawa, Marszałkowska 99", 52.2297, 21.0122),
    ("Fresh Market Północ", "Gdańsk, Długa 1", 54.3480, 18.6466),
    ("Eko-Sklep Południe", "Kraków, Rynek Główny 12", 50.0619, 19.9373),
]

PL_CENTER = (52.2297, 21.0122)

def nominatim_geocode(query: str) -> tuple[float, float] | None:
    """Zwraca (lat, lon) dla pełnego adresu przy użyciu Nominatim OSM."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": "ShopManagerApp/1.1 (kontakt@example.com)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=6)
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return None


def wikigeocode(city: str):
    url = f"https://pl.wikipedia.org/wiki/{city.strip()}"
    try:
        html = requests.get(url, timeout=6).text
        soup = BeautifulSoup(html, "html.parser")
        lat = soup.select('.latitude')[1].text.replace(',', '.')
        lon = soup.select('.longitude')[1].text.replace(',', '.')
        return float(lat), float(lon)
    except Exception:
        return 52.2297, 21.0122


class Store:
    def __init__(self, name: str, address: str):
        self.name = name
        self.address = address
        self.employees: list[Employee] = []
        self.suppliers: list[Supplier] = []
        self.marker = None

        coords = nominatim_geocode(address)
        if coords is None:
            # brak w OSM – informacja i wyjątek,
            # add_store() przechwyci i nie doda rekordu
            raise ValueError(
                f"Adres „{address}” nie został odnaleziony w OpenStreetMap."
            )
        self.lat, self.lon = coords

    def __str__(self) -> str:
        return f"{self.name} ({self.address})"


class Employee:
    def __init__(self, fullname, position, location, store=None):
        self.fullname = fullname
        self.position = position
        self.location = location
        self.lat, self.lon = wikigeocode(location)
        self.store = store
        self.marker = None

    def __str__(self):
        return f"{self.fullname} – {self.position} ({self.location})"


class Supplier:
    def __init__(self, name, category, location, store=None):
        self.name = name
        self.category = category
        self.location = location
        self.lat, self.lon = wikigeocode(location)
        self.store = store
        self.marker = None

    def __str__(self):
        return f"{self.name} – {self.category} ({self.location})"


def launch_main_app() -> None:
    stores: list[Store] = []
    employees: list[Employee] = []
    suppliers: list[Supplier] = []

    for name, addr, lat, lon in PRESET_STORES:
        try:
            st = Store(name, addr)  # utworzy strukturę, waliduje dane
        except ValueError:
            # jeśli adresu nie ma w OSM, tworzymy „na sucho”
            st = object.__new__(Store)
            st.name, st.address = name, addr
            st.employees, st.suppliers = [], []
            st.marker = None

        # nadpisujemy współrzędne precyzyjnymi wartościami
        st.lat, st.lon = lat, lon
        stores.append(st)
    current_markers: list[tkintermapview.TkinterMapView] = []

    # --------------- helpers (listboxy) -----------------
    def refresh_store_lb():
        store_lb.delete(0, tk.END)
        for i, st in enumerate(stores):
            store_lb.insert(i, str(st))

    def refresh_emp_lb():
        employee_lb.delete(0, tk.END)
        flt = emp_filter_cmb.get()
        src = employees if flt == "– Wszystkie –" else next(
            (s for s in stores if str(s) == flt), None
        ).employees
        for i, e in enumerate(src):
            employee_lb.insert(i, str(e))

    def refresh_sup_lb():
        supplier_lb.delete(0, tk.END)
        flt = sup_filter_cmb.get()
        src = suppliers if flt == "– Wszystkie –" else next(
            (s for s in stores if str(s) == flt), None
        ).suppliers
        for i, s in enumerate(src):
            supplier_lb.insert(i, str(s))

    # --------------- helpers (mapa) ---------------------
    def clear_markers():
        for m in current_markers:
            m.delete()
        current_markers.clear()

    def fit_map():
        if not current_markers:
            return
        lats = [m.position[0] for m in current_markers]
        lons = [m.position[1] for m in current_markers]
        map_w.set_position(sum(lats) / len(lats), sum(lons) / len(lons))
        map_w.set_zoom(6 if len(current_markers) > 4 else 8)

    def refresh_map(*_):
        clear_markers()
        view = map_view_cmb.get()

        if view == "Sklepy – wszystkie":
            for st in stores:
                st.marker = map_w.set_marker(st.lat, st.lon, text=st.name)
                current_markers.append(st.marker)
            fit_map()

        elif view == "Pracownicy – cała sieć":
            for e in employees:
                e.marker = map_w.set_marker(e.lat, e.lon, text=e.fullname,
                                            marker_color_outside="orange")
                current_markers.append(e.marker)
            fit_map()

        elif view == "Pracownicy – wybrany sklep":
            if not store_lb.curselection():
                return
            st = stores[store_lb.curselection()[0]]
            for e in st.employees:
                e.marker = map_w.set_marker(e.lat, e.lon, text=e.fullname,
                                            marker_color_outside="orange")
                current_markers.append(e.marker)
            map_w.set_position(st.lat, st.lon)
            map_w.set_zoom(12)

        elif view == "Dostawcy – wybrany sklep":
            if not store_lb.curselection():
                return
            st = stores[store_lb.curselection()[0]]
            for s in st.suppliers:
                s.marker = map_w.set_marker(s.lat, s.lon, text=s.name,
                                            marker_color_outside="green")
                current_markers.append(s.marker)
            map_w.set_position(st.lat, st.lon)
            map_w.set_zoom(10)

    def sync_store_combos():
        vals = [str(s) for s in stores]
        emp_filter_cmb["values"] = ["– Wszystkie –"] + vals
        sup_filter_cmb["values"] = ["– Wszystkie –"] + vals
        emp_assign_cmb["values"] = ["(brak)"] + vals
        sup_assign_cmb["values"] = ["(brak)"] + vals

    # --------------- CRUD sklepy -----------------------

    def add_store():
        name = store_name_ent.get().strip()
        addr = store_loc_ent.get().strip()

        if not name or not addr:
            messagebox.showwarning("Brak danych", "Uzupełnij Nazwę i Adres.")
            return

        try:
            st = Store(name, addr)
        except ValueError as err:
            messagebox.showerror("Geokoder", str(err))
            return

        stores.append(st)
        store_name_ent.delete(0, tk.END)
        store_loc_ent.delete(0, tk.END)

        refresh_store_lb();
        sync_store_combos();
        refresh_map()

    def del_store():
        if not store_lb.curselection():
            return
        st = stores.pop(store_lb.curselection()[0])
        if st.marker:
            st.marker.delete()
        for e in st.employees:
            employees.remove(e)
        for s in st.suppliers:
            suppliers.remove(s)
        refresh_store_lb();
        sync_store_combos()
        refresh_emp_lb();
        refresh_sup_lb();
        refresh_map()

    # --------------- CRUD pracownicy -------------------
    def add_emp():
        fn, pos, loc = emp_name_ent.get().strip(), emp_pos_ent.get().strip(), emp_loc_ent.get().strip()
        if not fn or not pos or not loc:
            return
        idx = emp_assign_cmb.current() - 1
        st = stores[idx] if idx >= 0 else None
        e = Employee(fn, pos, loc, st)
        employees.append(e)
        if st:
            st.employees.append(e)
        for w in (emp_name_ent, emp_pos_ent, emp_loc_ent):
            w.delete(0, tk.END)
        emp_assign_cmb.set("(brak)")
        refresh_emp_lb();
        refresh_map()

    def del_emp():
        if not employee_lb.curselection():
            return
        flt = emp_filter_cmb.get()
        if flt == "– Wszystkie –":
            e = employees.pop(employee_lb.curselection()[0])
        else:
            st = next(s for s in stores if str(s) == flt)
            e = st.employees.pop(employee_lb.curselection()[0])
            employees.remove(e)
        if e.marker:
            e.marker.delete()
        refresh_emp_lb();
        refresh_map()

    # --------------- CRUD dostawcy ---------------------
    def add_sup():
        n, cat, loc = sup_name_ent.get().strip(), sup_cat_ent.get().strip(), sup_loc_ent.get().strip()
        if not n or not cat or not loc:
            return
        idx = sup_assign_cmb.current() - 1
        st = stores[idx] if idx >= 0 else None
        s = Supplier(n, cat, loc, st)
        suppliers.append(s)
        if st:
            st.suppliers.append(s)
        for w in (sup_name_ent, sup_cat_ent, sup_loc_ent):
            w.delete(0, tk.END)
        sup_assign_cmb.set("(brak)")
        refresh_sup_lb();
        refresh_map()

    def del_sup():
        if not supplier_lb.curselection():
            return
        flt = sup_filter_cmb.get()
        if flt == "– Wszystkie –":
            s = suppliers.pop(supplier_lb.curselection()[0])
        else:
            st = next(s for s in stores if str(s) == flt)
            s = st.suppliers.pop(supplier_lb.curselection()[0])
            suppliers.remove(s)
        if s.marker:
            s.marker.delete()
        refresh_sup_lb();
        refresh_map()

    # ---------------- GUI -----------------------------
    app = tk.Tk()
    app.title("System Zarządzania Sklepami")
    app.geometry("1280x750")

    tabs = ttk.Notebook(app)
    tab_s, tab_e, tab_sup, tab_m = (ttk.Frame(tabs) for _ in range(4))
    for t, lbl in zip((tab_s, tab_e, tab_sup, tab_m), ("Sklepy", "Pracownicy", "Dostawcy", "Mapa")):
        tabs.add(t, text=lbl)
    tabs.pack(expand=True, fill="both")

    # sklepy

    ttk.Label(tab_s, text="Sklepy", font=("Arial", 14)).pack(pady=8)

    frm_s = ttk.Frame(tab_s);
    frm_s.pack()

    ttk.Label(frm_s, text="Nazwa:").grid(row=0, column=0, sticky="e")
    store_name_ent = tk.Entry(frm_s, width=25);
    store_name_ent.grid(row=0, column=1)

    ttk.Label(frm_s, text="Adres (miasto, ul. nr):").grid(row=1, column=0, sticky="e")
    store_loc_ent = tk.Entry(frm_s, width=25);
    store_loc_ent.grid(row=1, column=1)

    add_btn = ttk.Button(frm_s, text="Dodaj", command=add_store)
    add_btn.grid(row=2, columnspan=2, pady=4)

    store_lb = tk.Listbox(tab_s, width=50, height=12);
    store_lb.pack(pady=6)

    ttk.Button(tab_s, text="Usuń", command=del_store).pack(pady=2)
    ttk.Button(tab_s, text="Edytuj", command=edit_store).pack(pady=2)
    # --- koniec zakładki Sklepy ----------------------------------

    # ------ zakładka Pracownicy -------
    ttk.Label(tab_e, text="Pracownicy", font=("Arial", 14)).pack(pady=8)
    frm_e = ttk.Frame(tab_e);
    frm_e.pack()
    ttk.Label(frm_e, text="Imię i nazwisko:").grid(row=0, column=0, sticky="e")
    emp_name_ent = tk.Entry(frm_e, width=25);
    emp_name_ent.grid(row=0, column=1)
    ttk.Label(frm_e, text="Stanowisko:").grid(row=1, column=0, sticky="e")
    emp_pos_ent = tk.Entry(frm_e, width=25);
    emp_pos_ent.grid(row=1, column=1)
    ttk.Label(frm_e, text="Miejscowość:").grid(row=2, column=0, sticky="e")
    emp_loc_ent = tk.Entry(frm_e, width=25);
    emp_loc_ent.grid(row=2, column=1)
    ttk.Label(frm_e, text="Sklep (opc.):").grid(row=3, column=0, sticky="e")
    emp_assign_cmb = ttk.Combobox(frm_e, width=23, state="readonly")
    emp_assign_cmb.grid(row=3, column=1, pady=2);
    emp_assign_cmb.set("(brak)")
    ttk.Button(frm_e, text="Dodaj pracownika", command=add_emp).grid(row=4, columnspan=2, pady=4)

    emp_filter_cmb = ttk.Combobox(tab_e, width=40, state="readonly")
    emp_filter_cmb.pack(pady=3);
    emp_filter_cmb.set("– Wszystkie –")
    emp_filter_cmb.bind("<<ComboboxSelected>>", lambda *_: refresh_emp_lb())
    employee_lb = tk.Listbox(tab_e, width=60, height=12);
    employee_lb.pack()
    ttk.Button(tab_e, text="Usuń", command=del_emp).pack(pady=4)

    # ------ zakładka Dostawcy ---------
    ttk.Label(tab_sup, text="Dostawcy", font=("Arial", 14)).pack(pady=8)
    frm_sup = ttk.Frame(tab_sup);
    frm_sup.pack()
    ttk.Label(frm_sup, text="Nazwa:").grid(row=0, column=0, sticky="e")
    sup_name_ent = tk.Entry(frm_sup, width=25);
    sup_name_ent.grid(row=0, column=1)
    ttk.Label(frm_sup, text="Kategoria:").grid(row=1, column=0, sticky="e")
    sup_cat_ent = tk.Entry(frm_sup, width=25);
    sup_cat_ent.grid(row=1, column=1)
    ttk.Label(frm_sup, text="Miejscowość:").grid(row=2, column=0, sticky="e")
    sup_loc_ent = tk.Entry(frm_sup, width=25);
    sup_loc_ent.grid(row=2, column=1)
    ttk.Label(frm_sup, text="Sklep (opc.):").grid(row=3, column=0, sticky="e")
    sup_assign_cmb = ttk.Combobox(frm_sup, width=23, state="readonly")
    sup_assign_cmb.grid(row=3, column=1, pady=2);
    sup_assign_cmb.set("(brak)")
    ttk.Button(frm_sup, text="Dodaj dostawcę", command=add_sup).grid(row=4, columnspan=2, pady=4)

    sup_filter_cmb = ttk.Combobox(tab_sup, width=40, state="readonly")
    sup_filter_cmb.pack(pady=3);
    sup_filter_cmb.set("– Wszystkie –")
    sup_filter_cmb.bind("<<ComboboxSelected>>", lambda *_: refresh_sup_lb())
    supplier_lb = tk.Listbox(tab_sup, width=60, height=12);
    supplier_lb.pack()
    ttk.Button(tab_sup, text="Usuń", command=del_sup).pack(pady=4)

    # ------ zakładka Mapa -------------
    ttk.Label(tab_m, text="Mapa", font=("Arial", 14)).pack(pady=6)
    top_m = ttk.Frame(tab_m);
    top_m.pack()
    ttk.Label(top_m, text="Widok:").grid(row=0, column=0, sticky="e")
    map_view_cmb = ttk.Combobox(
        top_m, width=45, state="readonly",
        values=[
            "Sklepy – wszystkie",
            "Pracownicy – cała sieć",
            "Pracownicy – wybrany sklep",
            "Dostawcy – wybrany sklep",
        ]
    )
    map_view_cmb.grid(row=0, column=1);
    map_view_cmb.current(0)
    map_view_cmb.bind("<<ComboboxSelected>>", refresh_map)

    map_w = tkintermapview.TkinterMapView(tab_m, width=1180, height=520, corner_radius=0)
    map_w.pack();
    map_w.set_position(52.2297, 21.0122);
    map_w.set_zoom(6)

    # ------ init --------
    store_lb.bind("<<ListboxSelect>>", lambda *_: refresh_map())
    sync_store_combos()
    refresh_store_lb();
    refresh_emp_lb();
    refresh_sup_lb()
    app.mainloop()


# skończyłam na tym
# zostawiam
login_window = tk.Tk()
login_window.title("Logowanie do Systemu")
login_window.geometry("400x200")

tk.Label(login_window, text="Nazwa użytkownika:").pack(pady=5)
username_entry = tk.Entry(login_window)
username_entry.pack()

tk.Label(login_window, text="Hasło:").pack(pady=5)
password_entry = tk.Entry(login_window, show="*")
password_entry.pack()

login_button = tk.Button(login_window, text="Zaloguj", command=attempt_login)
login_button.pack(pady=20)

login_window.mainloop()
