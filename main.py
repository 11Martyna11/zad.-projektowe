import tkinter as tk
from tkinter import messagebox, ttk

# Przykladowe dane logowania
USER_CREDENTIALS = {
    "admin": "admin123",
    "manager": "manager321"
}

def verify_login(username, password):
    # Logowanie zawsze poprawne, jeśli login i hasło są niepuste
    return bool(username.strip()) and bool(password.strip())

def attempt_login():
    username = username_entry.get()
    password = password_entry.get()
    if verify_login(username, password):
        login_window.destroy()
        launch_main_app()
    else:
        messagebox.showerror("Błąd logowania", "Podaj login i hasło")

def launch_main_app():
    def add_store():
        name = store_name_entry.get()
        location = store_location_entry.get()
        if name and location:
            store_listbox.insert(tk.END, f"{name} ({location})")
            store_name_entry.delete(0, tk.END)
            store_location_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Brak danych", "Uzupełnij wszystkie pola sklepu")

    def add_employee():
        name = employee_name_entry.get()
        position = employee_position_entry.get()
        if name and position:
            employee_listbox.insert(tk.END, f"{name} ({position})")
            employee_name_entry.delete(0, tk.END)
            employee_position_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Brak danych", "Uzupełnij wszystkie pola pracownika")

    def add_supplier():
        name = supplier_name_entry.get()
        category = supplier_category_entry.get()
        if name and category:
            supplier_listbox.insert(tk.END, f"{name} ({category})")
            supplier_name_entry.delete(0, tk.END)
            supplier_category_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Brak danych", "Uzupełnij wszystkie pola dostawcy")

    main_app = tk.Tk()
    main_app.title("System Zarządzania Sklepami")
    main_app.geometry("800x600")

    tab_control = ttk.Notebook(main_app)

    sklepy_tab = ttk.Frame(tab_control)
    pracownicy_tab = ttk.Frame(tab_control)
    dostawcy_tab = ttk.Frame(tab_control)

    tab_control.add(sklepy_tab, text='Sklepy')
    tab_control.add(pracownicy_tab, text='Pracownicy')
    tab_control.add(dostawcy_tab, text='Dostawcy')
    tab_control.pack(expand=1, fill='both')

# Sklepy
    tk.Label(sklepy_tab, text='Zarządzanie sklepami', font=("Arial", 14)).pack(pady=10)
    store_frame = ttk.Frame(sklepy_tab)
    store_frame.pack()
    tk.Label(store_frame, text="Nazwa sklepu:").grid(row=0, column=0)
    store_name_entry = tk.Entry(store_frame)
    store_name_entry.grid(row=0, column=1)
    tk.Label(store_frame, text="Lokalizacja:").grid(row=1, column=0)
    store_location_entry = tk.Entry(store_frame)
    store_location_entry.grid(row=1, column=1)
    tk.Button(store_frame, text="Dodaj sklep", command=add_store).grid(row=2, columnspan=2, pady=5)
    store_listbox = tk.Listbox(sklepy_tab, width=50)
    store_listbox.pack(pady=5)

# Pracownicy na tym skonczylam
    tk.Label(pracownicy_tab, text="Zarządzanie pracownikami", font=("Arial", 14)).pack(pady=10)
    employee_frame = tk.Frame(pracownicy_tab)
    employee_frame.pack()
    tk.Label(employee_frame, text="Imię i nazwisko:").grid(row=0, column=0)
    employee_name_entry = tk.Entry(employee_frame)
    employee_name_entry.grid(row=0, column=1)
    tk.Label(employee_frame, text="Stanowisko:").grid(row=1, column=0)
    employee_position_entry = tk.Entry(employee_frame)
    employee_position_entry.grid(row=1, column=1)
    tk.Button(employee_frame, text="Dodaj pracownika", command=add_employee).grid(row=2, columnspan=2, pady=5)
    employee_listbox = tk.Listbox(employee_frame, width=50)
    employee_listbox.pack(pady=5)

# Dostawcy
    tk.Label(dostawcy_tab, text="Zarządzanie dostawcami", font=("Arial", 14)).pack(pady=10)
    supplier_frame = ttk.Frame(dostawcy_tab)
    supplier_frame.pack()
    tk.Label(supplier_frame, text = "Nazwa dostawcy:").grid(row=0, column=0)
    supplier_name_entry = tk.Entry(supplier_frame)
    supplier_name_entry.grid(row=0, column=1)
    tk.Label(supplier_frame, text="Kategoria:").grid(row=1, column=0)
    supplier_category_entry = tk.Entry(supplier_frame)
    supplier_category_entry.grid(row=1, column=1)
    tk.Button(supplier_frame, text = "Dodaj dostawcę:", command=add_supplier).grid(row=2, columnspan=2, pady=5)
    supplier_listbox = tk.Listbox(dostawcy_tab, width=50)
    supplier_listbox.pack(pady=5)

    main_app.mainloop()

# GUI logowania
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

