# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author: tsfeith
"""

import tkinter as tk
from PIL import Image, ImageTk
# Estes imports só servem para editar o icon (pelo menos por enquanto)
import tempfile, base64, zlib
import time

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
        print("Import fit")
    
    def say_new(self):
        print("Create new fit")
        
root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
