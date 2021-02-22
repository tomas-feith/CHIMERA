# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author: tsfeith
"""

import tkinter as tk
from PIL import Image, ImageTk
# Estes imports só servem para editar o icon (pelo menos por enquanto)
import tempfile, base64, zlib
from tkinter import ttk

count= 0

class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        
        # Tirar o icon do tkinter
        ICON = zlib.decompress(base64.b64decode('eJxjYGAEQgEBBiDJwZDBy'
        'sAgxsDAoAHEQCEGBQaIOAg4sDIgACMUj4JRMApGwQgF/ykEAFXxQRc='))
        _, ICON_PATH = tempfile.mkstemp()
        with open(ICON_PATH, 'wb') as icon_file:
            icon_file.write(ICON)
        self.master.iconbitmap(default=ICON_PATH)
        # Tirar o título
        self.winfo_toplevel().title("")
        
        # Tamanhos default para a janela
        self.width  = int(.8*self.master.winfo_screenwidth())
        self.height = int(.8*self.master.winfo_screenheight())
        
        # Array para conter as canvas
        # [0]: Titulo, [1]: Logo
        self.canvases = []
        
        # Frames para conter os objetos
        self.top = tk.Frame(self.master, bg = '#FCF6F5')
        self.top.pack(in_ = self.master)
        self.bottom = tk.Frame(self.master, bg = '#FCF6F5')
        self.bottom.pack(in_ = self.master)
        
        # Canvases para as figuras
        self.title_canvas = tk.Canvas(self.top)
        self.title_canvas.pack(in_ = self.top)
        self.logo_canvas = tk.Canvas(self.bottom)
        self.logo_canvas.grid(in_ = self.bottom, column = 1, row = 0, pady = self.height/10)
        
        # Começar a definir a janela
        self.master.geometry(str(self.width)+"x"+str(self.height))
        self.master.configure(background='#FCF6F5')
        self.master.update()
        self.pack
        self.place_item("./img/Name_white.PNG", 0.6, self.title_canvas)
        self.place_item("./img/Image_white.PNG", 0.25, self.logo_canvas)
        self.create_widgets()
        
        global count
        # Para garantir que os widgets e imagens mudam de tamanho
        if(count == 0):
            self.master.bind('<Configure>', self._resize_window)
    
    def place_item(self, src, ratio, canvas):
        """
        Função para colocar um item genérico na janela

        Parameters
        ----------
        src : string
            Caminho para a imagem a colocar na canvas.
        ratio : float
            Razão entre o tamanho da imagem e o tamanho da janela pretendida.
        canvas : tk.Canvas
            Canvas onde se vai desenhar a imagem.

        Returns
        -------
        None.

        """
        img_src = Image.open(src)
        img_ratio = self.master.winfo_width()*ratio/float(img_src.size[0])
        img_src = img_src.resize((int(img_src.size[0]*img_ratio), int(img_src.size[1]*img_ratio)))
        canvas.config(width = img_src.size[0], height = img_src.size[1], highlightthickness = 0)
        img = ImageTk.PhotoImage(img_src)
        canvas.create_image(canvas.winfo_width()/2, canvas.winfo_height()/2,image = img)
        canvas.image = img
        
    def _resize_window(self, event):
        # Idea. Try to place all of these in one single function that is activated at once
        # The canvases are interfering with each other
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.place_item("./img/Name_white.PNG", 0.6, self.title_canvas)
        self.place_item("./img/Image_white.PNG", 0.25, self.logo_canvas)

    def create_widgets(self):
        self.new = tk.Button(self.bottom,
                             width = 13,
                             height=1,
                             fg='white',
                             bg='red',
                             activebackground='white',
                             activeforeground='red')
        self.new["text"] = "NEW FIT"
        self.new["font"] = ("Roboto",int(35*1000/self.master.winfo_width()),"bold")
        self.new["command"] = self.say_new
        self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
        # Alterar as cores quando entra e sai
        self.new.bind("<Enter>", func=lambda e: self.new.config(bg='white',fg='red'))
        self.new.bind("<Leave>", func=lambda e: self.new.config(bg='red',fg='white'))
        
        self.old = tk.Button(self.bottom,
                             width = 13,
                             height=1,
                             fg='white',
                             bg='red',
                             activebackground='white',
                             activeforeground='red')
        self.old["text"] = "IMPORT FIT"
        self.old["font"] = ("Roboto",int(35*1000/self.master.winfo_width()),"bold")
        self.old["command"] = self.say_import
        self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10))) 
        self.old.bind("<Enter>", func=lambda e: self.old.config(bg='white',fg='red'))
        self.old.bind("<Leave>", func=lambda e: self.old.config(bg='red',fg='white'))

    def say_import(self):
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.old.destroy()
        self.new.destroy()
        global count
        count = 1
        print("Import fit")
        self.master.configure(background='#FCF6F5')
        
    
    def say_new(self):
        print("Create new fit")
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.old.destroy()
        self.new.destroy()
        global count
        count = 1
        self.master.configure(background='#FCF6F5')
        
        self.frameleft = tk.Frame(self.master,  bg='#FCF6F5')
        self.frameleft.place( in_ = self.master, relwidth =0.5, relheight = 1,relx=0, rely=0)
        
        self.frameright = tk.Frame(self.master,  bg='#FCF6F5')
        self.frameright.place( in_ = self.master, relwidth=0.5, relheight=1,relx=0.5, rely=0)
        
        self.subframeright1=tk.Frame(self.frameright, bg = '#FCF6F5')
        self.subframeright1.place(in_ = self.frameright, relwidth=1, relheight=0.5, relx=0, rely=0)
        
        self.textentry = tk.Label(self.subframeright1,text= "Parameter")
        self.textentry.place(relwidth=0.65, rely=0.0, relheight=0.05)
        self.entry = tk.Entry(self.subframeright1, font=40)
        self.entry.place(relwidth=0.55, rely=0.05, relheight=0.05)
        self.entry.focus_set()
        self.upbutton = tk.Button(self.subframeright1, text= "update")
        self.upbutton.place(relwidth=0.1,relx=0.55, rely=0.05,relheight=0.05 )
        self.upbutton["command"] = self.update_parameter
        
        self.subframeright2=tk.Frame(self.frameright, bg = '#FCF6F5')
        self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.5, relx=0, rely=0.5)
    
    def update_parameter(self):
        self.parameter = self.entry.get()
        first_split = self.parameter.split(' ')
        clean_split = []
        for val in first_split:
            for param in val.split(','):
                if param:
                    clean_split.append(param)
                    
        boxnumber = len(clean_split)
        self.paramboxes=[]
        self.paramlabel=[]
        self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0)
        self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)
        
        
        self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
        self.paramscrolly.pack(side=tk.RIGHT, fill="y")
        
        self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
        self.paramcanvas.bind('<Configure>', lambda e: self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all")))
        
        self.anotherframe=tk.Frame(self.paramcanvas)
        
        
        self.paramcanvas.create_window((0,0), window = self.anotherframe, anchor = "nw")
        
        
        for x in range(boxnumber):
            self.paramboxes.append(tk.Entry(self.anotherframe, font=40))
            self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]))
            
        
        for x in range(boxnumber):
            self.paramlabel[x].grid(column = 0, row = x, pady=10)
            self.paramboxes[x].grid(column = 1, row = x, pady=10)
        
        
        
root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
