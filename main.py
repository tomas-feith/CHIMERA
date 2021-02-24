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
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt

# Isto serve para quê?
count = 0

def parser(expr, params, indep):    
    np.seterr(all='raise')
    functions = ['sin', # seno
             'cos', # cosseno
             'tan', # tangente
             'arcsin', # arco seno
             'arccos', # arco cosseno
             'arctan', # arco tangente
             'exp', # exponencial
             'log', # logaritmo natural
             'sqrt', # raiz quadrada
             'absolute', # módulo
             'heaviside', # função heaviside
             'cbrt', # raíz cúbica
             'sign' # operador sinal
             ]
    # Fazer limpeza dos params
    # Assumindo que estão separados por virgulas ou espaços
    # Os parâmetros limpos serão guardados neste array
    clean_split = []
    # Divide-se ao longo dos espaços todos
    first_split = params.split(' ')
    for val in first_split:
        # Divide-se cada um dos resultados da divisão anterior, agora ao longo das vírgulas
        for param in val.split(','):
            # Se param != ''
            if param:
                clean_split.append(param)
                
    # Verificar se nenhum dos nomes das variáveis são funções
    for val in clean_split:
        if val in functions:
            return 'O nome \''+str(val)+'\' já está associado a uma função. Dê um nome diferente.'
    # Aproveitar e verificar se a variável independente não é uma função
    if indep in functions:
        return 'O nome \''+str(indep)+'\' já está associado a uma função. Dê um nome diferente.'
                    
    # Ver se nenhum dos parâmetros é repetido
    for val in clean_split:
        if clean_split.count(val) > 1:
            return 'O parâmetro \''+str(val)+'\' foi dado mais que uma vez. Dê nomes distintos a cada parâmetro.'
                        
    # E já agora verificar se não está nos parâmetros
    if indep in clean_split:
        return 'O nome \''+str(indep)+'\' foi dado à variável independente e a um parâmetro. Altere um deles.'

    # Verificar se nenhum dos parâmetros são números
    for val in clean_split:
        try:
            float(val)
        except ValueError:
            pass
        # Se não der nenhum erro é por é um número e não queremos isso
        else:
            return 'O parâmetro dado \''+str(val)+'\' é um número. Utilize um parâmetro diferente.'
    # E verificar se a variável independente também não é
    try:
        float(indep)
    except ValueError:
        pass
    # Igual a acima
    else:
        return 'A variável independente dada \''+str(indep)+'\' é um número. Utilize uma diferente.'
    
    # Substituir as funções pelo equivalente numpy
    # Primeira substituição temporária para não haver erros de conversão
    for function in enumerate(functions):
        expr = expr.split(function[1])
        expr = ('['+str(len(clean_split)+function[0])+']').join(expr)
    # Substituir os nomes dos parâmetros
    for pair in enumerate(clean_split):
        expr = expr.split(pair[1])
        expr = ('B['+str(pair[0])+']').join(expr)
    
    # Substituir a variável independente
    expr = expr.split(indep)
    expr = 'x'.join(expr)

    # Voltar a substituir os elementos pelas funções
    for function in enumerate(functions):
        expr = expr.split('['+str(function[0]+len(clean_split))+']')
        expr = ('np.'+str(function[1])).join(expr)
    
    # Vamos finalmente testar se a função funciona
    # Valores de teste só porque sim
    B = [np.pi/2]*len(clean_split)
    x=-1
    try:
        eval(expr)
    except NameError as error:
        return 'A função \''+str(error).split('\'')[1]+'\' não foi reconhecida.'
    except FloatingPointError:
        return expr
    except SyntaxError:
        return 'Não foi possível compilar a sua expressão. Verifique se todos os parâmetros estão definidos e a expressão está escrita corretamente.'
                                                    
    return expr



class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # Esta é a janela principal
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

        # Definir o tamanho mínimo da janela
        self.master.minsize(int(0.5*self.master.winfo_screenwidth()),int(0.5*self.master.winfo_screenheight()))

        # Tamanhos default para a janela
        self.width  = int(.8*self.master.winfo_screenwidth())
        self.height = int(.8*self.master.winfo_screenheight())

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
        # Criar a janela per se
        self.pack
        # Colocar as imagens e botoes
        self.place_item("./img/Name_white.PNG", 0.6, self.title_canvas)
        self.place_item("./img/Image_white.PNG", 0.25, self.logo_canvas)
        self.create_widgets()

        global count
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
        # Definir a canvas para pôr tudo na tela
        canvas.config(width = img_src.size[0], height = img_src.size[1], highlightthickness = 0)
        img = ImageTk.PhotoImage(img_src)
        canvas.create_image(canvas.winfo_width()/2, canvas.winfo_height()/2,image = img)
        # Guardar a imagem só porque às vezes o tkinter é chato
        canvas.image = img

    def _resize_window(self, event):
        # Isto serve para quê?
        if(count == 0):
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
        self.new["command"] = self.create_new
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
        self.old["command"] = self.create_import
        self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10)))
        self.old.bind("<Enter>", func=lambda e: self.old.config(bg='white',fg='red'))
        self.old.bind("<Leave>", func=lambda e: self.old.config(bg='red',fg='white'))

    def create_import(self):
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.old.destroy()
        self.new.destroy()
        global count
        count = 1
        print("Import fit")
        self.master.configure(background='#FCF6F5')


    def create_new(self):
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

        self.independentlabel = tk.Label(self.subframeright1,text= "Independent Variable")
        self.independentlabel.place(relwidth=0.2, rely=0, relheight=0.1)
        self.independententry = tk.Entry(self.subframeright1, font=40)
        self.independententry.place(relwidth=0.8, rely=0, relheight=0.1, relx = 0.2)
        self.independententry.focus_set()


        self.parameterlabel = tk.Label(self.subframeright1,text= "Parameter")
        self.parameterlabel.place(relwidth=0.2, rely=0.1, relheight=0.1)
        self.parameterentry = tk.Entry(self.subframeright1, font=40)
        self.parameterentry.place(relwidth=0.6, rely=0.1, relheight=0.1,relx = 0.2)
        self.parameterentry.focus_set()
        self.upbutton = tk.Button(self.subframeright1, text= "update")
        self.upbutton.place(relwidth=0.2,relx=0.8, rely=0.1,relheight=0.1 )
        self.upbutton["command"] = self.update_parameter

        self.functionlabel = tk.Label(self.subframeright1,text= "Function")
        self.functionlabel.place(relwidth=0.2, rely=0.2, relheight=0.1)
        self.functionentry = tk.Entry(self.subframeright1, font=40)
        self.functionentry.place(relwidth=0.8,relx=0.2, rely=0.2, relheight=0.1)
        self.functionentry.focus_set()
        self.compilebutton = tk.Button(self.subframeright1, text= "compile")
        self.compilebutton.place(relwidth=0.2,relx=0.8, rely=0.2,relheight=0.1 )
        self.compilebutton["command"] = self.compile_function


        self.subframeright2=tk.Frame(self.frameright, bg = '#FCF6F5')
        self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.3, relx=0, rely=0.25)

        self.subframeleft1=tk.Frame(self.frameleft, bg = '#FCF6F5')
        self.subframeleft1.place(in_ = self.frameleft, relwidth=1, relheight=0.5, relx=0, rely=0)

        self.subframeleft2 = tk.Frame(self.frameleft, bg = 'white')
        self.subframeleft2.place(in_ = self.frameleft, relwidth = 1, relheight= 0.5, relx=0, rely=0.5)

        self.subframeright3 = tk.Frame(self.frameright)
        self.subframeright3.place(in_ = self.frameright, relwidth = 1, relheight = 0.40, rely=0.60)

        self.xaxislabel = tk.Label(self.subframeright3, text= "X Axis")
        self.xaxislabel.place(in_ = self.subframeright3, relwidth = 0.5, relheight=0.1, relx=0, rely=0)

        self.yaxislabel = tk.Label(self.subframeright3, text= "Y Axis")
        self.yaxislabel.place(in_ = self.subframeright3, relwidth = 0.5, relheight=0.1, relx=0.5, rely=0)

        self.xaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from")
        self.xaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.15, relheight=0.1, relx = 0, rely = 0.1)

        self.xaxisminentry = tk.Entry(self.subframeright3)
        self.xaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.15, rely=0.1)

        self.xaxistolabel = tk.Label(self.subframeright3, text = "to")
        self.xaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.25, rely=0.1)

        self.xaxismaxentry = tk.Entry(self.subframeright3)
        self.xaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.3, rely=0.1)

        self.xaxistitlelabel = tk.Label(self.subframeright3, text = "Title")
        self.xaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0, rely=0.25)

        self.xaxistitleentry = tk.Entry(self.subframeright3)
        self.xaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.4, relheight = 0.1, relx = 0.1, rely=0.25)

        self.xaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing")
        self.xaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.15, relheight = 0.1, relx=0, rely= 0.4)

        self.xaxistickspentry = tk.Entry(self.subframeright3)
        self.xaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.15, rely=0.4)


        self.yaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from")
        self.yaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.15, relheight=0.1, relx = 5, rely = 0.1)

        self.yaxisminentry = tk.Entry(self.subframeright3)
        self.yaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.65, rely=0.1)

        self.yaxistolabel = tk.Label(self.subframeright3, text = "to")
        self.yaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.75, rely=0.1)

        self.yaxismaxentry = tk.Entry(self.subframeright3)
        self.yaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.8, rely=0.1)

        self.yaxistitlelabel = tk.Label(self.subframeright3, text = "Title")
        self.yaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0.5, rely=0.25)

        self.yaxistitleentry = tk.Entry(self.subframeright3)
        self.yaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.4, relheight = 0.1, relx = 0.6, rely=0.25)

        self.yaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing")
        self.yaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.15, relheight = 0.1, relx=0.5, rely= 0.4)

        self.yaxistickspentry = tk.Entry(self.subframeright3)
        self.yaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.65, rely=0.4)



        self.dataentry = ScrolledText(self.subframeleft2)
        self.dataentry.pack(expand = 1, fill = tk.BOTH)


                                                    
    def compile_function(self):
        # A partir daqui a função já está definida e podemos usá-la
        # ATENÇÃO: Para usar é a função fit_func, não a self.function
        # A primeira devolve números, a segunda é só uma string
        self.function = parser(
                                self.functionentry.get(),
                                self.parameterentry.get(),
                                self.independententry.get()
                                )

        # Daqui para baixo é fazer o plot em si

        self.datastring = self.dataentry.get("1.0", "end-1c")
        print(self.datastring)

        first_split = self.datastring.split()

        print(first_split)

        self.abcissas = []
        self.erabcissas = []
        self.ordenadas = []
        self.erordenadas = []

        #adicionar condiçoes
        tam = int(len(first_split)/4)
        print(tam)
        for x in range(tam):
            self.abcissas.append(float(first_split[0+x*4]))
            self.erabcissas.append(float(first_split[1+x*4]))
            self.ordenadas.append(float(first_split[2+x*4]))
            self.erordenadas.append(float(first_split[3+x*4]))



        self.abc = np.array(self.abcissas)
        self.erabc = np.array(self.erabcissas)
        self.ord = np.array(self.ordenadas)
        self.erord = np.array(self.erordenadas)

        fig = Figure(figsize=(10,10))

        x_ticks = []
        y_ticks = []

        xticknumber =1+int((float(self.xaxismaxentry.get())-float(self.xaxisminentry.get()))/float(self.xaxistickspentry.get()))
        yticknumber =1+int((float(self.yaxismaxentry.get())-float(self.yaxisminentry.get()))/float(self.yaxistickspentry.get()))


        for x in range(xticknumber):
            x_ticks.append(x*float(self.xaxistickspentry.get()) + float(self.xaxisminentry.get()))

        for x in range(yticknumber):
            y_ticks.append(x*float(self.yaxistickspentry.get()) + float(self.yaxisminentry.get()))

        a = fig.add_subplot(111,projection = None, xlim = (float(self.xaxisminentry.get()), float(self.xaxismaxentry.get())),
                     ylim = (float(self.yaxisminentry.get()), float(self.yaxismaxentry.get())),
                     xticks = x_ticks, yticks = y_ticks, ylabel = self.yaxistitleentry.get(),
                     xlabel = self.xaxistitleentry.get())




        a.errorbar(self.abc, self.ord, xerr = self.erabc, yerr = self.erord, fmt = 'none')

        self.canvas = FigureCanvasTkAgg(fig, master=self.subframeleft1)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

    def update_parameter(self):
        self.parameter = self.parameterentry.get()
        first_split = self.parameter.split(' ')
        clean_split = []
        for val in first_split:
            for param in val.split(','):
                if param:
                    clean_split.append(param)





        global count
        if (count==2) :
            for x in range(self.boxnumber):
                self.paramboxes[x].grid_forget()
                self.paramlabel[x].grid_forget()
                self.paramboxes[x].grid_rowconfigure(x, weight=1)


            self.subframeright2.destroy()

            self.subframeright2=tk.Frame(self.frameright, bg = '#FCF6F5')
            self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.3, relx=0, rely=0.25)

            self.boxnumber = len(clean_split)

            self.paramlabel=[]
            self.paramboxes=[]

            self.paramscrolly.destroy()
            self.anotherframe.destroy()
            self.paramcanvas.destroy()


            self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0)
            self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)

            self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
            self.paramscrolly.pack(side=tk.RIGHT, fill="y")

            self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
            self.paramcanvas.bind('<Configure>', lambda e: self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all")))


            self.anotherframe=tk.Frame(self.paramcanvas)

            self.anotherframe.grid_columnconfigure(0, weight=1)
            self.anotherframe.grid_columnconfigure(1, weight=1)
            self.paramcanvas.create_window((0,0), window = self.anotherframe, anchor = "nw")


            self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))




            for x in range(self.boxnumber):
                self.anotherframe.grid_rowconfigure(x, weight=1)
                self.paramboxes.append(tk.Entry(self.anotherframe))
                self.paramboxes[x].grid(column = 1, row = x, pady=10, sticky='nsew')
                self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]))
                self.paramlabel[x].grid(column = 0, row = x, pady=10, sticky= 'nsew')



        if (count == 1):

            self.paramlabel=[]
            self.paramboxes=[]

            self.boxnumber = len(clean_split)

            self.inicialguesslabel = tk.Label(self.subframeright1, text= "Inicial Guess")
            self.inicialguesslabel.place(rely=0.4, relwidth=0.3, relheight = 0.1, relx=0)

            self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0)
            self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)




            self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
            self.paramscrolly.pack(side=tk.RIGHT, fill="y")

            self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
            self.paramcanvas.bind('<Configure>', lambda e: self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all")))


            self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))

            self.anotherframe=tk.Frame(self.paramcanvas)

            self.paramcanvas.create_window((0,0), window = self.anotherframe, anchor = "nw")



            for x in range(self.boxnumber):
                self.paramboxes.append(tk.Entry(self.anotherframe))
                self.paramboxes[x].grid(column = 1, row = x, pady=10, sticky='nsew')
                self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]))
                self.paramlabel[x].grid(column = 0, row = x, pady=10, sticky= 'nsew')

        count = 2
        
    def fit_function(self, x, B):
        return eval(self.function)

root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
