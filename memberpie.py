import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import os
import shutil
import zipfile
from datetime import datetime
import cv2
from PIL import Image, ImageTk, ImageDraw

# --- Version Info ---
APP_VERSION = "v0.1.4"

# --- 1. Database Setup (Plain Text CSV) ---
DB_FILE = 'members.csv'
FIELDNAMES = ['memberid', 'name', 'member_since', 'end_date', 'phone', 'email', 'notes', 'photo_path']

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
                row['phone'] = row.get('phone', '')
                row['email'] = row.get('email', '')
                row['notes'] = row.get('notes', '')
                members.append(row)
    return members

def save_all_members(members):
    with open(DB_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(members)

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
        # Title now includes the Semantic Versioning variable
        self.root.title(f"MemberPie - Membership Management {APP_VERSION}")
        self.root.geometry("800x600")
        
        # Maximize the window on startup (Windows standard)
        self.root.state('zoomed')

        # Top Bar
        top_frame = tk.Frame(root, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_frame, text="Search Anywhere:", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, font=("Arial", 14), width=25)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind('<KeyRelease>', self.perform_search) 

        # Action Buttons (Packed to the right)
        self.btn_add = tk.Button(top_frame, text="+ Add Member", command=self.open_add_window, bg="lightblue")
        self.btn_add.pack(side=tk.RIGHT, padx=10)

        self.btn_backup = tk.Button(top_frame, text="📦 Backup Data", command=self.create_backup, bg="#f5deb3")
        self.btn_backup.pack(side=tk.RIGHT, padx=5)

        # Credits Footer
        credits_label = tk.Label(root, text="Brought to you by dualityps @ Ticstyle", font=("Arial", 10, "italic"), fg="gray")
        credits_label.pack(side=tk.BOTTOM, pady=5)

        # Main Display Area (Canvas + Scrollbar)
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

        self.load_all_members()
        self.search_entry.focus()

    # --- Backup Logic ---
    def create_backup(self):
        # Generate a default filename with today's date
        default_name = f"MemberPie_Backup_{datetime.today().strftime('%Y%m%d%hh%mm')}.zip"
        
        backup_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip Archive", "*.zip")],
            title="Save Backup Archive",
            initialfile=default_name
        )
        
        if not backup_path:
            return # User cancelled

        try:
            # Create the zip file
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Add the database file
                if os.path.exists(DB_FILE):
                    zipf.write(DB_FILE, arcname=DB_FILE)
                
                # 2. Add all photos in the directory
                photo_dir = 'member_photos'
                if os.path.exists(photo_dir):
                    for root_dir, _, files in os.walk(photo_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            # Keep folder structure inside the zip
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
        phone = member.get('phone', '')
        email = member.get('email', '')
        notes = member.get('notes', '')
        photo_path = member['photo_path']
        
        status_text, status_color = self.calculate_status(end_date)

        card = tk.Frame(self.display_frame, bd=2, relief=tk.GROOVE, padx=10, pady=10, cursor="hand2")
        card.pack(fill=tk.X, padx=20, pady=5, ipadx=50) 

        # Profile Picture
        lbl_img = tk.Label(card)
        lbl_img.pack(side=tk.LEFT, padx=10)
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

        # Member Info
        info_frame = tk.Frame(card)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)

        header_frame = tk.Frame(info_frame)
        header_frame.pack(fill=tk.X)
        
        left_header = tk.Frame(header_frame)
        left_header.pack(side=tk.LEFT)
        tk.Label(left_header, text=f"ID: {memberid}", font=("Arial", 14, "bold")).pack(anchor="w", pady=1)
        tk.Label(left_header, text=f"Name: {name}", font=("Arial", 14)).pack(anchor="w", pady=1)
        tk.Label(left_header, text=f"Member Since: {member_since}", font=("Arial", 10, "italic")).pack(anchor="w", pady=1)
        tk.Label(left_header, text=f"Paid Until: {end_date}", font=("Arial", 12)).pack(anchor="w", pady=1)
        
        contact_frame = tk.Frame(info_frame)
        contact_frame.pack(fill=tk.X, pady=5)
        if phone: tk.Label(contact_frame, text=f"📞 {phone}", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 15))
        if email: tk.Label(contact_frame, text=f"✉️ {email}", font=("Arial", 10)).pack(side=tk.LEFT)

        lbl_status = tk.Label(header_frame, text=status_text.upper(), font=("Arial", 14, "bold"), fg=status_color)
        lbl_status.pack(side=tk.RIGHT, anchor="n")

        if notes:
            tk.Label(info_frame, text=notes, font=("Arial", 10, "italic"), fg="gray", wraplength=350, justify=tk.LEFT).pack(anchor="w", pady=5)

        self.make_clickable(card, member)

    def make_clickable(self, widget, member_data):
        widget.bind("<Button-1>", lambda event, m=member_data: self.open_edit_window(m))
        for child in widget.winfo_children():
            self.make_clickable(child, member_data)

    # --- 3. Add / Edit Member Windows ---
    def open_add_window(self):
        self.open_form_window(mode="add")

    def open_edit_window(self, member_data):
        self.open_form_window(mode="edit", member_data=member_data)

    def open_form_window(self, mode="add", member_data=None):
        self.form_win = tk.Toplevel(self.root)
        self.form_win.title("Add New Member" if mode == "add" else "Edit Member")
        self.form_win.geometry("450x850")
        self.form_win.transient(self.root) 

        self.current_photo_path = ""
        self.original_memberid = None
        self.original_photo_path = ""

        tk.Label(self.form_win, text="Member ID (Integer):").pack(pady=2)
        self.entry_id = tk.Entry(self.form_win, width=30)
        self.entry_id.pack()

        tk.Label(self.form_win, text="Full Name:").pack(pady=2)
        self.entry_name = tk.Entry(self.form_win, width=30)
        self.entry_name.pack()

        tk.Label(self.form_win, text="Phone Number:").pack(pady=2)
        self.entry_phone = tk.Entry(self.form_win, width=30)
        self.entry_phone.pack()

        tk.Label(self.form_win, text="Email:").pack(pady=2)
        self.entry_email = tk.Entry(self.form_win, width=30)
        self.entry_email.pack()

        tk.Label(self.form_win, text="Member Since (YYYY-MM-DD):").pack(pady=2)
        self.entry_since = tk.Entry(self.form_win, width=30)
        self.entry_since.pack()

        tk.Label(self.form_win, text="End Date (YYYY-MM-DD):").pack(pady=2)
        self.entry_date = tk.Entry(self.form_win, width=30)
        self.entry_date.pack()

        tk.Label(self.form_win, text="Notes (max 500 characters):").pack(pady=2)
        self.text_notes = tk.Text(self.form_win, height=4, width=35, font=("Arial", 10))
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
            self.entry_name.insert(0, member_data['name'])
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
            self.entry_since.insert(0, get_today_date()) 
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
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not access the webcam.")
            return

        ret, frame = cap.read()
        if ret:
            temp_path = os.path.join("member_photos", "temp_capture.jpg")
            cv2.imwrite(temp_path, frame)
            self.current_photo_path = temp_path
            self.show_preview(temp_path)
        else:
            messagebox.showerror("Error", "Failed to capture image.")
        cap.release()

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
        phone = self.entry_phone.get().strip()
        email = self.entry_email.get().strip()
        member_since = self.entry_since.get().strip()
        end_date = self.entry_date.get().strip()
        notes = self.text_notes.get("1.0", tk.END).strip()[:500] 

        if not memberid_str or not name or not end_date:
            messagebox.showwarning("Error", "ID, Name, and End Date fields must be filled!")
            return None

        try:
            memberid = int(memberid_str)
        except ValueError:
            messagebox.showwarning("Error", "Member ID must be a number!")
            return None

        try:
            datetime.strptime(end_date, "%Y-%m-%d")
            if member_since:
                datetime.strptime(member_since, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Error", "Dates must be in YYYY-MM-DD format!")
            return None

        return str(memberid), name, member_since, end_date, phone, email, notes

    def save_new_member(self):
        inputs = self.validate_inputs()
        if not inputs: return
        memberid, name, member_since, end_date, phone, email, notes = inputs
        
        members = get_all_members()
        
        if any(m['memberid'] == memberid for m in members):
            messagebox.showerror("Duplicate ID", f"A member with ID {memberid} already exists!")
            return

        final_photo_path = self.process_photo_for_saving(self.current_photo_path, memberid)

        members.append({
            'memberid': memberid,
            'name': name,
            'member_since': member_since,
            'end_date': end_date,
            'phone': phone,
            'email': email,
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
        memberid, name, member_since, end_date, phone, email, notes = inputs
        
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
                m['member_since'] = member_since
                m['end_date'] = end_date
                m['phone'] = phone
                m['email'] = email
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