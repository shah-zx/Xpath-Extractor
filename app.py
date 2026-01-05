import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar, END
from lxml import etree
import pandas as pd  # Required for Excel export

# --- Core Logic Functions ---

def build_logical_xpath(element):
    """
    Constructs the logical XPath by traversing up the parent elements, reading the 
    'path' attribute, and applying special handling for top-level objects.
    """
    path_segments = []
    current = element
    
    while current is not None:
        segment = None
        
        # Priority 1: Use the 'path' attribute
        if 'path' in current.attrib:
            segment = current.get('path')
        
        # Priority 2: Special handling for top-level logical objects
        elif current.tag == 'object' and 'id' in current.attrib:
            object_id = current.get('id')
            if object_id.lower() == 'data':
                segment = 'data'
            elif object_id.lower() == 'policy':
                segment = 'policy'
        
        # Stop traversal at the document roots
        elif current.tag in ('model', 'ManuScript'):
            break

        if segment:
            path_segments.insert(0, segment)

        current = current.getparent()

    return "/".join(path_segments)

def find_xpath_for_field(tree, field_name):
    """Finds XPath for a single field ID."""
    try:
        xpath_query = f'//public[@id="{field_name}"]'
        elements = tree.xpath(xpath_query)
        if elements:
            elem = elements[0]
            return f"{field_name} : {build_logical_xpath(elem)}"
        else:
            return f"{field_name} : NOT FOUND"
    except Exception as e:
        return f"{field_name} : ERROR ({str(e)})"

def extract_group_xpaths(tree, group_name):
    """
    Finds the Input and Output objects for a given group and extracts 
    the XPaths of all public fields within them.
    """
    results = []
    target_ids = [f"{group_name}Input", f"{group_name}Output"]
    
    base_name = group_name.replace("And", "")
    if base_name + "Input" not in target_ids:
        target_ids.extend([f"{base_name}Input", f"{base_name}Output"])

    for target_id in target_ids:
        obj_element = tree.find(f".//object[@id='{target_id}']")
        if obj_element is not None:
            public_fields = obj_element.findall(".//public")
            for field in public_fields:
                field_id = field.get('id')
                xpath = build_logical_xpath(field)
                results.append(f"{field_id} : {xpath}")
    
    return results

# --- Export Logic ---

def export_to_excel(results_list):
    """
    Parses the text results and saves them to an Excel file.
    """
    if not results_list:
        messagebox.showwarning("Warning", "No data to export.")
        return

    # Parse the list of strings ["Field : XPath", ...] into a list of dictionaries
    data = []
    for item in results_list:
        if " : " in item:
            field, xpath = item.split(" : ", 1)
            data.append({"Field ID": field.strip(), "XPath": xpath.strip()})
        else:
            data.append({"Field ID": item, "XPath": "Error/Format Unknown"})

    # Ask user where to save
    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")],
        title="Save Export As"
    )

    if file_path:
        try:
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Success", f"Data exported successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save file:\n{str(e)}")

# --- UI and Workflow Functions ---

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
    entry_file.delete(0, END)
    entry_file.insert(0, file_path)

def add_field():
    field_id = entry_field.get().strip()
    if field_id and field_id not in field_listbox.get(0, END):
        field_listbox.insert(END, field_id)
        entry_field.delete(0, END)

def remove_field():
    selected = field_listbox.curselection()
    if selected:
        field_listbox.delete(selected[0])

def show_results(title, results):
    """
    Displays results in a popup and provides an Export button.
    """
    if not results:
        messagebox.showinfo("No Results", "No data found.")
        return
    
    out_win = tk.Toplevel(app)
    out_win.title(title)
    
    # Scrollbar and Text Area
    frame = tk.Frame(out_win)
    frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    txt = tk.Text(frame, height=20, width=95, yscrollcommand=scrollbar.set)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    txt.insert(END, "\n".join(results))
    txt.config(state=tk.DISABLED)
    
    scrollbar.config(command=txt.yview)

    # Export Button
    btn_frame = tk.Frame(out_win)
    btn_frame.pack(pady=10)
    
    tk.Button(
        btn_frame, 
        text="Export to Excel", 
        command=lambda: export_to_excel(results), 
        bg="#4CAF50", 
        fg="white",
        font=("Arial", 10, "bold")
    ).pack()

def process_individual():
    path = entry_file.get()
    fields = list(field_listbox.get(0, END))
    if not path or not fields:
        messagebox.showerror("Error", "Select file and add fields.")
        return
    try:
        tree = etree.parse(path)
        res = [find_xpath_for_field(tree, f) for f in fields]
        show_results("Individual Results", res)
    except Exception as e:
        messagebox.showerror("XML Error", f"Could not parse file:\n{str(e)}")

def process_group():
    path = entry_file.get()
    group = entry_group.get().strip()
    if not path or not group:
        messagebox.showerror("Error", "Select file and enter Group Name.")
        return
    try:
        tree = etree.parse(path)
        res = extract_group_xpaths(tree, group)
        if not res:
            messagebox.showinfo("Not Found", f"No fields found for group: {group}")
        else:
            show_results(f"Group Results: {group}", res)
    except Exception as e:
        messagebox.showerror("XML Error", f"Could not parse file:\n{str(e)}")

# --- UI Setup ---
app = tk.Tk()
app.title("XPath Extraction Tool")

# Global File Selection
tk.Label(app, text="1. Select Manuscript :").pack(pady=(10,0))
file_frame = tk.Frame(app)
file_frame.pack(pady=5)
entry_file = tk.Entry(file_frame, width=50)
entry_file.pack(side=tk.LEFT, padx=5)
tk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.LEFT)

# Option A: Group Extraction
group_frame = tk.LabelFrame(app, text="Option A: Extract by Group Name", padx=10, pady=10)
group_frame.pack(fill="x", padx=10, pady=5)
tk.Label(group_frame, text="Group Name:").grid(row=0, column=0)
entry_group = tk.Entry(group_frame, width=35)
entry_group.grid(row=0, column=1, padx=5)
tk.Button(group_frame, text="Extract Group", command=process_group, bg="lightblue").grid(row=0, column=2)

# Option B: Individual Field Extraction
field_frame = tk.LabelFrame(app, text="Option B: Individual Field IDs", padx=10, pady=10)
field_frame.pack(fill="x", padx=10, pady=5)
entry_field = tk.Entry(field_frame, width=35)
entry_field.pack(side=tk.LEFT, padx=5)
tk.Button(field_frame, text="Add", command=add_field).pack(side=tk.LEFT)
tk.Button(field_frame, text="Remove", command=remove_field).pack(side=tk.LEFT, padx=5)

field_listbox = Listbox(app, height=6, width=70)
field_listbox.pack(pady=5)
tk.Button(app, text="Extract fields XPath", command=process_individual, bg="lightgreen").pack(pady=5)

app.mainloop()