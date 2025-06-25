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

# ─────────  MODELE  ─────────
class Store:
    def __init__(self, name: str, address: str):
        self.name, self.address = name, address
        self.employees: list[Employee] = []
        self.suppliers: list[Supplier] = []
        self.marker = None
        coords = nominatim_geocode(address)
        if coords is None:
            raise ValueError(f"Adres „{address}” nie znaleziony w OSM.")
        self.lat, self.lon = coords

    @classmethod
    def raw(cls, name: str, address: str, lat: float, lon: float) -> "Store":
        obj = object.__new__(cls)
        obj.name, obj.address = name, address
        obj.lat, obj.lon = lat, lon
        obj.employees, obj.suppliers, obj.marker = [], [], None
        return obj

    def __str__(self) -> str:
        return f"{self.name} ({self.address})"


class Employee:
    def __init__(self, fullname: str, position: str, location: str, store: Store | None = None):
        self.fullname, self.position, self.location = fullname, position, location
        self.lat, self.lon = wikigeocode(location)
        self.store = store
        self.marker = None

    def __str__(self):
        return f"{self.fullname} – {self.position} ({self.location})"


class Supplier:
    def __init__(self, name: str, category: str, location: str, store: Store | None = None):
        self.name, self.category, self.location = name, category, location
        self.lat, self.lon = wikigeocode(location)
        self.store = store
        self.marker = None

    def __str__(self):
        return f"{self.name} – {self.category} ({self.location})"

# ─────────  LOGOWANIE  ─────────
def verify_login(username: str, password: str) -> bool:
    return USER_CREDENTIALS.get(username.strip()) == password.strip()


def attempt_login() -> None:
    if verify_login(username_entry.get(), password_entry.get()):
        messagebox.showinfo("Logowanie udane", "Zalogowano pomyślnie.")
        login_window.destroy()
        launch_main_app()
    else:
        messagebox.showerror("Błąd logowania", "Nieprawidłowy login lub hasło")

# ─────────  GŁÓWNA APP  ─────────
def launch_main_app() -> None:
    # centralne listy
    stores: list[Store] = []
    employees: list[Employee] = []
    suppliers: list[Supplier] = []

    # sklepy startowe
    for n, a, lat, lon in PRESET_STORES:
        try:
            st = Store(n, a)
        except ValueError:
            st = Store.raw(n, a, lat, lon)
        st.lat, st.lon = lat, lon
        stores.append(st)

    app = tk.Tk()
    app.title("System Zarządzania Sklepami")
    app.geometry("1280x760")

    current_markers: list[tkintermapview.TkinterMapView] = []

    # ── helpers ─────────────────────────────────────────
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

    def refresh_store_lb():
        store_lb.delete(0, tk.END)
        for i, st in enumerate(stores):
            store_lb.insert(i, str(st))

    def refresh_emp_lb():
        employee_lb.delete(0, tk.END)
        flt = emp_filter_cmb.get()
        src = employees if flt == "– Wszystkie –" else (
            next((s for s in stores if str(s) == flt), None).employees or [])
        for i, e in enumerate(src):
            employee_lb.insert(i, str(e))

    def refresh_sup_lb():
        supplier_lb.delete(0, tk.END)
        flt = sup_filter_cmb.get()
        src = suppliers if flt == "– Wszystkie –" else (
            next((s for s in stores if str(s) == flt), None).suppliers or [])
        for i, s in enumerate(src):
            supplier_lb.insert(i, str(s))

    def sync_store_combos():
        vals = [str(s) for s in stores]
        emp_filter_cmb["values"] = ["– Wszystkie –"] + vals
        sup_filter_cmb["values"] = ["– Wszystkie –"] + vals
        emp_assign_cmb["values"] = ["(brak)"] + vals
        sup_assign_cmb["values"] = ["(brak)"] + vals

    # ── MAPA ────────────────────────────────────────────
    def refresh_map(*_):
        clear_markers()
        view = map_view_cmb.get()

        if view == "Sklepy – wszystkie":
            for st in stores:
                st.marker = map_w.set_marker(st.lat, st.lon, text=st.name, marker_color_outside="blue")
                current_markers.append(st.marker)
            fit_map()

        elif view == "Pracownicy – cała sieć":
            for e in employees:
                e.marker = map_w.set_marker(e.lat, e.lon, text=e.fullname, marker_color_outside="orange")
                current_markers.append(e.marker)
            fit_map()

        elif view == "Pracownicy – wybrany sklep":
            if not store_lb.curselection():
                return
            st = stores[store_lb.curselection()[0]]
            for e in st.employees:
                e.marker = map_w.set_marker(e.lat, e.lon, text=e.fullname, marker_color_outside="orange")
                current_markers.append(e.marker)
            map_w.set_position(st.lat, st.lon)
            map_w.set_zoom(12)

        elif view == "Dostawcy – wybrany sklep":
            if not store_lb.curselection():
                return
            st = stores[store_lb.curselection()[0]]
            for s in st.suppliers:
                s.marker = map_w.set_marker(s.lat, s.lon, text=s.name, marker_color_outside="green")
                current_markers.append(s.marker)
            map_w.set_position(st.lat, st.lon)
            map_w.set_zoom(10)

    # ── geokoder w wątku ────────────────────────────────
    def threaded_geocode(addr: str, callback):
        def job():
            coords = nominatim_geocode(addr)
            app.after(0, callback, coords)
        threading.Thread(target=job, daemon=True).start()

    # ── CRUD sklepów ────────────────────────────────────
    def add_store():
        name, addr = store_name_ent.get().strip(), store_loc_ent.get().strip()
        if not name or not addr:
            messagebox.showwarning("Brak danych", "Uzupełnij nazwę i adres.")
            return

        def _finish(coords):
            if coords is None:
                messagebox.showerror("Geokoder", f"Adres „{addr}” nie znaleziono.")
                return
            stores.append(Store.raw(name, addr, *coords))
            store_name_ent.delete(0, tk.END); store_loc_ent.delete(0, tk.END)
            refresh_store_lb(); sync_store_combos(); refresh_map()

        threaded_geocode(addr, _finish)

    def del_store():
        if not store_lb.curselection():
            return
        idx = store_lb.curselection()[0]
        st = stores.pop(idx)
        if st.marker: st.marker.delete()
        for e in list(st.employees): employees.remove(e)
        for s in list(st.suppliers): suppliers.remove(s)
        refresh_store_lb(); refresh_emp_lb(); refresh_sup_lb()
        sync_store_combos(); refresh_map()

    def edit_store():
        if not store_lb.curselection():
            return
        st = stores[store_lb.curselection()[0]]

        win = tk.Toplevel(app); win.title("Edytuj sklep")
        ttk.Label(win, text="Nazwa:").grid(row=0, column=0, sticky="e")
        name_ent = tk.Entry(win, width=30); name_ent.grid(row=0, column=1); name_ent.insert(0, st.name)
        ttk.Label(win, text="Adres:").grid(row=1, column=0, sticky="e")
        addr_ent = tk.Entry(win, width=30); addr_ent.grid(row=1, column=1); addr_ent.insert(0, st.address)

        def _save():
            new_name, new_addr = name_ent.get().strip(), addr_ent.get().strip()
            if not new_name or not new_addr:
                messagebox.showwarning("Brak danych", "Uzupełnij wszystkie pola.")
                return

            def _finish(coords):
                if coords is None:
                    messagebox.showerror("Geokoder", f"Adres „{new_addr}” nie znaleziono.")
                    return
                st.name, st.address, (st.lat, st.lon) = new_name, new_addr, coords
                refresh_store_lb(); sync_store_combos(); refresh_map(); win.destroy()

            threaded_geocode(new_addr, _finish)

        ttk.Button(win, text="Zapisz", command=_save).grid(row=2, columnspan=2, pady=6)

    # ── CRUD pracowników ───────────────────────────────
    def add_emp():
        fn, pos, loc = emp_name_ent.get().strip(), emp_pos_ent.get().strip(), emp_loc_ent.get().strip()
        if not fn or not pos or not loc:
            return
        idx = emp_assign_cmb.current() - 1
        st = stores[idx] if idx >= 0 else None
        e = Employee(fn, pos, loc, st)
        employees.append(e)
        if st: st.employees.append(e)
        for w in (emp_name_ent, emp_pos_ent, emp_loc_ent): w.delete(0, tk.END)
        emp_assign_cmb.set("(brak)"); refresh_emp_lb(); refresh_map()

    def del_emp():
        if not employee_lb.curselection():
            return
        flt, idx = emp_filter_cmb.get(), employee_lb.curselection()[0]
        e = employees.pop(idx) if flt == "– Wszystkie –" else (
            next(s for s in stores if str(s) == flt).employees.pop(idx))
        if e.marker: e.marker.delete()
        if e in employees: employees.remove(e)
        refresh_emp_lb(); refresh_map()

    def edit_emp():
        if not employee_lb.curselection():
            return
        flt, idx = emp_filter_cmb.get(), employee_lb.curselection()[0]
        e = employees[idx] if flt == "– Wszystkie –" else (
            next(s for s in stores if str(s) == flt).employees[idx])

        win = tk.Toplevel(app); win.title("Edytuj pracownika")
        for i, (lbl, val) in enumerate([("Imię i nazwisko:", e.fullname),
                                        ("Stanowisko:", e.position),
                                        ("Miejscowość:", e.location)]):
            ttk.Label(win, text=lbl).grid(row=i, column=0, sticky="e")
            ent = tk.Entry(win, width=30); ent.grid(row=i, column=1); ent.insert(0, val)
            if i == 0: name_ent = ent
            elif i == 1: pos_ent = ent
            else: loc_ent = ent
        ttk.Label(win, text="Sklep:").grid(row=3, column=0, sticky="e")
        cmb = ttk.Combobox(win, width=28, state="readonly", values=["(brak)"] + [str(s) for s in stores])
        cmb.grid(row=3, column=1); cmb.set(str(e.store) if e.store else "(brak)")

        def _save():
            e.fullname, e.position = name_ent.get().strip(), pos_ent.get().strip()
            new_loc = loc_ent.get().strip()
            new_store = stores[cmb.current() - 1] if cmb.current() > 0 else None
            if e.store is not new_store:
                if e.store: e.store.employees.remove(e)
                if new_store: new_store.employees.append(e)
                e.store = new_store
            if new_loc != e.location:
                e.location = new_loc; e.lat, e.lon = wikigeocode(new_loc)
            refresh_emp_lb(); refresh_map(); win.destroy()

        ttk.Button(win, text="Zapisz", command=_save).grid(row=4, columnspan=2, pady=6)



# ─────────  OKNO LOGOWANIA  ─────────





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
