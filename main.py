"""CHIMERA — the Tkinter desktop application (windows, widgets, fitting/plotting flow).

The optional CHIMERA Online features live in ``online_ui.OnlineUIMixin``; pure,
GUI-independent logic lives in ``chimera_core``, ``db``, ``expr_eval`` and ``fitting``.
"""

import tkinter as tk
from tkinter import ttk

import matplotlib
import numpy as np
from PIL import Image, ImageTk

matplotlib.use('TkAgg')
import os
import sys
import webbrowser
from io import StringIO
from tkinter.scrolledtext import ScrolledText

import requests
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from chimera_core import (
    math_2_latex,  # noqa: F401  re-exported so tests can import it from ``main``
    parser,
    process_params,
    read_file,
)
from expr_eval import safe_eval
from fitting import run_odr_fit
from online_ui import OnlineUIMixin
from project_io import ProjectIOMixin


def check_version():
    current_version = '1.7.1'
    try:
        response = requests.get('https://sites.google.com/view/chimera-fit/install', timeout=1)
    except requests.RequestException:
        return
    words = response.text.split(' ')
    # Locate the token following 'Current' in the scraped page. Guard against
    # the page changing shape so a failed scrape never crashes startup.
    pos = None
    for idx, elem in enumerate(words):
        if 'Current' in elem:
            pos = idx + 1
            break
    if pos is None or pos + 1 >= len(words):
        return
    clean_version = ''
    for char in words[pos + 1]:
        if char == '<':
            break
        clean_version += char

    if clean_version != current_version:
        if tk.messagebox.askyesno('UPDATE AVAILABLE', f'There is a new version available ({current_version} -> {clean_version})! Do you want to be redirected to download it now?'):
            webbrowser.open('https://sites.google.com/view/chimera-fit/install')

def resource_path(relative_path):
    """Get the absolute path to a resource, working both in dev and under PyInstaller."""
    # PyInstaller unpacks bundled data into a temp folder exposed as sys._MEIPASS.
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class MainWindow(OnlineUIMixin, ProjectIOMixin, tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # This is the main window
        self.master = master
        self.master.title('CHIMERA')
        if os.name == 'posix':
            self.master.attributes('-zoomed',True)
        if os.name == 'nt':
            self.master.state('zoomed')
        self.master.iconphoto(True, tk.PhotoImage(file=resource_path('img/Logo.png')))

        # Enable the custom window-close function
        self.master.protocol("WM_DELETE_WINDOW", self.close)

        # Set the minimum window size
        self.master.minsize(int(0.5*self.master.winfo_screenwidth()),int(0.5*self.master.winfo_screenheight()))

        # Default sizes for the window
        self.width  = int(.8*self.master.winfo_screenwidth())
        self.height = int(.8*self.master.winfo_screenheight())

        # Frames to hold the objects
        self.top = tk.Frame(self.master, bg = '#E4E4E4')
        self.top.pack(in_ = self.master)
        self.bottom = tk.Frame(self.master, bg = '#E4E4E4')
        self.bottom.pack(in_ = self.master)

        # Canvases for the figures
        self.title_canvas = tk.Canvas(self.top, bg = '#E4E4E4')
        self.title_canvas.pack(in_ = self.top)
        self.logo_canvas = tk.Canvas(self.bottom, bg = '#E4E4E4')
        self.logo_canvas.grid(in_ = self.bottom, column = 1, row = 0, pady = self.height/10)

        # Start setting up the window
        self.master.geometry(str(self.width)+"x"+str(self.height))
        self.master.configure(background='#E4E4E4')
        self.master.update()
        # Create the window itself
        self.pack
        # Place the images and buttons
        self.place_item(resource_path("img/chimtext.png"), 0.6, self.title_canvas)
        self.place_item(resource_path("img/Logo.png"), 0.26, self.logo_canvas)
        self.create_widgets()

        # State shared between methods to control the construction of the
        # parameter boxes (was a global variable).
        self.count = 0
        # To ensure the widgets and images are resized
        self.master.bind('<Configure>', self.resize_window)
        check_version()

    def place_item(self, src, ratio, canvas):
        img_src = Image.open(src)
        img_ratio = self.master.winfo_width()*ratio/float(img_src.size[0])
        img_src = img_src.resize((int(img_src.size[0]*img_ratio), int(img_src.size[1]*img_ratio)))
        # Set up the canvas to put everything on screen
        canvas.config(width = img_src.size[0], height = img_src.size[1], highlightthickness = 0)
        img = ImageTk.PhotoImage(img_src)
        canvas.create_image(canvas.winfo_width()/2, canvas.winfo_height()/2,image = img)
        # Keep a reference to the image because tkinter is sometimes finicky
        canvas.image = img

    def resize_window(self, event):
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.place_item(resource_path("img/chimtext.png"), 0.6, self.title_canvas)
        self.place_item(resource_path("img/Logo.png"), 0.26, self.logo_canvas)
        # Define new positions relative to the window
        self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
        # Define new sizes relative to the window
        self.new["font"] = ("Roboto",int(0.018*self.master.winfo_width()),"bold")
        self.new.configure(height = 1)

    def create_widgets(self):
        # Create button for a new fit
        self.new = tk.Button(self.bottom,
                             width = int(0.011*self.master.winfo_width()),
                             height=1,
                             fg='white',
                             bg='#F21112',
                             activebackground='white',
                             activeforeground='#F21112')
        self.new["text"] = "NEW FIT"
        self.new["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        self.new["command"] = self.create_scatter
        self.new.grid(column = 3, row = 0, padx = (int(self.master.winfo_width()/10),20))
        # Change the colors on enter and leave
        self._add_hover(self.new)

        # Create button to import a fit
        self.old = tk.Button(self.bottom,
                              width = int(0.011*self.master.winfo_width()),
                              height=1,
                              fg='white',
                              bg='#F21112',
                              activebackground='white',
                              activeforeground='#F21112')
        self.old["text"] = "OPEN FIT"
        self.old["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        self.old["command"] = self.open_project
        self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10)))
        self._add_hover(self.old)

    def focus_window(self, window):
        window.lift()
        window.focus_force()
        window.grab_set()
        window.grab_release()

    def create_scatter(self):
        # bindings for hotkeys
        # Remove the image size adjustements
        self.master.unbind('<Configure>')
        # Export Image
        self.master.bind('<Control-Shift-E>', self.export_image)
        self.master.bind('<Control-Shift-e>', self.export_image)
        # New Project
        self.master.bind('<Control-N>', self.restart)
        self.master.bind('<Control-n>', self.restart)
        # Save Project
        self.master.bind('<Control-S>', self.save_everything)
        self.master.bind('<Control-s>', self.save_everything)
        # Save Project As...
        self.master.bind('<Control-Shift-S>', self.save_as)
        self.master.bind('<Control-Shift-s>', self.save_as)
        # Import Project
        self.master.bind('<Control-O>', self.open_project)
        self.master.bind('<Control-o>', self.open_project)
        # Create Residue Plot
        self.master.bind('<Control-Shift-R>', self.create_residue_data)
        self.master.bind('<Control-Shift-r>', self.create_residue_data)
        # Login to online mode
        self.master.bind('<Control-L>', self.create_login)
        self.master.bind('<Control-l>', self.create_login)

        self.selected_dataset = 0

        self.count_plots = 0
        # Destroy everything that was in the window
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.new.destroy()
        self.count = 1

        # Define the array for the labels up front
        self.data_labels = ['']
        self.plot_labels = ['']
        self.fit_labels = ['']

        # Define arrays to store text and their positions
        self.plot_text = ['']
        self.text_pos = [[0,0]]
        self.text_size = [10]

        # Define the functions, variables and the like
        self.indeps = ['x']
        self.params = ['A,omega,phi,lambda']
        self.functions = ['A*sin(omega*x+phi)*exp(-lambda*x)']
        self.clean_functions = ['B[0]*np.sin(B[1]*_x+B[2])*np.exp(-B[3]*_x)']

        self.fit_params = [['']]
        self.fit_uncert = [['']]
        self.fit_chi = ['']
        self.fit_r2 = ['']
        self.init_values = [[1.0,1.0,1.0,1.0]]

        self.x_func = [[]]
        self.y_func = [[]]

        self.x_fitted_func = [[]]
        self.y_fitted_func = [[]]

        self.full_output = ['']

        self.x_ticks_ref = []
        self.y_ticks_ref = []

        # Set the figure ratio
        self.width_ratio = 1
        self.height_ratio = 1

        self.master.configure(background='#E4E4E4')

        # Create the window's frame structure
        self.frame_left = tk.Frame(self.master,  bg='#E4E4E4')
        self.frame_left.place(in_=self.master, relwidth=0.5, relheight=1, relx=0, rely=0)

        # frame_right holds everything on the right side of the window
        self.frame_right = tk.Frame(self.master,  bg='#E4E4E4')
        self.frame_right.place( in_ = self.master, relwidth=0.5, relheight=1,relx=0.5, rely=0)

        # Subsection where the parameter, independent-variable and function entries go
        self.subframe_right_1=tk.Frame(self.frame_right, bg='#E4E4E4', highlightbackground="black", highlightthickness=0, padx=20, pady=20)
        self.subframe_right_1.place(in_=self.frame_right, relwidth=1, relheight=0.5, relx=0, rely=0)

         # Create the frames for the visual editing of the plot
        self.subframe_right_2=tk.Frame(self.frame_right, bg='#E4E4E4')
        self.subframe_right_2.place(in_ = self.frame_right, relwidth=1, relheight=0.2, relx=0, rely=0.25)

        self.subframe_left_1=tk.Frame(self.frame_left, bg='#E4E4E4')
        self.subframe_left_1.place(in_ = self.frame_left, relwidth=1, relheight=0.5, relx=0, rely=0)

        self.plot_button_frame = tk.Frame(self.frame_left, bg= '#E4E4E4')
        self.plot_button_frame.place(in_ = self.frame_left, relwidth=1, relheight=0.05, relx=0, rely=0.5)

        self.data_button_frame = tk.Frame(self.frame_left, bg='#E4E4E4')
        self.data_button_frame.place(in_ = self.frame_left, relwidth=1, relheight=0.05, relx=0, rely=0.93)

        self.subframe_left_2 = tk.Frame(self.frame_left, bg='#E4E4E4')
        self.subframe_left_2.place(in_ = self.frame_left, relwidth = 1, relheight= 0.38, relx=0, rely=0.55)

        # Create the area where the plot's axis information is entered
        self.subframe_right_3 = tk.Frame(self.frame_right, bg='#E4E4E4')
        self.subframe_right_3.place(in_ = self.frame_right, relwidth = 1, relheight = 0.52, rely=0.48)

        # Create the button that calls the function that processes the function
        self.compile_button = tk.Button(self.subframe_right_1,
                                       text="COMPILE",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112',
                                       justify='center')
        self.compile_button.place(relwidth=0.2,relx=0.8, rely=0.2,relheight=0.1 )
        self.compile_button["command"] = self.compile_function

        # Button used to update the list of parameter entries
        self.up_button = tk.Button(self.subframe_right_1,
                                  text="UPDATE",
                                  fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        self.up_button.place(relwidth=0.2,relx=0.8, rely=0.1,relheight=0.1 )
        self.up_button["command"] = self.update_parameter

        # Button to plot the dataset; calls the plot_dataset function
        self.plot_button = tk.Button(self.plot_button_frame,
                                       text="PLOT",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')

        self.plot_button.place(in_  = self.plot_button_frame, relwidth=0.2, relheight=1, relx=0.25)
        self.plot_button["command"] = self.plot_dataset

        # Button to plot the function; calls the plot_function function
        self.plot_function_button = tk.Button(self.plot_button_frame,
                                       text="PLOT FUNCTION",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')

        self.plot_function_button.place(in_  = self.plot_button_frame, relwidth=0.3, relheight=1,relx = 0.5)
        self.plot_function_button["command"] = self.plot_function
        self.want_function = [tk.BooleanVar()]
        self.want_function[0].set(0)

        # Button to import files
        self.import_data = tk.Button(self.data_button_frame,
                                     text='IMPORT DATA',
                                     fg='white',
                                     bg='#F21112',
                                     activebackground='white',
                                     activeforeground='#F21112')
        self.import_data.place(relwidth=0.23, relheight=1,relx = 0.05)
        self.import_data["command"] = self.import_window

        self.add_labels = tk.Button(self.data_button_frame,
                                    text='SET LABELS',
                                    fg='white',
                                    bg='#F21112',
                                    activebackground='white',
                                    activeforeground='#F21112')
        self.add_labels.place(relwidth=0.2, relheight=1, relx=0.33)
        self.add_labels["command"] = self.labels

        # Button to add text entries
        self.add_text = tk.Button(self.data_button_frame,
                                  text='SET TEXT',
                                  fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        self.add_text.place(relwidth=0.16, relheight=1, relx=0.58)
        self.add_text["command"] = self.text

        # Button to export as LaTeX
        self.export_latex = tk.Button(self.data_button_frame,
                                      text="LaTeX-ify",
                                      fg='white',
                                      bg='#F21112',
                                      activebackground='white',
                                      activeforeground='#F21112')
        self.export_latex.place(relwidth=0.16, relheight=1, relx=0.79)
        self.export_latex["command"] = self.latexify

        # Create the button linked to the function that adds another dataset
        self.add_dataset_button = tk.Button(self.plot_button_frame,
                                       text="+",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112', command = lambda: self.add_dataset(''))
        self.add_dataset_button.place(in_ = self.plot_button_frame, relwidth=0.05, relheight=0.5, relx = 0.15, rely=0)

        # Button to remove datasets
        self.remove_dataset_button = tk.Button(self.plot_button_frame,
                                             text="-",
                                             fg='white',
                                             bg='#F21112',
                                             activebackground='white',
                                             activeforeground='#F21112')
        self.remove_dataset_button.place(in_ = self.plot_button_frame, relwidth=0.05, relheight=0.5, relx= 0.15, rely=0.5)
        self.remove_dataset_button["command"] = self.remove_dataset

        self.fit_button = tk.Button(self.plot_button_frame,
                                       text="FIT",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')
        self.fit_button.place(in_ = self.plot_button_frame, relwidth=0.1, relheight=1, relx = 0.85)
        self.fit_button["command"] = self.fit_activate
        self.want_fit = [tk.BooleanVar()]
        self.want_fit[0].set(0)

        # Variable to store all the buttons
        self.buttons = [self.up_button,
                  self.compile_button,
                  self.plot_button,
                  self.plot_function_button,
                  self.import_data,
                  self.add_dataset_button,
                  self.fit_button,
                  self.export_latex,
                  self.remove_dataset_button,
                  self.add_labels,
                  self.add_text
                  ]

        for button in self.buttons:
            self._add_hover(button)
            button["font"] = ("Roboto",int(0.011*self.master.winfo_width()))

        # Create a menu bar
        # this self.menu_bar is the top-level one; it contains the others
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        # This is the file button in self.menu_bar
        self.file_options = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", underline=0, menu=self.file_options)
        self.file_options.add_command(label='Start New', command = self.restart, accelerator="Ctrl+N")
        self.file_options.add_command(label='Save Local', command=self.save_everything, accelerator="Ctrl+S")
        self.file_options.add_command(label='Save Local As', command=self.save_as, accelerator="Ctrl+Shift+S")
        self.file_options.add_command(label='Open Project', command=self.open_project, accelerator="Ctrl+O")
        self.file_options.add_command(label='Export Image', command=self.export_image, accelerator="Ctrl+Shift+E")

        # Button in self.menu_bar to choose the plot options
        self.plot_options = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Plot options", menu=self.plot_options)

        # These 3 variables let the user choose what they want to see
        self.want_points = [tk.BooleanVar()]
        self.want_line = [tk.BooleanVar()]
        self.want_error = [tk.BooleanVar()]
        # Default values for those variables
        self.want_points[0].set(1)
        self.want_line[0].set(0)
        self.want_error[0].set(1)

        # Here we add the 3 checkbuttons of the checklist of what the user wants to read,
        # the variables defined above record whether the user has each setting selected or not
        self.plot_options.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.want_points[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.want_line[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.want_error[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.want_fit[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.want_function[self.selected_dataset])

        # These 3 menus in self.menu_bar select the color of the markers (points), the line and the error bars
        self.choose_color = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Choose Colors", menu = self.choose_color)

        self.current_selection = 0

        self.marker_color_var = []
        self.line_color_var = []
        self.error_color_var = []
        self.func_fit_color_var = []
        self.func_plot_color_var = []

        self.marker_color_var.append('black')
        self.line_color_var.append('black')
        self.error_color_var.append('black')
        self.func_fit_color_var.append('black')
        self.func_plot_color_var.append('black')

        # Here I'm just putting the checkbuttons in the boxes
        self.choose_color.add_command(label = 'Marker Color', command = lambda: self.pick_color('marker_color_var'))
        self.choose_color.add_command(label = 'Connection Color', command = lambda: self.pick_color('line_color_var'))
        self.choose_color.add_command(label = 'Errorbar Color', command = lambda: self.pick_color('error_color_var'))
        self.choose_color.add_command(label = 'Plot Function Color', command = lambda: self.pick_color('func_plot_color_var'))
        self.choose_color.add_command(label = 'Fit Function Color', command = lambda: self.pick_color('func_fit_color_var'))

        self.datasets_to_plot = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label = "Choose Datasets", menu = self.datasets_to_plot)

        self.datasets_to_plot_var = []
        self.datasets_to_plot_var.append(tk.BooleanVar())
        self.datasets_to_plot_var[0].set(1)

        self.datasets_to_plot.add_checkbutton(label = "Plot Dataset 1", onvalue = 1, offvalue = 0, variable = self.datasets_to_plot_var[0] )

        # create the dropdown menu for the more advanced options
        self.advanced = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label = 'Advanced', menu = self.advanced)
        self.advanced.add_command(label='Tick Placement', command = self.set_ticks)
        self.advanced.add_command(label='Figure Ratio', command = self.set_ratio)
        self.advanced.add_command(label='Generate Residue Plot', command = self.create_residue_data, accelerator = 'Ctrl+Shift+R')

        # create the section to access online mode
        self.online = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='CHIMERA Online', menu = self.online)
        self.online.add_command(label='Login', command = self.create_login, accelerator = 'Ctrl + L')
        self.online.add_command(label='Create Account', command = self.setup_account)

        # create the dropdown menu for the help entries
        self.help = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label = 'Help', menu = self.help)
        self.help.add_command(label='Documentation', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/docs'))
        self.help.add_command(label='FAQs', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/faq'))
        self.help.add_command(label='About', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/about'))

        # Create the area to enter the independent variable
        self.independent_label = tk.Label(self.subframe_right_1,text="Independent Var", bg='#E4E4E4')
        self.independent_label["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.independent_label.place(relwidth=0.25, rely=0, relheight=0.1)
        self.independent_entry = tk.Entry(self.subframe_right_1, font=30)
        self.independent_entry.place(relwidth=0.30, rely=0, relheight=0.1, relx = 0.27)
        self.independent_entry.insert(0, 'x')
        self.independent_entry.focus_set()

        # Create the area to enter the parameters
        self.parameter_label = tk.Label(self.subframe_right_1,text="Parameter", bg='#E4E4E4')
        self.parameter_label["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.parameter_label.place(relwidth=0.22, rely=0.1, relheight=0.1)
        self.parameter_entry = tk.Entry(self.subframe_right_1, font=30)
        self.parameter_entry.place(relwidth=0.55, rely=0.1, relheight=0.1,relx = 0.27)
        self.parameter_entry.insert(0, "A,omega,phi,lambda")
        self.parameter_entry.focus_set()

        # Create the area where the function is entered
        self.function_label = tk.Label(self.subframe_right_1,text= "Function", bg='#E4E4E4')
        self.function_label["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.function_label.place(relwidth=0.22, rely=0.2, relheight=0.1)
        self.function_entry = tk.Entry(self.subframe_right_1, font=30)
        self.function_entry.place(relwidth=0.55,relx=0.27, rely=0.2, relheight=0.1)
        self.function_entry.insert(0, "A*sin(omega*x+phi)*exp(-lambda*x)")
        self.function_entry.focus_set()

        self.autoscale_x = tk.BooleanVar()
        self.autoscale_x.set(1)
        self.x_axis_autoscale = tk.Checkbutton(self.subframe_right_3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.autoscale_x, text = 'Autoscale', anchor = 'w')
        self.x_axis_autoscale.place(in_ = self.subframe_right_3, relwidth = 0.295, relheight = 0.05, rely = 0.4, relx = 0.05)

        self.log_x = tk.BooleanVar()
        self.log_x.set(0)
        self.log_x_button = tk.Checkbutton(self.subframe_right_3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.log_x, text = 'Log Scale', anchor = 'w')
        self.log_x_button.place(in_ = self.subframe_right_3, relwidth = 0.295, relheight = 0.05, rely = 0.45, relx = 0.05)

        self.x_axis_label = tk.Label(self.subframe_right_3, text="X Axis", bg='#E4E4E4')
        self.x_axis_label.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight=0.1, relx=0.2, rely=0)

        self.y_axis_label = tk.Label(self.subframe_right_3, text="Y Axis", bg='#E4E4E4')
        self.y_axis_label.place(in_ = self.subframe_right_3, relwidth = 0.5, relheight=0.1, relx=0.5, rely=0)

        self.x_axis_range_label = tk.Label(self.subframe_right_3, text = "Range: from", bg='#E4E4E4')
        self.x_axis_range_label.place(in_ = self.subframe_right_3, relwidth=0.2, relheight=0.1, relx = 0, rely = 0.1)

        self.remove_autoscale = True
        def remove_auto_x(event):
            if self.count == 2 and self.remove_autoscale:
                self.autoscale_x.set(0)
        def remove_auto_y(event):
            if self.count == 2 and self.remove_autoscale:
                self.autoscale_y.set(0)

        x_min = tk.StringVar()
        x_min.trace("w", lambda name, index, mode, x_min=x_min: remove_auto_x(x_min))
        self.x_axis_min_entry = tk.Entry(self.subframe_right_3, justify='center', textvariable=x_min)
        self.x_axis_min_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight=0.1, relx=0.2, rely=0.1)
        self.x_axis_min_entry.insert(0, "0")

        self.x_axis_to_label = tk.Label(self.subframe_right_3, text = "to", bg='#E4E4E4')
        self.x_axis_to_label.place(in_ = self.subframe_right_3, relwidth=0.05, relheight=0.1, relx=0.3, rely=0.1)

        x_max = tk.StringVar()
        x_max.trace('w', lambda name, index, mode, x_min=x_min: remove_auto_x(x_max))
        self.x_axis_max_entry = tk.Entry(self.subframe_right_3, justify='center', textvariable=x_max)
        self.x_axis_max_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight=0.1, relx=0.35, rely=0.1)
        self.x_axis_max_entry.insert(0, "10")

        self.x_axis_title_label = tk.Label(self.subframe_right_3, text = "Title", bg='#E4E4E4')
        self.x_axis_title_label.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight = 0.1, relx = 0, rely=0.25)

        self.x_axis_title_entry = tk.Entry(self.subframe_right_3)
        self.x_axis_title_entry.place(in_ = self.subframe_right_3, relwidth = 0.3, relheight = 0.1, relx = 0.1, rely=0.25)
        self.x_axis_title_entry.insert(0, "x")

        self.x_axis_tick_space_label = tk.Label(self.subframe_right_3, text = "Tick Spacing", bg='#E4E4E4')
        self.x_axis_tick_space_label.place(in_=self.subframe_right_3, relwidth = 0.22, relheight = 0.1, relx=0.175, rely= 0.4)

        x_space = tk.StringVar()
        x_space.trace('w', lambda name, index, mode, x_space=x_space: remove_auto_x(x_space))
        self.x_axis_tick_space_entry = tk.Entry(self.subframe_right_3, textvariable=x_space)
        self.x_axis_tick_space_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight = 0.1, relx = 0.35, rely=0.45, anchor="w")
        self.x_axis_tick_space_entry.insert(0, "1")

        self.autoscale_y = tk.BooleanVar()
        self.autoscale_y.set(1)
        self.y_axis_auto_scale = tk.Checkbutton(self.subframe_right_3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.autoscale_y, text = 'Autoscale', anchor = 'w')
        self.y_axis_auto_scale.place(in_ = self.subframe_right_3, relwidth = 0.295, relheight = 0.05, rely = 0.4, relx = 0.55)

        self.log_y = tk.BooleanVar()
        self.log_y.set(0)
        self.log_y_button = tk.Checkbutton(self.subframe_right_3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.log_y, text = 'Log Scale', anchor = 'w')
        self.log_y_button.place(in_ = self.subframe_right_3, relwidth = 0.295, relheight = 0.05, rely = 0.45, relx = 0.55)

        self.y_axis_range_label = tk.Label(self.subframe_right_3, text = "Range: from", bg='#E4E4E4')
        self.y_axis_range_label.place(in_ = self.subframe_right_3, relwidth=0.2, relheight=0.1, relx = 0.50, rely = 0.1)

        y_min = tk.StringVar()
        y_min.trace('w', lambda name, index, mode, y_min=y_min: remove_auto_y(y_min))
        self.y_axis_min_entry = tk.Entry(self.subframe_right_3, justify='center', textvariable=y_min)
        self.y_axis_min_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight=0.1, relx=0.70, rely=0.1)
        self.y_axis_min_entry.insert(0, "0")

        self.y_axis_to_label = tk.Label(self.subframe_right_3, text = "to", bg='#E4E4E4')
        self.y_axis_to_label.place(in_ = self.subframe_right_3, relwidth=0.05, relheight=0.1, relx=0.80, rely=0.1)

        y_max = tk.StringVar()
        y_max.trace('w', lambda name, index, mode, y_max=y_max: remove_auto_y(y_max))
        self.y_axis_max_entry = tk.Entry(self.subframe_right_3, justify='center', textvariable=y_max)
        self.y_axis_max_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight=0.1, relx=0.85, rely=0.1)
        self.y_axis_max_entry.insert(0, "10")

        self.y_axis_title_label = tk.Label(self.subframe_right_3, text = "Title", bg='#E4E4E4')
        self.y_axis_title_label.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight = 0.1, relx = 0.5, rely=0.25)

        self.y_axis_title_entry = tk.Entry(self.subframe_right_3)
        self.y_axis_title_entry.place(in_ = self.subframe_right_3, relwidth = 0.3, relheight = 0.1, relx = 0.6, rely=0.25)
        self.y_axis_title_entry.insert(0, "y")

        self.y_axis_tick_space_label = tk.Label(self.subframe_right_3, text = "Tick Spacing", bg='#E4E4E4')
        self.y_axis_tick_space_label.place(in_=self.subframe_right_3, relwidth = 0.22, relheight = 0.1, relx = 0.675, rely= 0.4)

        y_space = tk.StringVar()
        y_space.trace('w', lambda name, index, mode, y_space=y_space: remove_auto_y(y_space))
        self.y_axis_tick_space_entry = tk.Entry(self.subframe_right_3, textvariable=y_space)
        self.y_axis_tick_space_entry.place(in_ = self.subframe_right_3, relwidth = 0.1, relheight = 0.1, relx=0.85, rely=0.45, anchor = "w")
        self.y_axis_tick_space_entry.insert(0, "1")

        self.line_width = []
        self.marker_size = []
        self.error_width = []
        self.func_plot_width = []
        self.func_fit_width = []

        self.line_width.append(tk.DoubleVar())
        self.marker_size.append(tk.DoubleVar())
        self.error_width.append(tk.DoubleVar())
        self.func_plot_width.append(tk.DoubleVar())
        self.func_fit_width.append(tk.DoubleVar())

        self.line_width[0].set(2)
        self.marker_size[0].set(2)
        self.error_width[0].set(2)
        self.func_plot_width[0].set(2)
        self.func_fit_width[0].set(2)

        self.line_scale_label = tk.Label(self.subframe_right_3, text = 'Connection Width', bg = '#E4E4E4')
        self.line_scale_label['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.line_scale_label.place(in_ = self.subframe_right_3, relwidth = 0.3, relx = 0.02, rely=0.56)
        self.line_scale_label_value = tk.Label(self.subframe_right_3, text = '2.0', bg = '#E4E4E4')
        self.line_scale_label_value['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.line_scale_label_value.place(in_ = self.subframe_right_3, relx = 0.55, rely=0.56)
        self.line_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.line_slider, showvalue = False, variable = self.line_width[0])
        self.line_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.56, relheight=0.06)
        self.line_width_scale['width'] = 0.025*self.master.winfo_width()
        self.line_width_scale['state'] = tk.DISABLED

        self.marker_scale_label = tk.Label(self.subframe_right_3, text = 'Marker Size', bg = '#E4E4E4')
        self.marker_scale_label['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.marker_scale_label.place(in_ = self.subframe_right_3, relwidth = 0.3, relx = 0.02, rely=0.64)
        self.marker_scale_label_value = tk.Label(self.subframe_right_3, text = '2.0', bg = '#E4E4E4')
        self.marker_scale_label_value['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.marker_scale_label_value.place(in_ = self.subframe_right_3, relx = 0.55, rely=0.64)
        self.marker_sizescale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.marker_slider,showvalue =False, variable = self.marker_size[0])
        self.marker_sizescale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.64, relheight=0.06)
        self.marker_sizescale['width'] = 0.025*self.master.winfo_width()
        self.marker_sizescale['state'] = tk.DISABLED

        self.error_scale_label = tk.Label(self.subframe_right_3, text = 'Errorbar Width', bg = '#E4E4E4')
        self.error_scale_label['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.error_scale_label.place(in_ = self.subframe_right_3,relwidth = 0.3, relx = 0.02, rely=0.88)
        self.error_scale_label_value = tk.Label(self.subframe_right_3, text = '2.0', bg = '#E4E4E4')
        self.error_scale_label_value['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.error_scale_label_value.place(in_ = self.subframe_right_3, relx = 0.55, rely=0.88)
        self.error_size_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.error_slider, showvalue = False, variable = self.error_width[0])
        self.error_size_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.88, relheight=0.06)
        self.error_size_scale['width'] = 0.025*self.master.winfo_width()
        self.error_size_scale['state'] = tk.DISABLED

        self.func_plot_scale_label = tk.Label(self.subframe_right_3, text = 'Plot Func. Width', bg = '#E4E4E4')
        self.func_plot_scale_label['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.func_plot_scale_label.place(in_ = self.subframe_right_3,relwidth = 0.3, relx = 0.02, rely=0.72)
        self.func_plot_scale_label_value = tk.Label(self.subframe_right_3, text = '2.0', bg = '#E4E4E4')
        self.func_plot_scale_label_value['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.func_plot_scale_label_value.place(in_ = self.subframe_right_3, relx = 0.55, rely=0.72)
        self.func_plot_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.func_plot_slider, showvalue = False, variable = self.func_plot_width[0])
        self.func_plot_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.72, relheight=0.06)
        self.func_plot_width_scale['width'] = 0.025*self.master.winfo_width()
        self.func_plot_width_scale['state'] = tk.DISABLED

        self.func_fit_scale_label = tk.Label(self.subframe_right_3, text = 'Fit Func. Width', bg = '#E4E4E4')
        self.func_fit_scale_label['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.func_fit_scale_label.place(in_ = self.subframe_right_3,relwidth = 0.3, relx = 0.022, rely=0.80)
        self.func_fit_scale_label_value = tk.Label(self.subframe_right_3, text = '2.0', bg = '#E4E4E4')
        self.func_fit_scale_label_value['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.func_fit_scale_label_value.place(in_ = self.subframe_right_3, relx = 0.55, rely=0.80)
        self.func_fit_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.func_fit_slider, showvalue = False, variable = self.func_fit_width[0])
        self.func_fit_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.80, relheight=0.06)
        self.func_fit_width_scale['width'] = 0.025*self.master.winfo_width()
        self.func_fit_width_scale['state'] = tk.DISABLED

        self.marker_option = tk.StringVar()
        self.marker_option_translater = []

        self.line_option = tk.StringVar()
        self.line_option_translater = []

        self.error_option = tk.StringVar()
        self.error_option_translater = []

        self.func_plot_option = tk.StringVar()
        self.func_plot_option_translater = []

        self.func_fit_option = tk.StringVar()
        self.func_fit_option_translater = []

        self.marker_size_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Triangle', 'Square', 'Circle', 'Star', 'Diamond', 'X'], textvariable = self.marker_option)
        self.marker_size_combo.current(2)
        self.marker_size_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.64, relheight=0.065)
        self.marker_size_combo.bind("<<ComboboxSelected>>", self.marker_selector)
        self.marker_option_translater.append('o')

        self.line_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.line_option)
        self.line_style_combo.current(0)
        self.line_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.56, relheight=0.065)
        self.line_style_combo.bind("<<ComboboxSelected>>", self.line_selector)
        self.line_option_translater.append('-')

        self.func_plot_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.func_plot_option)
        self.func_plot_style_combo.current(0)
        self.func_plot_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.72, relheight=0.065)
        self.func_plot_style_combo.bind("<<ComboboxSelected>>", self.func_plot_selector)
        self.func_plot_option_translater.append('-')

        self.func_fit_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.func_fit_option)
        self.func_fit_style_combo.current(0)
        self.func_fit_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.8, relheight=0.065)
        self.func_fit_style_combo.bind("<<ComboboxSelected>>", self.func_fit_selector)
        self.func_fit_option_translater.append('-')

        sty = ttk.Style(self.subframe_right_3)
        sty.configure("TSeparator", background="#F21112")

        self.chisq_label = tk.Label(self.frame_right, text = u'\u03C7'+'\N{SUPERSCRIPT TWO}'+'/'+'\u03BD', bg='#E4E4E4')
        self.chisq_label.place(rely=0.46, relx = 0.7)
        self.chisq_entry = tk.Entry(self.frame_right, justify='center')
        self.r2_label = tk.Label(self.frame_right, text=u'R\u00B2', bg='#E4E4E4')
        self.r2_label.place(rely=0.46, relx=0.2)
        self.r2_entry = tk.Entry(self.frame_right, justify='center')
        try: self.chisq_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.3e}")
        except Exception: pass
        try: self.r2_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.6e}")
        except Exception: pass
        self.chisq_entry.place(rely = 0.46, relx=0.75, relwidth=0.08)
        self.chisq_entry.config(state = 'readonly')
        self.r2_entry.place(rely=0.46, relx=0.24, relwidth=0.08)
        self.r2_entry.config(state='readonly')

        sep = ttk.Separator(self.subframe_right_3, orient = tk.VERTICAL)
        sep.place(in_ = self.subframe_right_3, relx=0.5, relheight = 0.5, rely=0.05)

        sep1 = ttk.Separator(self.subframe_right_3, orient = tk.HORIZONTAL )
        sep1.place(in_ = self.subframe_right_3, relx=0.3, rely=0.05, relwidth = 0.4)

        sep2 = ttk.Separator(self.subframe_right_3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframe_right_3, relx=0, rely=0.05, relwidth = 0.2)

        sep2 = ttk.Separator(self.subframe_right_3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframe_right_3, relx=0.8, rely=0.05, relwidth = 0.2)

        sep3 = ttk.Separator(self.subframe_right_3, orient = tk.HORIZONTAL)
        sep3.place(in_ = self.subframe_right_3, relx=0, rely=0.55, relwidth=1)

        # Create the text corresponding to the first dataset
        # The dataset_text variable holds the text present in each dataset
        self.dataset_text = []
        self.dataset_text.append("0.000000 0.200000 -4.220083 5.000000\n0.040080 0.200000 20.306079 5.000000\n0.080160 0.200000 29.509556 5.000000\n0.120240 0.200000 48.493836 5.000000\n0.160321 0.200000 68.609105 5.000000\n0.200401 0.200000 73.976780 5.000000\n0.240481 0.200000 90.348206 5.000000\n0.280561 0.200000 107.429971 5.000000\n0.320641 0.200000 108.084140 5.000000\n0.360721 0.200000 127.051755 5.000000\n0.400802 0.200000 134.937988 5.000000\n0.440882 0.200000 129.461255 5.000000\n0.480962 0.200000 150.258016 5.000000\n0.521042 0.200000 156.667045 5.000000\n0.561122 0.200000 172.252046 5.000000\n0.601202 0.200000 163.602874 5.000000\n0.641283 0.200000 171.550207 5.000000\n0.681363 0.200000 163.741960 5.000000\n0.721443 0.200000 173.751143 5.000000\n0.761523 0.200000 168.647742 5.000000\n0.801603 0.200000 170.747842 5.000000\n0.841683 0.200000 170.096170 5.000000\n0.881764 0.200000 160.471599 5.000000\n0.921844 0.200000 150.175606 5.000000\n0.961924 0.200000 152.733786 5.000000\n1.002004 0.200000 143.121698 5.000000\n1.042084 0.200000 146.264532 5.000000\n1.082164 0.200000 127.527399 5.000000\n1.122244 0.200000 119.731893 5.000000\n1.162325 0.200000 109.983294 5.000000\n1.202405 0.200000 107.143773 5.000000\n1.242485 0.200000 95.094167 5.000000\n1.282565 0.200000 92.440938 5.000000\n1.322645 0.200000 83.966296 5.000000\n1.362725 0.200000 66.828702 5.000000\n1.402806 0.200000 52.931513 5.000000\n1.442886 0.200000 36.324946 5.000000\n1.482966 0.200000 29.922973 5.000000\n1.523046 0.200000 7.976208 5.000000\n1.563126 0.200000 1.489428 5.000000\n1.603206 0.200000 -9.195030 5.000000\n1.643287 0.200000 -23.532098 5.000000\n1.683367 0.200000 -25.749417 5.000000\n1.723447 0.200000 -35.118530 5.000000\n1.763527 0.200000 -55.796327 5.000000\n1.803607 0.200000 -68.857647 5.000000\n1.843687 0.200000 -70.314311 5.000000\n1.883768 0.200000 -86.585397 5.000000\n1.923848 0.200000 -94.812446 5.000000\n1.963928 0.200000 -92.395743 5.000000\n2.004008 0.200000 -100.446687 5.000000\n2.044088 0.200000 -106.587079 5.000000\n2.084168 0.200000 -112.562231 5.000000\n2.124248 0.200000 -108.020072 5.000000\n2.164329 0.200000 -115.267282 5.000000\n2.204409 0.200000 -122.261355 5.000000\n2.244489 0.200000 -116.516333 5.000000\n2.284569 0.200000 -128.890452 5.000000\n2.324649 0.200000 -129.017330 5.000000\n2.364729 0.200000 -119.878573 5.000000\n2.404810 0.200000 -128.626340 5.000000\n2.444890 0.200000 -129.201100 5.000000\n2.484970 0.200000 -118.233865 5.000000\n2.525050 0.200000 -108.107293 5.000000\n2.565130 0.200000 -111.984111 5.000000\n2.605210 0.200000 -102.305572 5.000000\n2.645291 0.200000 -100.950003 5.000000\n2.685371 0.200000 -95.231812 5.000000\n2.725451 0.200000 -79.889093 5.000000\n2.765531 0.200000 -78.113814 5.000000\n2.805611 0.200000 -63.122766 5.000000\n2.845691 0.200000 -62.347123 5.000000\n2.885772 0.200000 -57.464439 5.000000\n2.925852 0.200000 -50.095949 5.000000\n2.965932 0.200000 -28.707316 5.000000\n3.006012 0.200000 -25.857203 5.000000\n3.046092 0.200000 -9.977920 5.000000\n3.086172 0.200000 -17.829600 5.000000\n3.126253 0.200000 -5.207881 5.000000\n3.166333 0.200000 3.204056 5.000000\n3.206413 0.200000 28.687108 5.000000\n3.246493 0.200000 27.405625 5.000000\n3.286573 0.200000 33.953569 5.000000\n3.326653 0.200000 36.077991 5.000000\n3.366733 0.200000 40.915877 5.000000\n3.406814 0.200000 52.547911 5.000000\n3.446894 0.200000 44.613076 5.000000\n3.486974 0.200000 68.303123 5.000000\n3.527054 0.200000 79.331374 5.000000\n3.567134 0.200000 80.976405 5.000000\n3.607214 0.200000 81.713514 5.000000\n3.647295 0.200000 78.158750 5.000000\n3.687375 0.200000 93.019663 5.000000\n3.727455 0.200000 86.270143 5.000000\n3.767535 0.200000 88.670332 5.000000\n3.807615 0.200000 92.136118 5.000000\n3.847695 0.200000 93.761178 5.000000\n3.887776 0.200000 88.573773 5.000000\n3.927856 0.200000 94.170806 5.000000\n3.967936 0.200000 86.460671 5.000000\n4.008016 0.200000 94.492714 5.000000\n4.048096 0.200000 90.596259 5.000000\n4.088176 0.200000 87.304429 5.000000\n4.128257 0.200000 87.532433 5.000000\n4.168337 0.200000 72.274535 5.000000\n4.208417 0.200000 66.245807 5.000000\n4.248497 0.200000 73.091925 5.000000\n4.288577 0.200000 60.468736 5.000000\n4.328657 0.200000 60.017482 5.000000\n4.368737 0.200000 58.271275 5.000000\n4.408818 0.200000 45.748794 5.000000\n4.448898 0.200000 40.314987 5.000000\n4.488978 0.200000 49.452884 5.000000\n4.529058 0.200000 26.422226 5.000000\n4.569138 0.200000 22.944044 5.000000\n4.609218 0.200000 16.095398 5.000000\n4.649299 0.200000 12.753866 5.000000\n4.689379 0.200000 6.909262 5.000000\n4.729459 0.200000 1.212596 5.000000\n4.769539 0.200000 3.055895 5.000000\n4.809619 0.200000 -14.751589 5.000000\n4.849699 0.200000 -20.025156 5.000000\n4.889780 0.200000 -31.446377 5.000000\n4.929860 0.200000 -31.690325 5.000000\n4.969940 0.200000 -40.431643 5.000000\n5.010020 0.200000 -33.717315 5.000000\n5.050100 0.200000 -43.198812 5.000000\n5.090180 0.200000 -45.091974 5.000000\n5.130261 0.200000 -54.723450 5.000000\n5.170341 0.200000 -52.448394 5.000000\n5.210421 0.200000 -54.470856 5.000000\n5.250501 0.200000 -66.779061 5.000000\n5.290581 0.200000 -67.979157 5.000000\n5.330661 0.200000 -66.643499 5.000000\n5.370741 0.200000 -72.572019 5.000000\n5.410822 0.200000 -65.619787 5.000000\n5.450902 0.200000 -70.286317 5.000000\n5.490982 0.200000 -66.983429 5.000000\n5.531062 0.200000 -66.396522 5.000000\n5.571142 0.200000 -58.528374 5.000000\n5.611222 0.200000 -63.276543 5.000000\n5.651303 0.200000 -57.647651 5.000000\n5.691383 0.200000 -58.155591 5.000000\n5.731463 0.200000 -59.947225 5.000000\n5.771543 0.200000 -56.605605 5.000000\n5.811623 0.200000 -48.498689 5.000000\n5.851703 0.200000 -44.906405 5.000000\n5.891784 0.200000 -35.595236 5.000000\n5.931864 0.200000 -36.182548 5.000000\n5.971944 0.200000 -35.946789 5.000000\n6.012024 0.200000 -26.033401 5.000000\n6.052104 0.200000 -21.916403 5.000000\n6.092184 0.200000 -18.744021 5.000000\n6.132265 0.200000 -19.034690 5.000000\n6.172345 0.200000 -3.464158 5.000000\n6.212425 0.200000 -9.989100 5.000000\n6.252505 0.200000 -18.031833 5.000000\n6.292585 0.200000 -0.473183 5.000000\n6.332665 0.200000 7.128211 5.000000\n6.372745 0.200000 10.383434 5.000000\n6.412826 0.200000 8.963351 5.000000\n6.452906 0.200000 17.957149 5.000000\n6.492986 0.200000 18.615820 5.000000\n6.533066 0.200000 28.568868 5.000000\n6.573146 0.200000 36.890251 5.000000\n6.613226 0.200000 28.441762 5.000000\n6.653307 0.200000 37.849841 5.000000\n6.693387 0.200000 32.059030 5.000000\n6.733467 0.200000 28.204411 5.000000\n6.773547 0.200000 48.291845 5.000000\n6.813627 0.200000 50.102458 5.000000\n6.853707 0.200000 42.508948 5.000000\n6.893788 0.200000 46.535820 5.000000\n6.933868 0.200000 48.448955 5.000000\n6.973948 0.200000 55.769351 5.000000\n7.014028 0.200000 54.062273 5.000000\n7.054108 0.200000 49.087978 5.000000\n7.094188 0.200000 57.951041 5.000000\n7.134269 0.200000 46.272647 5.000000\n7.174349 0.200000 47.668543 5.000000\n7.214429 0.200000 46.921758 5.000000\n7.254509 0.200000 42.871597 5.000000\n7.294589 0.200000 38.610888 5.000000\n7.334669 0.200000 39.815706 5.000000\n7.374749 0.200000 37.159121 5.000000\n7.414830 0.200000 31.996323 5.000000\n7.454910 0.200000 38.671490 5.000000\n7.494990 0.200000 30.193041 5.000000\n7.535070 0.200000 24.469951 5.000000\n7.575150 0.200000 27.829150 5.000000\n7.615230 0.200000 14.374572 5.000000\n7.655311 0.200000 18.588095 5.000000\n7.695391 0.200000 19.879006 5.000000\n7.735471 0.200000 14.032910 5.000000\n7.775551 0.200000 4.663582 5.000000\n7.815631 0.200000 -2.575609 5.000000\n7.855711 0.200000 -1.598550 5.000000\n7.895792 0.200000 -2.158824 5.000000\n7.935872 0.200000 -7.086892 5.000000\n7.975952 0.200000 -14.662059 5.000000\n8.016032 0.200000 -21.428117 5.000000\n8.056112 0.200000 -15.659874 5.000000\n8.096192 0.200000 -20.559999 5.000000\n8.136273 0.200000 -21.496457 5.000000\n8.176353 0.200000 -15.018610 5.000000\n8.216433 0.200000 -27.698434 5.000000\n8.256513 0.200000 -24.037836 5.000000\n8.296593 0.200000 -31.816119 5.000000\n8.336673 0.200000 -32.542239 5.000000\n8.376754 0.200000 -41.213083 5.000000\n8.416834 0.200000 -33.509833 5.000000\n8.456914 0.200000 -37.619873 5.000000\n8.496994 0.200000 -27.887921 5.000000\n8.537074 0.200000 -31.248875 5.000000\n8.577154 0.200000 -37.039771 5.000000\n8.617234 0.200000 -33.194420 5.000000\n8.657315 0.200000 -35.690008 5.000000\n8.697395 0.200000 -26.343880 5.000000\n8.737475 0.200000 -35.840091 5.000000\n8.777555 0.200000 -19.936502 5.000000\n8.817635 0.200000 -33.370277 5.000000\n8.857715 0.200000 -32.042716 5.000000\n8.897796 0.200000 -26.828380 5.000000\n8.937876 0.200000 -34.670138 5.000000\n8.977956 0.200000 -30.877291 5.000000\n9.018036 0.200000 -28.066351 5.000000\n9.058116 0.200000 -16.888626 5.000000\n9.098196 0.200000 -21.047476 5.000000\n9.138277 0.200000 -16.292002 5.000000\n9.178357 0.200000 -21.978134 5.000000\n9.218437 0.200000 -10.110033 5.000000\n9.258517 0.200000 -7.966969 5.000000\n9.298597 0.200000 -14.467292 5.000000\n9.338677 0.200000 -9.640137 5.000000\n9.378758 0.200000 -7.084470 5.000000\n9.418838 0.200000 -1.477334 5.000000\n9.458918 0.200000 0.219948 5.000000\n9.498998 0.200000 2.325002 5.000000\n9.539078 0.200000 6.512176 5.000000\n9.579158 0.200000 5.541867 5.000000\n9.619238 0.200000 11.372225 5.000000\n9.659319 0.200000 13.947301 5.000000\n9.699399 0.200000 13.590980 5.000000\n9.739479 0.200000 13.216626 5.000000\n9.779559 0.200000 16.390693 5.000000\n9.819639 0.200000 27.023087 5.000000\n9.859719 0.200000 17.697813 5.000000\n9.899800 0.200000 27.454231 5.000000\n9.939880 0.200000 23.537202 5.000000\n9.979960 0.200000 23.818608 5.000000\n10.020040 0.200000 14.047478 5.000000\n10.060120 0.200000 32.127949 5.000000\n10.100200 0.200000 24.409514 5.000000\n10.140281 0.200000 23.204936 5.000000\n10.180361 0.200000 26.134774 5.000000\n10.220441 0.200000 27.358767 5.000000\n10.260521 0.200000 20.644017 5.000000\n10.300601 0.200000 21.998389 5.000000\n10.340681 0.200000 17.857595 5.000000\n10.380762 0.200000 21.323762 5.000000\n10.420842 0.200000 20.252274 5.000000\n10.460922 0.200000 19.224765 5.000000\n10.501002 0.200000 16.624415 5.000000\n10.541082 0.200000 19.284652 5.000000\n10.581162 0.200000 27.722624 5.000000\n10.621242 0.200000 10.830659 5.000000\n10.661323 0.200000 18.016111 5.000000\n10.701403 0.200000 12.131010 5.000000\n10.741483 0.200000 25.532536 5.000000\n10.781563 0.200000 0.247603 5.000000\n10.821643 0.200000 6.395373 5.000000\n10.861723 0.200000 13.165740 5.000000\n10.901804 0.200000 3.000769 5.000000\n10.941884 0.200000 2.168944 5.000000\n10.981964 0.200000 3.228704 5.000000\n11.022044 0.200000 -1.992237 5.000000\n11.062124 0.200000 0.717827 5.000000\n11.102204 0.200000 -2.348446 5.000000\n11.142285 0.200000 -8.534931 5.000000\n11.182365 0.200000 -6.482811 5.000000\n11.222445 0.200000 -12.571645 5.000000\n11.262525 0.200000 -10.239189 5.000000\n11.302605 0.200000 -23.445802 5.000000\n11.342685 0.200000 -9.620284 5.000000\n11.382766 0.200000 -9.469368 5.000000\n11.422846 0.200000 -14.469548 5.000000\n11.462926 0.200000 -16.057060 5.000000\n11.503006 0.200000 -15.463553 5.000000\n11.543086 0.200000 -29.203668 5.000000\n11.583166 0.200000 -21.897996 5.000000\n11.623246 0.200000 -19.576155 5.000000\n11.663327 0.200000 -9.354795 5.000000\n11.703407 0.200000 -11.857799 5.000000\n11.743487 0.200000 -18.484859 5.000000\n11.783567 0.200000 -17.001798 5.000000\n11.823647 0.200000 -20.839559 5.000000\n11.863727 0.200000 -10.625569 5.000000\n11.903808 0.200000 -12.561239 5.000000\n11.943888 0.200000 -10.337802 5.000000\n11.983968 0.200000 -20.437828 5.000000\n12.024048 0.200000 -21.202328 5.000000\n12.064128 0.200000 -20.814618 5.000000\n12.104208 0.200000 -9.093745 5.000000\n12.144289 0.200000 -10.776351 5.000000\n12.184369 0.200000 -14.682031 5.000000\n12.224449 0.200000 -15.557082 5.000000\n12.264529 0.200000 -8.452130 5.000000\n12.304609 0.200000 -5.284851 5.000000\n12.344689 0.200000 -6.043369 5.000000\n12.384770 0.200000 -8.505228 5.000000\n12.424850 0.200000 -3.082345 5.000000\n12.464930 0.200000 2.547971 5.000000\n12.505010 0.200000 3.798123 5.000000\n12.545090 0.200000 9.212148 5.000000\n12.585170 0.200000 -1.805794 5.000000\n12.625251 0.200000 7.187777 5.000000\n12.665331 0.200000 3.731835 5.000000\n12.705411 0.200000 9.221259 5.000000\n12.745491 0.200000 -7.587803 5.000000\n12.785571 0.200000 14.854788 5.000000\n12.825651 0.200000 1.033444 5.000000\n12.865731 0.200000 10.726527 5.000000\n12.905812 0.200000 15.855602 5.000000\n12.945892 0.200000 9.741655 5.000000\n12.985972 0.200000 12.129298 5.000000\n13.026052 0.200000 6.866070 5.000000\n13.066132 0.200000 13.327839 5.000000\n13.106212 0.200000 22.548522 5.000000\n13.146293 0.200000 12.441904 5.000000\n13.186373 0.200000 14.290439 5.000000\n13.226453 0.200000 18.981131 5.000000\n13.266533 0.200000 14.088621 5.000000\n13.306613 0.200000 18.580735 5.000000\n13.346693 0.200000 5.400956 5.000000\n13.386774 0.200000 13.922285 5.000000\n13.426854 0.200000 12.228760 5.000000\n13.466934 0.200000 14.367235 5.000000\n13.507014 0.200000 10.069593 5.000000\n13.547094 0.200000 9.403623 5.000000\n13.587174 0.200000 10.807500 5.000000\n13.627255 0.200000 8.994746 5.000000\n13.667335 0.200000 17.059241 5.000000\n13.707415 0.200000 5.944681 5.000000\n13.747495 0.200000 14.293543 5.000000\n13.787575 0.200000 11.252237 5.000000\n13.827655 0.200000 16.805709 5.000000\n13.867735 0.200000 4.094287 5.000000\n13.907816 0.200000 5.383987 5.000000\n13.947896 0.200000 12.449402 5.000000\n13.987976 0.200000 7.040040 5.000000\n14.028056 0.200000 2.234196 5.000000\n14.068136 0.200000 6.228159 5.000000\n14.108216 0.200000 -1.072208 5.000000\n14.148297 0.200000 -5.193341 5.000000\n14.188377 0.200000 -4.510789 5.000000\n14.228457 0.200000 -3.619780 5.000000\n14.268537 0.200000 4.591740 5.000000\n14.308617 0.200000 -5.416248 5.000000\n14.348697 0.200000 -1.694420 5.000000\n14.388778 0.200000 -0.238606 5.000000\n14.428858 0.200000 -2.555457 5.000000\n14.468938 0.200000 -4.215943 5.000000\n14.509018 0.200000 -2.086985 5.000000\n14.549098 0.200000 -8.206409 5.000000\n14.589178 0.200000 -6.998627 5.000000\n14.629259 0.200000 -11.455970 5.000000\n14.669339 0.200000 -8.796179 5.000000\n14.709419 0.200000 -4.568559 5.000000\n14.749499 0.200000 -9.766033 5.000000\n14.789579 0.200000 -14.257980 5.000000\n14.829659 0.200000 -8.425578 5.000000\n14.869739 0.200000 -21.594720 5.000000\n14.909820 0.200000 -6.706730 5.000000\n14.949900 0.200000 -22.397763 5.000000\n14.989980 0.200000 -14.721651 5.000000\n15.030060 0.200000 -6.735613 5.000000\n15.070140 0.200000 -6.340337 5.000000\n15.110220 0.200000 -2.445827 5.000000\n15.150301 0.200000 -9.874866 5.000000\n15.190381 0.200000 -1.413741 5.000000\n15.230461 0.200000 -8.766435 5.000000\n15.270541 0.200000 -5.677615 5.000000\n15.310621 0.200000 -3.008112 5.000000\n15.350701 0.200000 -2.927042 5.000000\n15.390782 0.200000 -13.984512 5.000000\n15.430862 0.200000 -5.995535 5.000000\n15.470942 0.200000 -14.618264 5.000000\n15.511022 0.200000 0.097088 5.000000\n15.551102 0.200000 -13.189818 5.000000\n15.591182 0.200000 0.355034 5.000000\n15.631263 0.200000 0.784178 5.000000\n15.671343 0.200000 0.266240 5.000000\n15.711423 0.200000 -2.829156 5.000000\n15.751503 0.200000 -0.311902 5.000000\n15.791583 0.200000 0.066581 5.000000\n15.831663 0.200000 -2.041654 5.000000\n15.871743 0.200000 5.305573 5.000000\n15.911824 0.200000 5.302848 5.000000\n15.951904 0.200000 5.252021 5.000000\n15.991984 0.200000 -2.231145 5.000000\n16.032064 0.200000 1.885515 5.000000\n16.072144 0.200000 6.379447 5.000000\n16.112224 0.200000 6.896192 5.000000\n16.152305 0.200000 8.838547 5.000000\n16.192385 0.200000 6.327971 5.000000\n16.232465 0.200000 6.743566 5.000000\n16.272545 0.200000 4.314842 5.000000\n16.312625 0.200000 4.302374 5.000000\n16.352705 0.200000 0.469928 5.000000\n16.392786 0.200000 7.795278 5.000000\n16.432866 0.200000 10.292563 5.000000\n16.472946 0.200000 1.007937 5.000000\n16.513026 0.200000 7.731705 5.000000\n16.553106 0.200000 8.774526 5.000000\n16.593186 0.200000 3.301125 5.000000\n16.633267 0.200000 5.489381 5.000000\n16.673347 0.200000 11.807418 5.000000\n16.713427 0.200000 6.936980 5.000000\n16.753507 0.200000 10.544944 5.000000\n16.793587 0.200000 3.398610 5.000000\n16.833667 0.200000 -1.275229 5.000000\n16.873747 0.200000 10.642082 5.000000\n16.913828 0.200000 1.769257 5.000000\n16.953908 0.200000 3.303666 5.000000\n16.993988 0.200000 0.219273 5.000000\n17.034068 0.200000 11.769642 5.000000\n17.074148 0.200000 -10.607201 5.000000\n17.114228 0.200000 -1.017754 5.000000\n17.154309 0.200000 2.763988 5.000000\n17.194389 0.200000 -1.423901 5.000000\n17.234469 0.200000 5.356608 5.000000\n17.274549 0.200000 6.227375 5.000000\n17.314629 0.200000 6.759017 5.000000\n17.354709 0.200000 5.116336 5.000000\n17.394790 0.200000 1.193953 5.000000\n17.434870 0.200000 0.091315 5.000000\n17.474950 0.200000 -6.167816 5.000000\n17.515030 0.200000 -7.607873 5.000000\n17.555110 0.200000 -6.554534 5.000000\n17.595190 0.200000 -8.763374 5.000000\n17.635271 0.200000 -9.999903 5.000000\n17.675351 0.200000 1.444506 5.000000\n17.715431 0.200000 -2.940430 5.000000\n17.755511 0.200000 -2.074974 5.000000\n17.795591 0.200000 -4.999610 5.000000\n17.835671 0.200000 -8.447734 5.000000\n17.875752 0.200000 -9.219865 5.000000\n17.915832 0.200000 -0.884357 5.000000\n17.955912 0.200000 -13.630628 5.000000\n17.995992 0.200000 -3.362859 5.000000\n18.036072 0.200000 -2.861015 5.000000\n18.076152 0.200000 0.459927 5.000000\n18.116232 0.200000 2.075756 5.000000\n18.156313 0.200000 1.742471 5.000000\n18.196393 0.200000 -4.681144 5.000000\n18.236473 0.200000 -11.362966 5.000000\n18.276553 0.200000 -10.926193 5.000000\n18.316633 0.200000 -3.513967 5.000000\n18.356713 0.200000 4.763483 5.000000\n18.396794 0.200000 -2.458590 5.000000\n18.436874 0.200000 -4.460571 5.000000\n18.476954 0.200000 -8.472226 5.000000\n18.517034 0.200000 -18.139443 5.000000\n18.557114 0.200000 -3.079748 5.000000\n18.597194 0.200000 2.546519 5.000000\n18.637275 0.200000 5.423287 5.000000\n18.677355 0.200000 -4.911763 5.000000\n18.717435 0.200000 -0.456041 5.000000\n18.757515 0.200000 1.675098 5.000000\n18.797595 0.200000 2.913273 5.000000\n18.837675 0.200000 -1.921587 5.000000\n18.877756 0.200000 -2.727984 5.000000\n18.917836 0.200000 8.666047 5.000000\n18.957916 0.200000 0.215012 5.000000\n18.997996 0.200000 2.999787 5.000000\n19.038076 0.200000 5.302385 5.000000\n19.078156 0.200000 1.706727 5.000000\n19.118236 0.200000 -0.960444 5.000000\n19.158317 0.200000 -2.947608 5.000000\n19.198397 0.200000 8.699859 5.000000\n19.238477 0.200000 3.165915 5.000000\n19.278557 0.200000 2.699166 5.000000\n19.318637 0.200000 7.007208 5.000000\n19.358717 0.200000 1.366691 5.000000\n19.398798 0.200000 5.806320 5.000000\n19.438878 0.200000 5.205500 5.000000\n19.478958 0.200000 6.384510 5.000000\n19.519038 0.200000 2.091265 5.000000\n19.559118 0.200000 1.740590 5.000000\n19.599198 0.200000 -1.249371 5.000000\n19.639279 0.200000 13.168858 5.000000\n19.679359 0.200000 6.457068 5.000000\n19.719439 0.200000 -2.875295 5.000000\n19.759519 0.200000 6.103446 5.000000\n19.799599 0.200000 2.828744 5.000000\n19.839679 0.200000 8.695443 5.000000\n19.879760 0.200000 -1.042130 5.000000\n19.919840 0.200000 1.382902 5.000000\n19.959920 0.200000 5.380195 5.000000\n20.000000 0.200000 4.680706 5.000000")

        self.data_list_var = tk.StringVar()

        # Variable showing which one is selected
        self.data_list_var.set('dataset 1')

        # Variable holding the datasets and their number
        self.data_list = ['dataset 1']

        # Create the dataset selector button; link it to the update_databox function
        self.dataset_selector = ttk.Combobox(self.plot_button_frame, textvariable = self.data_list_var, values = self.data_list, postcommand = self.update_combobox_values,font=("Roboto", 8))
        self.dataset_selector.place(relx = 0, relheight = 1, relwidth=0.15)
        self.dataset_selector.bind("<<ComboboxSelected>>", self.update_databox)

        # Create the box holding the data and insert the first dataset's text into it
        self.data_entry = (ScrolledText(self.subframe_left_2))
        self.data_entry.pack(expand = 1, fill = tk.X)
        self.data_entry.insert(tk.INSERT,self.dataset_text[0])

        # Basically the logic starts with something because otherwise the indices break later; a lazy solution
        # just give it the default text values
        self.abcissas = [[0, 0, 0, 0]]
        self.err_abcissas = [[0, 0, 0, 0]]
        self.ordenadas = [[0, 0, 0, 0]]
        self.err_ordenadas = [[0, 0, 0, 0]]

        self.abc=[[]]
        self.err_abc = [[]]
        self.ord = [[]]
        self.err_ord = [[]]

        self.selected_dataset = 0
        self.number_datasets = 1

        self.abc.append(np.array(self.abcissas[0]))
        self.err_abc.append(np.array(self.err_abcissas[0]))
        self.ord.append(np.array(self.err_abcissas[0]))
        self.err_ord.append(np.array(self.err_abcissas[0]))

        self.dataset_points = []
        self.update_parameter()

    def marker_selector(self,event):
        if(self.marker_option.get() == 'Circle'):
            self.marker_option_translater[self.selected_dataset] = 'o'

        if(self.marker_option.get() == 'Square'):
            self.marker_option_translater[self.selected_dataset] = 's'

        if(self.marker_option.get() == 'Triangle'):
            self.marker_option_translater[self.selected_dataset] = '^'

        if self.marker_option.get() == 'Star':
            self.marker_option_translater[self.selected_dataset] = '*'

        if self.marker_option.get() == 'Diamond':
            self.marker_option_translater[self.selected_dataset] = 'D'
        if self.marker_option.get() == 'X':
            self.marker_option_translater[self.selected_dataset] = 'x'

        self.plot_dataset()

    def line_selector(self,event):
        if self.line_option.get() == 'Solid':
            self.line_option_translater[self.selected_dataset] = '-'

        if self.line_option.get() == 'Dashed':
            self.line_option_translater[self.selected_dataset] = '--'

        if self.line_option.get() == 'Dotted':
            self.line_option_translater[self.selected_dataset] = ':'

        if self.line_option.get() == 'DashDot':
            self.line_option_translater[self.selected_dataset] = '-.'

        self.plot_dataset()

    def func_plot_selector(self,event):
        if self.func_plot_option.get() == 'Solid':
            self.func_plot_option_translater[self.selected_dataset] = '-'

        if self.func_plot_option.get() == 'Dashed':
            self.func_plot_option_translater[self.selected_dataset] = '--'

        if self.func_plot_option.get() == 'Dotted':
            self.func_plot_option_translater[self.selected_dataset] = ':'

        if self.func_plot_option.get() == 'DashDot':
            self.func_plot_option_translater[self.selected_dataset] = '-.'

        self.plot_dataset()

    def func_fit_selector(self,event):
        if self.func_fit_option.get() == 'Solid':
            self.func_fit_option_translater[self.selected_dataset] = '-'

        if self.func_fit_option.get() == 'Dashed':
            self.func_fit_option_translater[self.selected_dataset] = '--'

        if self.func_fit_option.get() == 'Dotted':
            self.func_fit_option_translater[self.selected_dataset] = ':'

        if self.func_fit_option.get() == 'DashDot':
            self.func_fit_option_translater[self.selected_dataset] = '-.'

        self.plot_dataset()

    def update_combobox_values(self):
        if (self.dataset_selector.get() in self.data_list) and (self.dataset_selector.get() != self.data_list[self.selected_dataset]):
            tk.messagebox.showwarning('REPEATED NAMES',f'There is already a dataset with the name {self.dataset_selector.get()}. Use a different one.')
            self.dataset_selector.set(self.data_list[self.selected_dataset])
        else:
            self.data_list[self.selected_dataset] = self.dataset_selector.get()
            self.dataset_selector.config(values = self.data_list)

    def restart(self, event=None):
        if tk.messagebox.askyesno('START NEW', 'Starting new will erase all progess in your current session. Are you sure you want_ to start new?'):
            self.create_scatter()

    def erase_all_windows(self):
        try: self.ratio_window.destroy()
        except Exception: pass
        try: self.ticks_window.destroy()
        except Exception: pass
        try: self.text_window.destroy()
        except Exception: pass
        try: self.labels_window.destroy()
        except Exception: pass
        try: self.export_window.destroy()
        except Exception: pass
        try: self.import_window.destroy()
        except Exception: pass
        try: self.login_window.destroy()
        except Exception: pass
        try: self.new_account_window.destroy()
        except Exception: pass
        try: self.edit_account_window.destroy()
        except Exception: pass
        try: self.connections_window.destroy()
        except Exception: pass
        try: self.new_connect_window.destroy()
        except Exception: pass
        try: self.groups_window.destroy()
        except Exception: pass
        try: self.group_settings_window.destroy()
        except Exception: pass
        try: self.projects_window.destroy()
        except Exception: pass

    def set_ratio(self):
        self.erase_all_windows()

        self.ratio_window = tk.Toplevel(self.master)
        self.ratio_window.title('Figure Ratio')
        self.ratio_window.geometry('500x250')
        self.ratio_window.configure(background='#E4E4E4')
        self.ratio_window.resizable(False,False)
        self.focus_window(self.ratio_window)

        text = """
        Here you can set the figure ratio for the graph. Keep in mind that the
        actual values you insert don't matter, only the ratio between them, i.e.
        1:1 is the same as 5:5, or 1:5 is the same as 2:10.
        """
        intro = tk.Label(self.ratio_window,text=text,bg='#E4E4E4',justify='left')
        intro['font'] = ('Roboto', int(15*self.master.winfo_width()/2350))
        intro.pack(side='top')

        frame_ratio = tk.Frame(self.ratio_window, bg='#E4E4E4')

        label1 = tk.Label(frame_ratio,text='Figure Ratio',bg='#E4E4E4',anchor='w')
        label1['font'] = ('Roboto',int(15*self.master.winfo_width()/2350))
        label1.pack(side='left',padx=20)

        self.width_ratio_entry = tk.Entry(frame_ratio,width=4,justify='center')
        self.width_ratio_entry.insert(0, self.width_ratio)
        self.width_ratio_entry.pack(side='left')

        label2 = tk.Label(frame_ratio,text=':',bg='#E4E4E4')
        label2['font'] = ('Roboto',int(15*self.master.winfo_width()/2350))
        label2.pack(side='left')

        self.height_ratio_entry = tk.Entry(frame_ratio,width=4,justify='center')
        self.height_ratio_entry.insert(0, self.height_ratio)
        self.height_ratio_entry.pack(side='left')

        frame_ratio.pack(side='top', pady=20)

        save_button = tk.Button(self.ratio_window,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_ratio
        save_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        # Change the colors on enter and leave
        self._add_hover(save_button)
        save_button.pack(side='top',pady=20)

    def save_ratio(self):
        temp_width = self.width_ratio_entry.get().replace(' ','')
        temp_height = self.height_ratio_entry.get().replace(' ','')

        try:
            float(temp_width)
        except Exception:
            tk.messagebox.showwarning('ERROR',f'Non-numerical input found ({temp_width}) in width entry. Please correct it.')
            return

        try:
            float(temp_height)
        except Exception:
            tk.messagebox.showwarning('ERROR',f'Non-numerical input found ({temp_height}) in height entry. Please correct it.')
            return

        self.width_ratio = float(temp_width)
        self.height_ratio = float(temp_height)

        self.ratio_window.destroy()

        if not hasattr(self, 'fig'):
            return

        self.plot_dataset()

    def set_ticks(self):
        self.erase_all_windows()

        self.ticks_window = tk.Toplevel(self.master)
        self.ticks_window.title('Ticks Placement')
        self.ticks_window.geometry('500x400')
        self.ticks_window.configure(background='#E4E4E4')
        self.ticks_window.resizable(False,False)
        self.focus_window(self.ticks_window)

        text = """
        Ticks are, by default, set equally spaced starting at the left-most (for
        x-axis) or bottom-most (for y-axis) edge of the graph. Here you can
        customize that.\n
        There are two ways to customize the ticks placement:
            - If you insert only one value, then they will remain equally spaced
              but will be forced to pass on that value
            - If you insert more than one value, separated by commas or spaces,
              then they will only pass on the values you write
        """
        intro = tk.Label(self.ticks_window,text=text,bg='#E4E4E4',justify='left')
        intro["font"] = ("Roboto",int(15*self.master.winfo_width()/2350))
        intro.pack(side='top')

        frame_x = tk.Frame(self.ticks_window,bg='#E4E4E4')

        x_axis = tk.Label(frame_x,text='X-Axis',bg='#E4E4E4',anchor='w')
        x_axis['font'] = ('Roboto', int(15*self.master.winfo_width()/2350))
        x_axis.pack(side='left',padx=20)

        self.x_ticks = tk.Entry(frame_x,width=50)
        x_content = ''
        for val in self.x_ticks_ref:
            x_content += f'{val:.2f} '
        self.x_ticks.insert(0, x_content)
        self.x_ticks.pack(side='right',padx=20)

        frame_x.pack(side='top',pady=20)

        frame_y = tk.Frame(self.ticks_window,bg='#E4E4E4')

        y_axis = tk.Label(frame_y,text='Y-Axis',bg='#E4E4E4',anchor='w')
        y_axis['font'] = ('Roboto', int(15*self.master.winfo_width()/2350))
        y_axis.pack(side='left',padx=20)

        self.y_ticks = tk.Entry(frame_y,width=50)
        y_content = ''
        for val in self.y_ticks_ref:
            y_content += f'{val:.2f} '
        self.y_ticks.insert(0, y_content)
        self.y_ticks.pack(side='right',padx=20)

        frame_y.pack(side='top',pady=20)

        save_button = tk.Button(self.ticks_window,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_ticks
        save_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        # Change the colors on enter and leave
        self._add_hover(save_button)
        save_button.pack(side='top',pady=20)

    def save_ticks(self):
        x_temp = [val for val in self.x_ticks.get().replace(',',' ').split(' ') if val]
        y_temp = [val for val in self.y_ticks.get().replace(',',' ').split(' ') if val]

        for val in x_temp:
            try:
                float(val)
            except Exception:
                tk.messagebox.showwarning('ERROR','Non-numerical input found in x-axis ticks. Please correct it.')
                return
        for val in y_temp:
            try:
                float(val)
            except Exception:
                tk.messagebox.showwarning('ERROR','Non-numerical input found in y-axis ticks. Please correct it.')
                return

        self.x_ticks_ref = [float(val) for val in x_temp]
        self.y_ticks_ref = [float(val) for val in y_temp]

        if len(self.x_ticks_ref) > 1:
            self.x_axis_tick_space_entry.config(state='disabled')
        else:
            self.x_axis_tick_space_entry.config(state='normal')

        if len(self.y_ticks_ref) > 1:
            self.y_axis_tick_space_entry.config(state='disabled')
        else:
            self.y_axis_tick_space_entry.config(state='normal')

        self.ticks_window.destroy()

    def create_residue_data(self, event=None):
        try:
            B = [float(val) for val in self.fit_params[self.selected_dataset]]
            expr = self.clean_functions[self.selected_dataset]
            y = self.ordenadas[self.selected_dataset]
            for i in range(len(B)):
                expr = expr.replace(f'B[{i}]', str(B[i]))

            residues = [safe_eval(expr, {'np': np, '_x': _x}) for _x in self.abcissas[self.selected_dataset]]
            residues = [y[i] - residues[i] for i in range(len(residues))]
        except Exception:
            tk.messagebox.showwarning('ERROR', 'Can only generate residue data after fit.')
        # erase the plot
        try:
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        except Exception: pass
        data_string = ''
        if self.err_abcissas[self.selected_dataset][0] == 0:
            for i in range(len(self.abcissas[self.selected_dataset])):
                data_string += str(self.abcissas[self.selected_dataset][i]) + ' '
                data_string += str(residues[i]) + ' '
                data_string += str(self.err_ordenadas[self.selected_dataset][i]) + '\n'
        else:
            for i in range(len(self.abcissas[self.selected_dataset])):
                data_string += str(self.abcissas[self.selected_dataset][i]) + ' '
                data_string += str(self.err_abcissas[self.selected_dataset][i]) + ' '
                data_string += str(residues[i]) + ' '
                data_string += str(self.err_ordenadas[self.selected_dataset][i]) + '\n'

        self.add_dataset(data_string[:-1])
        self.datasets_to_plot_var[self.selected_dataset].set(0)
        self.data_list[-1] = f'Residues - {self.data_list[self.selected_dataset]}'
        self.want_error[-1].set(0)
        self.dataset_selector.set(self.data_list[-1])
        self.update_databox('')
        self.plot_dataset()

    def text(self):
        self.erase_all_windows()


        self.text_window = tk.Toplevel(self.master)
        self.text_window.title('Add Text')
        self.text_window.geometry('1000x600')
        self.text_window.configure(background='#E4E4E4')
        self.text_window.resizable(False,False)
        self.focus_window(self.text_window)

        canvas = tk.Canvas(master=self.text_window,bg='#E4E4E4',highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.text_window,orient='vertical',command=canvas.yview)
        scrollable_frame = tk.Frame(canvas,bg='#E4E4E4')
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0,0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left',fill='x',expand=True)
        scrollbar.pack(side='right',fill='y')

        self.text_entries = []
        self.x_entries = []
        self.y_entries = []
        self.fontsize_entries = []
        self.remove_buttons = []

        pos = tk.Label(scrollable_frame, text='X and Y positions must be set in plot coordinates.',bg='#E4E4E4')
        pos["font"] = ("Roboto",int(15*self.master.winfo_width()/2350))
        pos.pack(side='top')

        for i in range(len(self.plot_text)):
            frame = tk.Frame(scrollable_frame,bg='#E4E4E4')

            self.text_entries.append(tk.Entry(frame,width=60))
            self.text_entries[i].insert(0,self.plot_text[i])

            label = tk.Label(frame, text=f'Text {i+1}',bg='#E4E4E4')
            label["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

            x_label = tk.Label(frame, text='x', bg='#E4E4E4')
            x_label["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

            self.x_entries.append(tk.Entry(frame,width=7))
            self.x_entries[i].insert(0,self.text_pos[i][0])

            y_label = tk.Label(frame, text='y', bg='#E4E4E4')
            y_label["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

            self.y_entries.append(tk.Entry(frame,width=7))
            self.y_entries[i].insert(0,self.text_pos[i][1])

            font_label = tk.Label(frame, text='fontsize', bg='#E4E4E4')
            font_label["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

            self.fontsize_entries.append(tk.Entry(frame,width=10))
            self.fontsize_entries[i].insert(0,self.text_size[i])

            self.remove_buttons.append(tk.Button(frame,
                                    text='REMOVE',
                                    fg='white',
                                    bg='#F21112',
                                    activebackground='white',
                                    activeforeground='#F21112')
                                       )
            self.remove_buttons[i]["command"] = lambda pos=i: self.remove_text(pos)
            self.remove_buttons[i]["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
            # Change the colors on enter and leave
            self._add_hover(self.remove_buttons[i])

            label.pack(side='left',padx=5)
            self.text_entries[i].pack(side='left')
            x_label.pack(side='left',padx=5)
            self.x_entries[i].pack(side='left',padx=5)
            y_label.pack(side='left',padx=5)
            self.y_entries[i].pack(side='left',padx=5)
            font_label.pack(side='left',padx=5)
            self.fontsize_entries[i].pack(side='left',padx=5)
            self.remove_buttons[i].pack(side='left',padx=10)
            frame.pack(side='top',pady=10)

         # Place the button to save the legends
        frame = tk.Frame(scrollable_frame,bg='#E4E4E4')

        save_button = tk.Button(frame,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_text
        save_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        # Change the colors on enter and leave
        self._add_hover(save_button)
        save_button.pack(side='left',padx=20)

        add_button = tk.Button(frame,
                               text="ADD TEXT",
                               fg='white',
                               bg='#F21112',
                               activebackground='white',
                               activeforeground='#F21112')
        add_button["command"] = self.new_text
        add_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        self._add_hover(add_button)
        add_button.pack(side='right',padx=20)

        frame.pack(side='top')

    def remove_text(self, pos):
        self.save_text()
        if len(self.plot_text)==1:
            self.plot_text[0] = ''
            self.text_pos[0] = [0.0,0.0]
            self.text()
        else:
            self.plot_text.pop(pos)
            self.text_pos.pop(pos)
            self.text_size.pop(pos)
            self.text()

    def new_text(self):
        self.save_text()
        self.plot_text.append('')
        self.text_pos.append([0,0])
        self.text_size.append(10)
        self.text()

    def save_text(self):
        for i in range(len(self.text_entries)):
            if (self.text_entries[i].get().replace(' ','') != ''):
                try:
                    float(self.x_entries[i].get())
                except Exception:
                    tk.messagebox.showwarning('ERROR', f'Non-numerical input found in X position for text {i+1}.')
                    continue
                try:
                    float(self.y_entries[i].get())
                except Exception:
                    tk.messagebox.showwarning('ERROR', f'Non-numerical input found in Y position for text {i+1}.')
                    continue
                try:
                    float(self.fontsize_entries[i].get())
                except Exception:
                    tk.messagebox.showwarning('ERROR', f'Non-numerical input found in fontsize for text {i+1}.')
                    continue
                self.plot_text[i] = self.text_entries[i].get()
                self.text_pos[i] = [float(self.x_entries[i].get()), float(self.y_entries[i].get())]
                self.text_size[i] = float(self.fontsize_entries[i].get())
        self.text_window.destroy()

    def labels(self):
        self.erase_all_windows()

        self.labels_window = tk.Toplevel(self.master)
        self.labels_window.title('Add Labels')
        self.labels_window.geometry('400x400')
        self.labels_window.configure(background='#E4E4E4')
        self.labels_window.resizable(False,False)
        self.focus_window(self.labels_window)

        canvas = tk.Canvas(master=self.labels_window,bg='#E4E4E4',highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.labels_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas,bg='#E4E4E4')
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left")
        scrollbar.pack(side="right",fill='y')

        self.label_entries = []

        for i in range(len(self.dataset_text)):
            frame1 = tk.Frame(scrollable_frame,bg='#E4E4E4')
            frame2 = tk.Frame(scrollable_frame,bg='#E4E4E4')
            frame3 = tk.Frame(scrollable_frame,bg='#E4E4E4')

            self.label_entries.append([tk.Entry(frame1,width=35),
                                       tk.Entry(frame2,width=35),
                                       tk.Entry(frame3,width=35)])

            label1 = tk.Label(frame1, text=f'Label for Dataset {i+1}',bg='#E4E4E4')
            label1["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
            self.label_entries[i][0].insert(0,self.data_labels[i])
            label1.pack(side='left')
            self.label_entries[i][0].pack(side='right')
            frame1.pack(side='top',pady=10)

            label2 = tk.Label(frame2, text=f'Label for Plotted Function {i+1}',bg='#E4E4E4')
            label2["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
            self.label_entries[i][1].insert(0,self.plot_labels[i])
            label2.pack(side='left')
            self.label_entries[i][1].pack(side='right')
            frame2.pack(side='top',pady=10)

            label3 = tk.Label(frame3, text=f'Label for Fitted Function {i+1}',bg='#E4E4E4')
            label3["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
            self.label_entries[i][2].insert(0,self.fit_labels[i])
            label3.pack(side='left')
            self.label_entries[i][2].pack(side='right')
            frame3.pack(side='top',pady=10)

        # Place the button to save the legends
        save_button = tk.Button(scrollable_frame,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_labels
        save_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        # Change the colors on enter and leave
        self._add_hover(save_button)
        save_button.pack(side='bottom')

    def save_labels(self):
        for i in range(len(self.label_entries)):
            self.data_labels[i] = self.label_entries[i][0].get()
            self.plot_labels[i] = self.label_entries[i][1].get()
            self.fit_labels[i]  = self.label_entries[i][2].get()
        self.labels_window.destroy()

    def export_image(self, event=None):
        if not hasattr(self, 'fig'):
            tk.messagebox.showwarning('ERROR', 'The plot does not yet exist')
        else:
            file = tk.filedialog.asksaveasfilename(filetypes=(("PNG Image", "*.png"),("All Files", "*.*")),defaultextension='.png')
            if file:
                self.fig.tight_layout()
                self.fig.savefig(file,dpi=500)

    def _add_hover(self, widget):
        """Give a red/white button the standard hover colour swap."""
        widget.bind("<Enter>", lambda e: widget.config(bg='white', fg='#F21112'))
        widget.bind("<Leave>", lambda e: widget.config(bg='#F21112', fg='white'))

    def line_slider(self, val):
        self.line_scale_label_value['text'] = str(val)

    def marker_slider(self, val):
        self.marker_scale_label_value['text'] = str(val)

    def error_slider(self, val):
        self.error_scale_label_value['text'] = str(val)

    def func_plot_slider(self, val):
        self.func_plot_scale_label_value['text'] = str(val)

    def func_fit_slider(self, val):
        self.func_fit_scale_label_value['text'] = str(val)

    def fit_activate(self):
        for x in range(len(self.param_boxes)):
            try:
                self.init_values[self.selected_dataset][x] = float(self.param_boxes[x].get())
            except ValueError:
                if self.param_boxes[x].get().replace(' ','')=='':
                    tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                    self.want_fit[self.selected_dataset].set(0)
                else:
                    tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                    self.want_fit[self.selected_dataset].set(0)
                return False

        self.want_fit[self.selected_dataset].set(1)
        self.plot_dataset()

    def pick_color(self, attr):
        """Let the user pick a colour and store it on ``attr`` for the current dataset."""
        chosen = tk.colorchooser.askcolor()[1]
        if chosen is None:  # user cancelled the dialog
            return
        getattr(self, attr)[self.selected_dataset] = chosen
        self.plot_dataset()

    def import_window(self):
        self.erase_all_windows()

        self.import_window = tk.Toplevel(self.master)
        self.import_window.title('File Format')
        self.import_window.geometry('400x250')
        self.import_window.configure(background='#E4E4E4')
        self.import_window.resizable(False, False)
        self.focus_window(self.import_window)

        self.same_x = tk.BooleanVar()
        self.dif_x = tk.BooleanVar()
        self.dif_x_error = tk.BooleanVar()

        self.same_x.set(1)
        self.dif_x.set(0)
        self.dif_x_error.set(0)

        self.same_x_button = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.same_x, text = 'All datasets have same x', command = self.same_xfunction)
        self.same_x_button.place(in_ = self.import_window, relwidth = 0.7, relheight = 0.1, rely = 0.05, relx = 0.15)

        self.same_x_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

        self.same_x_text =tk.Label(self.import_window, bg = '#E4E4E4', text = 'First column will be x.\nSubsequent columns will be (y1, ey1, y2, ey2,...)')
        self.same_x_text.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.15, rely = 0.15, relx = 0.05)

        self.dif_x_button = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.dif_x, text = 'All datasets have their own x',  command = self.dif_xfunction)
        self.dif_x_button.place(in_ = self.import_window, relwidth = 0.8, relheight = 0.15, rely = 0.35, relx = 0.1)

        self.dif_x_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))

        self.dif_x_text =tk.Label(self.import_window, bg = '#E4E4E4', text = 'Columns will be (x1, y1, ey1, x2, y2, ey2,...)')
        self.dif_x_text.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.1, rely = 0.46, relx = 0.05)

        dif_x_error_button = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.dif_x_error, text = 'Include ex',  command = self.dif_x_errorfunction)
        dif_x_error_button.place(in_ = self.import_window, relwidth = 0.5, relheight = 0.1, rely = 0.6, relx = 0.25)

        import_button = tk.Button(self.import_window, text = "CHOOSE FILE", command = self.open_file, fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        import_button.place(in_ = self.import_window, relwidth =0.5, relheight = 0.15, relx=0.25, rely=0.8)
        import_button["font"] = ("Roboto",int(20*self.master.winfo_width()/2350))
        # Change the colors on enter and leave
        self._add_hover(import_button)

    def same_xfunction(self):
        self.dif_x.set(0)

    def dif_xfunction(self):
        self.same_x.set(0)

    def dif_x_errorfunction(self):
        self.dif_x_error.get()

        if self.dif_x_error.get():
            self.same_x_text['text'] = 'First columns will be (x, ex).\nSubsequent columns will be (y1, ey1, y2, ey2,...)'
            self.same_x_button['text'] = 'All datasets have same (x, ex)'
            self.dif_x_button['text'] = 'All datasets have their own (x, ex)'
            self.dif_x_text['text'] = 'Columns will be (x1, ex1, y1, ey1, x2, ex2, y2, ey2,...)'
        else:
            self.same_x_text['text'] = 'First column will be x.\nSubsequent columns will be (y1, ey1, y2, ey2,...)'
            self.same_x_button['text'] = 'All datasets have same x'
            self.dif_x_button['text'] = 'All datasets have their own x'
            self.dif_x_text['text'] = 'Columns will be (x1, y1, ey1, x2, y2, ey2,...)'

    # Function to add a dataset
    def add_dataset(self, string):
        # add the placeholder text and update the dataset-count variable
        self.number_datasets = self.number_datasets + 1
        if ("dataset " + str(len(self.data_list) + 1)) in self.data_list:
            i=1
            while ("dataset " + str(len(self.data_list) + 1) + "_" + str(i)) in self.data_list:
                i+=1
            self.data_list.append("dataset " + str(len(self.data_list)+1) + "_" + str(i))
        else:
            self.data_list.append("dataset " + str(len(self.data_list)+1))
        self.dataset_selector.config(values = self.data_list)

        self.dataset_text.append(string)

        self.data_labels.append('')
        self.plot_labels.append('')
        self.fit_labels.append('')

        self.indeps.append(self.indeps[self.selected_dataset])
        self.params.append(self.params[self.selected_dataset])
        self.functions.append(self.functions[self.selected_dataset])
        self.clean_functions.append(self.clean_functions[self.selected_dataset])

        self.fit_params.append([])
        self.fit_uncert.append([])
        self.fit_chi.append('')
        self.fit_r2.append('')
        self.init_values.append([1.0]*len(self.param_boxes))

        self.x_func.append([])
        self.y_func.append([])

        self.y_fitted_func.append([])
        self.x_fitted_func.append([])

        self.full_output.append('')

        # Append for all the color and option variables
        self.want_fit.append(tk.BooleanVar())
        self.want_fit[-1].set(0)
        self.want_points.append(tk.BooleanVar())
        self.want_points[-1].set(1)
        self.want_line.append(tk.BooleanVar())
        self.want_line[-1].set(0)
        self.want_error.append(tk.BooleanVar())
        self.want_error[-1].set(1)
        self.want_function.append(tk.BooleanVar())
        self.want_function[-1].set(0)

        self.abcissas.append([0, 0, 0, 0])
        self.err_abcissas.append([0, 0, 0, 0])
        self.ordenadas.append([0, 0, 0, 0])
        self.err_ordenadas.append([0, 0, 0, 0])

        self.abc.append(np.array(self.abcissas[-1]))
        self.err_abc.append(np.array(self.err_abcissas[-1]))
        self.ord.append(np.array(self.ordenadas[-1]))
        self.err_ord.append(np.array(self.err_ordenadas[-1]))

        # Create the variables for the color choice of each plot
        self.marker_color_var.append("black")
        self.line_color_var.append("black")
        self.error_color_var.append("black")
        self.func_fit_color_var.append("black")
        self.func_plot_color_var.append("black")

        self.marker_option_translater.append('o')
        self.line_option_translater.append('-')
        self.func_fit_option_translater.append('-')
        self.func_plot_option_translater.append('-')

        self.line_width.append(tk.DoubleVar())
        self.marker_size.append(tk.DoubleVar())
        self.error_width.append(tk.DoubleVar())
        self.func_fit_width.append(tk.DoubleVar())
        self.func_plot_width.append(tk.DoubleVar())

        self.marker_size[self.number_datasets - 1].set(2.0)
        self.line_width[self.number_datasets - 1].set(2.0)
        self.error_width[self.number_datasets - 1].set(2.0)
        self.func_fit_width[self.number_datasets - 1].set(2.0)
        self.func_plot_width[self.number_datasets - 1].set(2.0)

        self.datasets_to_plot_var.append(tk.BooleanVar())
        self.datasets_to_plot_var[self.number_datasets-1].set(1)

        self.datasets_to_plot.add_checkbutton(label = "Plot Dataset " + str(len(self.data_list)), onvalue = 1, offvalue = 0, variable = self.datasets_to_plot_var[self.number_datasets-1] )

    # Function to remove datasets
    def remove_dataset(self):
        if self.number_datasets == 1:
            tk.messagebox.showwarning('ERROR', 'At least one dataset is needed. Add one before removing this one.')
            return -1

        self.number_datasets -= 1

        # delete the dataset
        self.dataset_text.pop(self.selected_dataset)

        # remove all the stored variables
        self.data_list = ["data_list "+str(i+1) for i in range(self.number_datasets)]
        self.abcissas.pop(self.selected_dataset)
        self.err_abcissas.pop(self.selected_dataset)
        self.ordenadas.pop(self.selected_dataset)
        self.err_ordenadas.pop(self.selected_dataset)

        self.data_labels.pop(self.selected_dataset)
        self.plot_labels.pop(self.selected_dataset)
        self.fit_labels.pop(self.selected_dataset)

        self.indeps.pop(self.selected_dataset)
        self.params.pop(self.selected_dataset)
        self.functions.pop(self.selected_dataset)
        self.clean_functions.pop(self.selected_dataset)

        self.fit_params.pop(self.selected_dataset)
        self.fit_uncert.pop(self.selected_dataset)
        self.fit_chi.pop(self.selected_dataset)
        self.fit_r2.pop(self.selected_dataset)
        self.init_values.pop(self.selected_dataset)

        self.x_func.pop(self.selected_dataset)
        self.y_func.pop(self.selected_dataset)

        self.x_fitted_func.pop(self.selected_dataset)
        self.y_fitted_func.pop(self.selected_dataset)

        self.full_output.pop(self.selected_dataset)

        # remove all the color and option variables
        self.want_fit.pop(self.selected_dataset)
        self.want_points.pop(self.selected_dataset)
        self.want_line.pop(self.selected_dataset)
        self.want_error.pop(self.selected_dataset)
        self.want_function.pop(self.selected_dataset)

        self.plot_options.delete(0,tk.END)
        self.plot_options.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.want_points[0])
        self.plot_options.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.want_line[0])
        self.plot_options.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.want_error[0])
        self.plot_options.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.want_fit[0] )
        self.plot_options.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.want_function[0])

        self.abc.pop(self.selected_dataset)
        self.err_abc.pop(self.selected_dataset)
        self.ord.pop(self.selected_dataset)
        self.err_ord.pop(self.selected_dataset)

        # Create the variables for the color choice of each plot
        self.marker_color_var.pop(self.selected_dataset)
        self.line_color_var.pop(self.selected_dataset)
        self.error_color_var.pop(self.selected_dataset)
        self.func_fit_color_var.pop(self.selected_dataset)
        self.func_plot_color_var.pop(self.selected_dataset)

        self.marker_option_translater.pop(self.selected_dataset)
        self.line_option_translater.pop(self.selected_dataset)
        self.func_fit_option_translater.pop(self.selected_dataset)
        self.func_plot_option_translater.pop(self.selected_dataset)

        self.line_width.pop(self.selected_dataset)
        self.marker_size.pop(self.selected_dataset)
        self.error_width.pop(self.selected_dataset)
        self.func_fit_width.pop(self.selected_dataset)
        self.func_plot_width.pop(self.selected_dataset)

        self.menu_bar.delete("Choose Datasets")

        self.datasets_to_plot = tk.Menu(self.menu_bar)
        self.menu_bar.add_cascade(label = "Choose Datasets", menu = self.datasets_to_plot)

        self.datasets_to_plot_var.pop(self.selected_dataset)

        self.selected_dataset = 0
        self.current_selection = 0

        self.data_list_var.set(self.data_list[0])

        self.dataset_selector.destroy()
        self.dataset_selector = ttk.Combobox(self.plot_button_frame, textvariable = self.data_list_var, values = self.data_list)
        self.dataset_selector.place(relx = 0, relheight = 1, relwidth=0.15)
        self.dataset_selector.bind("<<ComboboxSelected>>", self.update_databox)

        for x in range(self.number_datasets):
            self.datasets_to_plot.add_checkbutton(label = "Plot Dataset " + str(x+1), onvalue = 1, offvalue = 0, variable = self.datasets_to_plot_var[x] )
            self.datasets_to_plot_var[x].set(self.datasets_to_plot_var[x].get())

        self.update_databox("remove")

    def check_databox(self):
        for x in range(len(self.dataset_text)):
            if (self.dataset_text[x].replace(' ','') == '' and self.datasets_to_plot_var[x].get()):
                tk.messagebox.showwarning('ERROR', f'Dataset {x+1} is empty. Insert your data or remove it.')
                return False

        for x in range(len(self.dataset_text)):
            split = self.dataset_text[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]
                if(len(ponto)!= 3 and len(ponto)!= 4 and self.datasets_to_plot_var[x].get()):
                     tk.messagebox.showwarning('ERROR', f'Dataset {x+1} has at least one point with an incorrect number of columns. Correct it.')
                     self.want_fit[self.selected_dataset].set(0)
                     return False

        for x in range(len(self.dataset_text)):
            split = self.dataset_text[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]

                for k in ponto:
                    try:
                        float(k)
                    except ValueError:
                        tk.messagebox.showwarning('ERROR', f'Dataset {x+1} contains non-numerical input. Only numerical input is allowed.')
                        self.want_fit[self.selected_dataset].set(0)
                        return False
        return True

    def update_databox(self, event):
        # Keep the current one
        if event != "remove":
            self.dataset_text[self.current_selection] = self.data_entry.get("1.0", "end-1c").replace('\t',' ')
        # This function shows the text for a dataset in the text box
        # The least messy way to do that is to destroy everything in the frame and put the information
        # for the new dataset
        self.update_combobox_values()
        select = self.data_list.index(self.data_list_var.get())
        self.selected_dataset = select
        self.current_selection = select

        self.function_entry.delete(0,tk.END)
        self.function_entry.insert(0,self.functions[self.selected_dataset])
        self.parameter_entry.delete(0,tk.END)
        self.parameter_entry.insert(0,self.params[self.selected_dataset])
        self.independent_entry.delete(0,tk.END)
        self.independent_entry.insert(0,self.indeps[self.selected_dataset])
        self.chisq_entry.delete(0,tk.END)
        self.r2_entry.delete(0,tk.END)

        self.update_parameter()

        self.plot_options.delete(0,tk.END)
        self.plot_options.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.want_points[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.want_line[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.want_error[self.selected_dataset])
        self.plot_options.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.want_fit[self.selected_dataset] )
        self.plot_options.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.want_function[self.selected_dataset])

        self.subframe_left_2.destroy()
        self.data_entry.destroy()

        self.subframe_left_2 = tk.Frame(self.frame_left, bg='#E4E4E4')
        self.subframe_left_2.place(in_ = self.frame_left, relwidth = 1, relheight= 0.38, relx=0, rely=0.55)

        # Create the text box with the corresponding information
        self.data_entry = (ScrolledText(self.subframe_left_2))
        self.data_entry.pack(expand = 1, fill = tk.X)
        self.data_entry.insert(tk.INSERT,self.dataset_text[select])

        # Same delete-and-recreate for the menus, so the right ones appear in the place corresponding
        # to the selected dataset
        self.marker_sizescale.destroy()
        self.line_width_scale.destroy()
        self.error_size_scale.destroy()
        self.func_fit_width_scale.destroy()
        self.func_plot_width_scale.destroy()

        self.marker_size_combo.destroy()
        self.line_style_combo.destroy()
        self.func_fit_style_combo.destroy()
        self.func_plot_style_combo.destroy()

        self.line_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.line_option)

        self.func_fit_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.func_fit_option)

        self.func_plot_style_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.func_plot_option)

        self.marker_size_combo = ttk.Combobox(self.subframe_right_3, values=[
            'Triangle', 'Square', 'Circle', 'Star', 'Diamond', 'X'], textvariable = self.marker_option )

        if self.marker_option_translater[self.selected_dataset] == 'x':
            self.marker_size_combo.current(5)
            self.marker_option.set('X')
        if self.marker_option_translater[self.selected_dataset] == 'D':
            self.marker_size_combo.current(4)
            self.marker_option.set('Diamond')
        if self.marker_option_translater[self.selected_dataset] == '*':
            self.marker_size_combo.current(3)
            self.marker_option.set('Star')
        if(self.marker_option_translater[self.selected_dataset] == 'o'):
            self.marker_size_combo.current(2)
            self.marker_option.set('Circle')
        if(self.marker_option_translater[self.selected_dataset] == 's'):
            self.marker_size_combo.current(1)
            self.marker_option.set('Square')
        if(self.marker_option_translater[self.selected_dataset] == '^'):
            self.marker_size_combo.current(0)
            self.marker_option.set('Triangle')

        if self.line_option_translater[self.selected_dataset] == '-':
            self.line_style_combo.current(0)
            self.line_option.set('Solid')
        if self.line_option_translater[self.selected_dataset] == '--':
            self.line_style_combo.current(1)
            self.line_option.set('Dashed')
        if self.line_option_translater[self.selected_dataset] == ':':
            self.line_style_combo.current(2)
            self.line_option.set('Dotted')
        if self.line_option_translater[self.selected_dataset] == '-.':
            self.line_style_combo.current(3)
            self.line_option.set('DashDot')

        if self.func_fit_option_translater[self.selected_dataset] == '-':
            self.func_fit_style_combo.current(0)
            self.func_fit_option.set('Solid')
        if self.func_fit_option_translater[self.selected_dataset] == '--':
            self.func_fit_style_combo.current(1)
            self.func_fit_option.set('Dashed')
        if self.func_fit_option_translater[self.selected_dataset] == ':':
            self.func_fit_style_combo.current(2)
            self.func_fit_option.set('Dotted')
        if self.func_fit_option_translater[self.selected_dataset] == '-.':
            self.func_fit_style_combo.current(3)
            self.func_fit_option.set('DashDot')

        if self.func_plot_option_translater[self.selected_dataset] == '-':
            self.func_plot_style_combo.current(0)
            self.func_plot_option.set('Solid')
        if self.func_plot_option_translater[self.selected_dataset] == '--':
            self.func_plot_style_combo.current(1)
            self.func_plot_option.set('Dashed')
        if self.func_plot_option_translater[self.selected_dataset] == ':':
            self.func_plot_style_combo.current(2)
            self.func_plot_option.set('Dotted')
        if self.func_plot_option_translater[self.selected_dataset] == '-.':
            self.func_plot_style_combo.current(3)
            self.func_plot_option.set('DashDot')

        self.marker_size_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.64, relheight=0.05)
        self.marker_size_combo.bind("<<ComboboxSelected>>", self.marker_selector)

        self.line_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.56, relheight=0.05)
        self.line_style_combo.bind("<<ComboboxSelected>>", self.line_selector)

        self.func_plot_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.72, relheight=0.05)
        self.func_plot_style_combo.bind("<<ComboboxSelected>>", self.func_plot_selector)

        self.func_fit_style_combo.place(in_ = self.subframe_right_3, relwidth = 0.15, relx = 0.63, rely=0.80, relheight=0.05)
        self.func_fit_style_combo.bind("<<ComboboxSelected>>", self.func_fit_selector)

        # Figure out which dataset is selected just to apply the correct colors and so on
        self.line_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.line_slider, showvalue = False, variable = self.line_width[self.selected_dataset])
        self.line_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.56, relheight=0.06)
        self.line_width_scale['width'] = 0.025*self.master.winfo_width()

        self.marker_sizescale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.marker_slider,showvalue =False, variable = self.marker_size[self.selected_dataset])
        self.marker_sizescale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.64, relheight=0.06)
        self.marker_sizescale['width'] = 0.025*self.master.winfo_width()

        self.func_plot_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.func_plot_slider, showvalue = False, variable = self.func_plot_width[self.selected_dataset])
        self.func_plot_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.72, relheight=0.06)
        self.func_plot_width_scale['width'] = 0.025*self.master.winfo_width()

        self.func_fit_width_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.func_fit_slider,showvalue =False, variable = self.func_fit_width[self.selected_dataset])
        self.func_fit_width_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.80, relheight=0.06)
        self.func_fit_width_scale['width'] = 0.025*self.master.winfo_width()

        self.error_size_scale = tk.Scale(self.subframe_right_3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.error_slider, showvalue = False, variable = self.error_width[self.selected_dataset])
        self.error_size_scale.place(in_ = self.subframe_right_3, relwidth = 0.17, relx = 0.34, rely=0.88, relheight=0.06)
        self.error_size_scale['width'] = 0.025*self.master.winfo_width()

        self.error_scale_label_value['text'] = self.error_width[self.selected_dataset].get()
        self.marker_scale_label_value['text'] = self.marker_size[self.selected_dataset].get()
        self.line_scale_label_value['text'] = self.line_width[self.selected_dataset].get()
        self.func_fit_scale_label_value['text'] = self.func_fit_width[self.selected_dataset].get()
        self.func_plot_scale_label_value['text'] = self.func_plot_width[self.selected_dataset].get()

        if(self.count_plots == 0):
            self.line_width_scale['state'] = tk.DISABLED
            self.marker_sizescale['state'] = tk.DISABLED
            self.error_size_scale['state'] = tk.DISABLED
            self.func_fit_width_scale['state'] = tk.DISABLED
            self.func_plot_width_scale['state'] = tk.DISABLED

    def compile_function(self):
        # clean the fit parameters
        for x in range(self.box_number):
            self.param_err_boxes[x].config(state = 'normal')
            self.param_err_boxes[x].delete(0, tk.END)
            self.param_err_boxes[x].config(state = 'readonly')

            self.param_res_boxes[x].config(state = 'normal')
            self.param_res_boxes[x].delete(0, tk.END)
            self.param_res_boxes[x].config(state = 'readonly')
        # clean r2 and chisq
        self.chisq_entry.config(state = 'normal')
        self.chisq_entry.delete(0, tk.END)
        self.chisq_entry.config(state = 'readonly')
        self.r2_entry.config(state='normal')
        self.r2_entry.delete(0, tk.END)
        self.r2_entry.config(state = 'readonly')
        # erase the graph
        self.want_fit[self.selected_dataset].set(0)
        try:
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        except Exception: pass

        parsed_input = parser(self.function_entry.get(),
                              self.parameter_entry.get(),
                              self.independent_entry.get())
        self.functions[self.selected_dataset] = self.function_entry.get()

        for x in range(len(self.param_boxes)):
            try:
                self.init_values[self.selected_dataset][x] = float(self.param_boxes[x].get())
            except ValueError:
                if (self.param_boxes[x].get().replace(' ','')==''):
                    tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                    self.want_fit[self.selected_dataset].set(0)
                else:
                    tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                    self.want_fit[self.selected_dataset].set(0)
        if parsed_input[0]:
            self.clean_functions[self.selected_dataset] = parsed_input[1]
        else:
            tk.messagebox.showwarning('ERROR', parsed_input[1])
            self.clean_functions[self.selected_dataset] = ''

    # Function to plot the function with numeric parameters given by the user
    def plot_fitted_function(self, dataset):
        self.x_fitted_func[dataset]=[0]*10000
        self.y_fitted_func[dataset]=[0]*10000

        x_max  = float(self.x_axis_max_entry.get().replace(' ',''))
        x_min  = float(self.x_axis_min_entry.get().replace(' ',''))
        amp = x_max - x_min

        B = self.fit_params[dataset]
        expr = self.clean_functions[dataset]
        for j in range(10000):
            _x = x_min + j*amp/9999
            self.x_fitted_func[dataset][j] = _x
            self.y_fitted_func[dataset][j] = safe_eval(expr, {'np': np, 'B': B, '_x': _x})

    def plot_function(self):
        parsed_input = parser(self.function_entry.get(),
                              self.parameter_entry.get(),
                              self.independent_entry.get())
        if parsed_input[0]:
            expr = parsed_input[1]
        else:
            tk.messagebox.showwarning('ERROR', parsed_input[1])
            self.want_function[self.selected_dataset].set(0)
            return parsed_input

        B = []

        for i in range(len(self.plot_param_boxes)):
             param_boxes = self.plot_param_boxes[i].get()
             param_boxes = param_boxes.replace(' ', '')
             if(param_boxes == ''):
                 tk.messagebox.showwarning('ERROR', 'No parameter values were provided for plot.')
                 self.want_function[self.selected_dataset].set(0)
                 return False
             try:
                 float(param_boxes)
             except ValueError:
                 tk.messagebox.showwarning('ERROR', 'A non-numerical parameter value was detected. Only numerical values are allowed.')
                 self.want_function[self.selected_dataset].set(0)
                 return False
             B.append(float(param_boxes))

        x_max  = float(self.x_axis_max_entry.get().replace(',','.').replace(' ',''))
        x_min  = float(self.x_axis_min_entry.get().replace(',','.').replace(' ',''))
        amp = x_max - x_min

        self.x_func[self.selected_dataset] = _x = [x_min + i*amp/9999 for i in range(10000)]
        self.y_func[self.selected_dataset] = []

        for i in range(10000):
            self.y_func[self.selected_dataset].append(safe_eval(expr.replace('_x','_x[i]'), {'np': np, 'B': B, '_x': _x, 'i': i}))

        self.want_function[self.selected_dataset].set(1)
        self.plot_dataset()

    def plot_dataset(self):
        # we don't want to remove autoscale while in here
        self.remove_autoscale = False

        # Test whether the limits are well defined. If not, we can skip all of this
        info_x = [(self.x_axis_max_entry, 'Max value of x'), (self.x_axis_min_entry, 'Min value of x'), (self.x_axis_tick_space_entry, 'X axis tick spacing')]
        info_y = [(self.y_axis_max_entry, 'Max value of y'), (self.y_axis_min_entry, 'Min value of y'), (self.y_axis_tick_space_entry, 'Y axis tick spacing')]

        if not self.autoscale_x.get():
            for var in info_x:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        tk.messagebox.showwarning('ERROR', var[1]+' contains no input.')
                    else:
                        tk.messagebox.showwarning('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
            # Also check that the max values are not smaller than the min
            if float(self.x_axis_max_entry.get().replace(',','.').replace(' ','')) <= float(self.x_axis_min_entry.get().replace(',','.').replace(' ','')):
                tk.messagebox.showwarning('ERROR', 'Upper limit for X axis is not greater that lower limit.')
                return False
            # And that the tick spacings are positive
            if float(self.x_axis_tick_space_entry.get().replace(',','.').replace(' ','')) <= 0:
                tk.messagebox.showwarning('ERROR', 'Tick spacing must be a positive non-zero number.')
                return False
            # And that we do not have too many ticks
            x_max  = float(self.x_axis_max_entry.get().replace(',','.').replace(' ',''))
            x_min  = float(self.x_axis_min_entry.get().replace(',','.').replace(' ',''))
            amp = x_max - x_min
            n_ticks = int(amp/float(self.x_axis_tick_space_entry.get().replace(',','.').replace(' ','')))
            if n_ticks > 100:
                tk.messagebox.showwarning('ERROR',f'Having {n_ticks} ticks will make your plot unreabable. Adjust X tick spacing.')
                return False

        if not self.autoscale_y.get():
            for var in info_y:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        tk.messagebox.showwarning('ERROR', var[1]+' contains no input.')
                    else:
                        tk.messagebox.showwarning('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
            # Also check that the max values are not smaller than the min
            if float(self.y_axis_max_entry.get().replace(',','.').replace(' ','')) <= float(self.y_axis_min_entry.get().replace(',','.').replace(' ','')):
                tk.messagebox.showwarning('ERROR', 'Upper limit for Y axis is not greater that lower limit.')
                return False
            # And that the tick spacings are positive
            if float(self.y_axis_tick_space_entry.get().replace(',','.').replace(' ','')) <= 0:
                tk.messagebox.showwarning('ERROR', 'Tick spacing must be a positive non-zero number.')
                return False
            y_max  = float(self.y_axis_max_entry.get().replace(',','.').replace(' ',''))
            y_min  = float(self.y_axis_min_entry.get().replace(',','.').replace(' ',''))
            amp = y_max - y_min
            n_ticks = int(amp/float(self.y_axis_tick_space_entry.get().replace(',','.').replace(' ','')))
            if n_ticks > 100:
                tk.messagebox.showwarning('ERROR',f'Having {n_ticks} ticks will make your plot unreabable. Adjust Y tick spacing.')
                return False

        # Test whether the data is fine. If not, we can skip all of this
        self.update_combobox_values()
        select = self.data_list.index(self.data_list_var.get())
        self.dataset_text[select]= self.data_entry.get("1.0", "end-1c").replace('\t',' ')

        if not self.check_databox():
            return False

        # set the data to plot=true
        self.datasets_to_plot_var[select].set(1)

        if(self.count_plots == 0):
            self.line_width_scale['state'] = tk.NORMAL
            self.marker_sizescale['state'] = tk.NORMAL
            self.error_size_scale['state'] = tk.NORMAL
            self.func_fit_width_scale['state'] = tk.NORMAL
            self.func_plot_width_scale['state'] = tk.NORMAL
            self.count_plots = 1

        for x in range(self.number_datasets):
            if self.datasets_to_plot_var[x].get():
                self.abcissas[x] = []
                self.err_abcissas[x] = []
                self.ordenadas[x] = []
                self.err_ordenadas[x] = []
                self.datastring = self.dataset_text[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                if data_sets == -2:
                    tk.messagebox.showwarning('ERROR', f'Dataset {select} has at least one point defined incorrectly. Make sure all points have the same number of columns.')
                    self.dataset_text[select] = ""
                    self.datasetring = ""
                    return False
                for i in range(len(data_sets[0])):
                    if len(data_sets[0][i]) == 4:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.err_abcissas[x].append(data_sets[0][i][1])
                        self.ordenadas[x].append(data_sets[0][i][2])
                        self.err_ordenadas[x].append(data_sets[0][i][3])

                    if len(data_sets[0][i]) == 3:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.err_abcissas[x].append(0)
                        self.ordenadas[x].append(data_sets[0][i][1])
                        self.err_ordenadas[x].append(data_sets[0][i][2])

                self.abc[x] = np.array(self.abcissas[x])
                self.err_abc[x] = np.array(self.err_abcissas[x])
                self.ord[x] = np.array(self.ordenadas[x])
                self.err_ord[x] = np.array(self.err_ordenadas[x])

        if 5*self.width_ratio/self.height_ratio > 10:
            figsize=(10,10*self.height_ratio/self.width_ratio)
        else:
            figsize=(5*self.width_ratio/self.height_ratio,5)

        self.fig = Figure(figsize=figsize,tight_layout=True)

        data_for_fit = []
        for x in range(self.number_datasets):
            if self.datasets_to_plot_var[x].get():
                self.datastring = self.dataset_text[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                data_for_fit.append(data_sets[0])
            else:
                data_for_fit.append('')
        a = []
        for dataset in data_for_fit:
            for point in dataset:
                a.append(point)

        if not self.autoscale_x.get():
            max_abc = float(self.x_axis_max_entry.get().replace(',','.').replace(' ',''))
            min_abc = float(self.x_axis_min_entry.get().replace(',','.').replace(' ',''))
            amp_x   = float(self.x_axis_tick_space_entry.get().replace(',','.').replace(' ',''))
        if self.autoscale_x.get():
            all_abc = []
            for x in range(len(a)):
                all_abc.append(a[x][0])

            min_abc = min(all_abc)
            max_abc = max(all_abc)

            if len(a[0]) == 4:
                min_indexes = []
                max_indexes = []
                for point in a:
                    if point[0] == min_abc and len(point)==4:
                        min_indexes.append(point[1])
                    if point[0] == max_abc and len(point)==4:
                        max_indexes.append(point[1])

                max_abc += max(max_indexes)
                min_abc -= max(min_indexes)

            amp_x = max_abc - min_abc

            max_abc += 0.05*amp_x
            min_abc -= 0.05*amp_x

            self.x_axis_max_entry.delete(0, 'end')
            self.x_axis_min_entry.delete(0, 'end')

            self.x_axis_max_entry.insert(0, f"{max_abc:.3e}")
            self.x_axis_min_entry.insert(0, f"{min_abc:.3e}")

            amp_x = amp_x/8
            self.x_axis_tick_space_entry.delete(0,'end')
            self.x_axis_tick_space_entry.insert(0, f"{amp_x:.3e}")

        if not self.autoscale_y.get():
            max_ord = float(self.y_axis_max_entry.get().replace(',','.').replace(' ',''))
            min_ord = float(self.y_axis_min_entry.get().replace(',','.').replace(' ',''))
            amp_y   = float(self.y_axis_tick_space_entry.get().replace(',','.').replace(' ',''))

        if self.autoscale_y.get():
            all_ord = []
            for x in range(len(a)):
                all_ord.append(a[x][-2])
                all_ord.append(a[x][-2])

            min_ord = min(all_ord)
            max_ord = max(all_ord)

            min_indexes = []
            max_indexes = []
            for point in a:
                if point[-2] == min_ord:
                    min_indexes.append(point[-1])
                if point[-2] == max_ord:
                    max_indexes.append(point[-1])

            min_ord -= max(min_indexes)
            max_ord += max(max_indexes)

            amp_y = max_ord - min_ord
            max_ord += 0.05*amp_y
            min_ord -= 0.05*amp_y

            self.y_axis_max_entry.delete(0, 'end')
            self.y_axis_min_entry.delete(0, 'end')

            self.y_axis_max_entry.insert(0, f"{max_ord:.3e}")
            self.y_axis_min_entry.insert(0, f"{min_ord:.3e}")

            amp_y = amp_y/8
            self.y_axis_tick_space_entry.delete(0,'end')
            self.y_axis_tick_space_entry.insert(0, f"{amp_y:.3e}")

        x_ticks = []
        y_ticks = []

        x_max  = max_abc
        x_min  = min_abc
        x_space = amp_x
        y_max  = max_ord
        y_min  = min_ord
        y_space = amp_y

        # determine the ticks for the x-axis
        if len(self.x_ticks_ref) == 0:
            x_tick_number = 1 + int((x_max - x_min)/x_space)
            for x in range(x_tick_number):
                x_ticks.append(x*x_space + x_min)

        if len(self.x_ticks_ref) == 1:
            x_tick_number = 1 + int((x_max - x_min)/x_space)
            temp = self.x_ticks_ref[0]
            if self.x_ticks_ref[0] < x_min:
                while temp < x_min:
                    temp += x_space
            if self.x_ticks_ref[0] > x_min:
                while temp - x_space > x_min:
                    temp -= x_space
            for x in range(x_tick_number):
                x_ticks.append(x*x_space + temp)

        if len(self.x_ticks_ref) > 1:
            x_ticks = self.x_ticks_ref

        # determine the ticks for the y-axis
        if len(self.y_ticks_ref) == 0:
            y_tick_number = 1 + int((y_max - y_min)/y_space)
            for y in range(y_tick_number):
                y_ticks.append(y*y_space + y_min)

        if len(self.y_ticks_ref) == 1:
            y_tick_number = 1 + int((y_max - y_min)/y_space)
            temp = self.y_ticks_ref[0]
            if self.y_ticks_ref[0] < y_min:
                while temp < y_min:
                    temp += y_space
            if self.y_ticks_ref[0] > y_min:
                while temp - y_space > y_min:
                    temp -= y_space
            for y in range(y_tick_number):
                y_ticks.append(y*y_space + temp)

        if len(self.y_ticks_ref) > 1:
            y_ticks = self.y_ticks_ref

        self.a = self.fig.add_subplot(111 ,projection = None,
                                 xlim = (x_min,x_max), ylim = (y_min, y_max),
                                 xticks = x_ticks, yticks = y_ticks,
                                 ylabel = self.y_axis_title_entry.get(), xlabel = self.x_axis_title_entry.get())

        self.subframe_left_1.destroy()
        self.subframe_left_1=tk.Frame(self.frame_left, bg='#E4E4E4')
        self.subframe_left_1.place(in_ = self.frame_left, relwidth=1, relheight=0.5, relx=0, rely=0)

        # first we see what scale we are using
        if self.log_x.get():
            if float(self.x_axis_min_entry.get().replace(',','.').replace(' ','')) > 0:
                self.a.set_xscale('log')
            else:
                self.a.set_xscale('symlog')
            self.a.set_xticks(x_ticks)
        if self.log_y.get():
            if float(self.y_axis_min_entry.get().replace(',','.').replace(' ','')) > 0:
                self.a.set_yscale('log')
            else:
                self.a.set_yscale('symlog')
            self.a.set_yticks(y_ticks)

        if self.check_databox():
            for i in range(self.number_datasets):
                if self.datasets_to_plot_var[i].get():
                    if self.want_error[i].get():
                        self.a.errorbar(self.abc[i], self.ord[i], xerr = self.err_abc[i], yerr = self.err_ord[i], fmt = 'none',zorder = -1,lw=0, ecolor = self.error_color_var[i], elinewidth = self.error_width[i].get())
                    if self.want_points[i].get():
                        if self.data_labels[i]:
                            self.a.plot(self.abc[i], self.ord[i], label=self.data_labels[i], marker = self.marker_option_translater[i], color = str(self.marker_color_var[i]), zorder = 1, lw=0, ms=self.marker_size[i].get()*2)
                        else:
                            self.a.plot(self.abc[i], self.ord[i], marker = self.marker_option_translater[i], color = str(self.marker_color_var[i]), zorder = 1, lw=0, ms=self.marker_size[i].get()*2)
                    if self.want_line[i].get():
                        self.a.plot(self.abc[i], self.ord[i], color = self.line_color_var[i], lw = self.line_width[i].get(), ls = str(self.line_option_translater[i]))
                    if self.want_function[i].get():
                        if self.plot_labels[i]:
                            self.a.plot(self.x_func[i], self.y_func[i], label=self.plot_labels[i], lw = self.func_plot_width[0].get(), ls = str(self.func_plot_option_translater[i]), color = self.func_plot_color_var[i])
                        else:
                            self.a.plot(self.x_func[i], self.y_func[i], lw = self.func_plot_width[0].get(), ls = str(self.func_plot_option_translater[i]), color = self.func_plot_color_var[i])
                    if self.want_fit[i].get():
                        (self.fit_params[i], self.fit_uncert[i], self.fit_chi[i], self.fit_r2[i]) = self.fit_data(data_for_fit[i], self.init_values[i], 2000, i)
                        self.plot_fitted_function(i)
                        if self.fit_labels[i]:
                            self.a.plot(self.x_fitted_func[i], self.y_fitted_func[i], label=self.fit_labels[i], lw = self.func_fit_width[i].get(), ls = str(self.func_fit_option_translater[i]), color = self.func_fit_color_var[i])
                        else:
                            self.a.plot(self.x_fitted_func[i], self.y_fitted_func[i], lw = self.func_fit_width[i].get(), ls = str(self.func_fit_option_translater[i]), color = self.func_fit_color_var[i])
                        if i == self.selected_dataset:
                            for x in range (len(self.param_res_boxes)):
                                self.param_res_boxes[x].config(state = 'normal')
                                self.param_res_boxes[x].delete(0, tk.END)
                                self.param_res_boxes[x].insert(0, f'{self.fit_params[self.selected_dataset][x]:.7e}')
                                self.param_res_boxes[x].config(state = 'readonly')
                                self.param_err_boxes[x].config(state = 'normal')
                                self.param_err_boxes[x].delete(0, tk.END)
                                self.param_err_boxes[x].insert(0, f'{self.fit_uncert[self.selected_dataset][x]:.7e}')
                                self.param_err_boxes[x].config(state = 'readonly')

                            self.chisq_entry.config(state = 'normal')
                            self.chisq_entry.delete(0, tk.END)
                            self.chisq_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.3e}")
                            self.chisq_entry.config(state = 'readonly')
                            self.r2_entry.config(state='normal')
                            self.r2_entry.delete(0, tk.END)
                            self.r2_entry.insert(0, f"{self.fit_r2[self.selected_dataset]:.6f}")
                            self.r2_entry.config(state = 'readonly')
        # Maybe also add a condition to check whether the user wants a grid
        self.a.grid(True)

        # Write the texts on the plot
        for i in range(len(self.plot_text)):
            self.a.text(self.text_pos[i][0],self.text_pos[i][1],self.plot_text[i],fontsize=self.text_size[i])

        if np.any(np.array(self.data_labels)!='') or np.any(np.array(self.plot_labels)!='') or np.any(np.array(self.fit_labels)!=''):
            self.a.legend()


        self.canvas = FigureCanvasTkAgg(self.fig, master=self.subframe_left_1)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

        # we don't want to remove autoscale while in here
        self.remove_autoscale = True

    def update_parameter(self):
        self.want_fit[self.selected_dataset].set(0)
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        # Same reasoning: destroy the box holding the parameters and initial guesses to put the new ones
        self.params[self.selected_dataset] = self.parameter_entry.get()
        self.indeps[self.selected_dataset] = self.independent_entry.get()

        if hasattr(self, 'param_boxes'):
            for x in range(len(self.param_boxes)):
                try:
                    self.init_values[self.selected_dataset][x] = float(self.param_boxes[x].get())
                except ValueError:
                    if (self.param_boxes[x].get().replace(' ','')==''):
                        tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                        self.want_fit[self.selected_dataset].set(0)
                    else:
                        tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                        self.want_fit[self.selected_dataset].set(0)

        process = process_params(self.parameter_entry.get(), self.independent_entry.get())
        if not process[0]:
            self.count = 1
            self.box_number = 0

            self.param_label = []
            self.param_boxes = []
            self.plot_param_label = []
            self.plot_param_boxes = []

            self.param_scroll_y.destroy()
            self.another_frame.destroy()
            self.param_canvas.destroy()
            self.initial_guess_label.destroy()
            tk.messagebox.showwarning('ERROR', process[1])
        else:
            self.process_params = process[1]
            clean_split = process[1]
            if self.count==2:
                self.subframe_right_2.destroy()

                self.subframe_right_2=tk.Frame(self.frame_right, bg='#E4E4E4')
                self.subframe_right_2.place(in_ = self.frame_right, relwidth=1, relheight=0.2, relx=0, rely=0.25)

                self.box_number = len(clean_split)

                self.param_scroll_y.destroy()
                self.another_frame.destroy()
                self.param_canvas.destroy()

                self.param_label = []
                self.param_boxes = []
                self.param_res_boxes = []
                self.param_res_label = []
                self.param_err_label = []
                self.param_err_boxes = []
                self.plot_param_label = []
                self.plot_param_boxes = []

                self.box_number = len(clean_split)
                if len(self.init_values[self.selected_dataset]) > self.box_number:
                    self.init_values[self.selected_dataset] = [1.0]*self.box_number
                else:
                    while len(self.init_values[self.selected_dataset]) != self.box_number:
                        self.init_values[self.selected_dataset].append(1.0)

                self.param_canvas = tk.Canvas(self.subframe_right_2, highlightthickness=0, bg='#E4E4E4')
                self.param_canvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)

                self.another_frame=tk.Frame(self.param_canvas, bg='#E4E4E4')

                self.param_scroll_y = ttk.Scrollbar(self.subframe_right_2, orient = "vertical", command=self.param_canvas.yview)
                self.param_scroll_y.pack(side=tk.RIGHT, fill="y")

                self.param_canvas.configure(yscrollcommand=self.param_scroll_y.set)
                self.param_canvas.bind('<Configure>', self.adjust_canvas)

                self.another_frame.columnconfigure(0, weight = 1)
                self.another_frame.columnconfigure(1, weight = 3)
                self.another_frame.columnconfigure(2, weight = 1)
                self.another_frame.columnconfigure(3, weight = 3)
                self.another_frame.columnconfigure(4, weight = 1)
                self.another_frame.columnconfigure(5, weight = 3)
                self.another_frame.columnconfigure(6, weight = 1)
                self.another_frame.columnconfigure(7, weight = 3)

                self.chisq_entry.config(state = 'normal')
                self.chisq_entry.delete(0, tk.END)
                self.chisq_entry.config(state = 'readonly')

                self.r2_entry.config(state = 'normal')
                self.r2_entry.delete(0, tk.END)
                self.r2_entry.config(state = 'readonly')
                for x in range(self.box_number):
                    self.param_err_label.append(tk.Label(self.another_frame, text = u'\u03b4' + clean_split[x], bg='#E4E4E4'))
                    self.param_err_label[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.param_err_boxes.append(tk.Entry(self.another_frame, cursor="arrow", takefocus=0))
                    self.param_err_boxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.param_err_boxes[x].config(state = 'readonly')
                    self.param_res_label.append(tk.Label(self.another_frame, text = clean_split[x], bg='#E4E4E4'))
                    self.param_res_label[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.param_res_boxes.append(tk.Entry(self.another_frame, cursor="arrow", takefocus=0))
                    self.param_res_boxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_res_boxes[x].config(state = 'readonly')
                    self.param_boxes.append(tk.Entry(self.another_frame))
                    try: self.param_boxes[x].insert(0,f"{self.init_values[self.selected_dataset][x]:e}")
                    except Exception: pass
                    self.param_boxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_label.append(tk.Label(self.another_frame, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#E4E4E4'))
                    self.param_label[x].grid(column = 2, row = x, pady=10, padx=(15,0), sticky= tk.E)
                    self.plot_param_label.append(tk.Label(self.another_frame, text = clean_split[x], bg = '#E4E4E4'))
                    self.plot_param_label[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plot_param_boxes.append(tk.Entry(self.another_frame))
                    self.plot_param_boxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(self.another_frame,
                                   text='GET FULL OUTPUT',
                                   fg='white',
                                   bg='#F21112',
                                   activebackground='white',
                                   activeforeground='#F21112')
                output['command'] = self.show_output
                output['font'] = ('Roboto',int(20*self.master.winfo_width()/2350))
                self._add_hover(output)
                output.grid(row = x+1, column = 5)

                self.windows_item = self.param_canvas.create_window((0,0), window=self.another_frame, anchor="nw")

            if (self.count == 1):
                self.param_label = []
                self.param_boxes = []
                self.param_res_boxes = []
                self.param_res_label = []
                self.param_err_label = []
                self.param_err_boxes = []
                self.plot_param_label = []
                self.plot_param_boxes = []

                self.box_number = len(clean_split)

                self.result_label = tk.Label(self.subframe_right_1, text="Results", bg='#E4E4E4')
                self.result_label.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.5)

                self.error_label = tk.Label(self.subframe_right_1, text="Errors", bg='#E4E4E4')
                self.error_label.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.75)

                self.initial_guess_label = tk.Label(self.subframe_right_1, text="Initial Guess", bg='#E4E4E4')
                self.initial_guess_label.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.25)

                self.func_plot_label = tk.Label(self.subframe_right_1, text="Plot Function", bg='#E4E4E4')
                self.func_plot_label.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=-0.03)

                self.param_canvas = tk.Canvas(self.subframe_right_2, highlightthickness=0, bg='#E4E4E4')
                self.param_canvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)

                self.another_frame = tk.Frame(self.param_canvas, bg='#E4E4E4')

                self.param_scroll_y = ttk.Scrollbar(self.subframe_right_2, orient = "vertical", command=self.param_canvas.yview)
                self.param_scroll_y.pack(side=tk.RIGHT, fill="y")

                self.param_canvas.configure(yscrollcommand=self.param_scroll_y.set)
                self.param_canvas.bind('<Configure>', self.adjust_canvas)

                self.another_frame.columnconfigure(0, weight = 1)
                self.another_frame.columnconfigure(1, weight = 3)
                self.another_frame.columnconfigure(2, weight = 1)
                self.another_frame.columnconfigure(3, weight = 3)
                self.another_frame.columnconfigure(4, weight = 1)
                self.another_frame.columnconfigure(5, weight = 3)
                self.another_frame.columnconfigure(6, weight = 1)
                self.another_frame.columnconfigure(7, weight = 3)

                self.chisq_entry.config(state = 'normal')
                self.chisq_entry.delete(0, tk.END)
                try: self.chisq_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.3e}")
                except Exception: pass
                self.chisq_entry.config(state = 'readonly')

                self.r2_entry.config(state = 'normal')
                self.r2_entry.delete(0, tk.END)
                try: self.r2_entry.insert(0, f"{self.fit_r2[self.selected_dataset]:.6f}")
                except Exception: pass
                self.r2_entry.config(state = 'readonly')
                for x in range(self.box_number):
                    self.param_err_label.append(tk.Label(self.another_frame, text = u'\u03b4' + clean_split[x], bg='#E4E4E4'))
                    self.param_err_label[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.param_err_boxes.append(tk.Entry(self.another_frame, cursor="arrow", takefocus=0))
                    try: self.param_err_boxes[x].insert(0,f"{self.fit_uncert[self.selected_dataset][x]:.7e}")
                    except Exception: pass
                    self.param_err_boxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.param_err_boxes[x].config(state = 'readonly')
                    self.param_res_label.append(tk.Label(self.another_frame, text = clean_split[x], bg='#E4E4E4'))
                    self.param_res_label[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.param_res_boxes.append(tk.Entry(self.another_frame, cursor="arrow", takefocus=0))
                    try: self.param_res_boxes[x].insert(0,f"{self.fit_params[self.selected_dataset][x]:.7e}")
                    except Exception: pass
                    self.param_res_boxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_res_boxes[x].config(state = 'readonly')
                    self.param_boxes.append(tk.Entry(self.another_frame))
                    try: self.param_boxes[x].insert(0,f"{self.init_values[self.selected_dataset][x]:e}")
                    except Exception: pass
                    self.param_boxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_label.append(tk.Label(self.another_frame, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#E4E4E4'))
                    self.param_label[x].grid(column = 2, row = x, pady=10, padx=(15,0), sticky= tk.E)
                    self.plot_param_label.append(tk.Label(self.another_frame, text = clean_split[x], bg = '#E4E4E4'))
                    self.plot_param_label[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plot_param_boxes.append(tk.Entry(self.another_frame))
                    self.plot_param_boxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(self.another_frame,
                                   text='GET FULL OUTPUT',
                                   fg='white',
                                   bg='#F21112',
                                   activebackground='white',
                                   activeforeground='#F21112')
                output['command'] = self.show_output
                output['font'] = ('Roboto',int(20*self.master.winfo_width()/2350))
                self._add_hover(output)
                output.grid(row = x+1, column = 5)

            self.count = 2

            self.windows_item = self.param_canvas.create_window((0,0), window=self.another_frame, anchor="nw")

            sep2_plot = ttk.Separator(self.frame_right, orient = tk.VERTICAL)
            sep2_plot.place(in_ = self.frame_right, relx = 0.24, relheight = 0.245, rely = 0.20)
            sep3_plot = ttk.Separator(self.frame_right, orient = tk.HORIZONTAL)
            sep3_plot.place(in_ = self.frame_right, relwidth = 1, rely = 0.2 )
            sep4_plot = ttk.Separator(self.frame_right, orient = tk.HORIZONTAL)
            sep4_plot.place(in_ = self.frame_right, relwidth = 1, rely = 0.445 )
            sep5_plot = ttk.Separator(self.frame_right, orient = tk.VERTICAL)
            sep5_plot.place(in_ = self.frame_right, relx = 0, relheight = 1, rely = 0)

            self.param_canvas.update()

    def show_output(self):
        if self.full_output[self.selected_dataset]:
            tk.messagebox.showinfo('FULL OUTPUT', self.full_output[self.selected_dataset])
        else:
            tk.messagebox.showwarning('ERROR', 'Fit not yet done.')

    def adjust_canvas(self, event):
        canvas_width = event.width
        self.param_canvas.itemconfig(self.windows_item, width = canvas_width)
        self.param_canvas.configure(scrollregion = self.param_canvas.bbox("all"))

    def update(self):
        "Update the canvas and the scrollregion"
        self.update_idletasks()
        self.param_canvas.config(scrollregion=self.param_canvas.bbox(self.windows_item))

    def fit_data(self, data, init_params, max_iter, dataset_number):
        """
        Parameters
        ----------
        data : array of array
            Points, in the format [[x1,ex1,y1,ey1],[x2,ex2,y2,ey2],...]

        init_params: array
            Initial estimates for the parameter values

        Returns
        -------
        fit.beta: fitted parameters
        fit.sd_beta: parameter uncertainties
        fit.res_var: reduced chi-squared
        r2: R^2 of the fit
        """
        for i in range(len(self.clean_functions)):
            if self.clean_functions[i] == '':
                tk.messagebox.showwarning('ERROR',f'Fitting function for dataset {i+1} is not defined. Make sure it is compiled without errors.')
                return 0

        x_points = []
        y_points = []
        x_err    = []
        y_err    = []

        # start by testing that all points have the same dimensions and that there are no repeated points
        dims = len(data[0])
        for point in data:
            if len(point)!=dims:
                tk.messagebox.showwarning('ERROR','There are points with x uncertainty and points without. All points need to match before a fit can be done.')
                return False
            if point[0] in x_points:
                tk.messagebox.showwarning('ERROR','There are repeated points. Remove them before fitting.')
                return False
            x_points.append(point[0])
            y_points.append(point[-2])
            y_err.append(point[-1])
            if dims == 4:
                x_err.append(point[1])

        if x_err and np.any(np.array(x_err)==0):
            tk.messagebox.showwarning('ERROR',f'At least one point in dataset {self.current_selection} has a null x uncertainty. It is not possible to fit data with null uncertainty.')
            return 0
        if y_err and np.any(np.array(y_err)==0):
            tk.messagebox.showwarning('ERROR',f'At least one point in dataset {self.current_selection} has a null y uncertainty. It is not possible to fit data with null uncertainty.')
            return 0

        beta, sd_beta, res_var, r2, output = run_odr_fit(
            self.clean_functions[dataset_number],
            x_points, y_points, x_err, y_err, init_params, max_iter,
        )
        self.full_output[dataset_number] = output
        return (beta, sd_beta, res_var, r2)

    def open_file(self):
        self.erase_all_windows()

        file = tk.filedialog.askopenfilename()

        if not file:
            return

        if self.same_x.get():
            new_data = read_file(file,str,True,0)

        if self.dif_x.get() and self.dif_x_error.get()==0:
            new_data = read_file(file,str,True,1)

        if self.dif_x_error.get() and self.dif_x.get() and self.same_x.get()==0:
            new_data = read_file(file,str,True,2)
        for x in range(len(new_data)):
            self.add_dataset(new_data[x])

    def close(self):
        if hasattr(self, 'database'):
            self.database.close()
        self.master.destroy()

def main():
    root = tk.Tk()
    app = MainWindow(master=root)
    app.mainloop()


if __name__ == '__main__':
    main()
