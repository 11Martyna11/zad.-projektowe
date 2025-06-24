import tkinter as tk
from tkinter import messagebox, ttk
import requests
from bs4 import BeautifulSoup
import tkintermapview

# dane logowania
USER_CREDENTIALS = {
    "admin": "admin123"
}

def verify_login(username, password):

    username = username.strip()
    password = password.strip()
    return USER_CREDENTIALS.get(username) == password

def attempt_login():
    username = username_entry.get()
    password = password_entry.get()
    if verify_login(username, password):
        messagebox.showinfo("Logowanie udane", "Zalogowano pomyślnie.")
        login_window.destroy()
        launch_main_app()
    else:
        messagebox.showerror("Błąd logowania", "Nieprawidłowy login lub hasło")

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
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.lat, self.lon = wikigeocode(location)
        self.employees = []
        self.suppliers = []
        self.marker = None

    def __str__(self):
        return f"{self.name} ({self.location})"

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

def launch_main_app():
    stores = []
    employees = []
    suppliers = []

    def refresh_store_listbox():
        store_listbox.delete(0, tk.END)
        for idx, s in enumerate(stores):
            store_listbox.insert(idx, str(s))

    def refresh_employee_listbox():
        employee_listbox.delete(0, tk.END)
        flt = emp_filter_combo.get()
        if flt == '– Wszystkie –':
            src = employees
        else:
            store = next((st for st in stores if str(st) == flt), None)
            src = store.employees if store else []
        for idx, e in enumerate(src):
            employee_listbox.insert(idx, str(e))

    def refresh_supplier_listbox():
        supplier_listbox.delete(0, tk.END)
        flt = sup_filter_combo.get()
        if flt == '– Wszystkie –':
            src = suppliers
        else:
            store = next((st for st in stores if str(st) == flt), None)
            src = store.suppliers if store else []
        for idx, s in enumerate(src):
            supplier_listbox.insert(idx, str(s))

    current_markers = []

    def clear_markers():
        for m in current_markers:
            m.delete()
        current_markers.clear()

    def zoom_to_fit():
        if not current_markers:
            return
        lats = [m.position[0] for m in current_markers]
        lons = [m.position[1] for m in current_markers]
        map_widget.set_position(sum(lats) / len(lats), sum(lons) / len(lons))
        map_widget.set_zoom(6 if len(current_markers) > 4 else 8)

        def refresh_map(*_):
            if 'map_widget' not in globals():
                return

            clear_markers()
            view = map_view_combo.get()

            if view == "Sklepy – wszystkie":
                for st in stores:
                    st.marker = map_widget.set_marker(st.lat, st.lon, text=st.name)
                    current_markers.append(st.marker)
                zoom_to_fit()

            elif view == "Pracownicy – cała sieć":
            for e in employees:
                e.marker = map_widget.set_marker(e.lat, e.lon, text=e.fullname,
                                                 marker_color_outside="orange")
                current_markers.append(e.marker)
                zoom_to_fit()

            elif view == "Pracownicy – wybrany sklep":
            sel = store_listbox.curselection()
            if not sel:
                return
            st = stores[sel[0]]
            for e in st.employees:
                e.marker = map_widget.set_marker(e.lat, e.lon, text=e.fullname,
                                                 marker_color_outside="orange")
                current_markers.append(e.marker)
                map_widget.set_position(st.lat, st.lon)
                map_widget.set_zoom(12)

            elif view == "Dostawcy – wybrany sklep":
            sel = store_listbox.curselection()
            if not sel:
                return
            st = stores[sel[0]]
            for s in st.suppliers:
                s.marker = map_widget.set_marker(s.lat, s.lon, text=s.name,
                                                 marker_color_outside="green")
                current_markers.append(s.marker)
            map_widget.set_position(st.lat, st.lon)
            map_widget.set_zoom(10)

    def sync_store_combos():
        vals = [str(s) for s in stores]
        for cb in (emp_filter_combo, sup_filter_combo):
            sel = cb.get()
            cb['values'] = ["– Wszystkie –"] + vals
            if sel not in cb['values']:
                cb.current(0)
        for cb in (emp_store_assign, sup_store_assign):
            sel = cb.get()
            cb['values'] = ["(brak)"] + vals
            if sel not in cb['values']:
                cb.current(0)

    def add_store():
        n, loc = store_name_entry.get().strip(), store_loc_entry.get().strip()
        if not (n and loc):
            return
        st = Store(n, loc)
        stores.append(st)
        store_name_entry.delete(0, 'end')
        store_loc_entry.delete(0, 'end')
        refresh_store_listbox()
        sync_store_combos()
        refresh_map()

    def remove_store():
        sel = store_listbox.curselection()
        if not sel:
            return
        st = stores.pop(sel[0])
        if st.marker:
            st.marker.delete()
        for e in list(st.employees):
            employees.remove(e)
        for s in list(st.suppliers):
            suppliers.remove(s)
        refresh_store_listbox()
        sync_store_combos()
        refresh_employee_listbox()
        refresh_supplier_listbox()
        refresh_map()

    def add_employee():
        fn = emp_name_entry.get().strip()
        pos = emp_pos_entry.get().strip()
        loc = emp_loc_entry.get().strip()
        if not (fn and pos and loc):
            return
        idx = emp_store_assign.current() - 1
        st = stores[idx] if idx >= 0 else None
        e = Employee(fn, pos, loc, st)
        employees.append(e)
        if st:
            st.employees.append(e)
        for w in (emp_name_entry, emp_pos_entry, emp_loc_entry):
            w.delete(0, 'end')
        emp_store_assign.set("(brak)")
        refresh_employee_listbox()
        refresh_map()

    def remove_employee():
        sel = employee_listbox.curselection()
        if not sel:
            return
        flt = emp_filter_combo.get()
        if flt == "– Wszystkie –":
            e = employees.pop(sel[0])
        else:
            st = next(s for s in stores if str(s) == flt)
            e = st.employees.pop(sel[0])
            employees.remove(e)
        if e.marker:
            e.marker.delete()
        refresh_employee_listbox()
        refresh_map()

    def add_supplier():
        n = sup_name_entry.get().strip()
        cat = sup_cat_entry.get().strip()
        loc = sup_loc_entry.get().strip()
        if not (n and cat and loc):
            return
        idx = sup_store_assign.current() - 1
        st = stores[idx] if idx >= 0 else None
        s = Supplier(n, cat, loc, st)
        suppliers.append(s)
        if st:
            st.suppliers.append(s)
        for w in (sup_name_entry, sup_cat_entry, sup_loc_entry):
            w.delete(0, 'end')
        sup_store_assign.set("(brak)")
        refresh_supplier_listbox()
        refresh_map()

    def remove_supplier():
        sel = supplier_listbox.curselection()
        if not sel:
            return
        flt = sup_filter_combo.get()
        if flt == "– Wszystkie –":
            s = suppliers.pop(sel[0])
        else:
            st = next(st for st in stores if str(st) == flt)
            s = st.suppliers.pop(sel[0])
            suppliers.remove(s)
        if s.marker:
            s.marker.delete()
        refresh_supplier_listbox()
        refresh_map()

    main_app = tk.Tk()
    main_app.title("System Zarządzania Sklepami")
    main_app.geometry("1200x750")

    tab_control = ttk.Notebook(main_app)
    sklepy_tab = ttk.Frame(tab_control)
    prac_tab = ttk.Frame(tab_control)
    dost_tab = ttk.Frame(tab_control)
    mapa_tab = ttk.Frame(tab_control)
    for frame, txt in [
        (sklepy_tab, 'Sklepy'),
        (prac_tab, 'Pracownicy'),
        (dost_tab, 'Dostawcy'),
        (mapa_tab, 'Mapa')
    ]:
        tab_control.add(frame, text=txt)
    tab_control.pack(expand=1, fill='both')

    tk.Label(sklepy_tab, text='Zarządzanie sklepami', font=("Arial", 14)).pack(pady=8)
    sf = ttk.Frame(sklepy_tab)
    sf.pack()
    tk.Label(sf, text="Nazwa:").grid(row=0, column=0, sticky='e')
    store_name_entry = tk.Entry(sf, width=25)
    store_name_entry.grid(row=0, column=1)
    tk.Label(sf, text="Miejscowość:").grid(row=1, column=0, sticky='e')
    store_loc_entry = tk.Entry(sf, width=25)
    store_loc_entry.grid(row=1, column=1)
    tk.Button(sf, text="Dodaj", command=add_store).grid(row=2, columnspan=2, pady=4)

    store_listbox = tk.Listbox(sklepy_tab, width=45, height=12)
    store_listbox.pack(pady=6)
    tk.Button(sklepy_tab, text="Usuń zaznaczony sklep", command=remove_store).pack(pady=4)

    tk.Label(prac_tab, text="Zarządzanie pracownikami", font=("Arial", 14)).pack(pady=8)
    pf = ttk.Frame(prac_tab)
    pf.pack()
    tk.Label(pf, text="Imię i nazwisko:").grid(row=0, column=0, sticky='e')
    emp_name_entry = tk.Entry(pf, width=25)
    emp_name_entry.grid(row=0, column=1)
    tk.Label(pf, text="Stanowisko:").grid(row=1, column=0, sticky='e')
    emp_pos_entry = tk.Entry(pf, width=25)
    emp_pos_entry.grid(row=1, column=1)
    tk.Label(pf, text="Miejscowość:").grid(row=2, column=0, sticky='e')
    emp_loc_entry = tk.Entry(pf, width=25)
    emp_loc_entry.grid(row=2, column=1)
    tk.Label(pf, text="Sklep (opc.):").grid(row=3, column=0, sticky='e')
    emp_store_assign = ttk.Combobox(pf, state='readonly', width=23, values=["(brak)"])
    emp_store_assign.current(0)
    emp_store_assign.grid(row=3, column=1, pady=2)
    tk.Button(pf, text="Dodaj pracownika", command=add_employee).grid(row=4, columnspan=2, pady=4)

    emp_filter_combo = ttk.Combobox(prac_tab, state='readonly', width=40, values=["– Wszystkie –"])
    emp_filter_combo.current(0)
    emp_filter_combo.pack(pady=3)
    emp_filter_combo.bind("<<ComboboxSelected>>", lambda *_: refresh_employee_listbox())
    employee_listbox = tk.Listbox(prac_tab, width=60, height=12)
    employee_listbox.pack()
    tk.Button(prac_tab, text="Usuń zaznaczonego pracownika", command=remove_employee).pack(pady=4)

    tk.Label(dost_tab, text="Zarządzanie dostawcami", font=("Arial", 14)).pack(pady=8)
    sf2 = ttk.Frame(dost_tab)
    sf2.pack()
    tk.Label(sf2, text="Nazwa:").grid(row=0, column=0, sticky='e')
    sup_name_entry = tk.Entry(sf2, width=25)
    sup_name_entry.grid(row=0, column=1)
    tk.Label(sf2, text="Kategoria:").grid(row=1, column=0, sticky='e')
    sup_cat_entry = tk.Entry(sf2, width=25)
    sup_cat_entry.grid(row=1, column=1)
    tk.Label(sf2, text="Miejscowość:").grid(row=2, column=0, sticky='e')
    sup_loc_entry = tk.Entry(sf2, width=25)
    sup_loc_entry.grid(row=2, column=1)
    tk.Label(sf2, text="Sklep (opc.):").grid(row=3, column=0, sticky='e')
    sup_store_assign = ttk.Combobox(sf2, state='readonly', width=23, values=["(brak)"])
    sup_store_assign.current(0)
    sup_store_assign.grid(row=3, column=1, pady=2)
    tk.Button(sf2, text="Dodaj dostawcę", command=add_supplier).grid(row=4, columnspan=2, pady=4)

    sup_filter_combo = ttk.Combobox(dost_tab, state='readonly', width=40, values=["– Wszystkie –"])
    sup_filter_combo.current(0)
    sup_filter_combo.pack(pady=3)
    sup_filter_combo.bind("<<ComboboxSelected>>", lambda *_: refresh_supplier_listbox())
    supplier_listbox = tk.Listbox(dost_tab, width=60, height=12)
    supplier_listbox.pack()
    tk.Button(dost_tab, text="Usuń zaznaczonego dostawcę", command=remove_supplier).pack(pady=4)

    top = ttk.Frame(mapa_tab)
    top.pack(pady=6)
    tk.Label(top, text="Widok mapy:").grid(row=0, column=0, sticky='e')
    map_view_combo = ttk.Combobox(
        top, state='readonly', width=45,
        values=[
            "Sklepy – wszystkie",
            "Pracownicy – cała sieć",
            "Pracownicy – wybrany sklep",
            "Dostawcy – wybrany sklep",
        ]
    )
    map_view_combo.current(0)
    map_view_combo.grid(row=0, column=1)
    map_view_combo.bind("<<ComboboxSelected>>", refresh_map)

    map_widget = tkintermapview.TkinterMapView(
        mapa_tab, width=1150, height=550, corner_radius=0
    )
    map_widget.pack()
    map_widget.set_position(52.2297, 21.0122)
    map_widget.set_zoom(6)

    store_listbox.bind("<<ListboxSelect>>", lambda *_: refresh_map())
    main_app.bind("<FocusIn>", lambda *_: refresh_map())
    refresh_store_listbox()
    refresh_employee_listbox()
    refresh_supplier_listbox()
    main_app.mainloop()

#skończyłam na tym
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

