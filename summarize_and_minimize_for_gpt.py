import tkinter as tk
from tkinter import ttk
import csv
import re

# Define the method to process the text
def process_text():
    input_text = text_input.get("1.0", tk.END)
    processed_text = input_text.strip().lower()
    
    # Enumerate through the CSV file and replace found words with an underline
    with open(r'D:\whisp - Copy\curse_words.csv', newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            for word in row:
                processed_text = processed_text.replace(word, '_')

    # Find and remove filler words (assuming a list of filler words is provided in a CSV file named fillers.csv)
    with open(r'C:\Users\dower\Documents\unsilence_2\filler.csv', newline='', encoding='utf-8') as fillersfile:
        fillers_reader = csv.reader(fillersfile)
        for row in fillers_reader:
            for filler in row:
                processed_text = processed_text.replace(filler, '')
    # New line to remove anything not a letter or number
    processed_text = re.sub(r'[^a-zA-Z0-9\s]', '', processed_text)

    # Condense information by removing excessive spaces and newlines
    processed_text = re.sub(r'\s+', ' ', processed_text).strip()
    
    # Output the processed text to the second tab
    text_output.delete("1.0", tk.END)
    text_output.insert("1.0", processed_text)

# Creating the main window
root = tk.Tk()
root.title("Text Processor")
root.geometry("600x500")

# Creating the tab control
tab_control = ttk.Notebook(root)

# Creating two tabs
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)

# Adding the tabs to the tab control
tab_control.add(tab1, text='Input')
tab_control.add(tab2, text='Results')

# Layout of the tabs
tab_control.pack(expand=1, fill="both")

# Adding widgets to the first tab
text_input_label = ttk.Label(tab1, text="Paste your text below:")
text_input_label.pack(pady=(5, 0))
text_input = tk.Text(tab1, height=20, width=70)
text_input.pack()

# Adding widgets to the second tab
text_output_label = ttk.Label(tab2, text="Processed text:")
text_output_label.pack(pady=(5, 0))
text_output = tk.Text(tab2, height=20, width=70)
text_output.pack()

# Adding the process button
process_button = ttk.Button(tab1, text="Process Text", command=process_text)
process_button.pack(pady=(10, 10))

root.mainloop()