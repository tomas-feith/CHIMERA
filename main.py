# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author: tsfeith
"""

import tkinter as tk
from PIL import Image, ImageTk

class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.grid_columnconfigure(0, weight=1)
        # self.master.grid_rowconfigure(0, weight=1)
        width  = int(.8*self.master.winfo_screenwidth())
        height = int(.8*self.master.winfo_screenheight())
        self.master.geometry(str(width)+"x"+str(height))
        self.master.configure(background='#FCF6F5')
        self.master.update()
        self.grid()
        self.place_title(0)
        # self.create_widgets()

    def place_title(self, mode):
        if mode:
            self.canvas.delete("all")
        # Criar a imagem
        self.img_src = Image.open("./img/Name_white.PNG")
        img_ratio = self.master.winfo_width()*0.6/float(self.img_src.size[0])
        self.img_src = self.img_src.resize((int(self.img_src.size[0]*img_ratio), int(self.img_src.size[1]*img_ratio)))
        # Criar a canvas
        if not mode:
            self.canvas = tk.Canvas(self.master, width = self.img_src.size[0], height = self.img_src.size[1] ,highlightthickness=0)
            self.canvas.grid(column = 0, columnspan = 3, padx = 20, pady = 30)
            self.canvas.update()
        else:
            self.canvas.config(width = self.img_src.size[0], height = self.img_src.size[1])
        # Inserir a imagem dentro da canvas
        self.img = ImageTk.PhotoImage(self.img_src)
        self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.img)
        # Para garantir que a imagem muda de tamanho quando a window muda de tamanho
        self.canvas.bind('<Configure>', self._resize_image)
    
    def _resize_image(self, event):
        self.place_title(1)

    def create_widgets(self):
        self.hi_there = tk.Button(self)
        self.hi_there["text"] = "Hello World\n(click me)"
        self.hi_there["command"] = self.say_hi
        self.hi_there.pack(side="bottom")

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.pack(side="bottom")

    def say_hi(self):
        print("hi there, everyone!")
        
root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()