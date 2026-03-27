import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import os
import shutil
import zipfile
import sys
import random
from datetime import datetime
import cv2
from PIL import Image, ImageTk, ImageDraw

# --- Auto-Minimize Terminal on Windows ---
if sys.platform.startswith('win'):
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        ctypes.windll.user32.ShowWindow(hwnd, 6)

# --- Version Info ---
APP_VERSION = "v0.1.9"

# --- 1. Database Setup (Plain Text CSV) ---
DB_FILE = 'members.csv'
FIELDNAMES = ['memberid', 'name', 'member_since', 'end_date', 'birth_date', 'phone', 'email', 'member_type', 'notes', 'photo_path']

def setup_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDNAMES)
            
    if not os.path.exists('member_photos'):
        os.makedirs('member_photos')

def get_all_members():
    members = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['member_since'] = row.get('member_since', '')
                row['birth_date'] = row.get('birth_date', '')
                row['phone'] = row.get('phone', '')
                row['email'] = row.get('email', '')
                row['member_type'] = row.get('member_type', '')
                row['notes'] = row.get('notes', '')
                members.append(row)
    return members

def save_all_members(members):
    with open(DB_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(members)

def generate_unique_id():
    members = get_all_members()
    existing_ids = {str(m['memberid']) for m in members}
    while True:
        new_id = str(random.randint(1000000000, 9999999999))
        if new_id not in existing_ids:
            return new_id

def get_today_date():
    return datetime.today().strftime('%Y-%m-%d')

def get_next_year_date():
    today = datetime.today()
    try:
        return today.replace(year=today.year + 1).strftime('%Y-%m-%d')
    except ValueError:
        return today.replace(year=today.year + 1, day=28).strftime('%Y-%m-%d')

def create_default_avatar():
    img = Image.new('RGB', (240, 85), color='white')
    draw = ImageDraw.Draw(img)
    draw.arc([105, 15, 135, 45], start=180, end=0, fill="darkgray", width=5)
    draw.line([135, 30, 135, 45], fill="darkgray", width=5)
    draw.line([135, 45, 120, 55], fill="darkgray", width=5)
    draw.line([120, 55, 120, 65], fill="darkgray", width=5)
    draw.ellipse([116, 70, 124, 78], fill="darkgray")
    return img

# --- 2. Main Application Class ---
class MemberPieApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"MemberPie - Membership Management {APP_VERSION}")
        self.root.geometry("800x700")
        
        self.root.state('zoomed')

        # Top Bar
        top_frame = tk.Frame(root, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_frame, text="Search Anywhere:", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, font=("Arial", 14), width=25)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind('<KeyRelease>', self.perform_search) 

        self.btn_add = tk.Button(top_frame, text="+ Add Member", command=self.open_add_window, bg="lightblue")
        self.btn_add.pack(side=tk.RIGHT, padx=10)

        self.btn_backup = tk.Button(top_frame, text="📦 Backup Data", command=self.create_backup, bg="#f5deb3")
        self.btn_backup.pack(side=tk.RIGHT, padx=5)

        # Credits Footer
        credits_label = tk.Label(root, text="Brought to you by dualityps @ Ticstyle", font=("Arial", 10, "italic"), fg="gray")
        credits_label.pack(side=tk.BOTTOM, pady=5)

        # Main Display Area 
        canvas_frame = tk.Frame(root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.display_frame = tk.Frame(self.canvas)

        self.display_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.display_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Mouse Scroll Bindings ---
        # We only listen for the scroll wheel when the mouse is hovering over the list area
        self.canvas.bind('<Enter>', self._bind_mousewheel)
        self.canvas.bind('<Leave>', self._unbind_mousewheel)

        self.load_all_members()
        self.search_entry.focus()

    # --- Mouse Wheel Logic ---
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel) # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel) # Linux scroll down

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        # Cross-platform handling of scroll direction
        if sys.platform == "darwin": # macOS
            self.canvas.yview_scroll(int(-1 * (event.delta)), "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    # --- Backup Logic ---
    def create_backup(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"MemberPie_Backup_{timestamp}.zip"
        
        backup_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip Archive", "*.zip")],
            title="Save Backup Archive",
            initialfile=default_name
        )
        
        if not backup_path:
            return 

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.exists(DB_FILE):
                    zipf.write(DB_FILE, arcname=DB_FILE)
                
                photo_dir = 'member_photos'
                if os.path.exists(photo_dir):
                    for root_dir, _, files in os.walk(photo_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            arcname = os.path.relpath(file_path, start=os.path.curdir)
                            zipf.write(file_path, arcname=arcname)
                            
            messagebox.showinfo("Backup Successful", f"Your database and photos have been backed up to:\n\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Backup Failed", f"An error occurred while zipping files:\n{e}")

    # --- Core Application Logic ---
    def calculate_status(self, end_date_str):
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date >= datetime.today().date():
                return "Active", "green"
            else:
                return "Expired", "red"
        except ValueError:
            return "Invalid Date", "orange"

    def perform_search(self, event=None):
        search_term = self.search_var.get().strip().lower()
        
        for widget in self.display_frame.winfo_children():
            widget.destroy()

        members = get_all_members()
        
        if search_term:
            members = [
                m for m in members 
                if any(search_term in str(value).lower() for value in m.values())
            ]

        if not members:
            tk.Label(self.display_frame, text="No members found.", font=("Arial", 12)).pack(pady=20)
            return

        for member in members:
            self.display_member_card(member)

    def load_all_members(self):
        self.search_var.set("") 
        self.perform_search()

    def display_member_card(self, member):
        memberid = member['memberid']
        name = member['name']
        member_since = member.get('member_since', '')
        end_date = member['end_date']
        birth_date = member.get('birth_date', '')
        phone = member.get('phone', '')
        email = member.get('email', '')
        member_type = member.get('member_type', '')
        notes = member.get('notes', '')
        photo_path = member['photo_path']
        
        status_text, status_color = self.calculate_status(end_date)

        card = tk.Frame(self.display_frame, bd=2, relief=tk.GROOVE, padx=15, pady=15, cursor="hand2")
        card.pack(fill=tk.X, padx=20, pady=8) 

        lbl_img = tk.Label(card, cursor="hand2")
        lbl_img.pack(side=tk.LEFT, padx=(0, 20))
        try:
            if photo_path and os.path.exists(photo_path):
                img = Image.open(photo_path)
                img.thumbnail((240, 320), Image.Resampling.LANCZOS)
            else:
                img = create_default_avatar() 
            
            photo = ImageTk.PhotoImage(img)
            lbl_img.config(image=photo)
            lbl_img.image = photo 
        except Exception:
            pass
            
        lbl_img.bind("<Button-1>", lambda event, p=photo_path: self.show_full_photo(p))

        info_frame = tk.Frame(card)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(info_frame)
        header_frame.pack(fill=tk.X, pady=(0, 2))
        
        tk.Label(header_frame, text=name, font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(header_frame, text=status_text.upper(), font=("Arial", 12, "bold"), fg=status_color).pack(side=tk.RIGHT)

        sub_header_text = f"Member ID: {memberid}"
        if member_type:
            sub_header_text += f"   |   Type: {member_type}"
            
        tk.Label(info_frame, text=sub_header_text, font=("Arial", 11), fg="dim gray").pack(anchor="w", pady=(0, 10))

        details_frame = tk.Frame(info_frame)
        details_frame.pack(fill=tk.X)

        col1 = tk.Frame(details_frame)
        col1.pack(side=tk.LEFT, padx=(0, 40))
        
        if birth_date: tk.Label(col1, text=f"Birth Date: {birth_date}", font=("Arial", 11)).pack(anchor="w", pady=2)
        if member_since: tk.Label(col1, text=f"Member Since: {member_since}", font=("Arial", 11)).pack(anchor="w", pady=2)
        tk.Label(col1, text=f"Paid Until: {end_date}", font=("Arial", 11)).pack(anchor="w", pady=2)

        col2 = tk.Frame(details_frame)
        col2.pack(side=tk.LEFT)
        
        if phone: tk.Label(col2, text=f"📞 {phone}", font=("Arial", 11)).pack(anchor="w", pady=2)
        if email: tk.Label(col2, text=f"✉️ {email}", font=("Arial", 11)).pack(anchor="w", pady=2)

        if notes:
            tk.Label(info_frame, text=notes, font=("Arial", 10, "italic"), fg="gray", wraplength=450, justify=tk.LEFT).pack(anchor="w", pady=(10, 0))

        self.make_clickable(card, member, exclude_widgets=[lbl_img])

    def make_clickable(self, widget, member_data, exclude_widgets=None):
        if exclude_widgets is None:
            exclude_widgets = []
            
        if widget in exclude_widgets:
            return 
            
        widget.bind("<Button-1>", lambda event, m=member_data: self.open_edit_window(m))
        for child in widget.winfo_children():
            self.make_clickable(child, member_data, exclude_widgets)

    def show_full_photo(self, photo_path):
        top = tk.Toplevel(self.root)
        top.title("Member Photo")
        top.transient(self.root) 
        
        lbl = tk.Label(top)
        lbl.pack(padx=20, pady=20)
        
        try:
            if photo_path and os.path.exists(photo_path):
                img = Image.open(photo_path)
            else:
                img = create_default_avatar()
                
            photo = ImageTk.PhotoImage(img)
            lbl.config(image=photo)
            lbl.image = photo 
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {e}")
            top.destroy()

    # --- 3. Add / Edit Member Windows ---
    def open_add_window(self):
        self.open_form_window(mode="add")

    def open_edit_window(self, member_data):
        self.open_form_window(mode="edit", member_data=member_data)

    def open_form_window(self, mode="add", member_data=None):
        self.form_win = tk.Toplevel(self.root)
        self.form_win.title("Add New Member" if mode == "add" else "Edit Member")
        self.form_win.geometry("480x920")
        self.form_win.transient(self.root) 

        self.current_photo_path = ""
        self.original_memberid = None
        self.original_photo_path = ""

        tk.Label(self.form_win, text="Member ID:").pack(pady=2)
        self.entry_id = tk.Entry(self.form_win, width=35)
        self.entry_id.pack()

        tk.Label(self.form_win, text="Member Type:").pack(pady=2)
        self.entry_type = tk.Entry(self.form_win, width=35)
        self.entry_type.pack()

        tk.Label(self.form_win, text="Full Name:").pack(pady=2)
        self.entry_name = tk.Entry(self.form_win, width=35)
        self.entry_name.pack()

        tk.Label(self.form_win, text="Birth Date (YYYY-MM-DD):").pack(pady=2)
        self.entry_birth = tk.Entry(self.form_win, width=35)
        self.entry_birth.pack()

        tk.Label(self.form_win, text="Phone Number:").pack(pady=2)
        self.entry_phone = tk.Entry(self.form_win, width=35)
        self.entry_phone.pack()

        tk.Label(self.form_win, text="Email:").pack(pady=2)
        self.entry_email = tk.Entry(self.form_win, width=35)
        self.entry_email.pack()

        tk.Label(self.form_win, text="Member Since (YYYY-MM-DD):").pack(pady=2)
        self.entry_since = tk.Entry(self.form_win, width=35)
        self.entry_since.pack()

        tk.Label(self.form_win, text="End Date (YYYY-MM-DD):").pack(pady=2)
        self.entry_date = tk.Entry(self.form_win, width=35)
        self.entry_date.pack()

        tk.Label(self.form_win, text="Notes (max 500 characters):").pack(pady=2)
        self.text_notes = tk.Text(self.form_win, height=4, width=40, font=("Arial", 10))
        self.text_notes.pack()

        tk.Label(self.form_win, text="Profile Photo:").pack(pady=10)
        
        btn_frame = tk.Frame(self.form_win)
        btn_frame.pack()
        tk.Button(btn_frame, text="Upload File", command=self.upload_photo).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Use Webcam", command=self.capture_photo).pack(side=tk.LEFT, padx=5)

        self.lbl_preview = tk.Label(self.form_win, text="No photo selected")
        self.lbl_preview.pack(pady=10)

        if mode == "edit" and member_data:
            self.original_memberid = member_data['memberid']
            self.original_photo_path = member_data['photo_path']
            
            self.entry_id.insert(0, member_data['memberid'])
            self.entry_type.insert(0, member_data.get('member_type', ''))
            self.entry_name.insert(0, member_data['name'])
            self.entry_birth.insert(0, member_data.get('birth_date', ''))
            self.entry_phone.insert(0, member_data.get('phone', ''))
            self.entry_email.insert(0, member_data.get('email', ''))
            self.entry_since.insert(0, member_data.get('member_since', ''))
            self.entry_date.insert(0, member_data['end_date'])
            self.text_notes.insert("1.0", member_data.get('notes', ''))
            
            self.current_photo_path = member_data['photo_path']
            if self.current_photo_path and os.path.exists(self.current_photo_path):
                self.show_preview(self.current_photo_path)
            else:
                self.show_default_preview()
                
            btn_text = "Update Member"
            btn_command = self.update_member
        else:
            self.entry_id.insert(0, generate_unique_id())
            # Intentionally left blank by default so it's not strictly required unless you type it
            self.entry_since.insert(0, "") 
            self.entry_date.insert(0, get_next_year_date()) 
            self.show_default_preview()
            btn_text = "Save New Member"
            btn_command = self.save_new_member

        tk.Button(self.form_win, text=btn_text, bg="lightgreen", font=("Arial", 12), command=btn_command).pack(pady=15)

    # --- 4. Photo Logic ---
    def upload_photo(self):
        fil = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if fil:
            self.current_photo_path = fil
            self.show_preview(fil)

    def capture_photo(self):
        self.form_win.config(cursor="watch")
        self.form_win.update()

        try:
            if sys.platform.startswith('win'):
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                messagebox.showerror("Error", "Could not access the webcam.")
                return

            for _ in range(5):
                cap.read()

            ret, frame = cap.read()
            if ret:
                temp_path = os.path.join("member_photos", "temp_capture.jpg")
                cv2.imwrite(temp_path, frame)
                self.current_photo_path = temp_path
                self.show_preview(temp_path)
            else:
                messagebox.showerror("Error", "Failed to capture image.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Webcam error: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            self.form_win.config(cursor="")

    def show_preview(self, path):
        img = Image.open(path)
        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.lbl_preview.config(image=photo, text="")
        self.lbl_preview.image = photo

    def show_default_preview(self):
        img = create_default_avatar()
        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.lbl_preview.config(image=photo, text="")
        self.lbl_preview.image = photo

    def process_photo_for_saving(self, source_path, memberid):
        if not source_path or not os.path.exists(source_path):
            return ""
            
        final_photo_path = os.path.join('member_photos', f"member_{memberid}.jpg")
        
        if os.path.abspath(source_path) == os.path.abspath(final_photo_path):
            return final_photo_path

        try:
            img = Image.open(source_path)
            img.thumbnail((480, 640), Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(final_photo_path, "JPEG")
            return final_photo_path
        except Exception as e:
            messagebox.showerror("Image Error", f"Could not process image: {e}")
            return ""

    # --- 5. Save / Update Logic ---
    def validate_inputs(self):
        memberid_str = self.entry_id.get().strip()
        name = self.entry_name.get().strip()
        birth_date = self.entry_birth.get().strip()
        phone = self.entry_phone.get().strip()
        email = self.entry_email.get().strip()
        member_type = self.entry_type.get().strip()
        member_since = self.entry_since.get().strip()
        end_date = self.entry_date.get().strip()
        notes = self.text_notes.get("1.0", tk.END).strip()[:500] 

        # Only restrict ID, Name, and End Date
        if not memberid_str or not name or not end_date:
            messagebox.showwarning("Error", "ID, Name, and End Date fields must be filled!")
            return None

        try:
            int(memberid_str)
        except ValueError:
            messagebox.showwarning("Error", "Member ID must be numbers only!")
            return None

        # Only check the date formatting IF they actually typed something into the field
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
            if member_since: datetime.strptime(member_since, "%Y-%m-%d")
            if birth_date: datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Error", "If providing a date, it must be in YYYY-MM-DD format!")
            return None

        return memberid_str, name, birth_date, member_since, end_date, phone, email, member_type, notes

    def save_new_member(self):
        inputs = self.validate_inputs()
        if not inputs: return
        memberid, name, birth_date, member_since, end_date, phone, email, member_type, notes = inputs
        
        members = get_all_members()
        
        if any(m['memberid'] == memberid for m in members):
            messagebox.showerror("Duplicate ID", f"A member with ID {memberid} already exists!")
            return

        final_photo_path = self.process_photo_for_saving(self.current_photo_path, memberid)

        members.append({
            'memberid': memberid,
            'name': name,
            'birth_date': birth_date,
            'member_since': member_since,
            'end_date': end_date,
            'phone': phone,
            'email': email,
            'member_type': member_type,
            'notes': notes,
            'photo_path': final_photo_path
        })
        
        save_all_members(members)
        messagebox.showinfo("Success", f"Member {name} saved!")
        self.form_win.destroy()
        self.load_all_members() 
        self.search_entry.focus()

    def update_member(self):
        inputs = self.validate_inputs()
        if not inputs: return
        memberid, name, birth_date, member_since, end_date, phone, email, member_type, notes = inputs
        
        members = get_all_members()

        if memberid != self.original_memberid:
            if any(m['memberid'] == memberid for m in members):
                messagebox.showerror("Duplicate ID", f"Cannot change to ID {memberid}, it is already in use!")
                return
                
        final_photo_path = self.process_photo_for_saving(self.current_photo_path, memberid)

        for m in members:
            if m['memberid'] == self.original_memberid:
                m['memberid'] = memberid
                m['name'] = name
                m['birth_date'] = birth_date
                m['member_since'] = member_since
                m['end_date'] = end_date
                m['phone'] = phone
                m['email'] = email
                m['member_type'] = member_type
                m['notes'] = notes
                m['photo_path'] = final_photo_path
                break
                
        if memberid != self.original_memberid and self.original_photo_path and os.path.exists(self.original_photo_path):
            if self.original_photo_path != final_photo_path:
                try: os.remove(self.original_photo_path)
                except Exception: pass

        save_all_members(members)
        messagebox.showinfo("Success", f"Member {name} updated!")
        self.form_win.destroy()
        self.perform_search() 
        self.search_entry.focus()

# --- 6. Run Application ---
if __name__ == "__main__":
    setup_db()
    root = tk.Tk()
    app = MemberPieApp(root)
    root.mainloop()