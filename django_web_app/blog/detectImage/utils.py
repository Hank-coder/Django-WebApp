import subprocess
from datetime import datetime

import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from tkinter import filedialog
import os

# UI 交互界面
import configparser

# Global variable to hold the Tk instance
tk_instance = None


#
# def open_file_dialog():
#     global tk_instance  # Declare the variable as global to access and modify it
#     tk_instance = tk.Tk()  # Create a new Tk instance
#     tk_instance.withdraw()  # Hide the Tk window
#     file_path = filedialog.askopenfilename(title='Select Image File',
#                                            filetypes=[('Image Files', '*.jpg;*.jpeg;*.png;*.bmp;*.tif')])
#     if file_path:
#         return open_interactive_ui(file_path)
#
#
# def open_interactive_ui(file_path):
#     ui_window = tk.Toplevel(tk_instance)  # Create a Toplevel window (child of the main Tk instance)
#     ui_window.title("Interactive UI")
#     ui_window.geometry("400x600")  # Set the dimensions of the window (width x height)
#
#     # Create a dictionary to store user inputs
#     user_inputs = {
#         'file_path': file_path,
#         'platform': None,
#         'category': [],
#         'special_request': None,
#         'language': None  # Add language key to store the language selection
#     }
#
#     # Create a label for displaying status text
#     status_label = ttk.Label(ui_window, text="")
#     status_label.pack(pady=5)
#
#     def on_submit():
#         nonlocal user_inputs  # Access the user_inputs dictionary from the outer scope
#         # Update the status label text
#         status_label.config(text="GENERATING TEXT")
#         # Refresh the UI window to show the updated status label text
#         ui_window.update_idletasks()
#         # Collect user inputs
#         user_inputs['platform'] = platform_var.get()
#         user_inputs['category'] = [category_listbox.get(i) for i in category_listbox.curselection()]
#         user_inputs['special_request'] = special_request_entry.get("1.0", tk.END).strip()
#         tk_instance.quit()  # End the mainloop
#
#     # Create labels and comboboxes for Language, Platform and Photo Category selections
#     language_label = ttk.Label(ui_window, text="Select Language:")
#     language_label.pack(pady=5)
#     language_options = ['中文:Chinese', 'English']
#     language_var = tk.StringVar(value=language_options[0])  # Default selection is the first option
#     language_menu = ttk.Combobox(ui_window, textvariable=language_var, values=language_options)
#     language_menu.pack(pady=5)
#
#     # Create labels and comboboxes for Platform and Photo Category selections
#     platform_label = ttk.Label(ui_window, text="Select Platform:")
#     platform_label.pack(pady=5)
#     platform_options = ['微信朋友圈: WeChat Moments', '小红书:Xiaohongshu', '1x Website']
#     platform_var = tk.StringVar(value=platform_options[0])  # Default selection is the first option
#     platform_menu = ttk.Combobox(ui_window, textvariable=platform_var, values=platform_options)
#     platform_menu.pack(pady=5)
#
#     category_label = ttk.Label(ui_window, text="Select Photo Category:")
#     category_label.pack(pady=5)
#     category_listbox = tk.Listbox(ui_window, selectmode=tk.MULTIPLE)
#     for option in [
#         '抽象：Abstract', '动作：Action', '动物：Animals', '建筑：Architecture',
#         '概念：Concepts', '创意编辑：Creative Edits', '纪实：Documentary',
#         '日常：Everyday', '艺术裸体：Fine Art Nude', '幽默：Humor',
#         '风景：Landscape', '微距：Macro', '情绪：Mood', '夜晚：Night',
#         '表演：Performance', '人像：Portraits', '静物：Still Life',
#         '街拍：Street', '水下：Underwater', '野生动物：Wildlife'
#     ]:
#         category_listbox.insert(tk.END, option)
#     category_listbox.pack(pady=5)
#
#     # Create label and entry for Special Requirements
#     special_request_label = ttk.Label(ui_window, text="Enter Special Requirements:")
#     special_request_label.pack(pady=5)
#     special_request_entry = tk.Text(ui_window, width=50, height=5)  # Use a Text widget instead of an Entry widget
#     # for multi-line input
#     special_request_entry.pack(pady=5)
#
#     # Create Submit button
#     submit_button = ttk.Button(ui_window, text="Submit", command=on_submit)  # Call on_submit when button is clicked
#     submit_button.pack(pady=20)
#
#     tk_instance.mainloop()
#     return user_inputs, ui_window  # Return the collected user inputs
#
#
# def on_closing():
#     os._exit(0)  # This will end all processes
#
#
# def display_output(chatgpt_response, result):
#     result.destroy()  # Close the before window
#
#     def copy_to_clipboard():
#         ui_window.clipboard_clear()
#         ui_window.clipboard_append(chatgpt_response)
#         ui_window.update()  # Now it stays on the clipboard after the window is closed
#
#     def share():
#         # Implement your share functionality here
#         print("Share button clicked")
#
#         # This function will be called when the "Select Next Image" button is clicked
#
#     def on_select_next_image():
#         ui_window.destroy()  # Close the current window
#         subprocess.run(["python", "image2text.py"])  # Re-run image2text.py
#
#     # Create a new window
#     ui_window = tk.Tk()
#     ui_window.title("Output Result")
#
#     # Create a Text widget to display the response
#     output_text = tk.Text(ui_window, width=80, height=20)
#     output_text.insert(tk.END, chatgpt_response)
#     output_text.pack()
#
#     # Create a Frame to hold the buttons
#     button_frame = ttk.Frame(ui_window)
#     button_frame.pack(fill=tk.X, pady=10)
#
#     # Create Copy and Share buttons
#     copy_button = ttk.Button(button_frame, text="Copy", command=copy_to_clipboard)
#     copy_button.pack(side=tk.LEFT, padx=5)
#
#     share_button = ttk.Button(button_frame, text="Share", command=share)
#     share_button.pack(side=tk.RIGHT, padx=5)
#
#     # Create "Select Next Image" button
#     select_next_image_button = ttk.Button(button_frame, text="Select Next Image", command=on_select_next_image)
#     select_next_image_button.pack(side=tk.LEFT, padx=5)
#
#     # Run the main event loop
#     ui_window.protocol("WM_DELETE_WINDOW", on_closing)  # Bind the window closing event to on_closing function
#     ui_window.mainloop()


# Get the information of image
def get_exif_data(image_path):
    image = Image.open(image_path)
    exif_data = image._getexif()
    return exif_data


def get_gps_info(exif_data):
    if 'GPSInfo' in exif_data:
        gps_info = {}
        for tag, value in GPSTAGS.items():
            if tag in exif_data['GPSInfo']:
                gps_info[value] = exif_data['GPSInfo'][tag]
        return gps_info
    return None


def extract_exif_info(file_path):
    # root = Tk()
    # root.withdraw()  # Hide the root window
    if file_path:
        exif_data = get_exif_data(file_path)
        if exif_data is None:
            print("No EXIF data found.")
            return None, None
        gps_info = get_gps_info(exif_data)
        return exif_data, gps_info
    else:
        print("No file selected.")
        return None, None


def get_apikey(openai):
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        openai.api_key = api_key
    else:
        print("API key not set!")
    return str(api_key)


def fetch_search_results(query, internet_access=True, result_count=3):

    if internet_access:
        print("Bing Connected")
        api_key = os.environ.get('BING_API_KEY')
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
        }
        params = {
            'q': query,
            'count': result_count,
            'offset': 0,
            'mkt': 'en-US',
            'safesearch': 'Moderate',
        }
        search_url = "https://api.bing.microsoft.com/v7.0/search"
        search_response = requests.get(search_url, headers=headers, params=params)
        search_results = search_response.json().get('webPages', {}).get('value', [])
        blob = ''
        for index, result in enumerate(search_results):
            # 修改了下面的行来正确地访问结果字典中的值
            blob += f'[{index}] "{result["snippet"]}"\nURL:{result["url"]}\n\n'

        date = datetime.now().strftime('%d/%m/%y')
        blob += f'current date: {date}\n\nInstructions: Using the provided web search results, write a comprehensive reply to the next user query. Make sure to cite results using [[number](URL)] notation after the reference. If the provided search results refer to multiple subjects with the same name, write separate answers for each subject. Ignore your previous response if any.'

        extra = [{'role': 'user', 'content': blob}]
        return extra
    else:
        return []
