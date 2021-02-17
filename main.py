# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author: tsfeith
"""

import tkinter as tk
from PIL import Image, ImageTk
# Estes imports só servem para editar o icon (pelo menos por enquanto)
import tempfile, base64, zlib

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
        
        width  = int(.8*self.master.winfo_screenwidth())
        height = int(.8*self.master.winfo_screenheight())
        self.master.geometry(str(width)+"x"+str(height))
        self.master.configure(background='#FCF6F5')
        self.master.update()
        self.pack()
        self.place_title(True)
        self.place_logo(True)
        self.create_widgets()
        
        # Para garantir que os widgets e imagens mudam de tamanho
        self.master.bind('<Configure>', self._resize_window)
        
    def place_title(self, first):
        # Criar a imagem
        self.top = tk.Frame(self.master, bg='#FCF6F5')
        self.top.pack(in_=self.master)
        self.title_src = Image.open("./img/Name_white.PNG")
        img_ratio = self.master.winfo_width()*0.6/float(self.title_src.size[0])
        self.title_src = self.title_src.resize((int(self.title_src.size[0]*img_ratio), int(self.title_src.size[1]*img_ratio)))
        # Criar a canvas
        if first:
            self.title_canvas = tk.Canvas(self.top, width = self.title_src.size[0], height = self.title_src.size[1] ,highlightthickness=0)
            self.title_canvas.pack(in_=self.top)
            self.title_canvas.update()
        else:
            self.title_canvas.config(width = self.title_src.size[0], height = self.title_src.size[1])
        # Inserir a imagem dentro da canvas
        self.title_img = ImageTk.PhotoImage(self.title_src)
        self.title_canvas.create_image(self.title_canvas.winfo_width()/2,self.title_canvas.winfo_height()/2,image=self.title_img)
    
    def place_logo(self, first):
        # Criar uma frame para colocar lá as coisas
        self.bottom = tk.Frame(self.master, bg='#FCF6F5')
        self.bottom.pack(in_=self.master, pady = 50)
        # Criar a imagem
        self.logo_src = Image.open("./img/Image_white.PNG")
        img_ratio = self.master.winfo_width()*0.25/float(self.logo_src.size[0])
        self.logo_src = self.logo_src.resize((int(self.logo_src.size[0]*img_ratio), int(self.logo_src.size[1]*img_ratio)))
        # Criar a canvas
        if first:
            self.logo_canvas = tk.Canvas(self.bottom, width = self.logo_src.size[0], height = self.logo_src.size[1] ,highlightthickness=0)
            self.logo_canvas.grid(column=1, row = 0)
            self.logo_canvas.update()
        else:
            self.logo_canvas.config(width = self.logo_src.size[0], height = self.logo_src.size[1])
        # Inserir a imagem dentro da canvas
        self.logo_img = ImageTk.PhotoImage(self.logo_src)
        self.logo_canvas.create_image(self.logo_canvas.winfo_width()/2,self.logo_canvas.winfo_height()/2,image=self.logo_img)
    
    def _resize_window(self, event):
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.place_title(False)
        self.place_logo(False)

    def create_widgets(self):
        
        self.new = tk.Button(self.bottom)
        self.new["text"] = "NEW FIT"
        self.new["command"] = self.say_new
        self.new.grid(column = 2, row = 0)
        
        self.hi_there = tk.Button(self.bottom)
        self.hi_there["text"] = "Hello World\n(click me)"
        self.hi_there["command"] = self.say_hi
        self.hi_there.grid(column = 0, row = 0)

    def say_hi(self):
        print("hi there, everyone!")
    
    def say_new(self):
        print("Create new fit")
        
root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()