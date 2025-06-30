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
    ("Lidl", "Warszawa, Płochocińska 202", 52.3629, 21.0280),
    ("Lidl", "Warszawa, Modlińska 35", 52.3040, 20.9868),
    ("Lidl", "Warszawa, Jana Kasprowicza 117", 52.2886, 20.9318),
    ("Lidl", "Warszawa, Radzymińska 314", 52.2934, 21.0815)
]

PL_CENTER = (52.2297, 21.0122)

# geokodowanie
def geocode(query: str) -> tuple[float, float] | None:
    "dla OSM"
    try:
        data = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "ShopManagerApp"},
            timeout=5
        ).json()
        return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None
    except Exception:
        return None

nominatim_geocode = geocode

def wikigeocode(city: str) -> tuple[float, float]:
    try:
        html = requests.get(f"https://pl.wikipedia.org/wiki/{city.strip()}", timeout=6).text
        soup = BeautifulSoup(html, "html.parser")
        lat = soup.select('.latitude')[1].text.replace(',', '.')
        lon = soup.select('.longitude')[1].text.replace(',', '.')
        return float(lat), float(lon)
    except Exception:
        return PL_CENTER

# modele
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
    def __init__(self,
                 fullname: str,
                 position: str,
                 location: str,
                 store: Store | None = None):

        self.fullname, self.position, self.location = fullname, position, location
        self.store = store
        self.marker = None

        # ➊ jeśli przypisany do sklepu → bierzemy współrzędne sklepu
        if store is not None:
            self.lat, self.lon = store.lat, store.lon
        else:
            # ➋ najpierw próbujemy Nominatim, potem fallback do wiki
            self.latlon_from_location(location)

    # pomocnicza metoda
    def latlon_from_location(self, location: str) -> None:
        coords = nominatim_geocode(location)
        if coords is None:
            coords = wikigeocode(location.split(",")[0])
        self.lat, self.lon = coords

    def __str__(self):
        return f"{self.fullname} – {self.position} ({self.location})"

class Supplier:
    def __init__(self,
                 name: str,
                 category: str,
                 location: str,
                 store: Store | None = None):

        self.name, self.category, self.location = name, category, location
        self.store = store
        self.marker = None

        if store is not None:
            self.lat, self.lon = store.lat, store.lon
        else:
            self.latlon_from_location(location)

    # ta sama pomocnicza metoda co wyżej
    latlon_from_location = Employee.latlon_from_location

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

        elif view == "Dostawcy – cała sieć":
            for s in suppliers:
                s.marker = map_w.set_marker(s.lat, s.lon,
                                            text=s.name,
                                            marker_color_outside="green")
                current_markers.append(s.marker)
            fit_map()

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

    # ── CRUD dostawców ────────────────────────────────
    def add_sup():
        n, cat, loc = sup_name_ent.get().strip(), sup_cat_ent.get().strip(), sup_loc_ent.get().strip()
        if not n or not cat or not loc:
            return
        idx = sup_assign_cmb.current() - 1
        st = stores[idx] if idx >= 0 else None
        s = Supplier(n, cat, loc, st)
        suppliers.append(s)
        if st: st.suppliers.append(s)
        for w in (sup_name_ent, sup_cat_ent, sup_loc_ent): w.delete(0, tk.END)
        sup_assign_cmb.set("(brak)"); refresh_sup_lb(); refresh_map()

    def del_sup():
        if not supplier_lb.curselection():
            return
        flt, idx = sup_filter_cmb.get(), supplier_lb.curselection()[0]
        s = suppliers.pop(idx) if flt == "– Wszystkie –" else (
            next(st for st in stores if str(st) == flt).suppliers.pop(idx))
        if s.marker: s.marker.delete()
        if s in suppliers: suppliers.remove(s)
        refresh_sup_lb(); refresh_map()

    def edit_sup():
        if not supplier_lb.curselection():
            return
        flt, idx = sup_filter_cmb.get(), supplier_lb.curselection()[0]
        s = suppliers[idx] if flt == "– Wszystkie –" else (
            next(st for st in stores if str(st) == flt).suppliers[idx])

        win = tk.Toplevel(app); win.title("Edytuj dostawcę")
        for i, (lbl, val) in enumerate([("Nazwa:", s.name),
                                        ("Kategoria:", s.category),
                                        ("Miejscowość:", s.location)]):
            ttk.Label(win, text=lbl).grid(row=i, column=0, sticky="e")
            ent = tk.Entry(win, width=30); ent.grid(row=i, column=1); ent.insert(0, val)
            if i == 0: name_ent = ent
            elif i == 1: cat_ent = ent
            else: loc_ent = ent
        ttk.Label(win, text="Sklep:").grid(row=3, column=0, sticky="e")
        cmb = ttk.Combobox(win, width=28, state="readonly", values=["(brak)"] + [str(st) for st in stores])
        cmb.grid(row=3, column=1); cmb.set(str(s.store) if s.store else "(brak)")

        def _save():
            s.name, s.category = name_ent.get().strip(), cat_ent.get().strip()
            new_loc = loc_ent.get().strip()
            new_store = stores[cmb.current() - 1] if cmb.current() > 0 else None
            if s.store is not new_store:
                if s.store: s.store.suppliers.remove(s)
                if new_store: new_store.suppliers.append(s)
                s.store = new_store
            if new_loc != s.location:
                s.location = new_loc; s.lat, s.lon = wikigeocode(new_loc)
            refresh_sup_lb(); refresh_map(); win.destroy()

        ttk.Button(win, text="Zapisz", command=_save).grid(row=4, columnspan=2, pady=6)

    # ─────────  GUI  ─────────
    tabs = ttk.Notebook(app)
    tab_s, tab_e, tab_sup, tab_m = (ttk.Frame(tabs) for _ in range(4))
    for t, lbl in zip((tab_s, tab_e, tab_sup, tab_m), ("Sklepy", "Pracownicy", "Dostawcy", "Mapa")):
        tabs.add(t, text=lbl)
    tabs.pack(expand=True, fill="both")

    # Sklepy
    ttk.Label(tab_s, text="Sklepy", font=("Arial", 14)).pack(pady=8)
    frm_s = ttk.Frame(tab_s); frm_s.pack()
    ttk.Label(frm_s, text="Nazwa:").grid(row=0, column=0, sticky="e")
    store_name_ent = tk.Entry(frm_s, width=25); store_name_ent.grid(row=0, column=1)
    ttk.Label(frm_s, text="Adres (miasto, ul. nr):").grid(row=1, column=0, sticky="e")
    store_loc_ent = tk.Entry(frm_s, width=25); store_loc_ent.grid(row=1, column=1)
    ttk.Button(frm_s, text="Dodaj", command=add_store).grid(row=2, columnspan=2, pady=3)
    store_lb = tk.Listbox(tab_s, width=50, height=12); store_lb.pack(pady=6)
    ttk.Button(tab_s, text="Usuń",  command=del_store).pack(pady=2)
    ttk.Button(tab_s, text="Edytuj", command=edit_store).pack()

    # Pracownicy
    ttk.Label(tab_e, text="Pracownicy", font=("Arial", 14)).pack(pady=8)
    frm_e = ttk.Frame(tab_e); frm_e.pack()
    for r, (lbl, var) in enumerate([("Imię i nazwisko:", "emp_name_ent"),
                                    ("Stanowisko:",     "emp_pos_ent"),
                                    ("Miejscowość:",    "emp_loc_ent")]):
        ttk.Label(frm_e, text=lbl).grid(row=r, column=0, sticky="e")
        ent = tk.Entry(frm_e, width=25); ent.grid(row=r, column=1)
        globals()[var] = ent
    ttk.Label(frm_e, text="Sklep (opc.):").grid(row=3, column=0, sticky="e")
    emp_assign_cmb = ttk.Combobox(frm_e, width=23, state="readonly"); emp_assign_cmb.grid(row=3, column=1)
    emp_assign_cmb.set("(brak)")
    ttk.Button(frm_e, text="Dodaj", command=add_emp).grid(row=4, columnspan=2, pady=3)
    emp_filter_cmb = ttk.Combobox(tab_e, width=40, state="readonly"); emp_filter_cmb.pack(pady=3)
    emp_filter_cmb.set("– Wszystkie –"); emp_filter_cmb.bind("<<ComboboxSelected>>", lambda *_: refresh_emp_lb())
    employee_lb = tk.Listbox(tab_e, width=60, height=12); employee_lb.pack()
    ttk.Button(tab_e, text="Usuń",  command=del_emp).pack(pady=2)
    ttk.Button(tab_e, text="Edytuj", command=edit_emp).pack()

    # Dostawcy
    ttk.Label(tab_sup, text="Dostawcy", font=("Arial", 14)).pack(pady=8)
    frm_sup = ttk.Frame(tab_sup); frm_sup.pack()
    for r, (lbl, var) in enumerate([("Nazwa:",      "sup_name_ent"),
                                    ("Kategoria:",  "sup_cat_ent"),
                                    ("Miejscowość:","sup_loc_ent")]):
        ttk.Label(frm_sup, text=lbl).grid(row=r, column=0, sticky="e")
        ent = tk.Entry(frm_sup, width=25); ent.grid(row=r, column=1)
        globals()[var] = ent
    ttk.Label(frm_sup, text="Sklep (opc.):").grid(row=3, column=0, sticky="e")
    sup_assign_cmb = ttk.Combobox(frm_sup, width=23, state="readonly"); sup_assign_cmb.grid(row=3, column=1)
    sup_assign_cmb.set("(brak)")
    ttk.Button(frm_sup, text="Dodaj", command=add_sup).grid(row=4, columnspan=2, pady=3)
    sup_filter_cmb = ttk.Combobox(tab_sup, width=40, state="readonly"); sup_filter_cmb.pack(pady=3)
    sup_filter_cmb.set("– Wszystkie –"); sup_filter_cmb.bind("<<ComboboxSelected>>", lambda *_: refresh_sup_lb())
    supplier_lb = tk.Listbox(tab_sup, width=60, height=12); supplier_lb.pack()
    ttk.Button(tab_sup, text="Usuń",  command=del_sup).pack(pady=2)
    ttk.Button(tab_sup, text="Edytuj", command=edit_sup).pack()

    # Mapa
    ttk.Label(tab_m, text="Mapa", font=("Arial", 14)).pack(pady=6)
    top_m = ttk.Frame(tab_m); top_m.pack()
    ttk.Label(top_m, text="Widok:").grid(row=0, column=0, sticky="e")
    map_view_cmb = ttk.Combobox(top_m, width=45, state="readonly",
                                values=["Sklepy – wszystkie",
                                        "Pracownicy – cała sieć",
                                        "Dostawcy – cała sieć",])
    map_view_cmb.grid(row=0, column=1); map_view_cmb.current(0)
    map_view_cmb.bind("<<ComboboxSelected>>", refresh_map)
    map_w = tkintermapview.TkinterMapView(tab_m, width=1180, height=520, corner_radius=0)
    map_w.pack(); map_w.set_position(*PL_CENTER); map_w.set_zoom(6)

    # inicjalizacja
    store_lb.bind("<<ListboxSelect>>", lambda *_: refresh_map())
    for lb, func in [(store_lb, edit_store), (employee_lb, edit_emp), (supplier_lb, edit_sup)]:
        lb.bind("<Double-1>", lambda e, f=func: f())

    sync_store_combos()
    refresh_store_lb(); refresh_emp_lb(); refresh_sup_lb(); refresh_map()
    app.mainloop()

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
