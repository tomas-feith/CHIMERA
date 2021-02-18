# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author: tsfeith
"""

import tkinter as tk
import tkinter.font
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
        
        # Para garantir que os widgets e imagens mudam de tamanho
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
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.place_item("./img/Name_white.PNG", 0.6, self.title_canvas)
        self.place_item("./img/Image_white.PNG", 0.25, self.logo_canvas)

    def create_widgets(self):
        self.new = tk.Button(self.bottom, width = 8, height = 1)
        self.new["text"] = "NEW FIT"
        self.new["font"] = ("Roboto",35,"bold")
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
