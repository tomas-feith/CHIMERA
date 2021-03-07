# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author:
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
# import matplotlib.pyplot as plt
import pandas as pd
from io import StringIO
from scipy import odr
from tkinter import colorchooser

count = 0

a = 0

def process_params(params, indep):
    allowed = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')
    functions = ['sin',
                 'cos',
                 'tan',
                 'arcsin',
                 'arccos',
                 'arctan',
                 'exp',
                 'log',
                 'sqrt',
                 'absolute',
                 'heaviside',
                 'cbrt',
                 'sign'
                 ]
    
    if (len([p for p in indep.split(' ') if p]) != 1):
        return (False, 'Multiple independent variables found. Only one is allowed.')
    indep.replace(' ','')
    
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
    
    # Ver se foi dado algum parâmetro
    if clean_split == []:
        return (False, 'No parameters were found.')
    # Ver se foi dada a variável independente
    # Mas primeiro apagar eventuais espaços na variável
    indep=indep.replace(' ','')
    if indep == '':
        return (False, 'No independent variable was found.')
    # Ver se algum dos parâmetros tem carateres proibidos
    for val in clean_split:
        for char in val:
            if char not in allowed:
                return (False, 'Parameter \''+str(val)+'\' contains the character \''+str(char)+'\'. Only letters or numbers allowed.')
    # Ver se a variavel indep tem caraters proibidos
    for char in indep:
        if char not in allowed:
            return (False, 'Independent variable \''+str(indep)+'\' contains the character \''+str(char)+'\'. Only letters or numbers allowed.')

    # Verificar se nenhum dos nomes das variáveis são funções
    for val in clean_split:
        if val in functions:
            return (False, 'Name \''+str(val)+'\' is already binded to a function. Provide a different name.')
    # Verificar se a variável independente não é uma função
    if indep in functions:
        return (False, 'Name \''+str(indep)+'\' is already associated to a function. Provide a different name.')

    # Ver se nenhum dos parâmetros é repetido
    for val in clean_split:
        if clean_split.count(val) > 1:
            return (False, 'Parameter \''+str(val)+'\' was provided more than once. Give different names to each parameter.')

    # Verificar se a variável independente não está nos parâmetros
    if indep in clean_split:
        return (False, 'Name \''+str(indep)+'\' was given to the independent variable and to a parameter. Change one of them.')

    # Verificar se nenhum dos parâmetros são números
    for val in clean_split:
        try:
            float(val)
        except ValueError:
            pass
        # Se não der nenhum erro é por é um número e não queremos isso
        else:
            return (False, 'Parameter \''+str(val)+'\' given is a number. Use a different name.')
    # E verificar se a variável independente também não é
    try:
        float(indep)
    except ValueError:
        pass
    # Igual a acima
    else:
        return (False, 'Independent variable \''+str(indep)+'\' given is a number. Use a different name.')
    
    return (True, clean_split)
    
def parser(expr, params, indep):
    np.seterr(all='raise')
    # Funções do numpy a utilizar
    # Ainda falta acrescentar as funções de estatística
    functions = ['sin',
                 'cos',
                 'tan',
                 'arcsin',
                 'arccos',
                 'arctan',
                 'exp',
                 'log',
                 'sqrt',
                 'absolute',
                 'heaviside',
                 'cbrt',
                 'sign'
                 ]
    
    # Ver se a função não está vazia
    expr=expr.replace(' ','')
    if expr == '':
        return (False, 'No fitting function was found.')

    process = process_params(params, indep)
    
    if process[0]:
        clean_split = process[1]
    else:
        return (False, process[1])
    
    # Ver se a função contém a variável independente
    if indep not in expr:
        return (False, "Independent variable is not present in fit function.")
    
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
    expr = '_x'.join(expr)

    # Voltar a substituir os elementos pelas funções
    for function in enumerate(functions):
        expr = expr.split('['+str(function[0]+len(clean_split))+']')
        expr = ('np.'+str(function[1])).join(expr)

    # Vamos finalmente testar se a função funciona
    # Valores de teste só porque sim
    
    B = [np.pi/2]*len(clean_split)
    _x=-1
    
    try:
        eval(expr)
    except NameError as error:
        return (False, 'Function \''+str(error).split('\'')[1]+'\' not recognized.')
    except AttributeError as error:
        return (False, 'Function '+str(error).split('attribute ')[1]+' not recognized.')
    except FloatingPointError:
        return (True, expr)
    except SyntaxError:
        return (False, 'It was not possible to compile your expression. Verify if all your parameters are defined and the expression is written correctly.')

    return (True, expr)

def read_file(src, out, mode, datatype):
    """
    Função para ler os dados de ficheiros de texto ou excel

    Parameters
    ----------
    src : string
        Caminho para o ficheiro.
    out : type
        str/float - devolver os elementos todos neste formato.
    mode : bool
        true: enviar os dados para a variavel dos dados

    Returns
    -------
    data : array of array of array
        Dados lidos do ficheiro.
    """
    formats = [['xls', 'xlsx', 'xlsm', 'xlsb', 'odf', 'ods', 'odt'],
               ['csv', 'txt', 'dat']
              ]
    form = -1
    # Determinar que tipo de ficheiro estamos a utilizar
    if isinstance(src, StringIO):
        form = 1
    else:
        for i in enumerate(formats):
            for ext in i[1]:
                if src.split('.')[-1] == ext:
                    form = i[0]
    # Se não for nenhum dos considerados, devolver -1 para marcar o erro
    if form == -1:
        return -1
    # Se for da classe ficheiro de texto
    if form:
        data = pd.read_csv(src, sep=r"\s+|;|:|None|,", engine='python', dtype="object", header=None)
    # Se for da classe Excel
    else:
        data = pd.read_excel(src, dtype="object",header=None)
    

    # Fazer a divisão nos datasets fornecidos
    # Se não houver incerteza no x, então o número de colunas é ímpar
    full_sets = []
    
    #Datatype 0 funciona dentro do programa, os outros dois so sao chamados caso venha de excel
    if(datatype == 0):
        if (data.shape[1]%2)!=0:
            for i in range(1,int((data.shape[1]+1)/2)):
                points = []
                for j in range(len(data[i].to_numpy())):
                    x = data[0].to_numpy(out)[j]
                    y = data[2*i-1].to_numpy(out)[j]
                    ey = data[2*i].to_numpy(out)[j]
                    # Procurar incoerências nas linhas
                    if (
                            (out==float and np.isnan(y)!=np.isnan(ey)) or
                            (out==str and y=='nan' and ey!='nan') or
                            (out==str and y!='nan'and ey=='nan')
                        ):
                        return -2
                    # Se a linha estiver vazia não se acrescenta
                    if (
                            not (out==float and np.isnan(x)) and
                            not (out==str and x=='nan') and
                            not (out==float and np.isnan(y) and np.isnan(ey)) and
                            not (out==str and y=='nan' and ey=='nan')
                        ):
                        points.append([x, y, ey])
                full_sets.append(points)
        # Se houver incerteza no x o tratamento é ligeiramente diferente
        else:
            for i in range(1,int((data.shape[1])/2)):
                points = []
                for j in range(len(data[2*i].to_numpy())):
                    x = data[0].to_numpy(out)[j]
                    ex = data[1].to_numpy(out)[j]
                    y = data[2*i].to_numpy(out)[j]
                    ey = data[2*i+1].to_numpy(out)[j]
                    # Procurar incoerências nas linhas
                    if (
                            (out==float and np.isnan(x)!=np.isnan(ex)) or
                            (out==str and x!='nan' and ex!='nan') or
                            (out==float and np.isnan(y)!=np.isnan(ey)) or
                            (out==str and y=='nan' and ey!='nan') or
                            (out==str and y!='nan'and ey=='nan')
                        ):
                        return -2
                    # Se a linha estiver vazia não se acrescenta
                    if (
                            not (out==float and np.isnan(x) and np.isnan(ex)) and
                            not (out==str and x=='nan' and ex=='nan') and
                            not (out==float and np.isnan(y) and np.isnan(ey)) and
                            not (out==str and y=='nan' and ey=='nan')
                        ):
                        points.append([x, ex, y, ey])
                full_sets.append(points)
    
    if(datatype == 1):
            for i in range(0,int((data.shape[1])/3)):
                points = []
                for j in range(len(data[3*i].to_numpy())):
                    x = data[3*i].to_numpy(out)[j]
                    y = data[3*i+1].to_numpy(out)[j]
                    ey = data[3*i+2].to_numpy(out)[j]
                    # Procurar incoerências nas linhas
                    #if (
                     #       (out==float and np.isnan(y)!=np.isnan(ey)) or
                      #      (out==str and y=='nan' and ey!='nan') or
                       #     (out==str and y!='nan'and ey=='nan')
                        #):
                        #return -2
                    # Se a linha estiver vazia não se acrescenta
                    if (
                            not (out==float and np.isnan(x)) and
                            not (out==str and x=='nan') and
                            not (out==float and np.isnan(y) and np.isnan(ey)) and
                            not (out==str and y=='nan' and ey=='nan')
                        ):
                        points.append([x, y, ey])
                full_sets.append(points)
                
                
    # Se houver incerteza no x o tratamento é ligeiramente diferente
    if(datatype == 2):
            for i in range(0,int((data.shape[1])/4)):
               
                points = []
                for j in range(len(data[4*i].to_numpy())):
                    x = data[4*i].to_numpy(out)[j]
                    ex = data[4*i+1].to_numpy(out)[j]
                    y = data[4*i+2].to_numpy(out)[j]
                    ey = data[4*i+3].to_numpy(out)[j]
                    # Procurar incoerências nas linhas
                    #if (
                     #       (out==float and np.isnan(x)!=np.isnan(ex)) or
                      #      (out==str and x!='nan' and ex!='nan') or
                       #     (out==float and np.isnan(y)!=np.isnan(ey)) or
                        #    (out==str and y=='nan' and ey!='nan') or
                          #  (out==str and y!='nan'and ey=='nan')
                        #):
                        #return -32
                    # Se a linha estiver vazia não se acrescenta
                    if (
                            not (out==float and np.isnan(x) and np.isnan(ex)) and
                            not (out==str and x=='nan' and ex=='nan') and
                            not (out==float and np.isnan(y) and np.isnan(ey)) and
                            not (out==str and y=='nan' and ey=='nan')
                        ):
                        points.append([x, ex, y, ey])
                full_sets.append(points)
        
    
    if mode:
        for i in range(len(full_sets)):
            for j in range(len(full_sets[i])):
                full_sets[i][j] = " ".join(full_sets[i][j])
            full_sets[i] = "\n".join(full_sets[i])        

    return full_sets

class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # Esta é a janela principal
        self.master = master
        
        
        
        master.state('zoomed')

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
        # Isto serve para quê? Pra so chamar estas cenas quando ainda tas no ecra inicial
        if(count == 0):
            self.title_canvas.delete("all")
            self.logo_canvas.delete("all")
            self.place_item("./img/Name_white.PNG", 0.6, self.title_canvas)
            self.place_item("./img/Image_white.PNG", 0.22, self.logo_canvas)
            #Define novas posicoes relativas a janela
            self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10)))
            self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
            #define novos tamanhos relativos a janela
            self.new["font"] = ("Roboto",int(0.018*self.master.winfo_width()),"bold")
            self.old["font"] = ("Roboto",int(0.018*self.master.winfo_width()),"bold")
            self.new.configure(height = 1)
            self.old.configure(height = 1)
            
            
        if(count == 1 or count == 2):    
            for button in self.buttons:
                button["font"] = ("Roboto",int(0.011*self.master.winfo_width()))
                self.functionlabel["font"] = ("Roboto",int(0.013*self.master.winfo_width()))
                self.parameterlabel["font"] = ("Roboto",int(0.013*self.master.winfo_width()))
                self.independentlabel["font"] = ("Roboto",int(0.012*self.master.winfo_width()))
                self.independententry.configure(font=("Roboto", int(0.028*self.master.winfo_height())))
                self.parameterentry.configure(font=("Roboto", int(0.028*self.master.winfo_height())))
                self.functionentry.configure(font=("Roboto", int(0.028*self.master.winfo_height())))
            
            

            
            

    def create_widgets(self):
        # Criar botão para um novo fit
        self.new = tk.Button(self.bottom,
                             width = int(0.011*self.master.winfo_width()),
                             height=1,
                             fg='white',
                             bg='red',
                             activebackground='white',
                             activeforeground='red')
        self.new["text"] = "NEW FIT"
        self.new["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        self.new["command"] = self.create_new
        self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
        # Alterar as cores quando entra e sai
        self.new.bind("<Enter>", func=lambda e: self.new.config(bg='white',fg='red'))
        self.new.bind("<Leave>", func=lambda e: self.new.config(bg='red',fg='white'))

        # Criar botão para importar um fit
        self.old = tk.Button(self.bottom,
                             width = int(0.011*self.master.winfo_width()),
                             height=1,
                             fg='white',
                             bg='red',
                             activebackground='white',
                             activeforeground='red')
        self.old["text"] = "IMPORT FIT"
        self.old["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        self.old["command"] = self.create_import
        self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10)))
        self.old.bind("<Enter>", func=lambda e: self.old.config(bg='white',fg='red'))
        self.old.bind("<Leave>", func=lambda e: self.old.config(bg='red',fg='white'))

    def create_import(self):
        # Destruir tudo o que estava na janela
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.old.destroy()
        self.new.destroy()
        global count
        count = 1
        self.master.configure(background='#FCF6F5')

    def create_new(self):
        self.countplots = 0
        # Destruir tudo o que estava na janela
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.old.destroy()
        self.new.destroy()
        global count
        count = 1
        
        self.master.configure(background='#FCF6F5')

        # Criação da estrutura de frames da janela
        self.frameleft = tk.Frame(self.master,  bg='#FCF6F5')
        self.frameleft.place(in_=self.master, relwidth=0.5, relheight=1, relx=0, rely=0)
        
        #Frameright, contem tudo na parte direita da janela
        self.frameright = tk.Frame(self.master,  bg='#FCF6F5')
        self.frameright.place( in_ = self.master, relwidth=0.5, relheight=1,relx=0.5, rely=0)

        #Subsecção da mesma onde se inserem as entrys de parametros, variavel independente e funçao
        self.subframeright1=tk.Frame(self.frameright, bg='#FCF6F5', highlightbackground="black", highlightthickness=0, padx=20, pady=20)
        self.subframeright1.place(in_=self.frameright, relwidth=1, relheight=0.5, relx=0, rely=0)
        
         # Criação das frames para a edição visual do gráfico
        self.subframeright2=tk.Frame(self.frameright, bg='#FCF6F5')
        self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.3, relx=0, rely=0.25)

        self.subframeleft1=tk.Frame(self.frameleft, bg='#FCF6F5')
        self.subframeleft1.place(in_ = self.frameleft, relwidth=1, relheight=0.5, relx=0, rely=0)

        self.plotbuttonframe = tk.Frame(self.frameleft, bg= '#FCF6F5')
        self.plotbuttonframe.place(in_ = self.frameleft, relwidth=1, relheight=0.05, relx=0, rely=0.5)
        
        self.subframeleft2 = tk.Frame(self.frameleft, bg='#FCF6F5')
        self.subframeleft2.place(in_ = self.frameleft, relwidth = 1, relheight= 0.45, relx=0, rely=0.55)
        
        #Criação da zona onde se inserem as informaçoes relativas aos eixos do grafico
        self.subframeright3 = tk.Frame(self.frameright, bg='#FCF6F5')
        self.subframeright3.place(in_ = self.frameright, relwidth = 1, relheight = 0.40, rely=0.60)

        #Criação do botão que chama a função que processa a funçao
        self.compilebutton = tk.Button(self.subframeright1,
                                       text="COMPILE",
                                       fg='white',
                                       bg='red',
                                       activebackground='white',
                                       activeforeground='red')
        self.compilebutton.place(relwidth=0.2,relx=0.8, rely=0.2,relheight=0.1 )
        self.compilebutton["command"] = self.compile_function
        
        #Botão que serve para updatar a lista de entries dos parâmetros
        self.upbutton = tk.Button(self.subframeright1,
                                  text="UPDATE",
                                  fg='white',
                                  bg='red',
                                  activebackground='white',
                                  activeforeground='red')
        self.upbutton.place(relwidth=0.2,relx=0.8, rely=0.1,relheight=0.1 )
        self.upbutton["command"] = self.update_parameter
        
        #Botão pra plottar o dataset, chama a função plot_dataset
        self.plotbutton = tk.Button(self.plotbuttonframe,
                                       text="PLOT",
                                       fg='white',
                                       bg='red',
                                       activebackground='white',
                                       activeforeground='red')
        
        self.plotbutton.place(in_  = self.plotbuttonframe, relwidth=0.2, relheight=1)
        self.plotbutton["command"] = self.plot_dataset
        
        #Botão pra plottar a funçao, chama a funçao plot_function
        self.plotfunctionbutton = tk.Button(self.plotbuttonframe,
                                       text="PLOT FUNCTION",
                                       fg='white',
                                       bg='red',
                                       activebackground='white',
                                       activeforeground='red')
        
        self.plotfunctionbutton.place(in_  = self.plotbuttonframe, relwidth=0.26, relheight=1,relx = 0.63)
        self.plotfunctionbutton["command"] = self.plot_function
        self.wantfunction = 0
        
        # Botão para importar ficheiros
        self.import_data = tk.Button(self.plotbuttonframe,
                                     text='IMPORT DATA',
                                     fg='white',
                                     bg='red',
                                     activebackground='white',
                                     activeforeground='red')
        self.import_data.place(in_  = self.plotbuttonframe, relwidth=0.23, relheight=1,relx = 0.4)
        self.import_data["command"] = self.import_window
        
        #Criação do botão ligado à funçao que adiciona mais um dataset
        self.adddatasetbutton = tk.Button(self.plotbuttonframe,
                                       text="+",
                                       fg='white',
                                       bg='red',
                                       activebackground='white',
                                       activeforeground='red', command = lambda: self.add_dataset(''))
        self.adddatasetbutton.place(in_ =self.plotbuttonframe, relwidth=0.05, relheight=1, relx = 0.35)
        
        self.fitbutton = tk.Button(self.plotbuttonframe,
                                       text="FIT",
                                       fg='white',
                                       bg='red',
                                       activebackground='white',
                                       activeforeground='red')
        self.fitbutton.place(in_ =self.plotbuttonframe, relwidth=0.11, relheight=1, relx = 0.89)
        self.fitbutton["command"] = self.fit_activate
        self.wantfit = tk.BooleanVar()
        self.wantfit.set(0)
        
        # Variável para armazenar todos os botoes
        self.buttons = [self.upbutton, 
                  self.compilebutton,
                  self.plotbutton,
                  self.plotfunctionbutton,
                  self.import_data,
                  self.adddatasetbutton,
                  self.fitbutton
                  ]
        
        for button in self.buttons:
            def hover(button):
                return lambda e: button.config(bg='white',fg='red')
            def unhover(button):
                return lambda e: button.config(bg='red',fg='white')
            button.bind("<Enter>", hover(button))
            button.bind("<Leave>", unhover(button))
            button["font"] = ("Roboto",int(0.011*self.master.winfo_width()))
        
        self.datastringcarrier = "1 0.5 2 0.5\n2 0.5 3 0.5\n3 0.5 5 0.5\n4 0.5 3 0.5\n5 0.5 6 0.5"
        # Criar uma menu bar
        # esta menubar é a mais geral, é a que contem as outras
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        menubar.add_radiobutton
        
        # Este é o botão file na menubar
        self.fileMenu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=self.fileMenu)
        
        # Botao na menubar para escolher as opçoes do plot
        self.plotoptions = tk.Menu(menubar)
        menubar.add_cascade(label="Plot options", menu=self.plotoptions)
        
        # Estas 3 variáveis servem para o utilizador escolher o que quer ver
        self.wantpoints = tk.BooleanVar()
        self.wantline = tk.BooleanVar()
        self.wanterror = tk.BooleanVar()
        # Valores default para as ditas variáveis
        self.wantpoints.set(1)
        self.wantline.set(0)
        self.wanterror.set(0)

        # Aqui adicionam-se os 3 checkbuttons da dita checklist do que o utilizador quer ler,
        # as variáveis definidas anteriormente servem para registar se o utilizador tem o dito setting selecionado ou nao
        self.plotoptions.add_checkbutton( label = "plot points", onvalue = 1, offvalue = 0, variable = self.wantpoints)
        self.plotoptions.add_checkbutton( label = "plot line", onvalue = 1, offvalue = 0, variable = self.wantline)
        self.plotoptions.add_checkbutton( label = "error bars", onvalue = 1, offvalue = 0, variable = self.wanterror)
       
        # Estes 3 menus na menubar servem para selecionar a cor dos markers(pontos), da linha e das errorbars
        self.choosecolor = tk.Menu(menubar)
        menubar.add_cascade(label="Choose Colors", menu = self.choosecolor)
        
        

        self.currentselection = 1
        
        self.markercolorvar = []
        self.linecolorvar = []
        self.errorcolorvar = []
        
        self.markercolorvar.append('black')
        self.linecolorvar.append('black')
        self.errorcolorvar.append('black')


       
        
        # Aqui tou so a meter os checkbuttons nas caixas
        self.choosecolor.add_command(label = 'Marker Color', command = self.markercolorpick)
        self.choosecolor.add_command(label = 'Line Color', command = self.linecolorpick)
        self.choosecolor.add_command(label = 'Errorbar Color', command = self.errorcolorpick)
       

        # Criação da zona para inserir a variável independente
        self.independentlabel = tk.Label(self.subframeright1,text="Independent Var", bg='#FCF6F5')
        self.independentlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.independentlabel.place(relwidth=0.25, rely=0, relheight=0.1)
        self.independententry = tk.Entry(self.subframeright1, font=int(0.01*self.master.winfo_width()))
        self.independententry.place(relwidth=0.30, rely=0, relheight=0.1, relx = 0.27)
        self.independententry.insert(0, 'x')
        self.independententry.focus_set()

        # Criação da zona para inserir os parâmetros
        self.parameterlabel = tk.Label(self.subframeright1,text="Parameter", bg='#FCF6F5')
        self.parameterlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.parameterlabel.place(relwidth=0.22, rely=0.1, relheight=0.1)
        self.parameterentry = tk.Entry(self.subframeright1, font=40)
        self.parameterentry.place(relwidth=0.55, rely=0.1, relheight=0.1,relx = 0.27)
        self.parameterentry.insert(0, "a,b")
        self.parameterentry.focus_set()
        
        # Criação da zona onde se insere a função
        self.functionlabel = tk.Label(self.subframeright1,text= "Function", bg='#FCF6F5')
        self.functionlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.functionlabel.place(relwidth=0.22, rely=0.2, relheight=0.1)
        self.functionentry = tk.Entry(self.subframeright1, font=40)
        self.functionentry.place(relwidth=0.55,relx=0.27, rely=0.2, relheight=0.1)
        self.functionentry.insert(0, "sin(x) + a*x + b")
        self.functionentry.focus_set()
        
        self.xaxislabel = tk.Label(self.subframeright3, text="X Axis", bg='#FCF6F5')
        self.xaxislabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.2, rely=0)

        self.yaxislabel = tk.Label(self.subframeright3, text="Y Axis", bg='#FCF6F5')
        self.yaxislabel.place(in_ = self.subframeright3, relwidth = 0.5, relheight=0.1, relx=0.5, rely=0)

        self.xaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from", bg='#FCF6F5')
        self.xaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.15, relheight=0.1, relx = 0, rely = 0.1)

        self.xaxisminentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.xaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.15, rely=0.1)
        self.xaxisminentry.insert(0, "0")

        self.xaxistolabel = tk.Label(self.subframeright3, text = "to", bg='#FCF6F5')
        self.xaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.25, rely=0.1)

        self.xaxismaxentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.xaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.3, rely=0.1)
        self.xaxismaxentry.insert(0, "10")
        
        self.xaxistitlelabel = tk.Label(self.subframeright3, text = "Title", bg='#FCF6F5')
        self.xaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0, rely=0.25)
        
        self.xaxistitleentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.xaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.1, rely=0.25)
        self.xaxistitleentry.insert(0, "Abcissas")

        self.xaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing", bg='#FCF6F5')
        self.xaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.15, relheight = 0.1, relx=0, rely= 0.4)

        self.xaxistickspentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.xaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.05, relheight = 0.1, relx = 0.15, rely=0.4)
        self.xaxistickspentry.insert(0, "1")
        
        self.autoscalex = tk.BooleanVar()
        self.autoscalex.set(0)
        self.xaxisautoscale = tk.Checkbutton(self.subframeright3, bg = '#FCF6F5', offvalue = 0, onvalue = 1, variable = self.autoscalex, text = 'Autoscale X')
        self.xaxisautoscale.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, rely = 0.4, relx = 0.2)

        self.yaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from", bg='#FCF6F5')
        self.yaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.15, relheight=0.1, relx = 0.5, rely = 0.1)

        self.yaxisminentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.yaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.65, rely=0.1)
        self.yaxisminentry.insert(0, "0")

        self.yaxistolabel = tk.Label(self.subframeright3, text = "to", bg='#FCF6F5')
        self.yaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.75, rely=0.1)

        self.yaxismaxentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.yaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.8, rely=0.1)
        self.yaxismaxentry.insert(0, "10")
        
        self.yaxistitlelabel = tk.Label(self.subframeright3, text = "Title", bg='#FCF6F5')
        self.yaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0.5, rely=0.25)

        self.yaxistitleentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.yaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.6, rely=0.25)
        self.yaxistitleentry.insert(0, "Ordenadas")
        
        self.yaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing", bg='#FCF6F5')
        self.yaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.15, relheight = 0.1, relx=0.5, rely= 0.4)

        self.yaxistickspentry = tk.Entry(self.subframeright3, bg='#FCF6F5')
        self.yaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.05, relheight = 0.1, relx = 0.65, rely=0.4)
        self.yaxistickspentry.insert(0, "1")
        
        self.autoscaley = tk.BooleanVar()
        self.autoscaley.set(0)
        self.yaxisautoscale = tk.Checkbutton(self.subframeright3, bg = '#FCF6F5', offvalue = 0, onvalue = 1, variable = self.autoscaley, text = 'Autoscale Y')
        self.yaxisautoscale.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, rely = 0.4, relx = 0.7)
        
       
        
        self.linewidth = []
        self.markersize = []
        self.errorwidth = []
       
        self.linewidth.append(tk.DoubleVar())
        self.markersize.append(tk.DoubleVar())
        self.errorwidth.append(tk.DoubleVar())
        
        self.linewidth[0].set(2)
        self.markersize[0].set(2)
        self.errorwidth[0].set(2)
        
        self.linewidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.lineslider, label = 'Line Width', variable = self.linewidth[0])
        self.linewidthscale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.07, rely=0.6)
        self.linewidthscale['state'] = tk.DISABLED
        
        self.markersizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.markerslider, label = 'Marker Size', variable = self.markersize[0])
        self.markersizescale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.37, rely=0.6)
        self.markersizescale['state'] = tk.DISABLED
        
        self.errorsizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.errorslider, label = 'Errorbar Width', variable = self.errorwidth[0])
        self.errorsizescale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.67, rely=0.6)
        self.errorsizescale['state'] = tk.DISABLED
        
        
        sty = ttk.Style(self.subframeright3)
        sty.configure("TSeparator", background="red")
        
        sep = ttk.Separator(self.subframeright3, orient = tk.VERTICAL )
        sep.place(in_ = self.subframeright3, relx=0.5, relheight = 0.5, rely=0.05)
        
        
        sep1 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep1.place(in_ = self.subframeright3, relx=0.3, rely=0.05, relwidth = 0.4)
        
        
        sep2 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframeright3, relx=0, rely=0.05, relwidth = 0.2)
        
        sep2 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframeright3, relx=0.8, rely=0.05, relwidth = 0.2)
        
        sep3 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL)
        sep3.place(in_ = self.subframeright3, relx=0, rely=0.55, relwidth=1)
        
        
        
        
        #Criação do texto respetivo ao primeiro dataset
        #A variável datasettext contém os textos presentes em cada dataset
        self.datasettext = []
        self.datasettext.append("1 0.5 1 0.5\n2 0.5 2 0.5\n3 0.5 4 0.5\n4 0.5 2 0.5\n5 0.5 5 0.5")
        
        self.datalistvariable = tk.StringVar()
        
        #Variável que mostra qual está selecionada
        self.datalistvariable.set('dataset 1')
        
        #Variável que contem os datasets e respetivo numero
        self.datalist = ['dataset 1']
        
        #Criação do botão seletor de data-sets, ligalo à função update_databox
        self.datasetselector = ttk.Combobox(self.plotbuttonframe, textvariable = self.datalistvariable, values = self.datalist)
        self.datasetselector.place(relx = 0.2, relheight = 1, relwidth=0.15)
        self.datasetselector.bind("<<ComboboxSelected>>", self.update_databox)
        
        #Criação da caixa que contem os dados, inserção do texto referente ao primeiro dataset na mesma
        self.dataentry = ( ScrolledText(self.subframeleft2))
        self.dataentry.pack(expand = 1, fill = tk.BOTH)
        self.dataentry.insert(tk.INSERT,self.datasettext[0])
        
        #Francamente eu so inicio isto assim pq ya, da pouco trabalho e resolveu um bug na altura,
        #NÃO MEXER, FUI EU A POR EU RESOLVO
        #Basicamente a lógica é isto começar com alguma coisa pq fode com indices dps, soluçao preguicosa
        #é darlhe os valores do textinho default
        self.abcissas = [[1, 1, 1, 1]]
        self.erabcissas = [[1, 1, 1, 1]]
        self.ordenadas = [[1,1,1,1]]
        self.erordenadas = [[1,1,1,1]]
        
        self.abc=[]
        self.erabc = []
        self.ord = []
        self.erord = []
        
        self.selecteddataset = 0
        self.numberdatasets = 1
        
        self.abc.append(np.array(self.abcissas[0]))
        self.erabc.append(np.array(self.erabcissas[0]))
        self.ord.append(np.array(self.erabcissas[0]))
        self.erord.append(np.array(self.erabcissas[0]))
        
        
        
        self.dataset_points = []
        self.update_parameter()
    
    def lineslider(self, a):
        self.plot_dataset()
    
    def markerslider(self, a):
        self.plot_dataset()
    
    def errorslider(self, a):
        self.plot_dataset()
    
    def fit_activate(self):
        
        if(self.wantfit.get() == 0):
            self.wantfit.set(1)
            self.fitbutton["text"] = 'HIDE'
        else:
            self.wantfit.set(0)
            self.fitbutton["text"] = 'FIT'
        
        self.plot_dataset()
        
        
    def markercolorpick(self):
        pick_color = tk.colorchooser.askcolor()[1]
        self.markercolorvar[self.selecteddataset] = pick_color
        self.plot_dataset()
    
    def linecolorpick(self):
        pick_color = tk.colorchooser.askcolor()[1]
        self.linecolorvar[self.selecteddataset] = pick_color
        self.plot_dataset()
    
    def errorcolorpick(self):
        pick_color = tk.colorchooser.askcolor()[1]
        self.errorcolorvar[self.selecteddataset] = pick_color
        self.plot_dataset()
        
    def import_window(self):
        self.import_window = tk.Toplevel(self.master)
        self.import_window.title('File Format')
        self.import_window.geometry('400x250')
        self.import_window.configure(background='#FCF6F5')
        self.import_window.resizable(False, False)
        
        self.samex = tk.BooleanVar()
        self.difx = tk.BooleanVar()
        self.difxerror = tk.BooleanVar()
                
        self.samex.set(1)
        self.difx.set(0)
        self.difxerror.set(0)
        
        
        samexbutton = tk.Checkbutton(self.import_window, bg = '#FCF6F5', offvalue = 0, onvalue = 1, variable = self.samex, text = 'All datasets have same (x,ex)', command = self.samexfunction)
        samexbutton.place(in_ = self.import_window, relwidth = 0.7, relheight = 0.1, rely = 0.05, relx = 0.15)
        
        samexbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        
        samextext=tk.Label(self.import_window, bg = '#FCF6F5', text = '2 first columns will be (x,ex).\nSubsequencial columns will be (y1, ey1, y2, ey2, ...)')
        samextext.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.15, rely = 0.15, relx = 0.05)
        
        difxbutton = tk.Checkbutton(self.import_window, bg = '#FCF6F5', offvalue = 0, onvalue = 1, variable = self.difx, text = 'All datasets have their own (x, ex)',  command = self.difxfunction)
        difxbutton.place(in_ = self.import_window, relwidth = 0.8, relheight = 0.15, rely = 0.35, relx = 0.1)
        
        difxbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        
        difxtext=tk.Label(self.import_window, bg = '#FCF6F5', text = 'Columns will be (x1, ex1, y1, ey1, ...)')
        difxtext.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.1, rely = 0.45, relx = 0.05)
        
        difxerrorbutton = tk.Checkbutton(self.import_window, bg = '#FCF6F5', offvalue = 0, onvalue = 1, variable = self.difxerror, text = 'Include ex',  command = self.difxerrorfunction)
        difxerrorbutton.place(in_ = self.import_window, relwidth = 0.5, relheight = 0.1, rely = 0.6, relx = 0.25)
        
        importbutton = tk.Button(self.import_window, text = "CHOOSE FILE", command = self.open_file, fg='white',
                                  bg='red',
                                  activebackground='white',
                                  activeforeground='red')
        importbutton.place(in_ = self.import_window, relwidth =0.5, relheight = 0.15, relx=0.25, rely=0.8)
        importbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        
    def samexfunction(self):
        self.difxerror.set(0)
        self.difx.set(0)
    
    def difxfunction(self):
        self.samex.set(0)
        self.difxerror.set(0)
    
    def difxerrorfunction(self):
        self.samex.set(0)
        self.difx.set(1)

    # Função para adicionar um dataset
    def add_dataset(self, string):
        # adicionar o texto merdoso, dar update À variavel do número de datasets
        self.numberdatasets = self.numberdatasets+1
        self.datalist.append("dataset " + str(len(self.datalist)+1))
        self.datasetselector.destroy()
        self.datasetselector = ttk.Combobox(self.plotbuttonframe, textvariable = self.datalistvariable, values = self.datalist)
        self.datasetselector.place(relx = 0.2, relheight = 1, relwidth=0.15)
        self.datasetselector.bind("<<ComboboxSelected>>", self.update_databox)
    
        self.datasettext.append(string)
    
        # Fazer a mesma coisa que fiz antes, que é encher o lixo de alguma coisa so pros arrays ja irem todos com o formato certinho
        self.abcissas.append([0, 0, 0, 0])
        self.erabcissas.append([0, 0, 0, 0])
        self.ordenadas.append([0, 0, 0, 0])
        self.erordenadas.append([0, 0, 0, 0])

        
        self.abc.append(np.array(self.abcissas[-1]))
        self.erabc.append(np.array(self.abcissas[-1]))
        self.ord.append(np.array(self.abcissas[-1]))
        self.erord.append(np.array(self.abcissas[-1]))
        
        # Criar as variáveis respetivas à escolha de cores para cada plot
    
        self.markercolorvar.append("black")
        self.linecolorvar.append("black")
        self.errorcolorvar.append("black")
        
        
        self.linewidth.append(tk.DoubleVar())
        self.markersize.append(tk.DoubleVar())
        self.errorwidth.append(tk.DoubleVar())
        
        self.markersize[self.numberdatasets-1].set(2.0)
        self.linewidth[self.numberdatasets-1].set(2.0)
        self.errorwidth[self.numberdatasets-1].set(2.0)
        
        # Definir a preto por default
       
    
    def check_databox(self):
        for x in range(len(self.datasettext)):   
            if (self.datasettext[x].replace(' ','') == ''):
                self.secondary_window('ERROR', 'Dataset {} is empty. Insert your data or remove it.'.format(x+1))
                return False
        
        for x in range(len(self.datasettext)):
            split = self.datasettext[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]
                if(len(ponto)!= 3 and len(ponto)!= 4):
                     self.secondary_window('ERROR', 'Dataset {} has at least one point with an incorrect number of columns. Correct it.'.format(x+1))
                     return False
                
        for x in range(len(self.datasettext)):
            split=[]
            split = self.datasettext[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]
                
                for k in ponto:
                     try:
                         float(k)
                     except ValueError:
                             self.secondary_window('ERROR', 'Dataset {} contains non-numerical input. Only numerical input is allowed.'.format(x+1))
                             return False
        return True
    
    def update_databox(self, event):

        #Guardar o atual na cena
        self.datasettext[self.currentselection - 1] = self.dataentry.get("1.0", "end-1c")
        
    
        # Esta função serve para aparecer o texto respetivo a um dataset na caixa de texto
        # Pra fazer isso a forma menos messy é mesmo destruir tudo o que tá na frame e por a informação
        # respetiva ao novo data-set
        select = int(self.datalistvariable.get()[-1])
        self.currentselection = select
        
        self.subframeleft2.destroy()
        self.dataentry.destroy()
        
        self.subframeleft2 = tk.Frame(self.frameleft, bg='#FCF6F5')
        self.subframeleft2.place(in_ = self.frameleft, relwidth = 1, relheight= 0.45, relx=0, rely=0.55)
        
        # Criação da caixa de texto com a informaçao respetiva
        self.dataentry = (ScrolledText(self.subframeleft2))
        self.dataentry.pack(expand = 1, fill = tk.BOTH)
        self.dataentry.insert(tk.INSERT,self.datasettext[select-1])
        
        # Mesma coisa de apagar e por novos para os menus, para aparecerem os certos no sitio que diz respeito
        # ao dataset selecionado
        
        self.markersizescale.destroy()
        self.linewidthscale.destroy()
        self.errorsizescale.destroy()
        
        
        
        # Saber qual o dataset selecionado so pra enfiar as cores e tal do correto
        self.selecteddataset = select-1
        
        self.markersizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.markerslider, label = 'Marker Size', variable = self.markersize[self.selecteddataset])
        self.markersizescale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.37, rely=0.6)
        
        self.linewidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.lineslider, label = 'Line Width', variable = self.linewidth[self.selecteddataset])
        self.linewidthscale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.07, rely=0.6)


        self.errorsizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = 'red', bg = '#FCF6F5', highlightthickness=0, command = self.errorslider, label = 'Errorbar Width', variable = self.errorwidth[self.selecteddataset])
        self.errorsizescale.place(in_ = self.subframeright3, relwidth = 0.25, relx = 0.67, rely=0.6)


    def secondary_window(self, title, message):

        new_window = tk.Toplevel(self.master)
        new_window.title(title)
        new_window.geometry('400x200')
        new_window.configure(background='#FCF6F5')
        new_window.resizable(False, False)

        # Criar as imagens do warning, 2 canvas porque uma de cada lado
        canvas1 = tk.Canvas(new_window, bg='#FCF6F5')
        canvas2 = tk.Canvas(new_window, bg='#FCF6F5')
        
        size = 50
        # Criação da imagem per se
        img_src = Image.open('./img/Warning.png')
        img_src = img_src.resize((size, size))
        # Definir a canvas para pôr tudo na tela
        canvas1.config(width = size, height = size, highlightthickness = 0)
        canvas2.config(width = size, height = size, highlightthickness = 0)
        img = ImageTk.PhotoImage(img_src)
        canvas1.create_image(size/2, size/2, image = img)
        canvas2.create_image(size/2, size/2, image = img)
        # Guardar a imagem só porque às vezes o tkinter é chato
        canvas1.image = img
        canvas2.image = img

        # Colocação da mensagem de erro
        warning = tk.Label(new_window, text=message, wraplength=250)
        warning["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        warning.configure(background='#FCF6F5')
        
        canvas1.place(relx=.1, rely=.5, anchor="c")
        warning.place(relx=.5, rely=.5, anchor="c")
        canvas2.place(relx=.9, rely=.5, anchor="c")

    def compile_function(self):
        parsed_input = parser(self.functionentry.get(),
                              self.parameterentry.get(),
                              self.independententry.get())
        if parsed_input[0]:
            self.function = parsed_input[1]
        else:
            self.secondary_window('ERROR', parsed_input[1])
            self.function = ''


        # Daqui para baixo é fazer o plot em si

        # Estas duas linhas extraem todos o dataset
        # E armazenam-nas num array de array de array
        # Nível 0: O data set
        # Nível 1: O ponto
        # Nível 2: A coordenada/incerteza
        #data = StringIO(self.dataentry.get("1.0", "end-1c"))
        #self.data_sets = read_file(data,float,False)

    # Função para plottar a funçao com parametros numericos dados pelo utilizador
    def plot_fittedfunction(self):
        np.seterr(all='raise')
        functions = ['sin',
                     'cos',
                     'tan',
                     'arcsin',
                     'arccos',
                     'arctan',
                     'exp',
                     'log',
                     'sqrt',
                     'absolute',
                     'heaviside',
                     'cbrt',
                     'sign'
                     ]
        
        expr = self.functionentry.get()
        params = self.parameterentry.get()
        indep = self.independententry.get()
        
        # Ver se a função não está vazia
        expr=expr.replace(' ','')
        if expr == '':
            return (False, 'Não foi encontrada nenhuma função de ajustamento.')
    
        process = process_params(params, indep)
        
        if process[0]:
            clean_split = process[1]
        else:
            return (False, process[1])
                  
        for function in enumerate(functions):
            expr = expr.split(function[1])
            expr = ('['+str(len(clean_split)+function[0])+']').join(expr)
        # Substituir os números dos parâmetros
        for pair in enumerate(clean_split):
            expr = expr.split(pair[1])
            expr = (str(self.fittedparams[pair[0]])).join(expr)
    
        # Por np atras da funçao para tipo, plottar isso
        for function in enumerate(functions):
            expr = expr.split('['+str(function[0]+len(clean_split))+']')
            expr = ('np.'+str(function[1])).join(expr)
        
       
        
        self.xfittedfunc=[]
        self.yfittedfunc=[]
        
        for i in range(100):
            x=0.2*i
            self.xfittedfunc.append(x)
            self.yfittedfunc.append(eval(expr))
        
        
    def plot_function(self):
        np.seterr(all='raise')
        functions = ['sin',
                     'cos',
                     'tan',
                     'arcsin',
                     'arccos',
                     'arctan',
                     'exp',
                     'log',
                     'sqrt',
                     'absolute',
                     'heaviside',
                     'cbrt',
                     'sign'
                     ]
        
        expr = self.functionentry.get()
        params = self.parameterentry.get()
        indep = self.independententry.get()
        
        # Ver se a função não está vazia
        expr=expr.replace(' ','')
        if expr == '':
            return (False, 'Não foi encontrada nenhuma função de ajustamento.')
    
        process = process_params(params, indep)
        
        if process[0]:
            clean_split = process[1]
        else:
            return (False, process[1])
        
        for x in range(len(self.plotparamboxes)):
            paramboxes = self.plotparamboxes[x].get()
            paramboxes = paramboxes.replace(' ', '')
            if(paramboxes == ''):
                self.secondary_window('ERROR', 'No parameter values were provided for plot.')
                return False
            try:
                float(paramboxes)
            except ValueError:
                self.secondary_window('ERROR', 'A non-numerical parameter value was detected. Only numerical values are allowed.')
                return False
                
        for function in enumerate(functions):
            expr = expr.split(function[1])
            expr = ('['+str(len(clean_split)+function[0])+']').join(expr)
        # Substituir os números dos parâmetros
        for pair in enumerate(clean_split):
            expr = expr.split(pair[1])
            expr = (str(self.plotparamboxes[pair[0]].get())).join(expr)
    
        # Por np atras da funçao para tipo, plottar isso
        for function in enumerate(functions):
            expr = expr.split('['+str(function[0]+len(clean_split))+']')
            expr = ('np.'+str(function[1])).join(expr)
    
        #Criação da figura que vai segurar o plot, e seguidamente espetada no canvas
        #Criação dos arrays com muitos pontinhos x e y(x)
        self.xfunc=[]
        self.yfunc=[]
        
        for i in range(100):
            x=0.2*i
            self.xfunc.append(x)
            self.yfunc.append(eval(expr))
        
        # Se calhar por também uma condição para ver se o utilizador quer grid
        if(self.wantfunction == 0):
            self.wantfunction = 1
            self.plotfunctionbutton['text'] = 'UN-PLOT FUNCTION'
        else:
            self.wantfunction = 0
            self.plotfunctionbutton['text'] = 'PLOT FUNCTION'
            
        self.plot_dataset()
        
    def plot_dataset(self):
        
        # Testar se os limites estão bem definidos. Se não estiverem podemos saltar isto tudo
        info_x = [(self.xaxismaxentry, 'Max value of x'), (self.xaxisminentry, 'Min value of x'), (self.xaxistickspentry, 'X axis tick spacing')]
        info_y = [(self.yaxismaxentry, 'Max value of y'), (self.yaxisminentry, 'Min value of y'), (self.yaxistickspentry, 'Y axis tick spacing')]
        
        if not self.autoscalex.get():
            for var in info_x:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        self.secondary_window('ERROR', var[1]+' contains no input.')
                    else:
                        self.secondary_window('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
        
        if not self.autoscaley.get():
            for var in info_y:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        self.secondary_window('ERROR', var[1]+' contains no input.')
                    else:
                        self.secondary_window('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
        
        # Testar se os dados estão bem. Se não estiverem podemos saltar isto tudo.
        select = int(self.datalistvariable.get()[-1])
        self.datasettext[select-1]= self.dataentry.get("1.0", "end-1c")
        self.datastring = self.datasettext[select-1]

        if not self.check_databox():
            return False
        
        data = StringIO(self.datastring)
        data_sets = read_file(data,float,False,0)
        
        if data_sets == -2:
            self.secondary_window('ERROR', 'Dataset {} has at least one point defined incorrectly. Make sure all points have the same number of columns.'.format(select))
            self.datasettext[select-1] = ""
            self.datasetring = ""
            return False
        
        if(self.countplots == 0):
            self.linewidthscale['state'] = tk.NORMAL
            self.markersizescale['state'] = tk.NORMAL
            self.errorsizescale['state'] = tk.NORMAL
            self.countplots = 1
        
        self.abcissas[select-1] = []
        self.erabcissas[select-1] = []
        self.ordenadas[select-1] = []
        self.erordenadas[select-1] = []

        #adicionar condiçoes
        for x in range(len(data_sets[0])):
            if(len(data_sets[0][x]) == 4):
                self.abcissas[select-1].append(data_sets[0][x][0])
                self.erabcissas[select-1].append(data_sets[0][x][1])
                self.ordenadas[select-1].append(data_sets[0][x][2])
                self.erordenadas[select-1].append(data_sets[0][x][3])
            
            if(len(data_sets[0][x]) == 3):
                self.abcissas[select-1].append(data_sets[0][x][0])
                self.erabcissas[select-1].append(0)
                self.ordenadas[select-1].append(data_sets[0][x][1])
                self.erordenadas[select-1].append(data_sets[0][x][2])

        
        self.abc[select-1] = np.array(self.abcissas[select-1])
        self.erabc[select-1] = np.array(self.erabcissas[select-1])
        self.ord[select-1] = np.array(self.ordenadas[select-1])
        self.erord[select-1] = np.array(self.erordenadas[select-1])

        fig = Figure(figsize=(10,10))

        if(self.autoscalex.get() == 1):
            allabc = []
            for x in range(len(self.abcissas)):
                allabc.append(max(self.abcissas[x]))
                allabc.append(min(self.abcissas[x]))
            
            minabc = min(allabc)
            maxabc = max(allabc)
            amp = maxabc - minabc
            maxabc = maxabc + 0.05*amp
            minabc = minabc - 0.05*amp
            
            self.xaxismaxentry.delete(0, 'end')
            self.xaxisminentry.delete(0, 'end')
            
            self.xaxismaxentry.insert(0, "{0:.2f}".format(maxabc))
            self.xaxisminentry.insert(0, "{0:.2f}".format(minabc))
            
            self.xaxistickspentry.delete(0,'end')
            self.xaxistickspentry.insert(0, "{0:.2f}".format(1+int(amp/10)))
            
            
        if(self.autoscaley.get() == 1):
            allord = []
            for x in range(len(self.ordenadas)):
                allord.append(max(self.ordenadas[x]))
                allord.append(min(self.ordenadas[x]))
            
            minord = min(allord)
            maxord = max(allord)
            amp = maxord - minord
            maxord = maxord + 0.05*amp
            minord = minord - 0.05*amp
            
            self.yaxismaxentry.delete(0, 'end')
            self.yaxisminentry.delete(0, 'end')
            
            self.yaxismaxentry.insert(0, "{0:.2f}".format(maxord))
            self.yaxisminentry.insert(0, "{0:.2f}".format(minord))
            
            self.yaxistickspentry.delete(0,'end')
            self.yaxistickspentry.insert(0, "{0:.2f}".format(1+int(amp/10)))
        
        x_ticks = []
        y_ticks = []
        
        x_max  = float(self.xaxismaxentry.get().replace(',','.').replace(' ',''))
        x_min  = float(self.xaxisminentry.get().replace(',','.').replace(' ',''))
        x_space = float(self.xaxistickspentry.get().replace(',','.').replace(' ',''))
        y_max  = float(self.yaxismaxentry.get().replace(',','.').replace(' ',''))
        y_min  = float(self.yaxisminentry.get().replace(',','.').replace(' ',''))
        y_space = float(self.yaxistickspentry.get().replace(',','.').replace(' ',''))



        xticknumber = 1+int((x_max-x_min)/x_space)
        yticknumber = 1+int((y_max-y_min)/y_space)
        
        for x in range(xticknumber):
            x_ticks.append(x*x_space + x_min)

        for x in range(yticknumber):
            y_ticks.append(x*y_space + y_min)
        
        self.a = fig.add_subplot(111 ,projection = None,
                                 xlim = (x_min,x_max), ylim = (y_min, y_max),
                                 xticks = x_ticks, yticks = y_ticks, 
                                 ylabel = self.yaxistitleentry.get(), xlabel = self.xaxistitleentry.get())
        
        

        self.subframeleft1.destroy()
        self.subframeleft1=tk.Frame(self.frameleft, bg='#FCF6F5')
        self.subframeleft1.place(in_ = self.frameleft, relwidth=1, relheight=0.5, relx=0, rely=0)
        
        self.fittedparams = []
        self.fittedparamserror = []
        self.chisq = 0
        
        
            
        
        
        if(self.check_databox()):
        
            if(self.wanterror.get() == 1):
                for x in range(self.numberdatasets):
                    self.a.errorbar(self.abc[x], self.ord[x], xerr = self.erabc[x], yerr = self.erord[x], fmt = 'none',zorder = -1, ecolor = self.errorcolorvar[x], elinewidth = self.errorwidth[x].get())
        
            if(self.wantpoints.get() == 1):
                for x in range(self.numberdatasets):
                    self.a.plot(self.abc[x], self.ord[x], marker = 'o', color = str(self.markercolorvar[x]), zorder = 1, lw=0, ms=self.markersize[x].get()*2)
        
       
            if(self.wantline.get() == 1):
                for x in range(self.numberdatasets):
                    self.a.plot(self.abc[x], self.ord[x], color = self.linecolorvar[x], lw = self.linewidth[x])
            
            if(self.wantfunction == 1):
                self.a.plot(self.xfunc, self.yfunc)
        
        
        
            if(self.wantfit.get() == 1):
                init_values = []
                for x in range(len(self.paramboxes)):
                    try:
                        init_values.append(float(self.paramboxes[x].get()))
                    except ValueError:
                        if (self.paramboxes[x].get().replace(' ','')==''):
                            self.secondary_window('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                        else:
                            self.secondary_window('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')

                        return False
                
                
                (self.fittedparams, self.fittedparamserror, self.chisq) = self.fit_data(data_sets, init_values, 1000)
                
                self.plot_fittedfunction()
                
                self.a.plot(self.xfittedfunc, self.yfittedfunc)
                
            
        # Se calhar por também uma condição para ver se o utilizador quer grid
        self.a.grid(True)

        self.canvas = FigureCanvasTkAgg(fig, master=self.subframeleft1)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

    def update_parameter(self):
        #Mesmo raciocinio de destruir a caixa onde se poem os parametros e inicial guesses para por as novas
        global count
        self.parameter = self.parameterentry.get()
        process = process_params(self.parameterentry.get(), self.independententry.get())
        if not process[0]:
            count = 1
            self.boxnumber = 0
        
            self.paramlabel=[]
            self.paramboxes=[]
            self.plotparamlabel = []
            self.plotparamboxes = []
    
            self.paramscrolly.destroy()
            self.anotherframe.destroy()
            self.paramcanvas.destroy()
            self.inicialguesslabel.destroy()
            self.secondary_window('ERROR', process[1])
        else:
            clean_split = process[1]
            if (count==2) :
                
                    
                self.subframeright2.destroy()
    
                self.subframeright2=tk.Frame(self.frameright, bg='#FCF6F5')
                self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.3, relx=0, rely=0.25)
    
                self.boxnumber = len(clean_split)
    
    
                self.paramscrolly.destroy()
                self.anotherframe.destroy()
                self.paramcanvas.destroy()
                
                self.paramlabel=[]
                self.paramboxes=[]
                self.paramresboxes=[]
                self.paramreslabel = []
                self.paramerrlabel = []
                self.paramerrboxes = []
                self.plotparamlabel = []
                self.plotparamboxes = []
    
                self.boxnumber = len(clean_split)
                
                self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0, bg='#FCF6F5')
                self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)
    
                #self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))
    
                self.anotherframe=tk.Frame(self.paramcanvas, bg='#FCF6F5')
                #self.anotherframe.pack(expand=True, fill = tk.BOTH)
                
                self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
                self.paramscrolly.pack(side=tk.RIGHT, fill="y")
    
                self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
                self.paramcanvas.bind('<Configure>', self.algumacoisa)
    
                #self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))
                
                self.anotherframe.columnconfigure(0, weight = 1)
                self.anotherframe.columnconfigure(1, weight = 3)
                self.anotherframe.columnconfigure(2, weight = 1)
                self.anotherframe.columnconfigure(3, weight = 3)
                self.anotherframe.columnconfigure(4, weight = 1)
                self.anotherframe.columnconfigure(5, weight = 3)
                self.anotherframe.columnconfigure(6, weight = 1)
                self.anotherframe.columnconfigure(7, weight = 3)
                
                for x in range(self.boxnumber):
                    self.paramerrlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#FCF6F5'))
                    self.paramerrlabel[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.paramerrboxes.append(tk.Entry(self.anotherframe))
                    self.paramerrboxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.paramreslabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#FCF6F5'))
                    self.paramreslabel[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.paramresboxes.append(tk.Entry(self.anotherframe))
                    self.paramresboxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramboxes.append(tk.Entry(self.anotherframe))
                    self.paramboxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#FCF6F5'))
                    self.paramlabel[x].grid(column = 2, row = x, pady=10, sticky= tk.E)
                    self.plotparamlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg = '#FCF6F5'))
                    self.plotparamlabel[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plotparamboxes.append(tk.Entry(self.anotherframe))
                    self.plotparamboxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
                
                self.windows_item = self.paramcanvas.create_window((0,0), window=self.anotherframe, anchor="nw")
           
               # self.paramcanvas.update()   

            if (count == 1):
    
                self.paramlabel=[]
                self.paramboxes=[]
                self.paramresboxes=[]
                self.paramreslabel = []
                self.paramerrlabel = []
                self.paramerrboxes = []
                self.plotparamlabel = []
                self.plotparamboxes = []
    
                self.boxnumber = len(clean_split)
                
                self.resultlabel = tk.Label(self.subframeright1, text="Resultados", bg='#FCF6F5')
                self.resultlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.5)
                
                self.errorlabel = tk.Label(self.subframeright1, text="Erros", bg='#FCF6F5')
                self.errorlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.75)
    
                self.inicialguesslabel = tk.Label(self.subframeright1, text="Initial Guess", bg='#FCF6F5')
                self.inicialguesslabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.25)
                
                self.funcplotlabel = tk.Label(self.subframeright1, text="Plot Function", bg='#FCF6F5')
                self.funcplotlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0)
    
                self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0, bg='#FCF6F5')
                self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)
    
                #self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
                #self.paramscrolly.pack(side=tk.RIGHT, fill="y")
    
                #self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
                #self.paramcanvas.bind('<Configure>', lambda e: self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all")))
    
                #self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))
                
                
                self.anotherframe=tk.Frame(self.paramcanvas, bg='#FCF6F5')
                #self.anotherframe.pack(expand=True, fill = tk.BOTH)
                
                self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
                self.paramscrolly.pack(side=tk.RIGHT, fill="y")
    
                self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
                self.paramcanvas.bind('<Configure>', self.algumacoisa)
    
                #self.paramcanvas.bind_all('<MouseWheel>', lambda event: self.paramcanvas.yview_scroll(int(-1*(event.delta/120)), "units"))
                
                self.anotherframe.columnconfigure(0, weight = 1)
                self.anotherframe.columnconfigure(1, weight = 3)
                self.anotherframe.columnconfigure(2, weight = 1)
                self.anotherframe.columnconfigure(3, weight = 3)
                self.anotherframe.columnconfigure(4, weight = 1)
                self.anotherframe.columnconfigure(5, weight = 3)
                self.anotherframe.columnconfigure(6, weight = 1)
                self.anotherframe.columnconfigure(7, weight = 3)
          
                
                for x in range(self.boxnumber):
                    self.paramerrlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#FCF6F5'))
                    self.paramerrlabel[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.paramerrboxes.append(tk.Entry(self.anotherframe))
                    self.paramerrboxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.paramreslabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#FCF6F5'))
                    self.paramreslabel[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.paramresboxes.append(tk.Entry(self.anotherframe))
                    self.paramresboxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramboxes.append(tk.Entry(self.anotherframe))
                    self.paramboxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#FCF6F5'))
                    self.paramlabel[x].grid(column = 2, row = x, pady=10, sticky= tk.E)
                    self.plotparamlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg = '#FCF6F5'))
                    self.plotparamlabel[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plotparamboxes.append(tk.Entry(self.anotherframe))
                    self.plotparamboxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
            count = 2
            
            self.windows_item = self.paramcanvas.create_window((0,0), window=self.anotherframe, anchor="nw")
           
            self.paramcanvas.update()
    
    def algumacoisa(self, event):
        canvas_width = event.width
        self.paramcanvas.itemconfig(self.windows_item, width = canvas_width)
        self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all"))
        
    
    def update(self):
        "Update the canvas and the scrollregion"

        self.update_idletasks()
        self.paramcanvas.config(scrollregion=self.paramcanvas.bbox(self.windows_item))
            
    def fit_data(self, data, init_params, max_iter):
        """
        Parameters
        ----------
        data : array of array
            Pontos, no formato [[x1,ex1,y1,ey1],[x2,ex2,y2,ey2],...]
        
        init_params: array
            Estimativas iniciais para os valores dos parâmetros

        Returns
        -------
        fit.beta: parametros de ajustamento
        fit.sd_beta: incertezas dos parametros
        fit.res_var: chi quadrado reduzido

        """
        
        # ESTA FUNÇÃO TODA TEM DE SER CORRIGIDA!!
        
        func = odr.Model(self.fit_function)
        try:
            print(self.function)
        except AttributeError:
            self.secondary_window('ERROR','Fitting function not defined. Make sure it is compiled without errors.')
            return 0
        
        x_points = []
        y_points = []
        x_err    = []
        y_err    = []
        
        
        for dataset in data:
            for point in dataset:
                x_points.append(point[0])
                y_points.append(point[-2])
                y_err.append(point[-1])
                if len(point) == 4:
                    x_err.append(point[1])
                    
        
        if (x_err and np.any(np.array(x_err)==0)):
            self.secondary_window('ERROR','At least one point in dataset {} has a null x uncertainty. It is not possible to fit data with null uncertainty.'.format(self.currentselection))
            return 0
        if (y_err and np.any(np.array(y_err)==0)):
            self.secondary_window('ERROR','At least one point in dataset {} has a null y uncertainty. It is not possible to fit data with null uncertainty.'.format(self.currentselection))
            return 0
            
        if (len(data[0])==3):
            fit_data = odr.RealData(x_points, y_points, sy=y_err, fix=[0]*len(x_points))
        else:
            fit_data = odr.RealData(x_points, y_points, sx=x_err, sy=y_err, fix=[0]*len(x_points))


        my_odr = odr.ODR(fit_data, func, beta0=init_params, maxit=max_iter)
        fit = my_odr.run()
        fit.pprint()
        
        
        
        return (fit.beta, fit.sd_beta, fit.res_var)
        
    def fit_function(self, B, _x):
        return eval(self.function)

    def open_file(self):
        
        self.import_window.destroy()
        
        # Isto ainda não faz nada, preciso de compreender melhor o programa
        file = tk.filedialog.askopenfilename()
        
        if(self.samex.get() == 1):
            new_data = read_file(file,str,True,0)
        
        if(self.difx.get() == 1 and self.difxerror.get()== 0):
            new_data = read_file(file,str,True,1)
        
        if(self.difxerror.get() == 1):
            new_data = read_file(file,str,True,2)
        
        
        
        for x in range(len(new_data)):
            self.add_dataset(new_data[x])
        
        
root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
