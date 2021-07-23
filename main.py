# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:58:13 2021

@author:
"""
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt
import pandas as pd
from io import StringIO
from scipy import odr
from tkinter import colorchooser
import pyperclip
import sys, os
import webbrowser
import requests

def check_version():
    current_version = '1.4.0'
    try:
        latest_version = requests.get('https://sites.google.com/view/chimera-fit/install', timeout=1)
    except:
        return
    latest_version = latest_version.text.split(' ')
    for elem in latest_version:
        if 'Current' in elem:
            pos = latest_version.index(elem) + 1
    clean_version = ''
    for char in latest_version[pos+1]:
        if char == '<':
            break
        else:
            clean_version += char

    if clean_version != current_version:
        if tk.messagebox.askyesno('UPDATE AVAILABLE','There is a new version available (%s -> %s)! Do you want to be redirected to download it now?' % (current_version, clean_version)):
            webbrowser.open('https://sites.google.com/view/chimera-fit/install')

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

count = 0
a = 0

def take_first(elem):
    return float(elem.split('&')[0].split('$\\pm$')[0])

def latexify_data(data,mode):
    """
    Função para, recebendo um batch de datasets, gerar o texto LaTeX para uma
    tabela.

    Parameters
    ----------
    data : array
        Conjunto dos datasets para gerar a tabela latex.
    mode : int
        0: Usar a mesma coluna de x para todos os sets.
        1: Usar uma coluna nova de x para cada um dos sets.

    Returns
    -------
    None.

    """
    datasets = [[[i for i in point.split(' ')] for point in dataset.split('\n')] for dataset in data]

    latex_table = r"""% Add the following required packages to your document preamble:
% \usepackage{graphicx}
\begin{table}[H]
\centering
% Use line below to set table size in terms of text width
\resizebox{\textwidth}{!}{
% Line below adds space between lines, to make table easier to read
{\renewcommand{\arraystretch}{1.1}
\begin{tabular}{"""
    if mode == 0:
        latex_table +=r'c|'
        for i in range(len(datasets)):
            latex_table += 'c'
        latex_table+='}\n\\hline\n X & '
        for i in range(len(datasets)):
            latex_table += 'Y%d & ' % (i+1)
        latex_table = latex_table[:-2] + '\\\\ \\hline \n'
        used_x = []
        data_text = []
        for dataset in datasets:
            for point in dataset:
                x = float(point[0])
                if x not in used_x:
                    if len(point) == 3:
                        data_text.append('%s & %s$\\pm$%s ' % (point[0], point[1], point[2]))
                    if len(point) == 4:
                        data_text.append('%s$\\pm$%s & %s$\\pm$%s' % (point[0], point[1], point[2], point[3]))
                    used_x.append(x)
                    for inner_dataset in datasets:
                        if inner_dataset != dataset:
                            found = 0
                            for inner_point in inner_dataset:
                                if float(inner_point[0]) == x:
                                    found = 1
                                    data_text[-1] += '& %s$\\pm$%s ' % (inner_point[-2], inner_point[-1])
                                    break
                            if found == 0:
                                data_text[-1] += '& $-$ '
                    data_text[-1] += ' \\\\'
        data_text.sort(key=take_first)

    if mode == 1:
        for i in range(len(datasets)):
            latex_table += 'cc|'
        latex_table = latex_table[:-1] + '}\n\\hline\n'
        for i in range(len(datasets)):
            latex_table += 'X%d & Y%d & ' % (i+1,i+1)
        latex_table = latex_table[:-2] + '\\\\ \\hline \n'
        max_size = max([len(dataset) for dataset in datasets])
        data_text = ['' for i in range(max_size)]
        for i in range(max_size):
            for dataset in datasets:
                if i >= len(dataset):
                    data_text[i] += ('$-$ & $-$ & ')
                else:
                    point = dataset[i]
                    if len(point) == 3:
                        data_text[i] += '%s & %s$\\pm$%s & ' % (point[0], point[1], point[2])
                    if len(point) == 4:
                        data_text[i] += '%s$\\pm$%s & %s$\\pm$%s & ' % (point[0], point[1], point[2], point[3])
        for i in range(len(data_text)):
            data_text[i] = data_text[i][:-2] + '\\\\'

    for line in data_text:
        latex_table += line + '\n'
    latex_table = latex_table[:-1] + ' '
    latex_table+='\\hline\n\\end{tabular}\n}\n}\n\\caption{<WRITE CAPTION HERE>}\n\\label{tab:my-table}\n\\end{table}'

    return latex_table

def math_2_latex(expr, params, indep):

    params = process_params(params,indep)[1]

    # agrupar todas as variáveis relevantes
    variables = params
    variables.append(indep)

    latex = expr.replace(' ','')

    operations = ['*','/','+','-','**','^']

    greek_letters = [
                    'alpha',
                    'beta',
                    'gamma',
                    'Gamma',
                    'delta',
                    'Delta',
                    'epsilon',
                    'varepsilon',
                    'zeta',
                    'eta',
                    'theta',
                    'vartheta',
                    'Theta',
                    'iota',
                    'kappa',
                    'lambda',
                    'Lambda',
                    'mu',
                    'nu',
                    'xi',
                    'Xi',
                    'pi',
                    'Pi',
                    'rho',
                    'varrho',
                    'sigma',
                    'Sigma',
                    'tau',
                    'upsilon',
                    'Upsilon',
                    'phi',
                    'varphi',
                    'Phi',
                    'chi',
                    'psi',
                    'Psi',
                    'omega',
                    'Omega'
                    ]

    # substituir todas as letras gregas nos parametros
    for var in variables:
        # se a variavel tiver um numero, só nos interessa a parte sem numero
        if ''.join([i for i in var if not i.isdigit()]) in greek_letters:
            latex = latex.replace(var,'\\'+var)

    # baixar todos os indices
    for var in variables:
        pos=0
        # temos de verificar até onde é que há números para baixar
        while pos<len(var):
            try:
                int(var[len(var)-pos-1])
            except ValueError:
                break
            pos+=1
        # se houver algum número, então fazemos replace
        if pos != 0:
            latex = latex.replace(var, var[:(len(var)-pos)]+'_{'+var[(len(var)-pos):]+'}')

    # tratar das potências
    latex = latex.replace('**','^')
    i=0
    while i<len(latex):
        if latex[i]=='^':
            if latex[i+1]!='(':
                latex = latex[:i+1]+'{'+latex[i+1:]
                for j in range(i+1,len(latex)):
                    if latex[j] in operations or latex[j]==')':
                        break
                latex = latex[:j-1]+'}'+latex[j-1:]
            else:
                latex = latex[:i+1]+'{'+latex[i+2:]
                deep = 1
                for j in range(i+1,len(latex)):
                    if latex[j] == ')':
                        deep -= 1
                    if latex[j] == '(':
                        deep += 1
                    if deep == 0:
                        break
                latex = latex[:j]+'}'+latex[j+1:]
        i+=1

    # tratar das frações
    i=0
    while i<len(latex):
        correction_after = 0
        correction_pre = 0
        if latex[i]=='/':
            # procurar para trás
            if latex[i-1]!=')':
                for k in range(i-1,-1,-1):
                    if latex[k] in operations:
                        break
            else:
                deep = 1
                latex = latex[:i-1]+latex[i:]
                for k in range(i-1,-1,-1):
                    if latex[k] == ')':
                        deep += 1
                    if latex[k] == '(':
                        deep -= 1
                    if deep == 0:
                        break
                k-=1
                latex = latex[:k+1]+latex[k+2:]
                i-=2

            # procurar para a frente
            if latex[i+1]!='(':
                for j in range(i+1,len(latex)):
                    if latex[j] in operations or latex[j]==')':
                        break
            else:
                deep = 1
                latex = latex[:i+1]+latex[i+2:]
                for j in range(i+1,len(latex)):
                    if latex[j] == ')':
                        deep -= 1
                    if latex[j] == '(':
                        deep += 1
                    if deep == 0:
                        break
                latex = latex[:j]+latex[j+1:]
            if j == len(latex) - 1:
                correction_after = 1
            if k == 0:
                correction_pre = 1
            latex = latex[:k+1-correction_pre]+'\\frac{'+latex[k+1-correction_pre:i]+'}{'+latex[i+1:j+correction_after]+'}'+latex[j+correction_after:]
        i+=1

    # Por fim tratar das funções
    i = 0
    functions = []
    while i < len(latex):
        if latex[i].isalpha() and i<len(latex) - 1:
            for j in range(i+1,len(latex)):
                if not latex[j].isalpha():
                    break
            if latex[i:j] != 'frac' and latex[i:j] not in [''.join([i for i in var if not i.isdigit()]) for var in variables]:
                functions.append(latex[i:j])
            i=j
        else:
            i+=1
    for function in functions:
        latex = latex.replace(function,'\\text{'+function+'}')

    # remover os * porque ninguém usa isso em LaTeX
    latex = latex.replace('*','')

    # e pôr os parentesis com os tamanhos corretos
    latex = latex.replace('(','\\left(')
    latex = latex.replace(')','\\right)')

    return latex

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
    forbidden = ['PI', 'E']

    if (len([p for p in indep.split(' ') if p]) > 1):
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

    # Verificar se nenhum dos nomes das variáveis está reservado
    for val in clean_split:
        if val in forbidden:
            return (False, 'Name \''+str(val)+'\' is a reserved keyword. Provide a different name.')
    # Verificar se a variável independente não é uma palavra reservada
    if indep in forbidden:
        return (False, 'Name \''+str(indep)+'\' is a reserved keyword. Provide a different name.')

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
    np.seterr(divide='warn', invalid='warn', under='warn', over='warn')
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
    forbidden = ['PI', 'E']


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
    # Substituir as palavras reservadas
    for keyword in forbidden:
        expr = expr.split(keyword)
        if keyword == 'PI':
            expr = '[3.14]'.join(expr)
        if keyword == 'E':
            expr = '[2.72]'.join(expr)

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

    # Pôr os números associados às palavras reservadas
    expr = expr.split('[3.14]')
    expr = 'np.pi'.join(expr)
    expr = expr.split('[2.72]')
    expr = 'np.e'.join(expr)

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
        if os.name == 'posix':
            self.master.attributes('-zoomed',True)
        if os.name == 'nt':
            self.master.state('zoomed')
        self.master.iconphoto(True, tk.PhotoImage(file=resource_path('img/Logo.png')))
        # Tirar o título
        self.winfo_toplevel().title("")

        # Definir o tamanho mínimo da janela
        self.master.minsize(int(0.5*self.master.winfo_screenwidth()),int(0.5*self.master.winfo_screenheight()))

        # Tamanhos default para a janela
        self.width  = int(.8*self.master.winfo_screenwidth())
        self.height = int(.8*self.master.winfo_screenheight())

        # Frames para conter os objetos
        self.top = tk.Frame(self.master, bg = '#E4E4E4')
        self.top.pack(in_ = self.master)
        self.bottom = tk.Frame(self.master, bg = '#E4E4E4')
        self.bottom.pack(in_ = self.master)

        # Canvases para as figuras
        self.title_canvas = tk.Canvas(self.top, bg = '#E4E4E4')
        self.title_canvas.pack(in_ = self.top)
        self.logo_canvas = tk.Canvas(self.bottom, bg = '#E4E4E4')
        self.logo_canvas.grid(in_ = self.bottom, column = 1, row = 0, pady = self.height/10)

        # Começar a definir a janela
        self.master.geometry(str(self.width)+"x"+str(self.height))
        self.master.configure(background='#E4E4E4')
        self.master.update()
        # Criar a janela per se
        self.pack
        # Colocar as imagens e botoes
        self.place_item(resource_path("img/chimtext.png"), 0.6, self.title_canvas)
        self.place_item(resource_path("img/Logo.png"), 0.26, self.logo_canvas)
        self.create_widgets()

        global count
        # Para garantir que os widgets e imagens mudam de tamanho
        self.master.bind('<Configure>', self.resize_window)
        check_version()

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

    def resize_window(self, event):
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.place_item(resource_path("img/chimtext.png"), 0.6, self.title_canvas)
        self.place_item(resource_path("img/Logo.png"), 0.26, self.logo_canvas)
        #Define novas posicoes relativas a janela
        self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
        #define novos tamanhos relativos a janela
        self.new["font"] = ("Roboto",int(0.018*self.master.winfo_width()),"bold")
        self.new.configure(height = 1)

    def create_widgets(self):
        # Criar botão para um novo fit
        self.new = tk.Button(self.bottom,
                             width = int(0.011*self.master.winfo_width()),
                             height=1,
                             fg='white',
                             bg='#F21112',
                             activebackground='white',
                             activeforeground='#F21112')
        self.new["text"] = "NEW FIT"
        self.new["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        self.new["command"] = self.create_new
        self.new.grid(column = 2, row = 0, padx = (int(self.master.winfo_width()/10),20))
        # Alterar as cores quando entra e sai
        self.new.bind("<Enter>", func=lambda e: self.new.config(bg='white',fg='#F21112'))
        self.new.bind("<Leave>", func=lambda e: self.new.config(bg='#F21112',fg='white'))

        # Criar botão para importar um fit
        # self.old = tk.Button(self.bottom,
        #                      width = int(0.011*self.master.winfo_width()),
        #                      height=1,
        #                      fg='white',
        #                      bg='#F21112',
        #                      activebackground='white',
        #                      activeforeground='#F21112')
        # self.old["text"] = "IMPORT FIT"
        # self.old["font"] = ("Roboto",int(0.02*self.master.winfo_width()),"bold")
        # self.old["command"] = self.create_import
        # self.old.grid(column = 0, row = 0, padx = (20,int(self.master.winfo_width()/10)))
        # self.old.bind("<Enter>", func=lambda e: self.old.config(bg='white',fg='#F21112'))
        # self.old.bind("<Leave>", func=lambda e: self.old.config(bg='#F21112',fg='white'))

    # def create_import(self):
    #     tk.messagebox.showwarning('SORRY', 'Feature still in development...')

        # ISTO AINDA NÃO ESTÁ FUNCIONAL
        # Destruir tudo o que estava na janela
        # self.title_canvas.delete("all")
        # self.logo_canvas.delete("all")
        # self.old.destroy()
        # self.new.destroy()
        # global count
        # count = 1
        # self.master.configure(background='#E4E4E4')

    def create_new(self, event=None):
        # bindings for hotkeys
        # Remove the image size adjustements
        self.master.unbind('<Configure>')
        # Export Image
        self.master.bind('<Control-Shift-E>', self.export_image)
        self.master.bind('<Control-Shift-e>', self.export_image)
        # New Project
        self.master.bind('<Control-N>', self.create_new)
        self.master.bind('<Control-n>', self.create_new)


        self.selecteddataset = 0

        self.countplots = 0
        # Destruir tudo o que estava na janela
        self.title_canvas.delete("all")
        self.logo_canvas.delete("all")
        self.new.destroy()
        global count
        count = 1

        # Definimos já o array para as labels
        self.data_labels = ['']
        self.plot_labels = ['']
        self.fit_labels = ['']

        # Definir arrays para armazenar texto e as suas posições
        self.plot_text = ['']
        self.text_pos = [[0,0]]
        self.text_size = [10]

        # Definimos as funções, variáveis e afins
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

        self.xfittedfunc = [[]]
        self.yfittedfunc = [[]]

        self.full_output = ['']

        self.x_ticks_ref = []
        self.y_ticks_ref = []

        # Definir o ratio da figura
        self.width_ratio = 1
        self.height_ratio = 1

        self.master.configure(background='#E4E4E4')

        # Criação da estrutura de frames da janela
        self.frameleft = tk.Frame(self.master,  bg='#E4E4E4')
        self.frameleft.place(in_=self.master, relwidth=0.5, relheight=1, relx=0, rely=0)

        # Frameright, contem tudo na parte direita da janela
        self.frameright = tk.Frame(self.master,  bg='#E4E4E4')
        self.frameright.place( in_ = self.master, relwidth=0.5, relheight=1,relx=0.5, rely=0)

        #Subsecção da mesma onde se inserem as entrys de parametros, variavel independente e funçao
        self.subframeright1=tk.Frame(self.frameright, bg='#E4E4E4', highlightbackground="black", highlightthickness=0, padx=20, pady=20)
        self.subframeright1.place(in_=self.frameright, relwidth=1, relheight=0.5, relx=0, rely=0)

         # Criação das frames para a edição visual do gráfico
        self.subframeright2=tk.Frame(self.frameright, bg='#E4E4E4')
        self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.2, relx=0, rely=0.25)

        self.subframeleft1=tk.Frame(self.frameleft, bg='#E4E4E4')
        self.subframeleft1.place(in_ = self.frameleft, relwidth=1, relheight=0.5, relx=0, rely=0)

        self.plotbuttonframe = tk.Frame(self.frameleft, bg= '#E4E4E4')
        self.plotbuttonframe.place(in_ = self.frameleft, relwidth=1, relheight=0.05, relx=0, rely=0.5)

        self.databuttonframe = tk.Frame(self.frameleft, bg='#E4E4E4')
        self.databuttonframe.place(in_ = self.frameleft, relwidth=1, relheight=0.05, relx=0, rely=0.93)

        self.subframeleft2 = tk.Frame(self.frameleft, bg='#E4E4E4')
        self.subframeleft2.place(in_ = self.frameleft, relwidth = 1, relheight= 0.38, relx=0, rely=0.55)

        #Criação da zona onde se inserem as informaçoes relativas aos eixos do grafico
        self.subframeright3 = tk.Frame(self.frameright, bg='#E4E4E4')
        self.subframeright3.place(in_ = self.frameright, relwidth = 1, relheight = 0.52, rely=0.48)

        #Criação do botão que chama a função que processa a funçao
        self.compilebutton = tk.Button(self.subframeright1,
                                       text="COMPILE",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')
        self.compilebutton.place(relwidth=0.2,relx=0.8, rely=0.2,relheight=0.1 )
        self.compilebutton["command"] = self.compile_function

        #Botão que serve para updatar a lista de entries dos parâmetros
        self.upbutton = tk.Button(self.subframeright1,
                                  text="UPDATE",
                                  fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        self.upbutton.place(relwidth=0.2,relx=0.8, rely=0.1,relheight=0.1 )
        self.upbutton["command"] = self.update_parameter

        #Botão pra plottar o dataset, chama a função plot_dataset
        self.plotbutton = tk.Button(self.plotbuttonframe,
                                       text="PLOT",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')

        self.plotbutton.place(in_  = self.plotbuttonframe, relwidth=0.2, relheight=1, relx=0.25)
        self.plotbutton["command"] = self.plot_dataset

        #Botão pra plottar a funçao, chama a funçao plot_function
        self.plotfunctionbutton = tk.Button(self.plotbuttonframe,
                                       text="PLOT FUNCTION",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')

        self.plotfunctionbutton.place(in_  = self.plotbuttonframe, relwidth=0.3, relheight=1,relx = 0.5)
        self.plotfunctionbutton["command"] = self.plot_function
        self.wantfunction = [tk.BooleanVar()]
        self.wantfunction[0].set(0)

        # Botão para importar ficheiros
        self.import_data = tk.Button(self.databuttonframe,
                                     text='IMPORT DATA',
                                     fg='white',
                                     bg='#F21112',
                                     activebackground='white',
                                     activeforeground='#F21112')
        self.import_data.place(relwidth=0.23, relheight=1,relx = 0.05)
        self.import_data["command"] = self.import_window

        self.add_labels = tk.Button(self.databuttonframe,
                                    text='SET LABELS',
                                    fg='white',
                                    bg='#F21112',
                                    activebackground='white',
                                    activeforeground='#F21112')
        self.add_labels.place(relwidth=0.2, relheight=1, relx=0.33)
        self.add_labels["command"] = self.labels

        # Botão para adicionar entradas de texto
        self.add_text = tk.Button(self.databuttonframe,
                                  text='SET TEXT',
                                  fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        self.add_text.place(relwidth=0.16, relheight=1, relx=0.58)
        self.add_text["command"] = self.text

        # Botão para exportar como latex
        self.export_latex = tk.Button(self.databuttonframe,
                                      text="LaTeX-ify",
                                      fg='white',
                                      bg='#F21112',
                                      activebackground='white',
                                      activeforeground='#F21112')
        self.export_latex.place(relwidth=0.16, relheight=1, relx=0.79)
        self.export_latex["command"] = self.latexify

        #Criação do botão ligado à funçao que adiciona mais um dataset
        self.adddatasetbutton = tk.Button(self.plotbuttonframe,
                                       text="+",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112', command = lambda: self.add_dataset(''))
        self.adddatasetbutton.place(in_ = self.plotbuttonframe, relwidth=0.05, relheight=0.5, relx = 0.15, rely=0)

        # Botão para remover datasets
        self.removedatasetbutton = tk.Button(self.plotbuttonframe,
                                             text="-",
                                             fg='white',
                                             bg='#F21112',
                                             activebackground='white',
                                             activeforeground='#F21112')
        self.removedatasetbutton.place(in_ = self.plotbuttonframe, relwidth=0.05, relheight=0.5, relx= 0.15, rely=0.5)
        self.removedatasetbutton["command"] = self.remove_dataset

        self.fitbutton = tk.Button(self.plotbuttonframe,
                                       text="FIT",
                                       fg='white',
                                       bg='#F21112',
                                       activebackground='white',
                                       activeforeground='#F21112')
        self.fitbutton.place(in_ =self.plotbuttonframe, relwidth=0.1, relheight=1, relx = 0.85)
        self.fitbutton["command"] = self.fit_activate
        self.wantfit = [tk.BooleanVar()]
        self.wantfit[0].set(0)

        # Variável para armazenar todos os botoes
        self.buttons = [self.upbutton,
                  self.compilebutton,
                  self.plotbutton,
                  self.plotfunctionbutton,
                  self.import_data,
                  self.adddatasetbutton,
                  self.fitbutton,
                  self.export_latex,
                  self.removedatasetbutton,
                  self.add_labels,
                  self.add_text
                  ]

        for button in self.buttons:
            def hover(button):
                return lambda e: button.config(bg='white',fg='#F21112')
            def unhover(button):
                return lambda e: button.config(bg='#F21112',fg='white')
            button.bind("<Enter>", hover(button))
            button.bind("<Leave>", unhover(button))
            button["font"] = ("Roboto",int(0.011*self.master.winfo_width()))

        self.datastringcarrier = "0.000000 0.200000 -4.220083 5.000000\n0.040080 0.200000 20.306079 5.000000\n0.080160 0.200000 29.509556 5.000000\n0.120240 0.200000 48.493836 5.000000\n0.160321 0.200000 68.609105 5.000000\n0.200401 0.200000 73.976780 5.000000\n0.240481 0.200000 90.348206 5.000000\n0.280561 0.200000 107.429971 5.000000\n0.320641 0.200000 108.084140 5.000000\n0.360721 0.200000 127.051755 5.000000\n0.400802 0.200000 134.937988 5.000000\n0.440882 0.200000 129.461255 5.000000\n0.480962 0.200000 150.258016 5.000000\n0.521042 0.200000 156.667045 5.000000\n0.561122 0.200000 172.252046 5.000000\n0.601202 0.200000 163.602874 5.000000\n0.641283 0.200000 171.550207 5.000000\n0.681363 0.200000 163.741960 5.000000\n0.721443 0.200000 173.751143 5.000000\n0.761523 0.200000 168.647742 5.000000\n0.801603 0.200000 170.747842 5.000000\n0.841683 0.200000 170.096170 5.000000\n0.881764 0.200000 160.471599 5.000000\n0.921844 0.200000 150.175606 5.000000\n0.961924 0.200000 152.733786 5.000000\n1.002004 0.200000 143.121698 5.000000\n1.042084 0.200000 146.264532 5.000000\n1.082164 0.200000 127.527399 5.000000\n1.122244 0.200000 119.731893 5.000000\n1.162325 0.200000 109.983294 5.000000\n1.202405 0.200000 107.143773 5.000000\n1.242485 0.200000 95.094167 5.000000\n1.282565 0.200000 92.440938 5.000000\n1.322645 0.200000 83.966296 5.000000\n1.362725 0.200000 66.828702 5.000000\n1.402806 0.200000 52.931513 5.000000\n1.442886 0.200000 36.324946 5.000000\n1.482966 0.200000 29.922973 5.000000\n1.523046 0.200000 7.976208 5.000000\n1.563126 0.200000 1.489428 5.000000\n1.603206 0.200000 -9.195030 5.000000\n1.643287 0.200000 -23.532098 5.000000\n1.683367 0.200000 -25.749417 5.000000\n1.723447 0.200000 -35.118530 5.000000\n1.763527 0.200000 -55.796327 5.000000\n1.803607 0.200000 -68.857647 5.000000\n1.843687 0.200000 -70.314311 5.000000\n1.883768 0.200000 -86.585397 5.000000\n1.923848 0.200000 -94.812446 5.000000\n1.963928 0.200000 -92.395743 5.000000\n2.004008 0.200000 -100.446687 5.000000\n2.044088 0.200000 -106.587079 5.000000\n2.084168 0.200000 -112.562231 5.000000\n2.124248 0.200000 -108.020072 5.000000\n2.164329 0.200000 -115.267282 5.000000\n2.204409 0.200000 -122.261355 5.000000\n2.244489 0.200000 -116.516333 5.000000\n2.284569 0.200000 -128.890452 5.000000\n2.324649 0.200000 -129.017330 5.000000\n2.364729 0.200000 -119.878573 5.000000\n2.404810 0.200000 -128.626340 5.000000\n2.444890 0.200000 -129.201100 5.000000\n2.484970 0.200000 -118.233865 5.000000\n2.525050 0.200000 -108.107293 5.000000\n2.565130 0.200000 -111.984111 5.000000\n2.605210 0.200000 -102.305572 5.000000\n2.645291 0.200000 -100.950003 5.000000\n2.685371 0.200000 -95.231812 5.000000\n2.725451 0.200000 -79.889093 5.000000\n2.765531 0.200000 -78.113814 5.000000\n2.805611 0.200000 -63.122766 5.000000\n2.845691 0.200000 -62.347123 5.000000\n2.885772 0.200000 -57.464439 5.000000\n2.925852 0.200000 -50.095949 5.000000\n2.965932 0.200000 -28.707316 5.000000\n3.006012 0.200000 -25.857203 5.000000\n3.046092 0.200000 -9.977920 5.000000\n3.086172 0.200000 -17.829600 5.000000\n3.126253 0.200000 -5.207881 5.000000\n3.166333 0.200000 3.204056 5.000000\n3.206413 0.200000 28.687108 5.000000\n3.246493 0.200000 27.405625 5.000000\n3.286573 0.200000 33.953569 5.000000\n3.326653 0.200000 36.077991 5.000000\n3.366733 0.200000 40.915877 5.000000\n3.406814 0.200000 52.547911 5.000000\n3.446894 0.200000 44.613076 5.000000\n3.486974 0.200000 68.303123 5.000000\n3.527054 0.200000 79.331374 5.000000\n3.567134 0.200000 80.976405 5.000000\n3.607214 0.200000 81.713514 5.000000\n3.647295 0.200000 78.158750 5.000000\n3.687375 0.200000 93.019663 5.000000\n3.727455 0.200000 86.270143 5.000000\n3.767535 0.200000 88.670332 5.000000\n3.807615 0.200000 92.136118 5.000000\n3.847695 0.200000 93.761178 5.000000\n3.887776 0.200000 88.573773 5.000000\n3.927856 0.200000 94.170806 5.000000\n3.967936 0.200000 86.460671 5.000000\n4.008016 0.200000 94.492714 5.000000\n4.048096 0.200000 90.596259 5.000000\n4.088176 0.200000 87.304429 5.000000\n4.128257 0.200000 87.532433 5.000000\n4.168337 0.200000 72.274535 5.000000\n4.208417 0.200000 66.245807 5.000000\n4.248497 0.200000 73.091925 5.000000\n4.288577 0.200000 60.468736 5.000000\n4.328657 0.200000 60.017482 5.000000\n4.368737 0.200000 58.271275 5.000000\n4.408818 0.200000 45.748794 5.000000\n4.448898 0.200000 40.314987 5.000000\n4.488978 0.200000 49.452884 5.000000\n4.529058 0.200000 26.422226 5.000000\n4.569138 0.200000 22.944044 5.000000\n4.609218 0.200000 16.095398 5.000000\n4.649299 0.200000 12.753866 5.000000\n4.689379 0.200000 6.909262 5.000000\n4.729459 0.200000 1.212596 5.000000\n4.769539 0.200000 3.055895 5.000000\n4.809619 0.200000 -14.751589 5.000000\n4.849699 0.200000 -20.025156 5.000000\n4.889780 0.200000 -31.446377 5.000000\n4.929860 0.200000 -31.690325 5.000000\n4.969940 0.200000 -40.431643 5.000000\n5.010020 0.200000 -33.717315 5.000000\n5.050100 0.200000 -43.198812 5.000000\n5.090180 0.200000 -45.091974 5.000000\n5.130261 0.200000 -54.723450 5.000000\n5.170341 0.200000 -52.448394 5.000000\n5.210421 0.200000 -54.470856 5.000000\n5.250501 0.200000 -66.779061 5.000000\n5.290581 0.200000 -67.979157 5.000000\n5.330661 0.200000 -66.643499 5.000000\n5.370741 0.200000 -72.572019 5.000000\n5.410822 0.200000 -65.619787 5.000000\n5.450902 0.200000 -70.286317 5.000000\n5.490982 0.200000 -66.983429 5.000000\n5.531062 0.200000 -66.396522 5.000000\n5.571142 0.200000 -58.528374 5.000000\n5.611222 0.200000 -63.276543 5.000000\n5.651303 0.200000 -57.647651 5.000000\n5.691383 0.200000 -58.155591 5.000000\n5.731463 0.200000 -59.947225 5.000000\n5.771543 0.200000 -56.605605 5.000000\n5.811623 0.200000 -48.498689 5.000000\n5.851703 0.200000 -44.906405 5.000000\n5.891784 0.200000 -35.595236 5.000000\n5.931864 0.200000 -36.182548 5.000000\n5.971944 0.200000 -35.946789 5.000000\n6.012024 0.200000 -26.033401 5.000000\n6.052104 0.200000 -21.916403 5.000000\n6.092184 0.200000 -18.744021 5.000000\n6.132265 0.200000 -19.034690 5.000000\n6.172345 0.200000 -3.464158 5.000000\n6.212425 0.200000 -9.989100 5.000000\n6.252505 0.200000 -18.031833 5.000000\n6.292585 0.200000 -0.473183 5.000000\n6.332665 0.200000 7.128211 5.000000\n6.372745 0.200000 10.383434 5.000000\n6.412826 0.200000 8.963351 5.000000\n6.452906 0.200000 17.957149 5.000000\n6.492986 0.200000 18.615820 5.000000\n6.533066 0.200000 28.568868 5.000000\n6.573146 0.200000 36.890251 5.000000\n6.613226 0.200000 28.441762 5.000000\n6.653307 0.200000 37.849841 5.000000\n6.693387 0.200000 32.059030 5.000000\n6.733467 0.200000 28.204411 5.000000\n6.773547 0.200000 48.291845 5.000000\n6.813627 0.200000 50.102458 5.000000\n6.853707 0.200000 42.508948 5.000000\n6.893788 0.200000 46.535820 5.000000\n6.933868 0.200000 48.448955 5.000000\n6.973948 0.200000 55.769351 5.000000\n7.014028 0.200000 54.062273 5.000000\n7.054108 0.200000 49.087978 5.000000\n7.094188 0.200000 57.951041 5.000000\n7.134269 0.200000 46.272647 5.000000\n7.174349 0.200000 47.668543 5.000000\n7.214429 0.200000 46.921758 5.000000\n7.254509 0.200000 42.871597 5.000000\n7.294589 0.200000 38.610888 5.000000\n7.334669 0.200000 39.815706 5.000000\n7.374749 0.200000 37.159121 5.000000\n7.414830 0.200000 31.996323 5.000000\n7.454910 0.200000 38.671490 5.000000\n7.494990 0.200000 30.193041 5.000000\n7.535070 0.200000 24.469951 5.000000\n7.575150 0.200000 27.829150 5.000000\n7.615230 0.200000 14.374572 5.000000\n7.655311 0.200000 18.588095 5.000000\n7.695391 0.200000 19.879006 5.000000\n7.735471 0.200000 14.032910 5.000000\n7.775551 0.200000 4.663582 5.000000\n7.815631 0.200000 -2.575609 5.000000\n7.855711 0.200000 -1.598550 5.000000\n7.895792 0.200000 -2.158824 5.000000\n7.935872 0.200000 -7.086892 5.000000\n7.975952 0.200000 -14.662059 5.000000\n8.016032 0.200000 -21.428117 5.000000\n8.056112 0.200000 -15.659874 5.000000\n8.096192 0.200000 -20.559999 5.000000\n8.136273 0.200000 -21.496457 5.000000\n8.176353 0.200000 -15.018610 5.000000\n8.216433 0.200000 -27.698434 5.000000\n8.256513 0.200000 -24.037836 5.000000\n8.296593 0.200000 -31.816119 5.000000\n8.336673 0.200000 -32.542239 5.000000\n8.376754 0.200000 -41.213083 5.000000\n8.416834 0.200000 -33.509833 5.000000\n8.456914 0.200000 -37.619873 5.000000\n8.496994 0.200000 -27.887921 5.000000\n8.537074 0.200000 -31.248875 5.000000\n8.577154 0.200000 -37.039771 5.000000\n8.617234 0.200000 -33.194420 5.000000\n8.657315 0.200000 -35.690008 5.000000\n8.697395 0.200000 -26.343880 5.000000\n8.737475 0.200000 -35.840091 5.000000\n8.777555 0.200000 -19.936502 5.000000\n8.817635 0.200000 -33.370277 5.000000\n8.857715 0.200000 -32.042716 5.000000\n8.897796 0.200000 -26.828380 5.000000\n8.937876 0.200000 -34.670138 5.000000\n8.977956 0.200000 -30.877291 5.000000\n9.018036 0.200000 -28.066351 5.000000\n9.058116 0.200000 -16.888626 5.000000\n9.098196 0.200000 -21.047476 5.000000\n9.138277 0.200000 -16.292002 5.000000\n9.178357 0.200000 -21.978134 5.000000\n9.218437 0.200000 -10.110033 5.000000\n9.258517 0.200000 -7.966969 5.000000\n9.298597 0.200000 -14.467292 5.000000\n9.338677 0.200000 -9.640137 5.000000\n9.378758 0.200000 -7.084470 5.000000\n9.418838 0.200000 -1.477334 5.000000\n9.458918 0.200000 0.219948 5.000000\n9.498998 0.200000 2.325002 5.000000\n9.539078 0.200000 6.512176 5.000000\n9.579158 0.200000 5.541867 5.000000\n9.619238 0.200000 11.372225 5.000000\n9.659319 0.200000 13.947301 5.000000\n9.699399 0.200000 13.590980 5.000000\n9.739479 0.200000 13.216626 5.000000\n9.779559 0.200000 16.390693 5.000000\n9.819639 0.200000 27.023087 5.000000\n9.859719 0.200000 17.697813 5.000000\n9.899800 0.200000 27.454231 5.000000\n9.939880 0.200000 23.537202 5.000000\n9.979960 0.200000 23.818608 5.000000\n10.020040 0.200000 14.047478 5.000000\n10.060120 0.200000 32.127949 5.000000\n10.100200 0.200000 24.409514 5.000000\n10.140281 0.200000 23.204936 5.000000\n10.180361 0.200000 26.134774 5.000000\n10.220441 0.200000 27.358767 5.000000\n10.260521 0.200000 20.644017 5.000000\n10.300601 0.200000 21.998389 5.000000\n10.340681 0.200000 17.857595 5.000000\n10.380762 0.200000 21.323762 5.000000\n10.420842 0.200000 20.252274 5.000000\n10.460922 0.200000 19.224765 5.000000\n10.501002 0.200000 16.624415 5.000000\n10.541082 0.200000 19.284652 5.000000\n10.581162 0.200000 27.722624 5.000000\n10.621242 0.200000 10.830659 5.000000\n10.661323 0.200000 18.016111 5.000000\n10.701403 0.200000 12.131010 5.000000\n10.741483 0.200000 25.532536 5.000000\n10.781563 0.200000 0.247603 5.000000\n10.821643 0.200000 6.395373 5.000000\n10.861723 0.200000 13.165740 5.000000\n10.901804 0.200000 3.000769 5.000000\n10.941884 0.200000 2.168944 5.000000\n10.981964 0.200000 3.228704 5.000000\n11.022044 0.200000 -1.992237 5.000000\n11.062124 0.200000 0.717827 5.000000\n11.102204 0.200000 -2.348446 5.000000\n11.142285 0.200000 -8.534931 5.000000\n11.182365 0.200000 -6.482811 5.000000\n11.222445 0.200000 -12.571645 5.000000\n11.262525 0.200000 -10.239189 5.000000\n11.302605 0.200000 -23.445802 5.000000\n11.342685 0.200000 -9.620284 5.000000\n11.382766 0.200000 -9.469368 5.000000\n11.422846 0.200000 -14.469548 5.000000\n11.462926 0.200000 -16.057060 5.000000\n11.503006 0.200000 -15.463553 5.000000\n11.543086 0.200000 -29.203668 5.000000\n11.583166 0.200000 -21.897996 5.000000\n11.623246 0.200000 -19.576155 5.000000\n11.663327 0.200000 -9.354795 5.000000\n11.703407 0.200000 -11.857799 5.000000\n11.743487 0.200000 -18.484859 5.000000\n11.783567 0.200000 -17.001798 5.000000\n11.823647 0.200000 -20.839559 5.000000\n11.863727 0.200000 -10.625569 5.000000\n11.903808 0.200000 -12.561239 5.000000\n11.943888 0.200000 -10.337802 5.000000\n11.983968 0.200000 -20.437828 5.000000\n12.024048 0.200000 -21.202328 5.000000\n12.064128 0.200000 -20.814618 5.000000\n12.104208 0.200000 -9.093745 5.000000\n12.144289 0.200000 -10.776351 5.000000\n12.184369 0.200000 -14.682031 5.000000\n12.224449 0.200000 -15.557082 5.000000\n12.264529 0.200000 -8.452130 5.000000\n12.304609 0.200000 -5.284851 5.000000\n12.344689 0.200000 -6.043369 5.000000\n12.384770 0.200000 -8.505228 5.000000\n12.424850 0.200000 -3.082345 5.000000\n12.464930 0.200000 2.547971 5.000000\n12.505010 0.200000 3.798123 5.000000\n12.545090 0.200000 9.212148 5.000000\n12.585170 0.200000 -1.805794 5.000000\n12.625251 0.200000 7.187777 5.000000\n12.665331 0.200000 3.731835 5.000000\n12.705411 0.200000 9.221259 5.000000\n12.745491 0.200000 -7.587803 5.000000\n12.785571 0.200000 14.854788 5.000000\n12.825651 0.200000 1.033444 5.000000\n12.865731 0.200000 10.726527 5.000000\n12.905812 0.200000 15.855602 5.000000\n12.945892 0.200000 9.741655 5.000000\n12.985972 0.200000 12.129298 5.000000\n13.026052 0.200000 6.866070 5.000000\n13.066132 0.200000 13.327839 5.000000\n13.106212 0.200000 22.548522 5.000000\n13.146293 0.200000 12.441904 5.000000\n13.186373 0.200000 14.290439 5.000000\n13.226453 0.200000 18.981131 5.000000\n13.266533 0.200000 14.088621 5.000000\n13.306613 0.200000 18.580735 5.000000\n13.346693 0.200000 5.400956 5.000000\n13.386774 0.200000 13.922285 5.000000\n13.426854 0.200000 12.228760 5.000000\n13.466934 0.200000 14.367235 5.000000\n13.507014 0.200000 10.069593 5.000000\n13.547094 0.200000 9.403623 5.000000\n13.587174 0.200000 10.807500 5.000000\n13.627255 0.200000 8.994746 5.000000\n13.667335 0.200000 17.059241 5.000000\n13.707415 0.200000 5.944681 5.000000\n13.747495 0.200000 14.293543 5.000000\n13.787575 0.200000 11.252237 5.000000\n13.827655 0.200000 16.805709 5.000000\n13.867735 0.200000 4.094287 5.000000\n13.907816 0.200000 5.383987 5.000000\n13.947896 0.200000 12.449402 5.000000\n13.987976 0.200000 7.040040 5.000000\n14.028056 0.200000 2.234196 5.000000\n14.068136 0.200000 6.228159 5.000000\n14.108216 0.200000 -1.072208 5.000000\n14.148297 0.200000 -5.193341 5.000000\n14.188377 0.200000 -4.510789 5.000000\n14.228457 0.200000 -3.619780 5.000000\n14.268537 0.200000 4.591740 5.000000\n14.308617 0.200000 -5.416248 5.000000\n14.348697 0.200000 -1.694420 5.000000\n14.388778 0.200000 -0.238606 5.000000\n14.428858 0.200000 -2.555457 5.000000\n14.468938 0.200000 -4.215943 5.000000\n14.509018 0.200000 -2.086985 5.000000\n14.549098 0.200000 -8.206409 5.000000\n14.589178 0.200000 -6.998627 5.000000\n14.629259 0.200000 -11.455970 5.000000\n14.669339 0.200000 -8.796179 5.000000\n14.709419 0.200000 -4.568559 5.000000\n14.749499 0.200000 -9.766033 5.000000\n14.789579 0.200000 -14.257980 5.000000\n14.829659 0.200000 -8.425578 5.000000\n14.869739 0.200000 -21.594720 5.000000\n14.909820 0.200000 -6.706730 5.000000\n14.949900 0.200000 -22.397763 5.000000\n14.989980 0.200000 -14.721651 5.000000\n15.030060 0.200000 -6.735613 5.000000\n15.070140 0.200000 -6.340337 5.000000\n15.110220 0.200000 -2.445827 5.000000\n15.150301 0.200000 -9.874866 5.000000\n15.190381 0.200000 -1.413741 5.000000\n15.230461 0.200000 -8.766435 5.000000\n15.270541 0.200000 -5.677615 5.000000\n15.310621 0.200000 -3.008112 5.000000\n15.350701 0.200000 -2.927042 5.000000\n15.390782 0.200000 -13.984512 5.000000\n15.430862 0.200000 -5.995535 5.000000\n15.470942 0.200000 -14.618264 5.000000\n15.511022 0.200000 0.097088 5.000000\n15.551102 0.200000 -13.189818 5.000000\n15.591182 0.200000 0.355034 5.000000\n15.631263 0.200000 0.784178 5.000000\n15.671343 0.200000 0.266240 5.000000\n15.711423 0.200000 -2.829156 5.000000\n15.751503 0.200000 -0.311902 5.000000\n15.791583 0.200000 0.066581 5.000000\n15.831663 0.200000 -2.041654 5.000000\n15.871743 0.200000 5.305573 5.000000\n15.911824 0.200000 5.302848 5.000000\n15.951904 0.200000 5.252021 5.000000\n15.991984 0.200000 -2.231145 5.000000\n16.032064 0.200000 1.885515 5.000000\n16.072144 0.200000 6.379447 5.000000\n16.112224 0.200000 6.896192 5.000000\n16.152305 0.200000 8.838547 5.000000\n16.192385 0.200000 6.327971 5.000000\n16.232465 0.200000 6.743566 5.000000\n16.272545 0.200000 4.314842 5.000000\n16.312625 0.200000 4.302374 5.000000\n16.352705 0.200000 0.469928 5.000000\n16.392786 0.200000 7.795278 5.000000\n16.432866 0.200000 10.292563 5.000000\n16.472946 0.200000 1.007937 5.000000\n16.513026 0.200000 7.731705 5.000000\n16.553106 0.200000 8.774526 5.000000\n16.593186 0.200000 3.301125 5.000000\n16.633267 0.200000 5.489381 5.000000\n16.673347 0.200000 11.807418 5.000000\n16.713427 0.200000 6.936980 5.000000\n16.753507 0.200000 10.544944 5.000000\n16.793587 0.200000 3.398610 5.000000\n16.833667 0.200000 -1.275229 5.000000\n16.873747 0.200000 10.642082 5.000000\n16.913828 0.200000 1.769257 5.000000\n16.953908 0.200000 3.303666 5.000000\n16.993988 0.200000 0.219273 5.000000\n17.034068 0.200000 11.769642 5.000000\n17.074148 0.200000 -10.607201 5.000000\n17.114228 0.200000 -1.017754 5.000000\n17.154309 0.200000 2.763988 5.000000\n17.194389 0.200000 -1.423901 5.000000\n17.234469 0.200000 5.356608 5.000000\n17.274549 0.200000 6.227375 5.000000\n17.314629 0.200000 6.759017 5.000000\n17.354709 0.200000 5.116336 5.000000\n17.394790 0.200000 1.193953 5.000000\n17.434870 0.200000 0.091315 5.000000\n17.474950 0.200000 -6.167816 5.000000\n17.515030 0.200000 -7.607873 5.000000\n17.555110 0.200000 -6.554534 5.000000\n17.595190 0.200000 -8.763374 5.000000\n17.635271 0.200000 -9.999903 5.000000\n17.675351 0.200000 1.444506 5.000000\n17.715431 0.200000 -2.940430 5.000000\n17.755511 0.200000 -2.074974 5.000000\n17.795591 0.200000 -4.999610 5.000000\n17.835671 0.200000 -8.447734 5.000000\n17.875752 0.200000 -9.219865 5.000000\n17.915832 0.200000 -0.884357 5.000000\n17.955912 0.200000 -13.630628 5.000000\n17.995992 0.200000 -3.362859 5.000000\n18.036072 0.200000 -2.861015 5.000000\n18.076152 0.200000 0.459927 5.000000\n18.116232 0.200000 2.075756 5.000000\n18.156313 0.200000 1.742471 5.000000\n18.196393 0.200000 -4.681144 5.000000\n18.236473 0.200000 -11.362966 5.000000\n18.276553 0.200000 -10.926193 5.000000\n18.316633 0.200000 -3.513967 5.000000\n18.356713 0.200000 4.763483 5.000000\n18.396794 0.200000 -2.458590 5.000000\n18.436874 0.200000 -4.460571 5.000000\n18.476954 0.200000 -8.472226 5.000000\n18.517034 0.200000 -18.139443 5.000000\n18.557114 0.200000 -3.079748 5.000000\n18.597194 0.200000 2.546519 5.000000\n18.637275 0.200000 5.423287 5.000000\n18.677355 0.200000 -4.911763 5.000000\n18.717435 0.200000 -0.456041 5.000000\n18.757515 0.200000 1.675098 5.000000\n18.797595 0.200000 2.913273 5.000000\n18.837675 0.200000 -1.921587 5.000000\n18.877756 0.200000 -2.727984 5.000000\n18.917836 0.200000 8.666047 5.000000\n18.957916 0.200000 0.215012 5.000000\n18.997996 0.200000 2.999787 5.000000\n19.038076 0.200000 5.302385 5.000000\n19.078156 0.200000 1.706727 5.000000\n19.118236 0.200000 -0.960444 5.000000\n19.158317 0.200000 -2.947608 5.000000\n19.198397 0.200000 8.699859 5.000000\n19.238477 0.200000 3.165915 5.000000\n19.278557 0.200000 2.699166 5.000000\n19.318637 0.200000 7.007208 5.000000\n19.358717 0.200000 1.366691 5.000000\n19.398798 0.200000 5.806320 5.000000\n19.438878 0.200000 5.205500 5.000000\n19.478958 0.200000 6.384510 5.000000\n19.519038 0.200000 2.091265 5.000000\n19.559118 0.200000 1.740590 5.000000\n19.599198 0.200000 -1.249371 5.000000\n19.639279 0.200000 13.168858 5.000000\n19.679359 0.200000 6.457068 5.000000\n19.719439 0.200000 -2.875295 5.000000\n19.759519 0.200000 6.103446 5.000000\n19.799599 0.200000 2.828744 5.000000\n19.839679 0.200000 8.695443 5.000000\n19.879760 0.200000 -1.042130 5.000000\n19.919840 0.200000 1.382902 5.000000\n19.959920 0.200000 5.380195 5.000000\n20.000000 0.200000 4.680706 5.000000"
        # Criar uma menu bar
        # esta self.menubar é a mais geral, é a que contem as outras
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # Este é o botão file na self.menubar
        self.file_options = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", underline=0, menu=self.file_options)
        self.file_options.add_command(label='Start New', command = self.restart, accelerator="Ctrl+N")
        self.file_options.add_command(label='Export Image', command=self.export_image, accelerator="Ctrl+Shift+E")
        # self.file_options.add_command(label='Save Project', command=self.save_everything)
        # self.file_options.add_command(label='Import Project', command=self.import_project)

        # Botao na self.menubar para escolher as opçoes do plot
        self.plotoptions = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Plot options", menu=self.plotoptions)

        # Estas 3 variáveis servem para o utilizador escolher o que quer ver
        self.wantpoints = [tk.BooleanVar()]
        self.wantline = [tk.BooleanVar()]
        self.wanterror = [tk.BooleanVar()]
        # Valores default para as ditas variáveis
        self.wantpoints[0].set(1)
        self.wantline[0].set(0)
        self.wanterror[0].set(0)

        # Aqui adicionam-se os 3 checkbuttons da dita checklist do que o utilizador quer ler,
        # as variáveis definidas anteriormente servem para registar se o utilizador tem o dito setting selecionado ou nao
        self.plotoptions.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.wantpoints[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.wantline[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.wanterror[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.wantfit[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.wantfunction[self.selecteddataset])

        # Estes 3 menus na self.menubar servem para selecionar a cor dos markers(pontos), da linha e das errorbars
        self.choosecolor = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Choose Colors", menu = self.choosecolor)

        self.currentselection = 0

        self.markercolorvar = []
        self.linecolorvar = []
        self.errorcolorvar = []
        self.funcfitcolorvar = []
        self.funcplotcolorvar = []

        self.markercolorvar.append('black')
        self.linecolorvar.append('black')
        self.errorcolorvar.append('black')
        self.funcfitcolorvar.append('black')
        self.funcplotcolorvar.append('black')

        # Aqui tou so a meter os checkbuttons nas caixas
        self.choosecolor.add_command(label = 'Marker Color', command = self.markercolorpick)
        self.choosecolor.add_command(label = 'Connection Color', command = self.linecolorpick)
        self.choosecolor.add_command(label = 'Errorbar Color', command = self.errorcolorpick)
        self.choosecolor.add_command(label = 'Plot Function Color', command = self.funcplotcolorpick)
        self.choosecolor.add_command(label = 'Fit Function Color', command = self.funcfitcolorpick)

        self.datasetstoplot = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label = "Choose Datasets", menu = self.datasetstoplot)

        self.datasetstoplotvar = []
        self.datasetstoplotvar.append(tk.BooleanVar())
        self.datasetstoplotvar[0].set(1)

        self.datasetstoplot.add_checkbutton(label = "Plot Dataset 1", onvalue = 1, offvalue = 0, variable = self.datasetstoplotvar[0] )

        # criação do dropdown menu para as opções mais avançadas
        self.advanced = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label = 'Advanced', menu = self.advanced)
        self.advanced.add_command(label='Tick Placement', command = self.set_ticks)
        self.advanced.add_command(label='Figure Ratio', command = self.set_ratio)

        # criação do dropdown menu para as ajudas
        self.help = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label = 'Help', menu = self.help)
        self.help.add_command(label='Documentation', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/docs'))
        self.help.add_command(label='FAQs', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/faq'))
        self.help.add_command(label='About', command=lambda: webbrowser.open('https://sites.google.com/view/chimera-fit/about'))

        # Criação da zona para inserir a variável independente
        self.independentlabel = tk.Label(self.subframeright1,text="Independent Var", bg='#E4E4E4')
        self.independentlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.independentlabel.place(relwidth=0.25, rely=0, relheight=0.1)
        self.independententry = tk.Entry(self.subframeright1, font=30)
        self.independententry.place(relwidth=0.30, rely=0, relheight=0.1, relx = 0.27)
        self.independententry.insert(0, 'x')
        self.independententry.focus_set()

        # Criação da zona para inserir os parâmetros
        self.parameterlabel = tk.Label(self.subframeright1,text="Parameter", bg='#E4E4E4')
        self.parameterlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.parameterlabel.place(relwidth=0.22, rely=0.1, relheight=0.1)
        self.parameterentry = tk.Entry(self.subframeright1, font=30)
        self.parameterentry.place(relwidth=0.55, rely=0.1, relheight=0.1,relx = 0.27)
        self.parameterentry.insert(0, "A,omega,phi,lambda")
        self.parameterentry.focus_set()

        # Criação da zona onde se insere a função
        self.functionlabel = tk.Label(self.subframeright1,text= "Function", bg='#E4E4E4')
        self.functionlabel["font"] = ("Roboto",int(0.01*self.master.winfo_width()))
        self.functionlabel.place(relwidth=0.22, rely=0.2, relheight=0.1)
        self.functionentry = tk.Entry(self.subframeright1, font=30)
        self.functionentry.place(relwidth=0.55,relx=0.27, rely=0.2, relheight=0.1)
        self.functionentry.insert(0, "A*sin(omega*x+phi)*exp(-lambda*x)")
        self.functionentry.focus_set()

        self.autoscalex = tk.BooleanVar()
        self.autoscalex.set(1)
        self.xaxisautoscale = tk.Checkbutton(self.subframeright3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.autoscalex, text = 'Autoscale', anchor = 'w')
        self.xaxisautoscale.place(in_ = self.subframeright3, relwidth = 0.295, relheight = 0.05, rely = 0.4, relx = 0.05)

        self.log_x = tk.BooleanVar()
        self.log_x.set(0)
        self.log_x_button = tk.Checkbutton(self.subframeright3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.log_x, text = 'Log Scale', anchor = 'w')
        self.log_x_button.place(in_ = self.subframeright3, relwidth = 0.295, relheight = 0.05, rely = 0.45, relx = 0.05)

        self.xaxislabel = tk.Label(self.subframeright3, text="X Axis", bg='#E4E4E4')
        self.xaxislabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.2, rely=0)

        self.yaxislabel = tk.Label(self.subframeright3, text="Y Axis", bg='#E4E4E4')
        self.yaxislabel.place(in_ = self.subframeright3, relwidth = 0.5, relheight=0.1, relx=0.5, rely=0)

        self.xaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from", bg='#E4E4E4')
        self.xaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.2, relheight=0.1, relx = 0, rely = 0.1)

        self.remove_autoscale = True
        def remove_auto_x(event):
            if count == 2 and self.remove_autoscale:
                self.autoscalex.set(0)
        def remove_auto_y(event):
            if count == 2 and self.remove_autoscale:
                self.autoscaley.set(0)

        x_min = tk.StringVar()
        x_min.trace("w", lambda name, index, mode, x_min=x_min: remove_auto_x(x_min))
        self.xaxisminentry = tk.Entry(self.subframeright3, justify='center', textvariable=x_min)
        self.xaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.2, rely=0.1)
        self.xaxisminentry.insert(0, "0")

        self.xaxistolabel = tk.Label(self.subframeright3, text = "to", bg='#E4E4E4')
        self.xaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.3, rely=0.1)

        x_max = tk.StringVar()
        x_max.trace('w', lambda name, index, mode, x_min=x_min: remove_auto_x(x_max))
        self.xaxismaxentry = tk.Entry(self.subframeright3, justify='center', textvariable=x_max)
        self.xaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.35, rely=0.1)
        self.xaxismaxentry.insert(0, "10")

        self.xaxistitlelabel = tk.Label(self.subframeright3, text = "Title", bg='#E4E4E4')
        self.xaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0, rely=0.25)

        self.xaxistitleentry = tk.Entry(self.subframeright3)
        self.xaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.1, rely=0.25)
        self.xaxistitleentry.insert(0, "Abcissas")

        self.xaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing", bg='#E4E4E4')
        self.xaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.22, relheight = 0.1, relx=0.175, rely= 0.4)

        x_space = tk.StringVar()
        x_space.trace('w', lambda name, index, mode, x_space=x_space: remove_auto_x(x_space))
        self.xaxistickspentry = tk.Entry(self.subframeright3, textvariable=x_space)
        self.xaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0.35, rely=0.45, anchor="w")
        self.xaxistickspentry.insert(0, "1")

        self.autoscaley = tk.BooleanVar()
        self.autoscaley.set(1)
        self.yaxisautoscale = tk.Checkbutton(self.subframeright3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.autoscaley, text = 'Autoscale', anchor = 'w')
        self.yaxisautoscale.place(in_ = self.subframeright3, relwidth = 0.295, relheight = 0.05, rely = 0.4, relx = 0.55)

        self.log_y = tk.BooleanVar()
        self.log_y.set(0)
        self.log_y_button = tk.Checkbutton(self.subframeright3, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.log_y, text = 'Log Scale', anchor = 'w')
        self.log_y_button.place(in_ = self.subframeright3, relwidth = 0.295, relheight = 0.05, rely = 0.45, relx = 0.55)

        self.yaxisrangelabel = tk.Label(self.subframeright3, text = "Range: from", bg='#E4E4E4')
        self.yaxisrangelabel.place(in_ = self.subframeright3, relwidth=0.2, relheight=0.1, relx = 0.50, rely = 0.1)

        y_min = tk.StringVar()
        y_min.trace('w', lambda name, index, mode, y_min=y_min: remove_auto_y(y_min))
        self.yaxisminentry = tk.Entry(self.subframeright3, justify='center', textvariable=y_min)
        self.yaxisminentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.70, rely=0.1)
        self.yaxisminentry.insert(0, "0")

        self.yaxistolabel = tk.Label(self.subframeright3, text = "to", bg='#E4E4E4')
        self.yaxistolabel.place(in_ = self.subframeright3, relwidth=0.05, relheight=0.1, relx=0.80, rely=0.1)

        y_max = tk.StringVar()
        y_max.trace('w', lambda name, index, mode, y_max=y_max: remove_auto_y(y_max))
        self.yaxismaxentry = tk.Entry(self.subframeright3, justify='center', textvariable=y_max)
        self.yaxismaxentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight=0.1, relx=0.85, rely=0.1)
        self.yaxismaxentry.insert(0, "10")

        self.yaxistitlelabel = tk.Label(self.subframeright3, text = "Title", bg='#E4E4E4')
        self.yaxistitlelabel.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx = 0.5, rely=0.25)

        self.yaxistitleentry = tk.Entry(self.subframeright3)
        self.yaxistitleentry.place(in_ = self.subframeright3, relwidth = 0.3, relheight = 0.1, relx = 0.6, rely=0.25)
        self.yaxistitleentry.insert(0, "Ordenadas")

        self.yaxisticksplabel = tk.Label(self.subframeright3, text = "Tick Spacing", bg='#E4E4E4')
        self.yaxisticksplabel.place(in_=self.subframeright3, relwidth = 0.22, relheight = 0.1, relx = 0.675, rely= 0.4)

        y_space = tk.StringVar()
        y_space.trace('w', lambda name, index, mode, y_space=y_space: remove_auto_y(y_space))
        self.yaxistickspentry = tk.Entry(self.subframeright3, textvariable=y_space)
        self.yaxistickspentry.place(in_ = self.subframeright3, relwidth = 0.1, relheight = 0.1, relx=0.85, rely=0.45, anchor = "w")
        self.yaxistickspentry.insert(0, "1")

        self.linewidth = []
        self.markersize = []
        self.errorwidth = []
        self.funcplotwidth = []
        self.funcfitwidth = []

        self.linewidth.append(tk.DoubleVar())
        self.markersize.append(tk.DoubleVar())
        self.errorwidth.append(tk.DoubleVar())
        self.funcplotwidth.append(tk.DoubleVar())
        self.funcfitwidth.append(tk.DoubleVar())

        self.linewidth[0].set(2)
        self.markersize[0].set(2)
        self.errorwidth[0].set(2)
        self.funcplotwidth[0].set(2)
        self.funcfitwidth[0].set(2)

        self.linescalelabel = tk.Label(self.subframeright3, text = 'Connection Width', bg = '#E4E4E4')
        self.linescalelabel['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.linescalelabel.place(in_ = self.subframeright3, relwidth = 0.3, relx = 0.02, rely=0.56)
        self.linescalelabelvalue = tk.Label(self.subframeright3, text = '2.0', bg = '#E4E4E4')
        self.linescalelabelvalue['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.linescalelabelvalue.place(in_ = self.subframeright3, relx = 0.55, rely=0.56)
        self.linewidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.lineslider, showvalue = False, variable = self.linewidth[0])
        self.linewidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.56, relheight=0.06)
        self.linewidthscale['width'] = 0.025*self.master.winfo_width()
        self.linewidthscale['state'] = tk.DISABLED

        self.markerscalelabel = tk.Label(self.subframeright3, text = 'Marker Size', bg = '#E4E4E4')
        self.markerscalelabel['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.markerscalelabel.place(in_ = self.subframeright3, relwidth = 0.3, relx = 0.02, rely=0.64)
        self.markerscalelabelvalue = tk.Label(self.subframeright3, text = '2.0', bg = '#E4E4E4')
        self.markerscalelabelvalue['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.markerscalelabelvalue.place(in_ = self.subframeright3, relx = 0.55, rely=0.64)
        self.markersizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.markerslider,showvalue =False, variable = self.markersize[0])
        self.markersizescale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.64, relheight=0.06)
        self.markersizescale['width'] = 0.025*self.master.winfo_width()
        self.markersizescale['state'] = tk.DISABLED

        self.errorscalelabel = tk.Label(self.subframeright3, text = 'Errorbar Width', bg = '#E4E4E4')
        self.errorscalelabel['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.errorscalelabel.place(in_ = self.subframeright3,relwidth = 0.3, relx = 0.02, rely=0.88)
        self.errorscalelabelvalue = tk.Label(self.subframeright3, text = '2.0', bg = '#E4E4E4')
        self.errorscalelabelvalue['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.errorscalelabelvalue.place(in_ = self.subframeright3, relx = 0.55, rely=0.88)
        self.errorsizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.errorslider, showvalue = False, variable = self.errorwidth[0])
        self.errorsizescale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.88, relheight=0.06)
        self.errorsizescale['width'] = 0.025*self.master.winfo_width()
        self.errorsizescale['state'] = tk.DISABLED

        self.funcplotscalelabel = tk.Label(self.subframeright3, text = 'Plot Func. Width', bg = '#E4E4E4')
        self.funcplotscalelabel['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.funcplotscalelabel.place(in_ = self.subframeright3,relwidth = 0.3, relx = 0.02, rely=0.72)
        self.funcplotscalelabelvalue = tk.Label(self.subframeright3, text = '2.0', bg = '#E4E4E4')
        self.funcplotscalelabelvalue['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.funcplotscalelabelvalue.place(in_ = self.subframeright3, relx = 0.55, rely=0.72)
        self.funcplotwidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.funcplotslider, showvalue = False, variable = self.funcplotwidth[0])
        self.funcplotwidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.72, relheight=0.06)
        self.funcplotwidthscale['width'] = 0.025*self.master.winfo_width()
        self.funcplotwidthscale['state'] = tk.DISABLED

        self.funcfitscalelabel = tk.Label(self.subframeright3, text = 'Fit Func. Width', bg = '#E4E4E4')
        self.funcfitscalelabel['font'] = ("Roboto",int(0.0075*self.master.winfo_width()))
        self.funcfitscalelabel.place(in_ = self.subframeright3,relwidth = 0.3, relx = 0.022, rely=0.80)
        self.funcfitscalelabelvalue = tk.Label(self.subframeright3, text = '2.0', bg = '#E4E4E4')
        self.funcfitscalelabelvalue['font'] = ("Roboto",int(0.009*self.master.winfo_width()))
        self.funcfitscalelabelvalue.place(in_ = self.subframeright3, relx = 0.55, rely=0.80)
        self.funcfitwidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.funcfitslider, showvalue = False, variable = self.funcfitwidth[0])
        self.funcfitwidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.80, relheight=0.06)
        self.funcfitwidthscale['width'] = 0.025*self.master.winfo_width()
        self.funcfitwidthscale['state'] = tk.DISABLED

        self.markeroption = tk.StringVar()
        self.markeroptiontranslater = []

        self.lineoption = tk.StringVar()
        self.lineoptiontranslater = []

        self.erroroption = tk.StringVar()
        self.erroroptiontranslater = []

        self.funcplotoption = tk.StringVar()
        self.funcplotoptiontranslater = []

        self.funcfitoption = tk.StringVar()
        self.funcfitoptiontranslater = []

        self.markersizecombo = ttk.Combobox(self.subframeright3, values=[
            'Triangle', 'Square', 'Circle', 'Star', 'Diamond', 'X'], textvariable = self.markeroption)
        self.markersizecombo.current(2)
        self.markersizecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.64, relheight=0.065)
        self.markersizecombo.bind("<<ComboboxSelected>>", self.markerselector)
        self.markeroptiontranslater.append('o')

        self.linestylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.lineoption)
        self.linestylecombo.current(0)
        self.linestylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.56, relheight=0.065)
        self.linestylecombo.bind("<<ComboboxSelected>>", self.lineselector)
        self.lineoptiontranslater.append('-')

        self.funcplotstylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.funcplotoption)
        self.funcplotstylecombo.current(0)
        self.funcplotstylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.72, relheight=0.065)
        self.funcplotstylecombo.bind("<<ComboboxSelected>>", self.funcplotselector)
        self.funcplotoptiontranslater.append('-')

        self.funcfitstylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.funcfitoption)
        self.funcfitstylecombo.current(0)
        self.funcfitstylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.8, relheight=0.065)
        self.funcfitstylecombo.bind("<<ComboboxSelected>>", self.funcfitselector)
        self.funcfitoptiontranslater.append('-')

        sty = ttk.Style(self.subframeright3)
        sty.configure("TSeparator", background="#F21112")

        self.chisqlabel = tk.Label(self.frameright, text = u'\u03C7'+'\N{SUPERSCRIPT TWO}'+'/'+'\u03BD', bg='#E4E4E4')
        self.chisqlabel.place(rely=0.46, relx = 0.7)
        self.chisqentry = tk.Entry(self.frameright, justify='center')
        self.r2label = tk.Label(self.frameright, text=u'R\u00B2', bg='#E4E4E4')
        self.r2label.place(rely=0.46, relx=0.2)
        self.r2entry = tk.Entry(self.frameright, justify='center')
        try: self.chisqentry.insert(0, "{0:.3e}".format(self.fit_chi[self.selecteddataset]))
        except: pass
        try: self.r2entry.insert(0, "{0:.6e}".format(self.fit_chi[self.selecteddataset]))
        except: pass
        self.chisqentry.place(rely = 0.46, relx=0.75, relwidth=0.08)
        self.chisqentry.config(state = 'readonly')
        self.r2entry.place(rely=0.46, relx=0.24, relwidth=0.08)
        self.r2entry.config(state='readonly')

        sep = ttk.Separator(self.subframeright3, orient = tk.VERTICAL)
        sep.place(in_ = self.subframeright3, relx=0.5, relheight = 0.5, rely=0.05)

        sep1 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep1.place(in_ = self.subframeright3, relx=0.3, rely=0.05, relwidth = 0.4)

        sep2 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframeright3, relx=0, rely=0.05, relwidth = 0.2)

        sep2 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL )
        sep2.place(in_ = self.subframeright3, relx=0.8, rely=0.05, relwidth = 0.2)

        sep3 = ttk.Separator(self.subframeright3, orient = tk.HORIZONTAL)
        sep3.place(in_ = self.subframeright3, relx=0, rely=0.55, relwidth=1)

        # Criação do texto respetivo ao primeiro dataset
        # A variável datasettext contém os textos presentes em cada dataset
        self.datasettext = []
        self.datasettext.append("0.000000 0.200000 -4.220083 5.000000\n0.040080 0.200000 20.306079 5.000000\n0.080160 0.200000 29.509556 5.000000\n0.120240 0.200000 48.493836 5.000000\n0.160321 0.200000 68.609105 5.000000\n0.200401 0.200000 73.976780 5.000000\n0.240481 0.200000 90.348206 5.000000\n0.280561 0.200000 107.429971 5.000000\n0.320641 0.200000 108.084140 5.000000\n0.360721 0.200000 127.051755 5.000000\n0.400802 0.200000 134.937988 5.000000\n0.440882 0.200000 129.461255 5.000000\n0.480962 0.200000 150.258016 5.000000\n0.521042 0.200000 156.667045 5.000000\n0.561122 0.200000 172.252046 5.000000\n0.601202 0.200000 163.602874 5.000000\n0.641283 0.200000 171.550207 5.000000\n0.681363 0.200000 163.741960 5.000000\n0.721443 0.200000 173.751143 5.000000\n0.761523 0.200000 168.647742 5.000000\n0.801603 0.200000 170.747842 5.000000\n0.841683 0.200000 170.096170 5.000000\n0.881764 0.200000 160.471599 5.000000\n0.921844 0.200000 150.175606 5.000000\n0.961924 0.200000 152.733786 5.000000\n1.002004 0.200000 143.121698 5.000000\n1.042084 0.200000 146.264532 5.000000\n1.082164 0.200000 127.527399 5.000000\n1.122244 0.200000 119.731893 5.000000\n1.162325 0.200000 109.983294 5.000000\n1.202405 0.200000 107.143773 5.000000\n1.242485 0.200000 95.094167 5.000000\n1.282565 0.200000 92.440938 5.000000\n1.322645 0.200000 83.966296 5.000000\n1.362725 0.200000 66.828702 5.000000\n1.402806 0.200000 52.931513 5.000000\n1.442886 0.200000 36.324946 5.000000\n1.482966 0.200000 29.922973 5.000000\n1.523046 0.200000 7.976208 5.000000\n1.563126 0.200000 1.489428 5.000000\n1.603206 0.200000 -9.195030 5.000000\n1.643287 0.200000 -23.532098 5.000000\n1.683367 0.200000 -25.749417 5.000000\n1.723447 0.200000 -35.118530 5.000000\n1.763527 0.200000 -55.796327 5.000000\n1.803607 0.200000 -68.857647 5.000000\n1.843687 0.200000 -70.314311 5.000000\n1.883768 0.200000 -86.585397 5.000000\n1.923848 0.200000 -94.812446 5.000000\n1.963928 0.200000 -92.395743 5.000000\n2.004008 0.200000 -100.446687 5.000000\n2.044088 0.200000 -106.587079 5.000000\n2.084168 0.200000 -112.562231 5.000000\n2.124248 0.200000 -108.020072 5.000000\n2.164329 0.200000 -115.267282 5.000000\n2.204409 0.200000 -122.261355 5.000000\n2.244489 0.200000 -116.516333 5.000000\n2.284569 0.200000 -128.890452 5.000000\n2.324649 0.200000 -129.017330 5.000000\n2.364729 0.200000 -119.878573 5.000000\n2.404810 0.200000 -128.626340 5.000000\n2.444890 0.200000 -129.201100 5.000000\n2.484970 0.200000 -118.233865 5.000000\n2.525050 0.200000 -108.107293 5.000000\n2.565130 0.200000 -111.984111 5.000000\n2.605210 0.200000 -102.305572 5.000000\n2.645291 0.200000 -100.950003 5.000000\n2.685371 0.200000 -95.231812 5.000000\n2.725451 0.200000 -79.889093 5.000000\n2.765531 0.200000 -78.113814 5.000000\n2.805611 0.200000 -63.122766 5.000000\n2.845691 0.200000 -62.347123 5.000000\n2.885772 0.200000 -57.464439 5.000000\n2.925852 0.200000 -50.095949 5.000000\n2.965932 0.200000 -28.707316 5.000000\n3.006012 0.200000 -25.857203 5.000000\n3.046092 0.200000 -9.977920 5.000000\n3.086172 0.200000 -17.829600 5.000000\n3.126253 0.200000 -5.207881 5.000000\n3.166333 0.200000 3.204056 5.000000\n3.206413 0.200000 28.687108 5.000000\n3.246493 0.200000 27.405625 5.000000\n3.286573 0.200000 33.953569 5.000000\n3.326653 0.200000 36.077991 5.000000\n3.366733 0.200000 40.915877 5.000000\n3.406814 0.200000 52.547911 5.000000\n3.446894 0.200000 44.613076 5.000000\n3.486974 0.200000 68.303123 5.000000\n3.527054 0.200000 79.331374 5.000000\n3.567134 0.200000 80.976405 5.000000\n3.607214 0.200000 81.713514 5.000000\n3.647295 0.200000 78.158750 5.000000\n3.687375 0.200000 93.019663 5.000000\n3.727455 0.200000 86.270143 5.000000\n3.767535 0.200000 88.670332 5.000000\n3.807615 0.200000 92.136118 5.000000\n3.847695 0.200000 93.761178 5.000000\n3.887776 0.200000 88.573773 5.000000\n3.927856 0.200000 94.170806 5.000000\n3.967936 0.200000 86.460671 5.000000\n4.008016 0.200000 94.492714 5.000000\n4.048096 0.200000 90.596259 5.000000\n4.088176 0.200000 87.304429 5.000000\n4.128257 0.200000 87.532433 5.000000\n4.168337 0.200000 72.274535 5.000000\n4.208417 0.200000 66.245807 5.000000\n4.248497 0.200000 73.091925 5.000000\n4.288577 0.200000 60.468736 5.000000\n4.328657 0.200000 60.017482 5.000000\n4.368737 0.200000 58.271275 5.000000\n4.408818 0.200000 45.748794 5.000000\n4.448898 0.200000 40.314987 5.000000\n4.488978 0.200000 49.452884 5.000000\n4.529058 0.200000 26.422226 5.000000\n4.569138 0.200000 22.944044 5.000000\n4.609218 0.200000 16.095398 5.000000\n4.649299 0.200000 12.753866 5.000000\n4.689379 0.200000 6.909262 5.000000\n4.729459 0.200000 1.212596 5.000000\n4.769539 0.200000 3.055895 5.000000\n4.809619 0.200000 -14.751589 5.000000\n4.849699 0.200000 -20.025156 5.000000\n4.889780 0.200000 -31.446377 5.000000\n4.929860 0.200000 -31.690325 5.000000\n4.969940 0.200000 -40.431643 5.000000\n5.010020 0.200000 -33.717315 5.000000\n5.050100 0.200000 -43.198812 5.000000\n5.090180 0.200000 -45.091974 5.000000\n5.130261 0.200000 -54.723450 5.000000\n5.170341 0.200000 -52.448394 5.000000\n5.210421 0.200000 -54.470856 5.000000\n5.250501 0.200000 -66.779061 5.000000\n5.290581 0.200000 -67.979157 5.000000\n5.330661 0.200000 -66.643499 5.000000\n5.370741 0.200000 -72.572019 5.000000\n5.410822 0.200000 -65.619787 5.000000\n5.450902 0.200000 -70.286317 5.000000\n5.490982 0.200000 -66.983429 5.000000\n5.531062 0.200000 -66.396522 5.000000\n5.571142 0.200000 -58.528374 5.000000\n5.611222 0.200000 -63.276543 5.000000\n5.651303 0.200000 -57.647651 5.000000\n5.691383 0.200000 -58.155591 5.000000\n5.731463 0.200000 -59.947225 5.000000\n5.771543 0.200000 -56.605605 5.000000\n5.811623 0.200000 -48.498689 5.000000\n5.851703 0.200000 -44.906405 5.000000\n5.891784 0.200000 -35.595236 5.000000\n5.931864 0.200000 -36.182548 5.000000\n5.971944 0.200000 -35.946789 5.000000\n6.012024 0.200000 -26.033401 5.000000\n6.052104 0.200000 -21.916403 5.000000\n6.092184 0.200000 -18.744021 5.000000\n6.132265 0.200000 -19.034690 5.000000\n6.172345 0.200000 -3.464158 5.000000\n6.212425 0.200000 -9.989100 5.000000\n6.252505 0.200000 -18.031833 5.000000\n6.292585 0.200000 -0.473183 5.000000\n6.332665 0.200000 7.128211 5.000000\n6.372745 0.200000 10.383434 5.000000\n6.412826 0.200000 8.963351 5.000000\n6.452906 0.200000 17.957149 5.000000\n6.492986 0.200000 18.615820 5.000000\n6.533066 0.200000 28.568868 5.000000\n6.573146 0.200000 36.890251 5.000000\n6.613226 0.200000 28.441762 5.000000\n6.653307 0.200000 37.849841 5.000000\n6.693387 0.200000 32.059030 5.000000\n6.733467 0.200000 28.204411 5.000000\n6.773547 0.200000 48.291845 5.000000\n6.813627 0.200000 50.102458 5.000000\n6.853707 0.200000 42.508948 5.000000\n6.893788 0.200000 46.535820 5.000000\n6.933868 0.200000 48.448955 5.000000\n6.973948 0.200000 55.769351 5.000000\n7.014028 0.200000 54.062273 5.000000\n7.054108 0.200000 49.087978 5.000000\n7.094188 0.200000 57.951041 5.000000\n7.134269 0.200000 46.272647 5.000000\n7.174349 0.200000 47.668543 5.000000\n7.214429 0.200000 46.921758 5.000000\n7.254509 0.200000 42.871597 5.000000\n7.294589 0.200000 38.610888 5.000000\n7.334669 0.200000 39.815706 5.000000\n7.374749 0.200000 37.159121 5.000000\n7.414830 0.200000 31.996323 5.000000\n7.454910 0.200000 38.671490 5.000000\n7.494990 0.200000 30.193041 5.000000\n7.535070 0.200000 24.469951 5.000000\n7.575150 0.200000 27.829150 5.000000\n7.615230 0.200000 14.374572 5.000000\n7.655311 0.200000 18.588095 5.000000\n7.695391 0.200000 19.879006 5.000000\n7.735471 0.200000 14.032910 5.000000\n7.775551 0.200000 4.663582 5.000000\n7.815631 0.200000 -2.575609 5.000000\n7.855711 0.200000 -1.598550 5.000000\n7.895792 0.200000 -2.158824 5.000000\n7.935872 0.200000 -7.086892 5.000000\n7.975952 0.200000 -14.662059 5.000000\n8.016032 0.200000 -21.428117 5.000000\n8.056112 0.200000 -15.659874 5.000000\n8.096192 0.200000 -20.559999 5.000000\n8.136273 0.200000 -21.496457 5.000000\n8.176353 0.200000 -15.018610 5.000000\n8.216433 0.200000 -27.698434 5.000000\n8.256513 0.200000 -24.037836 5.000000\n8.296593 0.200000 -31.816119 5.000000\n8.336673 0.200000 -32.542239 5.000000\n8.376754 0.200000 -41.213083 5.000000\n8.416834 0.200000 -33.509833 5.000000\n8.456914 0.200000 -37.619873 5.000000\n8.496994 0.200000 -27.887921 5.000000\n8.537074 0.200000 -31.248875 5.000000\n8.577154 0.200000 -37.039771 5.000000\n8.617234 0.200000 -33.194420 5.000000\n8.657315 0.200000 -35.690008 5.000000\n8.697395 0.200000 -26.343880 5.000000\n8.737475 0.200000 -35.840091 5.000000\n8.777555 0.200000 -19.936502 5.000000\n8.817635 0.200000 -33.370277 5.000000\n8.857715 0.200000 -32.042716 5.000000\n8.897796 0.200000 -26.828380 5.000000\n8.937876 0.200000 -34.670138 5.000000\n8.977956 0.200000 -30.877291 5.000000\n9.018036 0.200000 -28.066351 5.000000\n9.058116 0.200000 -16.888626 5.000000\n9.098196 0.200000 -21.047476 5.000000\n9.138277 0.200000 -16.292002 5.000000\n9.178357 0.200000 -21.978134 5.000000\n9.218437 0.200000 -10.110033 5.000000\n9.258517 0.200000 -7.966969 5.000000\n9.298597 0.200000 -14.467292 5.000000\n9.338677 0.200000 -9.640137 5.000000\n9.378758 0.200000 -7.084470 5.000000\n9.418838 0.200000 -1.477334 5.000000\n9.458918 0.200000 0.219948 5.000000\n9.498998 0.200000 2.325002 5.000000\n9.539078 0.200000 6.512176 5.000000\n9.579158 0.200000 5.541867 5.000000\n9.619238 0.200000 11.372225 5.000000\n9.659319 0.200000 13.947301 5.000000\n9.699399 0.200000 13.590980 5.000000\n9.739479 0.200000 13.216626 5.000000\n9.779559 0.200000 16.390693 5.000000\n9.819639 0.200000 27.023087 5.000000\n9.859719 0.200000 17.697813 5.000000\n9.899800 0.200000 27.454231 5.000000\n9.939880 0.200000 23.537202 5.000000\n9.979960 0.200000 23.818608 5.000000\n10.020040 0.200000 14.047478 5.000000\n10.060120 0.200000 32.127949 5.000000\n10.100200 0.200000 24.409514 5.000000\n10.140281 0.200000 23.204936 5.000000\n10.180361 0.200000 26.134774 5.000000\n10.220441 0.200000 27.358767 5.000000\n10.260521 0.200000 20.644017 5.000000\n10.300601 0.200000 21.998389 5.000000\n10.340681 0.200000 17.857595 5.000000\n10.380762 0.200000 21.323762 5.000000\n10.420842 0.200000 20.252274 5.000000\n10.460922 0.200000 19.224765 5.000000\n10.501002 0.200000 16.624415 5.000000\n10.541082 0.200000 19.284652 5.000000\n10.581162 0.200000 27.722624 5.000000\n10.621242 0.200000 10.830659 5.000000\n10.661323 0.200000 18.016111 5.000000\n10.701403 0.200000 12.131010 5.000000\n10.741483 0.200000 25.532536 5.000000\n10.781563 0.200000 0.247603 5.000000\n10.821643 0.200000 6.395373 5.000000\n10.861723 0.200000 13.165740 5.000000\n10.901804 0.200000 3.000769 5.000000\n10.941884 0.200000 2.168944 5.000000\n10.981964 0.200000 3.228704 5.000000\n11.022044 0.200000 -1.992237 5.000000\n11.062124 0.200000 0.717827 5.000000\n11.102204 0.200000 -2.348446 5.000000\n11.142285 0.200000 -8.534931 5.000000\n11.182365 0.200000 -6.482811 5.000000\n11.222445 0.200000 -12.571645 5.000000\n11.262525 0.200000 -10.239189 5.000000\n11.302605 0.200000 -23.445802 5.000000\n11.342685 0.200000 -9.620284 5.000000\n11.382766 0.200000 -9.469368 5.000000\n11.422846 0.200000 -14.469548 5.000000\n11.462926 0.200000 -16.057060 5.000000\n11.503006 0.200000 -15.463553 5.000000\n11.543086 0.200000 -29.203668 5.000000\n11.583166 0.200000 -21.897996 5.000000\n11.623246 0.200000 -19.576155 5.000000\n11.663327 0.200000 -9.354795 5.000000\n11.703407 0.200000 -11.857799 5.000000\n11.743487 0.200000 -18.484859 5.000000\n11.783567 0.200000 -17.001798 5.000000\n11.823647 0.200000 -20.839559 5.000000\n11.863727 0.200000 -10.625569 5.000000\n11.903808 0.200000 -12.561239 5.000000\n11.943888 0.200000 -10.337802 5.000000\n11.983968 0.200000 -20.437828 5.000000\n12.024048 0.200000 -21.202328 5.000000\n12.064128 0.200000 -20.814618 5.000000\n12.104208 0.200000 -9.093745 5.000000\n12.144289 0.200000 -10.776351 5.000000\n12.184369 0.200000 -14.682031 5.000000\n12.224449 0.200000 -15.557082 5.000000\n12.264529 0.200000 -8.452130 5.000000\n12.304609 0.200000 -5.284851 5.000000\n12.344689 0.200000 -6.043369 5.000000\n12.384770 0.200000 -8.505228 5.000000\n12.424850 0.200000 -3.082345 5.000000\n12.464930 0.200000 2.547971 5.000000\n12.505010 0.200000 3.798123 5.000000\n12.545090 0.200000 9.212148 5.000000\n12.585170 0.200000 -1.805794 5.000000\n12.625251 0.200000 7.187777 5.000000\n12.665331 0.200000 3.731835 5.000000\n12.705411 0.200000 9.221259 5.000000\n12.745491 0.200000 -7.587803 5.000000\n12.785571 0.200000 14.854788 5.000000\n12.825651 0.200000 1.033444 5.000000\n12.865731 0.200000 10.726527 5.000000\n12.905812 0.200000 15.855602 5.000000\n12.945892 0.200000 9.741655 5.000000\n12.985972 0.200000 12.129298 5.000000\n13.026052 0.200000 6.866070 5.000000\n13.066132 0.200000 13.327839 5.000000\n13.106212 0.200000 22.548522 5.000000\n13.146293 0.200000 12.441904 5.000000\n13.186373 0.200000 14.290439 5.000000\n13.226453 0.200000 18.981131 5.000000\n13.266533 0.200000 14.088621 5.000000\n13.306613 0.200000 18.580735 5.000000\n13.346693 0.200000 5.400956 5.000000\n13.386774 0.200000 13.922285 5.000000\n13.426854 0.200000 12.228760 5.000000\n13.466934 0.200000 14.367235 5.000000\n13.507014 0.200000 10.069593 5.000000\n13.547094 0.200000 9.403623 5.000000\n13.587174 0.200000 10.807500 5.000000\n13.627255 0.200000 8.994746 5.000000\n13.667335 0.200000 17.059241 5.000000\n13.707415 0.200000 5.944681 5.000000\n13.747495 0.200000 14.293543 5.000000\n13.787575 0.200000 11.252237 5.000000\n13.827655 0.200000 16.805709 5.000000\n13.867735 0.200000 4.094287 5.000000\n13.907816 0.200000 5.383987 5.000000\n13.947896 0.200000 12.449402 5.000000\n13.987976 0.200000 7.040040 5.000000\n14.028056 0.200000 2.234196 5.000000\n14.068136 0.200000 6.228159 5.000000\n14.108216 0.200000 -1.072208 5.000000\n14.148297 0.200000 -5.193341 5.000000\n14.188377 0.200000 -4.510789 5.000000\n14.228457 0.200000 -3.619780 5.000000\n14.268537 0.200000 4.591740 5.000000\n14.308617 0.200000 -5.416248 5.000000\n14.348697 0.200000 -1.694420 5.000000\n14.388778 0.200000 -0.238606 5.000000\n14.428858 0.200000 -2.555457 5.000000\n14.468938 0.200000 -4.215943 5.000000\n14.509018 0.200000 -2.086985 5.000000\n14.549098 0.200000 -8.206409 5.000000\n14.589178 0.200000 -6.998627 5.000000\n14.629259 0.200000 -11.455970 5.000000\n14.669339 0.200000 -8.796179 5.000000\n14.709419 0.200000 -4.568559 5.000000\n14.749499 0.200000 -9.766033 5.000000\n14.789579 0.200000 -14.257980 5.000000\n14.829659 0.200000 -8.425578 5.000000\n14.869739 0.200000 -21.594720 5.000000\n14.909820 0.200000 -6.706730 5.000000\n14.949900 0.200000 -22.397763 5.000000\n14.989980 0.200000 -14.721651 5.000000\n15.030060 0.200000 -6.735613 5.000000\n15.070140 0.200000 -6.340337 5.000000\n15.110220 0.200000 -2.445827 5.000000\n15.150301 0.200000 -9.874866 5.000000\n15.190381 0.200000 -1.413741 5.000000\n15.230461 0.200000 -8.766435 5.000000\n15.270541 0.200000 -5.677615 5.000000\n15.310621 0.200000 -3.008112 5.000000\n15.350701 0.200000 -2.927042 5.000000\n15.390782 0.200000 -13.984512 5.000000\n15.430862 0.200000 -5.995535 5.000000\n15.470942 0.200000 -14.618264 5.000000\n15.511022 0.200000 0.097088 5.000000\n15.551102 0.200000 -13.189818 5.000000\n15.591182 0.200000 0.355034 5.000000\n15.631263 0.200000 0.784178 5.000000\n15.671343 0.200000 0.266240 5.000000\n15.711423 0.200000 -2.829156 5.000000\n15.751503 0.200000 -0.311902 5.000000\n15.791583 0.200000 0.066581 5.000000\n15.831663 0.200000 -2.041654 5.000000\n15.871743 0.200000 5.305573 5.000000\n15.911824 0.200000 5.302848 5.000000\n15.951904 0.200000 5.252021 5.000000\n15.991984 0.200000 -2.231145 5.000000\n16.032064 0.200000 1.885515 5.000000\n16.072144 0.200000 6.379447 5.000000\n16.112224 0.200000 6.896192 5.000000\n16.152305 0.200000 8.838547 5.000000\n16.192385 0.200000 6.327971 5.000000\n16.232465 0.200000 6.743566 5.000000\n16.272545 0.200000 4.314842 5.000000\n16.312625 0.200000 4.302374 5.000000\n16.352705 0.200000 0.469928 5.000000\n16.392786 0.200000 7.795278 5.000000\n16.432866 0.200000 10.292563 5.000000\n16.472946 0.200000 1.007937 5.000000\n16.513026 0.200000 7.731705 5.000000\n16.553106 0.200000 8.774526 5.000000\n16.593186 0.200000 3.301125 5.000000\n16.633267 0.200000 5.489381 5.000000\n16.673347 0.200000 11.807418 5.000000\n16.713427 0.200000 6.936980 5.000000\n16.753507 0.200000 10.544944 5.000000\n16.793587 0.200000 3.398610 5.000000\n16.833667 0.200000 -1.275229 5.000000\n16.873747 0.200000 10.642082 5.000000\n16.913828 0.200000 1.769257 5.000000\n16.953908 0.200000 3.303666 5.000000\n16.993988 0.200000 0.219273 5.000000\n17.034068 0.200000 11.769642 5.000000\n17.074148 0.200000 -10.607201 5.000000\n17.114228 0.200000 -1.017754 5.000000\n17.154309 0.200000 2.763988 5.000000\n17.194389 0.200000 -1.423901 5.000000\n17.234469 0.200000 5.356608 5.000000\n17.274549 0.200000 6.227375 5.000000\n17.314629 0.200000 6.759017 5.000000\n17.354709 0.200000 5.116336 5.000000\n17.394790 0.200000 1.193953 5.000000\n17.434870 0.200000 0.091315 5.000000\n17.474950 0.200000 -6.167816 5.000000\n17.515030 0.200000 -7.607873 5.000000\n17.555110 0.200000 -6.554534 5.000000\n17.595190 0.200000 -8.763374 5.000000\n17.635271 0.200000 -9.999903 5.000000\n17.675351 0.200000 1.444506 5.000000\n17.715431 0.200000 -2.940430 5.000000\n17.755511 0.200000 -2.074974 5.000000\n17.795591 0.200000 -4.999610 5.000000\n17.835671 0.200000 -8.447734 5.000000\n17.875752 0.200000 -9.219865 5.000000\n17.915832 0.200000 -0.884357 5.000000\n17.955912 0.200000 -13.630628 5.000000\n17.995992 0.200000 -3.362859 5.000000\n18.036072 0.200000 -2.861015 5.000000\n18.076152 0.200000 0.459927 5.000000\n18.116232 0.200000 2.075756 5.000000\n18.156313 0.200000 1.742471 5.000000\n18.196393 0.200000 -4.681144 5.000000\n18.236473 0.200000 -11.362966 5.000000\n18.276553 0.200000 -10.926193 5.000000\n18.316633 0.200000 -3.513967 5.000000\n18.356713 0.200000 4.763483 5.000000\n18.396794 0.200000 -2.458590 5.000000\n18.436874 0.200000 -4.460571 5.000000\n18.476954 0.200000 -8.472226 5.000000\n18.517034 0.200000 -18.139443 5.000000\n18.557114 0.200000 -3.079748 5.000000\n18.597194 0.200000 2.546519 5.000000\n18.637275 0.200000 5.423287 5.000000\n18.677355 0.200000 -4.911763 5.000000\n18.717435 0.200000 -0.456041 5.000000\n18.757515 0.200000 1.675098 5.000000\n18.797595 0.200000 2.913273 5.000000\n18.837675 0.200000 -1.921587 5.000000\n18.877756 0.200000 -2.727984 5.000000\n18.917836 0.200000 8.666047 5.000000\n18.957916 0.200000 0.215012 5.000000\n18.997996 0.200000 2.999787 5.000000\n19.038076 0.200000 5.302385 5.000000\n19.078156 0.200000 1.706727 5.000000\n19.118236 0.200000 -0.960444 5.000000\n19.158317 0.200000 -2.947608 5.000000\n19.198397 0.200000 8.699859 5.000000\n19.238477 0.200000 3.165915 5.000000\n19.278557 0.200000 2.699166 5.000000\n19.318637 0.200000 7.007208 5.000000\n19.358717 0.200000 1.366691 5.000000\n19.398798 0.200000 5.806320 5.000000\n19.438878 0.200000 5.205500 5.000000\n19.478958 0.200000 6.384510 5.000000\n19.519038 0.200000 2.091265 5.000000\n19.559118 0.200000 1.740590 5.000000\n19.599198 0.200000 -1.249371 5.000000\n19.639279 0.200000 13.168858 5.000000\n19.679359 0.200000 6.457068 5.000000\n19.719439 0.200000 -2.875295 5.000000\n19.759519 0.200000 6.103446 5.000000\n19.799599 0.200000 2.828744 5.000000\n19.839679 0.200000 8.695443 5.000000\n19.879760 0.200000 -1.042130 5.000000\n19.919840 0.200000 1.382902 5.000000\n19.959920 0.200000 5.380195 5.000000\n20.000000 0.200000 4.680706 5.000000")

        self.datalistvariable = tk.StringVar()

        # Variável que mostra qual está selecionada
        self.datalistvariable.set('dataset 1')

        # Variável que contem os datasets e respetivo numero
        self.datalist = ['dataset 1']

        # Criação do botão seletor de data-sets, ligalo à função update_databox
        self.datasetselector = ttk.Combobox(self.plotbuttonframe, textvariable = self.datalistvariable, values = self.datalist, postcommand = self.update_combobox_values)
        self.datasetselector.place(relx = 0, relheight = 1, relwidth=0.15)
        self.datasetselector.bind("<<ComboboxSelected>>", self.update_databox)

        # Criação da caixa que contem os dados, inserção do texto referente ao primeiro dataset na mesma
        self.dataentry = (ScrolledText(self.subframeleft2))
        self.dataentry.pack(expand = 1, fill = tk.X)
        self.dataentry.insert(tk.INSERT,self.datasettext[0])

        # Basicamente a lógica é isto começar com alguma coisa pq fode com indices dps, soluçao preguicosa
        # é darlhe os valores do textinho default
        self.abcissas = [[0, 0, 0, 0]]
        self.erabcissas = [[0, 0, 0, 0]]
        self.ordenadas = [[0, 0, 0, 0]]
        self.erordenadas = [[0, 0, 0, 0]]

        self.abc=[[]]
        self.erabc = [[]]
        self.ord = [[]]
        self.erord = [[]]

        self.selecteddataset = 0
        self.numberdatasets = 1

        self.abc.append(np.array(self.abcissas[0]))
        self.erabc.append(np.array(self.erabcissas[0]))
        self.ord.append(np.array(self.erabcissas[0]))
        self.erord.append(np.array(self.erabcissas[0]))

        self.dataset_points = []
        self.update_parameter()

    def markerselector(self,event):
        if(self.markeroption.get() == 'Circle'):
            self.markeroptiontranslater[self.selecteddataset] = 'o'

        if(self.markeroption.get() == 'Square'):
            self.markeroptiontranslater[self.selecteddataset] = 's'

        if(self.markeroption.get() == 'Triangle'):
            self.markeroptiontranslater[self.selecteddataset] = '^'

        if self.markeroption.get() == 'Star':
            self.markeroptiontranslater[self.selecteddataset] = '*'

        if self.markeroption.get() == 'Diamond':
            self.markeroptiontranslater[self.selecteddataset] = 'D'
        if self.markeroption.get() == 'X':
            self.markeroptiontranslater[self.selecteddataset] = 'x'

        self.plot_dataset()

    def lineselector(self,event):
        if self.lineoption.get() == 'Solid':
            self.lineoptiontranslater[self.selecteddataset] = '-'

        if self.lineoption.get() == 'Dashed':
            self.lineoptiontranslater[self.selecteddataset] = '--'

        if self.lineoption.get() == 'Dotted':
            self.lineoptiontranslater[self.selecteddataset] = ':'

        if self.lineoption.get() == 'DashDot':
            self.lineoptiontranslater[self.selecteddataset] = '-.'

        self.plot_dataset()

    def funcplotselector(self,event):
        if self.funcplotoption.get() == 'Solid':
            self.funcplotoptiontranslater[self.selecteddataset] = '-'

        if self.funcplotoption.get() == 'Dashed':
            self.funcplotoptiontranslater[self.selecteddataset] = '--'

        if self.funcplotoption.get() == 'Dotted':
            self.funcplotoptiontranslater[self.selecteddataset] = ':'

        if self.funcplotoption.get() == 'DashDot':
            self.funcplotoptiontranslater[self.selecteddataset] = '-.'

        self.plot_dataset()

    def funcfitselector(self,event):
        if self.funcfitoption.get() == 'Solid':
            self.funcfitoptiontranslater[self.selecteddataset] = '-'

        if self.funcfitoption.get() == 'Dashed':
            self.funcfitoptiontranslater[self.selecteddataset] = '--'

        if self.funcfitoption.get() == 'Dotted':
            self.funcfitoptiontranslater[self.selecteddataset] = ':'

        if self.funcfitoption.get() == 'DashDot':
            self.funcfitoptiontranslater[self.selecteddataset] = '-.'

        self.plot_dataset()

    def update_combobox_values(self):
        if (self.datasetselector.get() in self.datalist) and (self.datasetselector.get() != self.datalist[self.selecteddataset]):
            tk.messagebox.showwarning('REPEATED NAMES','There is already a dataset with the name %s. Use a different one.' % self.datasetselector.get())
            self.datasetselector.set(self.datalist[self.selecteddataset])
        else:
            self.datalist[self.selecteddataset] = self.datasetselector.get()
            self.datasetselector.config(values = self.datalist)

    def restart(self):
        if tk.messagebox.askyesno('START NEW', 'Starting new will erase all progess in your current session. Are you sure you want to start new?'):
            self.create_new()

    def set_ratio(self):
        try:
            self.ratio_window.destroy()
        except:
            pass

        def hover(button):
            return lambda e: button.config(bg='white', fg='#F21112')
        def unhover(button):
            return lambda e: button.config(bg='#F21112', fg='white')

        self.ratio_window = tk.Toplevel(self.master)
        self.ratio_window.title('Figure Ratio')
        self.ratio_window.geometry('500x250')
        self.ratio_window.configure(background='#E4E4E4')
        self.ratio_window.resizable(False,False)

        text = """
        Here you can set the figure ratio for the graph. Keep in mind that the
        actual values you insert don't matter, only the ratio between them, i.e.
        1:1 is the same as 5:5, or 1:5 is the same as 2:10.'
        """
        intro = tk.Label(self.ratio_window,text=text,bg='#E4E4E4',justify='left')
        intro['font'] = ('Roboto', int(15*1000/self.master.winfo_width()))
        intro.pack(side='top')

        frame_ratio = tk.Frame(self.ratio_window, bg='#E4E4E4')

        label1 = tk.Label(frame_ratio,text='Figure Ratio',bg='#E4E4E4',anchor='w')
        label1['font'] = ('Roboto',int(15*1000/self.master.winfo_width()))
        label1.pack(side='left',padx=20)

        self.width_ratio_entry = tk.Entry(frame_ratio,width=4,justify='center')
        self.width_ratio_entry.insert(0, self.width_ratio)
        self.width_ratio_entry.pack(side='left')

        label2 = tk.Label(frame_ratio,text=':',bg='#E4E4E4')
        label2['font'] = ('Roboto',int(15*1000/self.master.winfo_width()))
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
        save_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        save_button.bind("<Enter>", func=lambda e: save_button.config(bg='white',fg='#F21112'))
        save_button.bind("<Leave>", func=lambda e: save_button.config(bg='#F21112',fg='white'))
        save_button.pack(side='top',pady=20)

    def save_ratio(self):
        temp_width = self.width_ratio_entry.get().replace(' ','')
        temp_height = self.height_ratio_entry.get().replace(' ','')

        try:
            float(temp_width)
        except:
            tk.messagebox.showwarning('ERROR','Non-numerical input found ({}) in width entry. Please correct it.'.format(temp_width))
            return

        try:
            float(temp_height)
        except:
            tk.messagebox.showwarning('ERROR','Non-numerical input found ({}) in height entry. Please correct it.'.format(temp_height))
            return

        self.width_ratio = float(temp_width)
        self.height_ratio = float(temp_height)

        self.ratio_window.destroy()

        if not hasattr(self, 'fig'):
            return

        self.plot_dataset()

    def set_ticks(self):
        try:
            self.ticks_window.destroy()
        except:
            pass

        def hover(button):
            return lambda e: button.config(bg='white', fg='#F21112')
        def unhover(button):
            return lambda e: button.config(bg='#F21112', fg='white')

        self.ticks_window = tk.Toplevel(self.master)
        self.ticks_window.title('Ticks Placement')
        self.ticks_window.geometry('500x400')
        self.ticks_window.configure(background='#E4E4E4')
        self.ticks_window.resizable(False,False)

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
        intro["font"] = ("Roboto",int(15*1000/self.master.winfo_width()))
        intro.pack(side='top')

        frame_x = tk.Frame(self.ticks_window,bg='#E4E4E4')

        x_axis = tk.Label(frame_x,text='X-Axis',bg='#E4E4E4',anchor='w')
        x_axis['font'] = ('Roboto', int(15*1000/self.master.winfo_width()))
        x_axis.pack(side='left',padx=20)

        self.x_ticks = tk.Entry(frame_x,width=50)
        x_content = ''
        for val in self.x_ticks_ref:
            x_content += '{0:.2f} '.format(val)
        self.x_ticks.insert(0, x_content)
        self.x_ticks.pack(side='right',padx=20)

        frame_x.pack(side='top',pady=20)

        frame_y = tk.Frame(self.ticks_window,bg='#E4E4E4')

        y_axis = tk.Label(frame_y,text='Y-Axis',bg='#E4E4E4',anchor='w')
        y_axis['font'] = ('Roboto', int(15*1000/self.master.winfo_width()))
        y_axis.pack(side='left',padx=20)

        self.y_ticks = tk.Entry(frame_y,width=50)
        y_content = ''
        for val in self.y_ticks_ref:
            y_content += '{0:.2f} '.format(val)
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
        save_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        save_button.bind("<Enter>", func=lambda e: save_button.config(bg='white',fg='#F21112'))
        save_button.bind("<Leave>", func=lambda e: save_button.config(bg='#F21112',fg='white'))
        save_button.pack(side='top',pady=20)

    def save_ticks(self):
        x_temp = [val for val in self.x_ticks.get().replace(',',' ').split(' ') if val]
        y_temp = [val for val in self.y_ticks.get().replace(',',' ').split(' ') if val]

        for val in x_temp:
            try:
                float(val)
            except:
                tk.messagebox.showwarning('ERROR','Non-numerical input found in x-axis ticks. Please correct it.')
                return
        for val in y_temp:
            try:
                float(val)
            except:
                tk.messagebox.showwarning('ERROR','Non-numerical input found in y-axis ticks. Please correct it.')
                return

        self.x_ticks_ref = [float(val) for val in x_temp]
        self.y_ticks_ref = [float(val) for val in y_temp]

        if len(self.x_ticks_ref) > 1:
            self.xaxistickspentry.config(state='disabled')
        else:
            self.xaxistickspentry.config(state='normal')

        if len(self.y_ticks_ref) > 1:
            self.yaxistickspentry.config(state='disabled')
        else:
            self.yaxistickspentry.config(state='normal')

        self.ticks_window.destroy()

    def text(self):
        try:
            self.text_window.destroy()
        except:
            pass

        def hover(button):
            return lambda e: button.config(bg='white',fg='#F21112')
        def unhover(button):
            return lambda e: button.config(bg='#F21112',fg='white')

        self.text_window = tk.Toplevel(self.master)
        self.text_window.title('Add Text')
        self.text_window.geometry('1000x600')
        self.text_window.configure(background='#E4E4E4')
        self.text_window.resizable(False,False)

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
        pos["font"] = ("Roboto",int(15*1000/self.master.winfo_width()))
        pos.pack(side='top')

        for i in range(len(self.plot_text)):
            frame = tk.Frame(scrollable_frame,bg='#E4E4E4')

            self.text_entries.append(tk.Entry(frame,width=60))
            self.text_entries[i].insert(0,self.plot_text[i])

            label = tk.Label(frame, text='Text %d' % (i+1),bg='#E4E4E4')
            label["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

            x_label = tk.Label(frame, text='x', bg='#E4E4E4')
            x_label["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

            self.x_entries.append(tk.Entry(frame,width=7))
            self.x_entries[i].insert(0,self.text_pos[i][0])

            y_label = tk.Label(frame, text='y', bg='#E4E4E4')
            y_label["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

            self.y_entries.append(tk.Entry(frame,width=7))
            self.y_entries[i].insert(0,self.text_pos[i][1])

            font_label = tk.Label(frame, text='fontsize', bg='#E4E4E4')
            font_label["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

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
            self.remove_buttons[i]["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
            # Alterar as cores quando entra e sai
            self.remove_buttons[i].bind("<Enter>", hover(self.remove_buttons[i]))
            self.remove_buttons[i].bind("<Leave>", unhover(self.remove_buttons[i]))

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

         # Colocação do botão para salvar as legendas
        frame = tk.Frame(scrollable_frame,bg='#E4E4E4')

        save_button = tk.Button(frame,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_text
        save_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        save_button.bind("<Enter>", func=lambda e: save_button.config(bg='white',fg='#F21112'))
        save_button.bind("<Leave>", func=lambda e: save_button.config(bg='#F21112',fg='white'))
        save_button.pack(side='left',padx=20)

        add_button = tk.Button(frame,
                               text="ADD TEXT",
                               fg='white',
                               bg='#F21112',
                               activebackground='white',
                               activeforeground='#F21112')
        add_button["command"] = self.new_text
        add_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        add_button.bind("<Enter>", func=lambda e: add_button.config(bg='white',fg='#F21112'))
        add_button.bind("<Leave>", func=lambda e: add_button.config(bg='#F21112',fg='white'))
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
                except:
                    tk.messagebox.showwarning('ERROR', 'Non-numerical input found in X position for text %d.' % (i+1))
                    continue
                try:
                    float(self.y_entries[i].get())
                except:
                    tk.messagebox.showwarning('ERROR', 'Non-numerical input found in Y position for text %d.' % (i+1))
                    continue
                try:
                    float(self.fontsize_entries[i].get())
                except:
                    tk.messagebox.showwarning('ERROR', 'Non-numerical input found in fontsize for text %d.' % (i+1))
                    continue
                self.plot_text[i] = self.text_entries[i].get()
                self.text_pos[i] = [float(self.x_entries[i].get()), float(self.y_entries[i].get())]
                self.text_size[i] = float(self.fontsize_entries[i].get())
        self.text_window.destroy()

    def labels(self):
        try:
            self.labels_window.destroy()
        except:
            pass
        self.labels_window = tk.Toplevel(self.master)
        self.labels_window.title('Add Labels')
        self.labels_window.geometry('400x400')
        self.labels_window.configure(background='#E4E4E4')
        self.labels_window.resizable(False,False)

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

        for i in range(len(self.datasettext)):
            frame1 = tk.Frame(scrollable_frame,bg='#E4E4E4')
            frame2 = tk.Frame(scrollable_frame,bg='#E4E4E4')
            frame3 = tk.Frame(scrollable_frame,bg='#E4E4E4')

            self.label_entries.append([tk.Entry(frame1,width=35),
                                       tk.Entry(frame2,width=35),
                                       tk.Entry(frame3,width=35)])

            label1 = tk.Label(frame1, text='Label for Dataset %d' % (i+1),bg='#E4E4E4')
            label1["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
            self.label_entries[i][0].insert(0,self.data_labels[i])
            label1.pack(side='left')
            self.label_entries[i][0].pack(side='right')
            frame1.pack(side='top',pady=10)

            label2 = tk.Label(frame2, text='Label for Plotted Function %d' % (i+1),bg='#E4E4E4')
            label2["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
            self.label_entries[i][1].insert(0,self.plot_labels[i])
            label2.pack(side='left')
            self.label_entries[i][1].pack(side='right')
            frame2.pack(side='top',pady=10)

            label3 = tk.Label(frame3, text='Label for Fitted Function %d' % (i+1),bg='#E4E4E4')
            label3["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
            self.label_entries[i][2].insert(0,self.fit_labels[i])
            label3.pack(side='left')
            self.label_entries[i][2].pack(side='right')
            frame3.pack(side='top',pady=10)

        # Colocação do botão para salvar as legendas
        save_button = tk.Button(scrollable_frame,
                                text="SAVE",
                                fg='white',
                                bg='#F21112',
                                activebackground='white',
                                activeforeground='#F21112')
        save_button["command"] = self.save_labels
        save_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        save_button.bind("<Enter>", func=lambda e: save_button.config(bg='white',fg='#F21112'))
        save_button.bind("<Leave>", func=lambda e: save_button.config(bg='#F21112',fg='white'))
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

    # def save_everything(self):
    #     file = tk.filedialog.asksaveasfilename(filetypes=(("*Text File (.txt)", "*.txt"),),defaultextension='.txt')
    #     if file:
    #         file = open(file, 'w')
    #     else:
    #         return

    #     for text in self.plot_text:
    #         file.write(text)
    #     file.write('\nSECTION\n')
    #     for pos in self.text_pos:
    #         file.write('%s\n' % str(pos[0]))
    #         file.write('%s\n' % str(pos[1]))
    #     for i in range(len(self.datasettext)):
    #         file.write('DATASET\n')
    #         file.write(self.datasettext[i])
    #         file.write('\nSECTION\n')
    #         file.write(self.indeps[i])
    #         file.write('\nSECTION\n')
    #         file.write(self.params[i])
    #         file.write('\nSECTION\n')
    #         file.write(self.functions[i])
    #         file.write('\nSECTION\n')
    #         for value in self.init_values[i]:
    #             file.write('%s\n' % value)
    #         # file.write(self.init_values[i])
    #         file.write('SECTION\n')
    #         for param in self.fit_params[i]:
    #             file.write('%s\n' % param)
    #         # file.write(self.fit_params[i])
    #         file.write('SECTION\n')
    #         for uncert in self.fit_uncert[i]:
    #             file.write('%s\n' % uncert)
    #         # file.write(self.fit_uncert[i])
    #         file.write('SECTION\n')
    #         file.write(str(self.fit_chi[i]))
    #         file.write('\nSECTION\n')
    #         file.write('%s\n' % self.data_labels[i])
    #         file.write('%s\n' % self.plot_labels[i])
    #         file.write('%s\n' % self.fit_labels[i])

    #     file.close()

    # def import_project(self):

    #     file = tk.filedialog.askopenfilename()
    #     if not file:
    #         return
    #     try:
    #         file = open(file, 'r')
    #         data = file.read().split('\nDATASET\n')
    #         print(data)
    #         first = data[0].split('\nSECTION\n')
    #         self.plot_text = [text for text in first[0].split('\n')]
    #         print(first[1].split('\n'))
    #         self.text_pos = [[float(first[1].split('\n')[i]),float(first[1].split('\n')[i+1])] for i in range(0,len(first[1].split('\n')),2)]
    #         self.datasettext = []
    #         for dataset in data[1:]:
    #             split_data = dataset.set('\nSECTION\n')
    #             self.datasettext.append(split_data[0])
    #     except:
    #         tk.showwarning('ERROR','Unable to open. File corrupted.')
    #         return

    def latexify(self):
        try:
            self.export_window.destroy()
        except:
            pass
        self.export_window = tk.Toplevel(self.master)
        self.export_window.title('LaTeX-ify')
        self.export_window.geometry('400x200')
        self.export_window.configure(background='#E4E4E4')
        self.export_window.resizable(False, False)

        # Colocação das várias opções de exportação
        function = tk.Label(self.export_window, text='Fitting Function')
        function["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        function.configure(background='#E4E4E4')

        data_samex = tk.Label(self.export_window, text='Datasets (share x)')
        data_samex["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        data_samex.configure(background='#E4E4E4')

        data_diffx = tk.Label(self.export_window, text='Datasets (split x)')
        data_diffx["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        data_diffx.configure(background='#E4E4E4')

        # Colocação dos botões para copiar o texto
        self.function_button = tk.Button(self.export_window,
                                    text="COPY",
                                    fg='white',
                                    bg='#F21112',
                                    activebackground='white',
                                    activeforeground='#F21112')
        self.function_button["command"] = self.export_function
        self.function_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        self.function_button.bind("<Enter>", func=lambda e: self.function_button.config(bg='white',fg='#F21112'))
        self.function_button.bind("<Leave>", func=lambda e: self.function_button.config(bg='#F21112',fg='white'))

        self.data_samex_button = tk.Button(self.export_window,
                                           text="COPY",
                                           fg='white',
                                           bg='#F21112',
                                           activebackground='white',
                                           activeforeground='#F21112')
        self.data_samex_button["command"] = self.export_data_samex
        self.data_samex_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        self.data_samex_button.bind("<Enter>", func=lambda e: self.data_samex_button.config(bg='white',fg='#F21112'))
        self.data_samex_button.bind("<Leave>", func=lambda e: self.data_samex_button.config(bg='#F21112',fg='white'))

        self.data_diffx_button = tk.Button(self.export_window,
                                           text="COPY",
                                           fg='white',
                                           bg='#F21112',
                                           activebackground='white',
                                           activeforeground='#F21112')
        self.data_diffx_button["command"] = self.export_data_diffx
        self.data_diffx_button["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        self.data_diffx_button.bind("<Enter>", func=lambda e: self.data_diffx_button.config(bg='white',fg='#F21112'))
        self.data_diffx_button.bind("<Leave>", func=lambda e: self.data_diffx_button.config(bg='#F21112',fg='white'))

        # Dizer as posições dos vários elementos na tela
        function.place(relx=.05, rely=.15, anchor='w')
        data_samex.place(relx=.05,rely=.5,anchor='w')
        data_diffx.place(relx=.05,rely=.85,anchor='w')
        self.function_button.place(relx=.85, rely=.15, anchor='c')
        self.data_samex_button.place(relx=.85,rely=.5, anchor='c')
        self.data_diffx_button.place(relx=.85,rely=.85,anchor='c')

    def export_function(self):
        # Se a função já tiver sido compilada
        try:
            self.functions[self.selecteddataset]
        except:
            tk.messagebox.showwarning('ERROR', 'The function has not been compiled yet! Compile before exporting.')
            self.export_window.destroy()
            return
        if self.functions[self.selecteddataset]:
            # Algumas operações de estética
            self.function_button.configure(text='COPIED!',fg='#F21112',bg='white')
            self.data_samex_button.configure(text='COPY',fg='white',bg='#F21112')
            self.data_diffx_button.configure(text='COPY',fg='white',bg='#F21112')

            self.function_button.bind("<Enter>", func=lambda e: '')
            self.function_button.bind("<Leave>", func=lambda e: '')
            self.data_samex_button.bind("<Enter>", func=lambda e: self.data_samex_button.config(bg='white',fg='#F21112'))
            self.data_samex_button.bind("<Leave>", func=lambda e: self.data_samex_button.config(bg='#F21112',fg='white'))
            self.data_diffx_button.bind("<Enter>", func=lambda e: self.data_diffx_button.config(bg='white',fg='#F21112'))
            self.data_diffx_button.bind("<Leave>", func=lambda e: self.data_diffx_button.config(bg='#F21112',fg='white'))

            text = math_2_latex(self.functions[self.selecteddataset],self.params[self.selecteddataset],self.indeps[self.selecteddataset])
            pyperclip.copy(text)
        else:
            tk.messagebox.showwarning('ERROR','The function was compiled with errors! Make sure it compiles correctly before exporting.')
            self.export_window.destroy()

    def export_data_samex(self):
        # Algumas operações de estética
        self.function_button.configure(text='COPY',fg='white',bg='#F21112')
        self.data_samex_button.configure(text='COPIED!',fg='#F21112',bg='white')
        self.data_diffx_button.configure(text='COPY',fg='white',bg='#F21112')

        self.function_button.bind("<Enter>", func=lambda e: self.function_button.config(bg='white',fg='#F21112'))
        self.function_button.bind("<Leave>", func=lambda e: self.function_button.config(bg='#F21112',fg='white'))
        self.data_samex_button.bind("<Enter>", func=lambda e: '')
        self.data_samex_button.bind("<Leave>", func=lambda e: '')
        self.data_diffx_button.bind("<Enter>", func=lambda e: self.data_diffx_button.config(bg='white',fg='#F21112'))
        self.data_diffx_button.bind("<Leave>", func=lambda e: self.data_diffx_button.config(bg='#F21112',fg='white'))
        text = latexify_data(self.datasettext,0)
        pyperclip.copy(text)

    def export_data_diffx(self):
        # Algumas operações de estética
        self.function_button.configure(text='COPY',fg='white',bg='#F21112')
        self.data_samex_button.configure(text='COPY',fg='white',bg='#F21112')
        self.data_diffx_button.configure(text='COPIED!',fg='#F21112',bg='white')

        self.function_button.bind("<Enter>", func=lambda e: self.function_button.config(bg='white',fg='#F21112'))
        self.function_button.bind("<Leave>", func=lambda e: self.function_button.config(bg='#F21112',fg='white'))
        self.data_samex_button.bind("<Enter>", func=lambda e: self.data_samex_button.config(bg='white',fg='#F21112'))
        self.data_samex_button.bind("<Leave>", func=lambda e: self.data_samex_button.config(bg='#F21112',fg='white'))
        self.data_diffx_button.bind("<Enter>", func=lambda e: '')
        self.data_diffx_button.bind("<Leave>", func=lambda e: '')
        text = latexify_data(self.datasettext,0)
        pyperclip.copy(text)

    def lineslider(self, a):
        self.linescalelabelvalue['text'] = str(a)
        # self.plot_dataset()

    def markerslider(self, a):
        self.markerscalelabelvalue['text'] = str(a)
        # self.plot_dataset()

    def errorslider(self, a):
        self.errorscalelabelvalue['text'] = str(a)
        # self.plot_dataset()

    def funcplotslider(self, a):
        self.funcplotscalelabelvalue['text'] = str(a)
        # self.plot_dataset()

    def funcfitslider(self, a):
        self.funcfitscalelabelvalue['text'] = str(a)
        # self.plot_dataset()

    def fit_activate(self):
        for x in range(len(self.paramboxes)):
            try:
                self.init_values[self.selecteddataset][x] = float(self.paramboxes[x].get())
            except ValueError:
                if (self.paramboxes[x].get().replace(' ','')==''):
                    tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                    self.wantfit[self.selecteddataset].set(0)
                else:
                    tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                    self.wantfit[self.selecteddataset].set(0)
                return False

        self.wantfit[self.selecteddataset].set(1)
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

    def funcplotcolorpick(self):
        pick_color = tk.colorchooser.askcolor()[1]
        self.funcplotcolorvar[self.selecteddataset] = pick_color
        self.plot_dataset()

    def funcfitcolorpick(self):
        pick_color = tk.colorchooser.askcolor()[1]
        self.funcfitcolorvar[self.selecteddataset] = pick_color
        self.plot_dataset()

    def import_window(self):
        self.import_window = tk.Toplevel(self.master)
        self.import_window.title('File Format')
        self.import_window.geometry('400x250')
        self.import_window.configure(background='#E4E4E4')
        self.import_window.resizable(False, False)

        self.samex = tk.BooleanVar()
        self.difx = tk.BooleanVar()
        self.difxerror = tk.BooleanVar()

        self.samex.set(1)
        self.difx.set(0)
        self.difxerror.set(0)

        self.samexbutton = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.samex, text = 'All datasets have same x', command = self.samexfunction)
        self.samexbutton.place(in_ = self.import_window, relwidth = 0.7, relheight = 0.1, rely = 0.05, relx = 0.15)

        self.samexbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

        self.samextext=tk.Label(self.import_window, bg = '#E4E4E4', text = 'First column will be x.\nSubsequencial columns will be (y1, ey1, y2, ey2,...)')
        self.samextext.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.15, rely = 0.15, relx = 0.05)

        self.difxbutton = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.difx, text = 'All datasets have their own x',  command = self.difxfunction)
        self.difxbutton.place(in_ = self.import_window, relwidth = 0.8, relheight = 0.15, rely = 0.35, relx = 0.1)

        self.difxbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))

        self.difxtext=tk.Label(self.import_window, bg = '#E4E4E4', text = 'Columns will be (x1, y1, ey1, x2, y2, ey2,...)')
        self.difxtext.place(in_ = self.import_window, relwidth = 0.9, relheight = 0.1, rely = 0.46, relx = 0.05)

        difxerrorbutton = tk.Checkbutton(self.import_window, bg = '#E4E4E4', offvalue = 0, onvalue = 1, variable = self.difxerror, text = 'Include ex',  command = self.difxerrorfunction)
        difxerrorbutton.place(in_ = self.import_window, relwidth = 0.5, relheight = 0.1, rely = 0.6, relx = 0.25)

        importbutton = tk.Button(self.import_window, text = "CHOOSE FILE", command = self.open_file, fg='white',
                                  bg='#F21112',
                                  activebackground='white',
                                  activeforeground='#F21112')
        importbutton.place(in_ = self.import_window, relwidth =0.5, relheight = 0.15, relx=0.25, rely=0.8)
        importbutton["font"] = ("Roboto",int(20*1000/self.master.winfo_width()))
        # Alterar as cores quando entra e sai
        importbutton.bind("<Enter>", func=lambda e: importbutton.config(bg='white',fg='#F21112'))
        importbutton.bind("<Leave>", func=lambda e: importbutton.config(bg='#F21112',fg='white'))

    def samexfunction(self):
        self.difx.set(0)

    def difxfunction(self):
        self.samex.set(0)

    def difxerrorfunction(self):
        self.difxerror.get()

        if self.difxerror.get():
            self.samextext['text'] = 'First columns will be (x, ex).\nSubsequencial columns will be (y1, ey1, y2, ey2,...)'
            self.samexbutton['text'] = 'All datasets have same (x, ex)'
            self.difxbutton['text'] = 'All datasets have their own (x, ex)'
            self.difxtext['text'] = 'Columns will be (x1, ex1, y1, ey1, x2, ex2, y2, ey2,...)'
        else:
            self.samextext['text'] = 'First column will be x.\nSubsequencial columns will be (y1, ey1, y2, ey2,...)'
            self.samexbutton['text'] = 'All datasets have same x'
            self.difxbutton['text'] = 'All datasets have their own x'
            self.difxtext['text'] = 'Columns will be (x1, y1, ey1, x2, y2, ey2,...)'

    # Função para adicionar um dataset
    def add_dataset(self, string):
        # adicionar o texto merdoso, dar update À variavel do número de datasets
        self.numberdatasets = self.numberdatasets+1
        if ("dataset " + str(len(self.datalist) + 1)) in self.datalist:
            i=1
            while ("dataset " + str(len(self.datalist) + 1) + "_" + str(i)) in self.datalist:
                i+=1
            self.datalist.append("dataset " + str(len(self.datalist)+1) + "_" + str(i))
        else:
            self.datalist.append("dataset " + str(len(self.datalist)+1))
        self.datasetselector.config(values=self.datalist)

        self.datasettext.append(string)

        self.data_labels.append('')
        self.plot_labels.append('')
        self.fit_labels.append('')

        self.indeps.append(self.indeps[self.selecteddataset])
        self.params.append(self.params[self.selecteddataset])
        self.functions.append(self.functions[self.selecteddataset])
        self.clean_functions.append(self.clean_functions[self.selecteddataset])

        self.fit_params.append([])
        self.fit_uncert.append([])
        self.fit_chi.append('')
        self.fit_r2.append('')
        self.init_values.append([1.0]*len(self.paramboxes))

        self.x_func.append([])
        self.y_func.append([])

        self.yfittedfunc.append([])
        self.xfittedfunc.append([])

        self.full_output.append('')

        # Acrescentar para todas as variaveis de cores e opcoes
        self.wantfit.append(tk.BooleanVar())
        self.wantfit[-1].set(0)
        self.wantpoints.append(tk.BooleanVar())
        self.wantpoints[-1].set(1)
        self.wantline.append(tk.BooleanVar())
        self.wantline[-1].set(0)
        self.wanterror.append(tk.BooleanVar())
        self.wanterror[-1].set(0)
        self.wantfunction.append(tk.BooleanVar())
        self.wantfunction[-1].set(0)

        self.abcissas.append([0, 0, 0, 0])
        self.erabcissas.append([0, 0, 0, 0])
        self.ordenadas.append([0, 0, 0, 0])
        self.erordenadas.append([0, 0, 0, 0])

        self.abc.append(np.array(self.abcissas[-1]))
        self.erabc.append(np.array(self.erabcissas[-1]))
        self.ord.append(np.array(self.ordenadas[-1]))
        self.erord.append(np.array(self.erordenadas[-1]))

        # Criar as variáveis respetivas à escolha de cores para cada plot
        self.markercolorvar.append("black")
        self.linecolorvar.append("black")
        self.errorcolorvar.append("black")
        self.funcfitcolorvar.append("black")
        self.funcplotcolorvar.append("black")

        self.markeroptiontranslater.append('o')
        self.lineoptiontranslater.append('-')
        self.funcfitoptiontranslater.append('-')
        self.funcplotoptiontranslater.append('-')

        self.linewidth.append(tk.DoubleVar())
        self.markersize.append(tk.DoubleVar())
        self.errorwidth.append(tk.DoubleVar())
        self.funcfitwidth.append(tk.DoubleVar())
        self.funcplotwidth.append(tk.DoubleVar())

        self.markersize[self.numberdatasets-1].set(2.0)
        self.linewidth[self.numberdatasets-1].set(2.0)
        self.errorwidth[self.numberdatasets-1].set(2.0)
        self.funcfitwidth[self.numberdatasets-1].set(2.0)
        self.funcplotwidth[self.numberdatasets-1].set(2.0)

        self.datasetstoplotvar.append(tk.BooleanVar())
        self.datasetstoplotvar[self.numberdatasets-1].set(1)

        self.datasetstoplot.add_checkbutton(label = "Plot Dataset " + str(len(self.datalist)), onvalue = 1, offvalue = 0, variable = self.datasetstoplotvar[self.numberdatasets-1] )

    # Função para remover datasets
    def remove_dataset(self):

        if self.numberdatasets == 1:
            tk.messagebox.showwarning('ERROR', 'At least one dataset is needed. Add one before removing this one.')
            return -1

        self.numberdatasets -= 1

        # apagar o data_set
        self.datasettext.pop(self.selecteddataset)

        # remover todas as variáveis guardadas
        self.datalist = ["datalist "+str(i+1) for i in range(self.numberdatasets)]
        self.abcissas.pop(self.selecteddataset)
        self.erabcissas.pop(self.selecteddataset)
        self.ordenadas.pop(self.selecteddataset)
        self.erordenadas.pop(self.selecteddataset)

        self.data_labels.pop(self.selecteddataset)
        self.plot_labels.pop(self.selecteddataset)
        self.fit_labels.pop(self.selecteddataset)

        self.indeps.pop(self.selecteddataset)
        self.params.pop(self.selecteddataset)
        self.functions.pop(self.selecteddataset)
        self.clean_functions.pop(self.selecteddataset)

        self.fit_params.pop(self.selecteddataset)
        self.fit_uncert.pop(self.selecteddataset)
        self.fit_chi.pop(self.selecteddataset)
        self.fit_r2.pop(self.selecteddataset)
        self.init_values.pop(self.selecteddataset)

        self.x_func.pop(self.selecteddataset)
        self.y_func.pop(self.selecteddataset)

        self.xfittedfunc.pop(self.selecteddataset)
        self.yfittedfunc.pop(self.selecteddataset)

        self.full_output.pop(self.selecteddataset)

        # remover todas as variaveis de cores e opcoes
        self.wantfit.pop(self.selecteddataset)
        self.wantpoints.pop(self.selecteddataset)
        self.wantline.pop(self.selecteddataset)
        self.wanterror.pop(self.selecteddataset)
        self.wantfunction.pop(self.selecteddataset)

        self.plotoptions.delete(0,tk.END)
        self.plotoptions.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.wantpoints[0])
        self.plotoptions.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.wantline[0])
        self.plotoptions.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.wanterror[0])
        self.plotoptions.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.wantfit[0] )
        self.plotoptions.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.wantfunction[0])

        self.abc.pop(self.selecteddataset)
        self.erabc.pop(self.selecteddataset)
        self.ord.pop(self.selecteddataset)
        self.erord.pop(self.selecteddataset)

        # Criar as variáveis respetivas à escolha de cores para cada plot
        self.markercolorvar.pop(self.selecteddataset)
        self.linecolorvar.pop(self.selecteddataset)
        self.errorcolorvar.pop(self.selecteddataset)
        self.funcfitcolorvar.pop(self.selecteddataset)
        self.funcplotcolorvar.pop(self.selecteddataset)

        self.markeroptiontranslater.pop(self.selecteddataset)
        self.lineoptiontranslater.pop(self.selecteddataset)
        self.funcfitoptiontranslater.pop(self.selecteddataset)
        self.funcplotoptiontranslater.pop(self.selecteddataset)

        self.linewidth.pop(self.selecteddataset)
        self.markersize.pop(self.selecteddataset)
        self.errorwidth.pop(self.selecteddataset)
        self.funcfitwidth.pop(self.selecteddataset)
        self.funcplotwidth.pop(self.selecteddataset)

        self.menubar.delete("Choose Datasets")

        self.datasetstoplot = tk.Menu(self.menubar)
        self.menubar.add_cascade(label = "Choose Datasets", menu = self.datasetstoplot)

        self.datasetstoplotvar.pop(self.selecteddataset)

        self.selecteddataset = 0
        self.currentselection = 0

        self.datalistvariable.set(self.datalist[0])

        self.datasetselector.destroy()
        self.datasetselector = ttk.Combobox(self.plotbuttonframe, textvariable = self.datalistvariable, values = self.datalist)
        self.datasetselector.place(relx = 0, relheight = 1, relwidth=0.15)
        self.datasetselector.bind("<<ComboboxSelected>>", self.update_databox)

        for x in range(self.numberdatasets):
            self.datasetstoplot.add_checkbutton(label = "Plot Dataset " + str(x+1), onvalue = 1, offvalue = 0, variable = self.datasetstoplotvar[x] )
            self.datasetstoplotvar[x].set(self.datasetstoplotvar[x].get())

        self.update_databox("remove")

    def check_databox(self):
        for x in range(len(self.datasettext)):
            if (self.datasettext[x].replace(' ','') == '' and self.datasetstoplotvar[x].get()):
                tk.messagebox.showwarning('ERROR', 'Dataset {} is empty. Insert your data or remove it.'.format(x+1))
                return False

        for x in range(len(self.datasettext)):
            split = self.datasettext[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]
                if(len(ponto)!= 3 and len(ponto)!= 4 and self.datasetstoplotvar[x].get()):
                     tk.messagebox.showwarning('ERROR', 'Dataset {} has at least one point with an incorrect number of columns. Correct it.'.format(x+1))
                     self.wantfit[self.selecteddataset].set(0)
                     return False

        for x in range(len(self.datasettext)):
            split = self.datasettext[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(' ')
                ponto = [p for p in ponto if p]

                for k in ponto:
                    try:
                        float(k)
                    except ValueError:
                        tk.messagebox.showwarning('ERROR', 'Dataset {} contains non-numerical input. Only numerical input is allowed.'.format(x+1))
                        self.wantfit[self.selecteddataset].set(0)
                        return False
        return True

    def update_databox(self, event):
        # Guardar o atual na cena
        if event != "remove":
            self.datasettext[self.currentselection] = self.dataentry.get("1.0", "end-1c").replace('\t',' ')
        # Esta função serve para aparecer o texto respetivo a um dataset na caixa de texto
        # Pra fazer isso a forma menos messy é mesmo destruir tudo o que tá na frame e por a informação
        # respetiva ao novo data-set
        select = self.datalist.index(self.datalistvariable.get())
        self.selecteddataset = select
        self.currentselection = select

        self.functionentry.delete(0,tk.END)
        self.functionentry.insert(0,self.functions[self.selecteddataset])
        self.parameterentry.delete(0,tk.END)
        self.parameterentry.insert(0,self.params[self.selecteddataset])
        self.independententry.delete(0,tk.END)
        self.independententry.insert(0,self.indeps[self.selecteddataset])
        self.chisqentry.delete(0,tk.END)
        self.r2entry.delete(0,tk.END)

        self.update_parameter()

        self.plotoptions.delete(0,tk.END)
        self.plotoptions.add_checkbutton(label = "Plot points", onvalue = 1, offvalue = 0, variable = self.wantpoints[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Connect points", onvalue = 1, offvalue = 0, variable = self.wantline[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Error bars", onvalue = 1, offvalue = 0, variable = self.wanterror[self.selecteddataset])
        self.plotoptions.add_checkbutton(label = "Plot fit", onvalue = 1, offvalue = 0, variable = self.wantfit[self.selecteddataset] )
        self.plotoptions.add_checkbutton(label = "Plot function", onvalue =1, offvalue = 0, variable=self.wantfunction[self.selecteddataset])


        self.subframeleft2.destroy()
        self.dataentry.destroy()

        self.subframeleft2 = tk.Frame(self.frameleft, bg='#E4E4E4')
        self.subframeleft2.place(in_ = self.frameleft, relwidth = 1, relheight= 0.38, relx=0, rely=0.55)

        # Criação da caixa de texto com a informaçao respetiva
        self.dataentry = (ScrolledText(self.subframeleft2))
        self.dataentry.pack(expand = 1, fill = tk.X)
        self.dataentry.insert(tk.INSERT,self.datasettext[select])

        # Mesma coisa de apagar e por novos para os menus, para aparecerem os certos no sitio que diz respeito
        # ao dataset selecionado
        self.markersizescale.destroy()
        self.linewidthscale.destroy()
        self.errorsizescale.destroy()
        self.funcfitwidthscale.destroy()
        self.funcplotwidthscale.destroy()

        self.markersizecombo.destroy()
        self.linestylecombo.destroy()
        self.funcfitstylecombo.destroy()
        self.funcplotstylecombo.destroy()

        self.linestylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.lineoption)

        self.funcfitstylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.funcfitoption)

        self.funcplotstylecombo = ttk.Combobox(self.subframeright3, values=[
            'Solid', 'Dashed', 'Dotted', 'DashDot'], textvariable = self.funcplotoption)

        self.markersizecombo = ttk.Combobox(self.subframeright3, values=[
            'Triangle', 'Square', 'Circle', 'Star', 'Diamond', 'X'], textvariable = self.markeroption )

        if self.markeroptiontranslater[self.selecteddataset] == 'x':
            self.markersizecombo.current(5)
            self.markeroption.set('X')
        if self.markeroptiontranslater[self.selecteddataset] == 'D':
            self.markersizecombo.current(4)
            self.markeroption.set('Diamond')
        if self.markeroptiontranslater[self.selecteddataset] == '*':
            self.markersizecombo.current(3)
            self.markeroption.set('Star')
        if(self.markeroptiontranslater[self.selecteddataset] == 'o'):
            self.markersizecombo.current(2)
            self.markeroption.set('Circle')
        if(self.markeroptiontranslater[self.selecteddataset] == 's'):
            self.markersizecombo.current(1)
            self.markeroption.set('Square')
        if(self.markeroptiontranslater[self.selecteddataset] == '^'):
            self.markersizecombo.current(0)
            self.markeroption.set('Triangle')

        if self.lineoptiontranslater[self.selecteddataset] == '-':
            self.linestylecombo.current(0)
            self.lineoption.set('Solid')
        if self.lineoptiontranslater[self.selecteddataset] == '--':
            self.linestylecombo.current(1)
            self.lineoption.set('Dashed')
        if self.lineoptiontranslater[self.selecteddataset] == ':':
            self.linestylecombo.current(2)
            self.lineoption.set('Dotted')
        if self.lineoptiontranslater[self.selecteddataset] == '-.':
            self.linestylecombo.current(3)
            self.lineoption.set('DashDot')

        if self.funcfitoptiontranslater[self.selecteddataset] == '-':
            self.funcfitstylecombo.current(0)
            self.funcfitoption.set('Solid')
        if self.funcfitoptiontranslater[self.selecteddataset] == '--':
            self.funcfitstylecombo.current(1)
            self.funcfitoption.set('Dashed')
        if self.funcfitoptiontranslater[self.selecteddataset] == ':':
            self.funcfitstylecombo.current(2)
            self.funcfitoption.set('Dotted')
        if self.funcfitoptiontranslater[self.selecteddataset] == '-.':
            self.funcfitstylecombo.current(3)
            self.funcfitoption.set('DashDot')

        if self.funcplotoptiontranslater[self.selecteddataset] == '-':
            self.funcplotstylecombo.current(0)
            self.funcplotoption.set('Solid')
        if self.funcplotoptiontranslater[self.selecteddataset] == '--':
            self.funcplotstylecombo.current(1)
            self.funcplotoption.set('Dashed')
        if self.funcplotoptiontranslater[self.selecteddataset] == ':':
            self.funcplotstylecombo.current(2)
            self.funcplotoption.set('Dotted')
        if self.funcplotoptiontranslater[self.selecteddataset] == '-.':
            self.funcplotstylecombo.current(3)
            self.funcplotoption.set('DashDot')

        self.markersizecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.64, relheight=0.05)
        self.markersizecombo.bind("<<ComboboxSelected>>", self.markerselector)

        self.linestylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.56, relheight=0.05)
        self.linestylecombo.bind("<<ComboboxSelected>>", self.lineselector)

        self.funcplotstylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.72, relheight=0.05)
        self.funcplotstylecombo.bind("<<ComboboxSelected>>", self.funcplotselector)

        self.funcfitstylecombo.place(in_ = self.subframeright3, relwidth = 0.15, relx = 0.63, rely=0.80, relheight=0.05)
        self.funcfitstylecombo.bind("<<ComboboxSelected>>", self.funcfitselector)

        # Saber qual o dataset selecionado so pra enfiar as cores e tal do correto
        self.linewidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.lineslider, showvalue = False, variable = self.linewidth[self.selecteddataset])
        self.linewidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.56, relheight=0.06)
        self.linewidthscale['width'] = 0.025*self.master.winfo_width()

        self.markersizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.markerslider,showvalue =False, variable = self.markersize[self.selecteddataset])
        self.markersizescale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.64, relheight=0.06)
        self.markersizescale['width'] = 0.025*self.master.winfo_width()

        self.funcplotwidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.funcplotslider, showvalue = False, variable = self.funcplotwidth[self.selecteddataset])
        self.funcplotwidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.72, relheight=0.06)
        self.funcplotwidthscale['width'] = 0.025*self.master.winfo_width()

        self.funcfitwidthscale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.funcfitslider,showvalue =False, variable = self.funcfitwidth[self.selecteddataset])
        self.funcfitwidthscale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.80, relheight=0.06)
        self.funcfitwidthscale['width'] = 0.025*self.master.winfo_width()

        self.errorsizescale = tk.Scale(self.subframeright3, from_ = 1, to= 5, resolution = 0.5,orient = tk.HORIZONTAL, troughcolor = '#F21112', bg = '#E4E4E4', highlightthickness=0, command = self.errorslider, showvalue = False, variable = self.errorwidth[self.selecteddataset])
        self.errorsizescale.place(in_ = self.subframeright3, relwidth = 0.17, relx = 0.34, rely=0.88, relheight=0.06)
        self.errorsizescale['width'] = 0.025*self.master.winfo_width()

        self.errorscalelabelvalue['text'] = self.errorwidth[self.selecteddataset].get()
        self.markerscalelabelvalue['text'] = self.markersize[self.selecteddataset].get()
        self.linescalelabelvalue['text'] = self.linewidth[self.selecteddataset].get()
        self.funcfitscalelabelvalue['text'] = self.funcfitwidth[self.selecteddataset].get()
        self.funcplotscalelabelvalue['text'] = self.funcplotwidth[self.selecteddataset].get()

        if(self.countplots == 0):
            self.linewidthscale['state'] = tk.DISABLED
            self.markersizescale['state'] = tk.DISABLED
            self.errorsizescale['state'] = tk.DISABLED
            self.funcfitwidthscale['state'] = tk.DISABLED
            self.funcplotwidthscale['state'] = tk.DISABLED

    def compile_function(self):
        # clean the fit parameters
        for x in range(self.boxnumber):
            self.paramerrboxes[x].config(state = 'normal')
            self.paramerrboxes[x].delete(0, tk.END)
            self.paramerrboxes[x].config(state = 'readonly')

            self.paramresboxes[x].config(state = 'normal')
            self.paramresboxes[x].delete(0, tk.END)
            self.paramresboxes[x].config(state = 'readonly')
        # clean r2 and chisq
        self.chisqentry.config(state = 'normal')
        self.chisqentry.delete(0, tk.END)
        self.chisqentry.config(state = 'readonly')
        self.r2entry.config(state='normal')
        self.r2entry.delete(0, tk.END)
        self.r2entry.config(state = 'readonly')
        # erase the graph
        self.wantfit[self.selecteddataset].set(0)
        try:
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        except: pass

        parsed_input = parser(self.functionentry.get(),
                              self.parameterentry.get(),
                              self.independententry.get())
        self.functions[self.selecteddataset] = self.functionentry.get()

        for x in range(len(self.paramboxes)):
            try:
                self.init_values[self.selecteddataset][x] = float(self.paramboxes[x].get())
            except ValueError:
                if (self.paramboxes[x].get().replace(' ','')==''):
                    tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                    self.wantfit[self.selecteddataset].set(0)
                else:
                    tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                    self.wantfit[self.selecteddataset].set(0)
        if parsed_input[0]:
            self.clean_functions[self.selecteddataset] = parsed_input[1]
        else:
            tk.messagebox.showwarning('ERROR', parsed_input[1])
            self.clean_functions[self.selecteddataset] = ''

    # Função para plottar a funçao com parametros numericos dados pelo utilizador
    def plot_fittedfunction(self, dataset):
        self.xfittedfunc[dataset]=[0]*10000
        self.yfittedfunc[dataset]=[0]*10000

        x_max  = float(self.xaxismaxentry.get().replace(' ',''))
        x_min  = float(self.xaxisminentry.get().replace(' ',''))
        amp = x_max - x_min

        B = self.fit_params[dataset]
        expr = self.clean_functions[dataset]
        for j in range(10000):
            _x = x_min + j*amp/9999
            self.xfittedfunc[dataset][j] = _x
            # try:
            self.yfittedfunc[dataset][j] = eval(expr)
            # except FloatingPointError:
                # self.yfittedfunc[dataset][j] = 0

    def plot_function(self):

        parsed_input = parser(self.functionentry.get(),
                              self.parameterentry.get(),
                              self.independententry.get())
        if parsed_input[0]:
            expr = parsed_input[1]
        else:
            tk.messagebox.showwarning('ERROR', parsed_input[1])
            self.wantfunction[self.selecteddataset].set(0)
            return parsed_input

        B = []

        for i in range(len(self.plotparamboxes)):
             paramboxes = self.plotparamboxes[i].get()
             paramboxes = paramboxes.replace(' ', '')
             if(paramboxes == ''):
                 tk.messagebox.showwarning('ERROR', 'No parameter values were provided for plot.')
                 self.wantfunction[self.selecteddataset].set(0)
                 return False
             try:
                 float(paramboxes)
             except ValueError:
                 tk.messagebox.showwarning('ERROR', 'A non-numerical parameter value was detected. Only numerical values are allowed.')
                 self.wantfunction[self.selecteddataset].set(0)
                 return False
             B.append(float(paramboxes))

        x_max  = float(self.xaxismaxentry.get().replace(',','.').replace(' ',''))
        x_min  = float(self.xaxisminentry.get().replace(',','.').replace(' ',''))
        amp = x_max - x_min

        self.x_func[self.selecteddataset] = _x = [x_min + i*amp/9999 for i in range(10000)]
        self.y_func[self.selecteddataset] = []

        for i in range(10000):
            self.y_func[self.selecteddataset].append(eval(expr.replace('_x','_x[i]')))

        self.wantfunction[self.selecteddataset].set(1)
        self.plot_dataset()

    def plot_dataset(self):

        # we don't want to remove autoscale while in here
        self.remove_autoscale = False

        # Testar se os limites estão bem definidos. Se não estiverem podemos saltar isto tudo
        info_x = [(self.xaxismaxentry, 'Max value of x'), (self.xaxisminentry, 'Min value of x'), (self.xaxistickspentry, 'X axis tick spacing')]
        info_y = [(self.yaxismaxentry, 'Max value of y'), (self.yaxisminentry, 'Min value of y'), (self.yaxistickspentry, 'Y axis tick spacing')]

        if not self.autoscalex.get():
            for var in info_x:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        tk.messagebox.showwarning('ERROR', var[1]+' contains no input.')
                    else:
                        tk.messagebox.showwarning('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
            # Ver ainda se não temos os max menores que os min
            if float(self.xaxismaxentry.get().replace(',','.').replace(' ','')) <= float(self.xaxisminentry.get().replace(',','.').replace(' ','')):
                tk.messagebox.showwarning('ERROR', 'Upper limit for X axis is not greater that lower limit.')
                return False
            # E se os espaçamentos dos ticks são positivos
            if float(self.xaxistickspentry.get().replace(',','.').replace(' ','')) <= 0:
                tk.messagebox.showwarning('ERROR', 'Tick spacing must be a positive non-zero number.')
                return False
            # E se não estamos com demasiados ticks
            x_max  = float(self.xaxismaxentry.get().replace(',','.').replace(' ',''))
            x_min  = float(self.xaxisminentry.get().replace(',','.').replace(' ',''))
            amp = x_max - x_min
            n_ticks = int(amp/float(self.xaxistickspentry.get().replace(',','.').replace(' ','')))
            if n_ticks > 100:
                tk.messagebox.showwarning('ERROR','Having {} ticks will make your plot unreabable. Adjust X tick spacing.'.format(n_ticks))
                return False

        if not self.autoscaley.get():
            for var in info_y:
                try:
                    float(var[0].get().replace(',','.').replace(' ',''))
                except ValueError:
                    if var[0].get().replace(' ','')=='':
                        tk.messagebox.showwarning('ERROR', var[1]+' contains no input.')
                    else:
                        tk.messagebox.showwarning('ERROR', var[1]+' contains non-numerical input. Only numerical input allowed.')
                    return False
            # Ver ainda se não temos os max menores que os min
            if float(self.yaxismaxentry.get().replace(',','.').replace(' ','')) <= float(self.yaxisminentry.get().replace(',','.').replace(' ','')):
                tk.messagebox.showwarning('ERROR', 'Upper limit for Y axis is not greater that lower limit.')
                return False
            # E se os espaçamentos dos ticks são positivos
            if float(self.yaxistickspentry.get().replace(',','.').replace(' ','')) <= 0:
                tk.messagebox.showwarning('ERROR', 'Tick spacing must be a positive non-zero number.')
                return False
            y_max  = float(self.yaxismaxentry.get().replace(',','.').replace(' ',''))
            y_min  = float(self.yaxisminentry.get().replace(',','.').replace(' ',''))
            amp = y_max - y_min
            n_ticks = int(amp/float(self.yaxistickspentry.get().replace(',','.').replace(' ','')))
            if n_ticks > 100:
                tk.messagebox.showwarning('ERROR','Having {} ticks will make your plot unreabable. Adjust Y tick spacing.'.format(n_ticks))
                return False


        # Testar se os dados estão bem. Se não estiverem podemos saltar isto tudo.
        select = self.datalist.index(self.datalistvariable.get())
        self.datasettext[select]= self.dataentry.get("1.0", "end-1c").replace('\t',' ')

        if not self.check_databox():
            return False

        # pôr os dados em plot=true
        self.datasetstoplotvar[select].set(1)

        if(self.countplots == 0):
            self.linewidthscale['state'] = tk.NORMAL
            self.markersizescale['state'] = tk.NORMAL
            self.errorsizescale['state'] = tk.NORMAL
            self.funcfitwidthscale['state'] = tk.NORMAL
            self.funcplotwidthscale['state'] = tk.NORMAL
            self.countplots = 1

        for x in range(self.numberdatasets):
            if self.datasetstoplotvar[x].get():
                self.abcissas[x] = []
                self.erabcissas[x] = []
                self.ordenadas[x] = []
                self.erordenadas[x] = []
                self.datastring = self.datasettext[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                if data_sets == -2:
                    tk.messagebox.showwarning('ERROR', 'Dataset {} has at least one point defined incorrectly. Make sure all points have the same number of columns.'.format(select))
                    self.datasettext[select] = ""
                    self.datasetring = ""
                    return False
                for i in range(len(data_sets[0])):
                    if len(data_sets[0][i]) == 4:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.erabcissas[x].append(data_sets[0][i][1])
                        self.ordenadas[x].append(data_sets[0][i][2])
                        self.erordenadas[x].append(data_sets[0][i][3])

                    if len(data_sets[0][i]) == 3:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.erabcissas[x].append(0)
                        self.ordenadas[x].append(data_sets[0][i][1])
                        self.erordenadas[x].append(data_sets[0][i][2])

                self.abc[x] =np.array(self.abcissas[x])
                self.erabc[x] = np.array(self.erabcissas[x])
                self.ord[x] = np.array(self.ordenadas[x])
                self.erord[x] = np.array(self.erordenadas[x])

        if 5.5*self.width_ratio/self.height_ratio > 10.5:
            figsize=(10.5,10.5*self.height_ratio/self.width_ratio)
        else:
            figsize=(5.5*self.width_ratio/self.height_ratio,5.5)

        self.fig = Figure(figsize=figsize,tight_layout=True)

        dataforfit = []
        for x in range(self.numberdatasets):
            if self.datasetstoplotvar[x].get():
                self.datastring = self.datasettext[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                dataforfit.append(data_sets[0])
        a = []
        for dataset in dataforfit:
            for point in dataset:
                a.append(point)

        if not self.autoscalex.get():
            maxabc = float(self.xaxismaxentry.get().replace(',','.').replace(' ',''))
            minabc = float(self.xaxisminentry.get().replace(',','.').replace(' ',''))
            ampx   = float(self.xaxistickspentry.get().replace(',','.').replace(' ',''))
        if self.autoscalex.get():
            allabc = []
            for x in range(len(a)):
                allabc.append(a[x][0])

            minabc = min(allabc)
            maxabc = max(allabc)

            if len(a[0]) == 4:
                min_indexes = []
                max_indexes = []
                for point in a:
                    if point[0] == minabc and len(point)==4:
                        min_indexes.append(point[1])
                    if point[0] == maxabc and len(point)==4:
                        max_indexes.append(point[1])

                maxabc += max(max_indexes)
                minabc -= max(min_indexes)

            ampx = maxabc - minabc

            maxabc += 0.05*ampx
            minabc -= 0.05*ampx

            self.xaxismaxentry.delete(0, 'end')
            self.xaxisminentry.delete(0, 'end')

            self.xaxismaxentry.insert(0, "{0:.3e}".format(maxabc))
            self.xaxisminentry.insert(0, "{0:.3e}".format(minabc))

            ampx = ampx/8
            self.xaxistickspentry.delete(0,'end')
            self.xaxistickspentry.insert(0, "{0:.3e}".format(ampx))

        if not self.autoscaley.get():
            maxord = float(self.yaxismaxentry.get().replace(',','.').replace(' ',''))
            minord = float(self.yaxisminentry.get().replace(',','.').replace(' ',''))
            ampy   = float(self.yaxistickspentry.get().replace(',','.').replace(' ',''))

        if self.autoscaley.get():
            allord = []
            for x in range(len(a)):
                allord.append(a[x][-2])
                allord.append(a[x][-2])

            minord = min(allord)
            maxord = max(allord)

            min_indexes = []
            max_indexes = []
            for point in a:
                if point[-2] == minord:
                    min_indexes.append(point[-1])
                if point[-2] == maxord:
                    max_indexes.append(point[-1])

            minord -= max(min_indexes)
            maxord += max(max_indexes)

            ampy = maxord - minord
            maxord += 0.05*ampy
            minord -= 0.05*ampy

            self.yaxismaxentry.delete(0, 'end')
            self.yaxisminentry.delete(0, 'end')

            self.yaxismaxentry.insert(0, "{0:.3e}".format(maxord))
            self.yaxisminentry.insert(0, "{0:.3e}".format(minord))

            ampy = ampy/8
            self.yaxistickspentry.delete(0,'end')
            self.yaxistickspentry.insert(0, "{0:.3e}".format(ampy))


        x_ticks = []
        y_ticks = []

        x_max  = maxabc
        x_min  = minabc
        x_space = ampx
        y_max  = maxord
        y_min  = minord
        y_space = ampy

        # determine the ticks for the x-axis
        if len(self.x_ticks_ref) == 0:
            xticknumber = 1+int((x_max-x_min)/x_space)
            for x in range(xticknumber):
                x_ticks.append(x*x_space + x_min)

        if len(self.x_ticks_ref) == 1:
            xticknumber = 1+int((x_max-x_min)/x_space)
            temp = self.x_ticks_ref[0]
            if self.x_ticks_ref[0] < x_min:
                while temp < x_min:
                    temp += x_space
            if self.x_ticks_ref[0] > x_min:
                while temp - x_space > x_min:
                    temp -= x_space
            for x in range(xticknumber):
                x_ticks.append(x*x_space + temp)

        if len(self.x_ticks_ref) > 1:
            x_ticks = self.x_ticks_ref

        # determine the ticks for the y-axis
        if len(self.y_ticks_ref) == 0:
            yticknumber = 1+int((y_max-y_min)/y_space)
            for y in range(yticknumber):
                y_ticks.append(y*y_space + y_min)

        if len(self.y_ticks_ref) == 1:
            yticknumber = 1+int((y_max-y_min)/y_space)
            temp = self.y_ticks_ref[0]
            if self.y_ticks_ref[0] < y_min:
                while temp < y_min:
                    temp += y_space
            if self.y_ticks_ref[0] > y_min:
                while temp - y_space > y_min:
                    temp -= y_space
            for y in range(yticknumber):
                y_ticks.append(y*y_space + temp)

        if len(self.y_ticks_ref) > 1:
            y_ticks = self.y_ticks_ref

        self.a = self.fig.add_subplot(111 ,projection = None,
                                 xlim = (x_min,x_max), ylim = (y_min, y_max),
                                 xticks = x_ticks, yticks = y_ticks,
                                 ylabel = self.yaxistitleentry.get(), xlabel = self.xaxistitleentry.get())

        self.subframeleft1.destroy()
        self.subframeleft1=tk.Frame(self.frameleft, bg='#E4E4E4')
        self.subframeleft1.place(in_ = self.frameleft, relwidth=1, relheight=0.5, relx=0, rely=0)

        # first we see what scale we are using
        if self.log_x.get():
            if float(self.xaxisminentry.get().replace(',','.').replace(' ','')) > 0:
                self.a.set_xscale('log')
            else:
                self.a.set_xscale('symlog')
            self.a.set_xticks(x_ticks)
        if self.log_y.get():
            if float(self.yaxisminentry.get().replace(',','.').replace(' ','')) > 0:
                self.a.set_yscale('log')
            else:
                self.a.set_yscale('symlog')
            self.a.set_yticks(y_ticks)

        if self.check_databox():
            for i in range(self.numberdatasets):
                if self.datasetstoplotvar[i].get():
                    if self.wanterror[i].get():
                        self.a.errorbar(self.abc[i], self.ord[i], xerr = self.erabc[i], yerr = self.erord[i], fmt = 'none',zorder = -1,lw=0, ecolor = self.errorcolorvar[i], elinewidth = self.errorwidth[i].get())
                    if self.wantpoints[i].get():
                        if self.data_labels[i]:
                            self.a.plot(self.abc[i], self.ord[i], label=self.data_labels[i], marker = self.markeroptiontranslater[i], color = str(self.markercolorvar[i]), zorder = 1, lw=0, ms=self.markersize[i].get()*2)
                        else:
                            self.a.plot(self.abc[i], self.ord[i], marker = self.markeroptiontranslater[i], color = str(self.markercolorvar[i]), zorder = 1, lw=0, ms=self.markersize[i].get()*2)
                    if self.wantline[i].get():
                        self.a.plot(self.abc[i], self.ord[i], color = self.linecolorvar[i], lw = self.linewidth[i].get(), ls = str(self.lineoptiontranslater[i]))
                    if self.wantfunction[i].get():
                        if self.plot_labels[i]:
                            self.a.plot(self.x_func[i], self.y_func[i], label=self.plot_labels[i], lw = self.funcplotwidth[0].get(), ls = str(self.funcplotoptiontranslater[i]), color = self.funcplotcolorvar[i])
                        else:
                            self.a.plot(self.x_func[i], self.y_func[i], lw = self.funcplotwidth[0].get(), ls = str(self.funcplotoptiontranslater[i]), color = self.funcplotcolorvar[i])
                    if self.wantfit[i].get():
                        (self.fit_params[i], self.fit_uncert[i], self.fit_chi[i], self.fit_r2[i]) = self.fit_data(dataforfit[i], self.init_values[i], 2000, i)
                        self.plot_fittedfunction(i)
                        if self.fit_labels[i]:
                            self.a.plot(self.xfittedfunc[i], self.yfittedfunc[i], label=self.fit_labels[i], lw = self.funcfitwidth[i].get(), ls = str(self.funcfitoptiontranslater[i]), color = self.funcfitcolorvar[i])
                        else:
                            self.a.plot(self.xfittedfunc[i], self.yfittedfunc[i], lw = self.funcfitwidth[i].get(), ls = str(self.funcfitoptiontranslater[i]), color = self.funcfitcolorvar[i])
                        if i == self.selecteddataset:
                            for x in range (len(self.paramresboxes)):
                                self.paramresboxes[x].config(state = 'normal')
                                self.paramresboxes[x].delete(0, tk.END)
                                self.paramresboxes[x].insert(0, '{0:.7e}'.format(self.fit_params[self.selecteddataset][x]))
                                self.paramresboxes[x].config(state = 'readonly')
                                self.paramerrboxes[x].config(state = 'normal')
                                self.paramerrboxes[x].delete(0, tk.END)
                                self.paramerrboxes[x].insert(0, '{0:.7e}'.format(self.fit_uncert[self.selecteddataset][x]))
                                self.paramerrboxes[x].config(state = 'readonly')

                            self.chisqentry.config(state = 'normal')
                            self.chisqentry.delete(0, tk.END)
                            self.chisqentry.insert(0, "{0:.3e}".format(self.fit_chi[self.selecteddataset]))
                            self.chisqentry.config(state = 'readonly')
                            self.r2entry.config(state='normal')
                            self.r2entry.delete(0, tk.END)
                            self.r2entry.insert(0, "{0:.6f}".format(self.fit_r2[self.selecteddataset]))
                            self.r2entry.config(state = 'readonly')
        # Se calhar por também uma condição para ver se o utilizador quer grid
        self.a.grid(True)

        # Escrever os textos no gráfico
        for i in range(len(self.plot_text)):
            self.a.text(self.text_pos[i][0],self.text_pos[i][1],self.plot_text[i],fontsize=self.text_size[i])

        if np.any(np.array(self.data_labels)!='') or np.any(np.array(self.plot_labels)!='') or np.any(np.array(self.fit_labels)!=''):
            self.a.legend()


        self.canvas = FigureCanvasTkAgg(self.fig, master=self.subframeleft1)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

        # we don't want to remove autoscale while in here
        self.remove_autoscale = True

    def update_parameter(self):
        self.wantfit[self.selecteddataset].set(0)
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        #Mesmo raciocinio de destruir a caixa onde se poem os parametros e inicial guesses para por as novas
        global count
        self.params[self.selecteddataset] = self.parameterentry.get()
        self.indeps[self.selecteddataset] = self.independententry.get()

        if hasattr(self, 'paramboxes'):
            for x in range(len(self.paramboxes)):
                try:
                    self.init_values[self.selecteddataset][x] = float(self.paramboxes[x].get())
                except ValueError:
                    if (self.paramboxes[x].get().replace(' ','')==''):
                        tk.messagebox.showwarning('ERROR','Empty input found in initial guesses. Provide an initial guess for every parameter.')
                        self.wantfit[self.selecteddataset].set(0)
                    else:
                        tk.messagebox.showwarning('ERROR','Non-numerical input found in initial guesses. Only numerical input allowed.')
                        self.wantfit[self.selecteddataset].set(0)

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
            self.initialguesslabel.destroy()
            tk.messagebox.showwarning('ERROR', process[1])
        else:
            self.process_params = process[1]
            clean_split = process[1]
            if count==2:

                self.subframeright2.destroy()

                self.subframeright2=tk.Frame(self.frameright, bg='#E4E4E4')
                self.subframeright2.place(in_ = self.frameright, relwidth=1, relheight=0.2, relx=0, rely=0.25)

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
                if len(self.init_values[self.selecteddataset]) > self.boxnumber:
                    self.init_values[self.selecteddataset] = [1.0]*self.boxnumber
                else:
                    while len(self.init_values[self.selecteddataset]) != self.boxnumber:
                        self.init_values[self.selecteddataset].append(1.0)

                self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0, bg='#E4E4E4')
                self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)

                self.anotherframe=tk.Frame(self.paramcanvas, bg='#E4E4E4')

                self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
                self.paramscrolly.pack(side=tk.RIGHT, fill="y")

                self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
                self.paramcanvas.bind('<Configure>', self.adjust_canvas)

                self.anotherframe.columnconfigure(0, weight = 1)
                self.anotherframe.columnconfigure(1, weight = 3)
                self.anotherframe.columnconfigure(2, weight = 1)
                self.anotherframe.columnconfigure(3, weight = 3)
                self.anotherframe.columnconfigure(4, weight = 1)
                self.anotherframe.columnconfigure(5, weight = 3)
                self.anotherframe.columnconfigure(6, weight = 1)
                self.anotherframe.columnconfigure(7, weight = 3)

                self.chisqentry.config(state = 'normal')
                self.chisqentry.delete(0, tk.END)
                # try: self.chisqentry.insert(0, "{0:.3e}".format(self.fit_chi[self.selecteddataset]))
                # except: pass
                self.chisqentry.config(state = 'readonly')

                self.r2entry.config(state = 'normal')
                self.r2entry.delete(0, tk.END)
                # try: self.r2entry.insert(0, "{0:.6f}".format(self.fit_r2[self.selecteddataset]))
                # except: pass
                self.r2entry.config(state = 'readonly')
                for x in range(self.boxnumber):
                    self.paramerrlabel.append(tk.Label(self.anotherframe, text = u'\u03b4' + clean_split[x], bg='#E4E4E4'))
                    self.paramerrlabel[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.paramerrboxes.append(tk.Entry(self.anotherframe, cursor="arrow", takefocus=0))
                    # try: self.paramerrboxes[x].insert(0,"{0:.7e}".format(self.fit_uncert[self.selecteddataset][x]))
                    # except: pass
                    self.paramerrboxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.paramerrboxes[x].config(state = 'readonly')
                    self.paramreslabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#E4E4E4'))
                    self.paramreslabel[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.paramresboxes.append(tk.Entry(self.anotherframe, cursor="arrow", takefocus=0))
                    # try: self.paramresboxes[x].insert(0,"{0:.7e}".format(self.fit_params[self.selecteddataset][x]))
                    # except: pass
                    self.paramresboxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramresboxes[x].config(state = 'readonly')
                    self.paramboxes.append(tk.Entry(self.anotherframe))
                    try: self.paramboxes[x].insert(0,"{0:e}".format(self.init_values[self.selecteddataset][x]))
                    except: pass
                    self.paramboxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#E4E4E4'))
                    self.paramlabel[x].grid(column = 2, row = x, pady=10, padx=(15,0), sticky= tk.E)
                    self.plotparamlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg = '#E4E4E4'))
                    self.plotparamlabel[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plotparamboxes.append(tk.Entry(self.anotherframe))
                    self.plotparamboxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(self.anotherframe,
                                   text='GET FULL OUTPUT',
                                   fg='white',
                                   bg='#F21112',
                                   activebackground='white',
                                   activeforeground='#F21112')
                output['command'] = self.show_output
                output['font'] = ('Roboto',int(20*1000/self.master.winfo_width()))
                output.bind("<Enter>", func=lambda e: output.config(bg='white',fg='#F21112'))
                output.bind("<Leave>", func=lambda e: output.config(bg='#F21112',fg='white'))
                output.grid(row = x+1, column = 5)

                self.windows_item = self.paramcanvas.create_window((0,0), window=self.anotherframe, anchor="nw")

            if (count == 1):

                self.paramlabel = []
                self.paramboxes = []
                self.paramresboxes = []
                self.paramreslabel = []
                self.paramerrlabel = []
                self.paramerrboxes = []
                self.plotparamlabel = []
                self.plotparamboxes = []

                self.boxnumber = len(clean_split)

                self.resultlabel = tk.Label(self.subframeright1, text="Results", bg='#E4E4E4')
                self.resultlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.5)

                self.errorlabel = tk.Label(self.subframeright1, text="Errors", bg='#E4E4E4')
                self.errorlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.75)

                self.initialguesslabel = tk.Label(self.subframeright1, text="Initial Guess", bg='#E4E4E4')
                self.initialguesslabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=0.25)

                self.funcplotlabel = tk.Label(self.subframeright1, text="Plot Function", bg='#E4E4E4')
                self.funcplotlabel.place(rely=0.4, relwidth=0.25, relheight = 0.1, relx=-0.03)

                self.paramcanvas = tk.Canvas(self.subframeright2, highlightthickness=0, bg='#E4E4E4')
                self.paramcanvas.pack(side=tk.LEFT, fill = tk.BOTH, expand=1)

                self.anotherframe=tk.Frame(self.paramcanvas, bg='#E4E4E4')

                self.paramscrolly = ttk.Scrollbar(self.subframeright2, orient = "vertical", command=self.paramcanvas.yview)
                self.paramscrolly.pack(side=tk.RIGHT, fill="y")

                self.paramcanvas.configure(yscrollcommand=self.paramscrolly.set)
                self.paramcanvas.bind('<Configure>', self.adjust_canvas)

                self.anotherframe.columnconfigure(0, weight = 1)
                self.anotherframe.columnconfigure(1, weight = 3)
                self.anotherframe.columnconfigure(2, weight = 1)
                self.anotherframe.columnconfigure(3, weight = 3)
                self.anotherframe.columnconfigure(4, weight = 1)
                self.anotherframe.columnconfigure(5, weight = 3)
                self.anotherframe.columnconfigure(6, weight = 1)
                self.anotherframe.columnconfigure(7, weight = 3)

                self.chisqentry.config(state = 'normal')
                self.chisqentry.delete(0, tk.END)
                try: self.chisqentry.insert(0, "{0:.3e}".format(self.fit_chi[self.selecteddataset]))
                except: pass
                self.chisqentry.config(state = 'readonly')

                self.r2entry.config(state = 'normal')
                self.r2entry.delete(0, tk.END)
                try: self.r2entry.insert(0, "{0:.6f}".format(self.fit_r2[self.selecteddataset]))
                except: pass
                self.r2entry.config(state = 'readonly')
                for x in range(self.boxnumber):
                    self.paramerrlabel.append(tk.Label(self.anotherframe, text = u'\u03b4' + clean_split[x], bg='#E4E4E4'))
                    self.paramerrlabel[x].grid(column = 6, row = x, pady=10, sticky= tk.E)
                    self.paramerrboxes.append(tk.Entry(self.anotherframe, cursor="arrow", takefocus=0))
                    try: self.paramerrboxes[x].insert(0,"{0:.7e}".format(self.fit_uncert[self.selecteddataset][x]))
                    except: pass
                    self.paramerrboxes[x].grid(column=7, row=x, pady=10, padx=(0,10), sticky=tk.W + tk.E)
                    self.paramerrboxes[x].config(state = 'readonly')
                    self.paramreslabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg='#E4E4E4'))
                    self.paramreslabel[x].grid(column = 4, row = x, pady=10, sticky= tk.E)
                    self.paramresboxes.append(tk.Entry(self.anotherframe, cursor="arrow", takefocus=0))
                    try: self.paramresboxes[x].insert(0,"{0:.7e}".format(self.fit_params[self.selecteddataset][x]))
                    except: pass
                    self.paramresboxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramresboxes[x].config(state = 'readonly')
                    self.paramboxes.append(tk.Entry(self.anotherframe))
                    try: self.paramboxes[x].insert(0,"{0:e}".format(self.init_values[self.selecteddataset][x]))
                    except: pass
                    self.paramboxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.paramlabel.append(tk.Label(self.anotherframe, text = clean_split[x]+'\N{SUBSCRIPT ZERO}', bg='#E4E4E4'))
                    self.paramlabel[x].grid(column = 2, row = x, pady=10, padx=(15,0), sticky= tk.E)
                    self.plotparamlabel.append(tk.Label(self.anotherframe, text = clean_split[x], bg = '#E4E4E4'))
                    self.plotparamlabel[x].grid(column=0, row=x, pady=10, sticky = tk.E)
                    self.plotparamboxes.append(tk.Entry(self.anotherframe))
                    self.plotparamboxes[x].grid(column = 1, row = x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(self.anotherframe,
                                   text='GET FULL OUTPUT',
                                   fg='white',
                                   bg='#F21112',
                                   activebackground='white',
                                   activeforeground='#F21112')
                output['command'] = self.show_output
                output['font'] = ('Roboto',int(20*1000/self.master.winfo_width()))
                output.bind("<Enter>", func=lambda e: output.config(bg='white',fg='#F21112'))
                output.bind("<Leave>", func=lambda e: output.config(bg='#F21112',fg='white'))
                output.grid(row = x+1, column = 5)

            count = 2

            self.windows_item = self.paramcanvas.create_window((0,0), window=self.anotherframe, anchor="nw")

            sep2_plot = ttk.Separator(self.frameright, orient = tk.VERTICAL)
            sep2_plot.place(in_ = self.frameright, relx = 0.24, relheight = 0.245, rely = 0.20)
            sep3_plot = ttk.Separator(self.frameright, orient = tk.HORIZONTAL)
            sep3_plot.place(in_ = self.frameright, relwidth = 1, rely = 0.2 )
            sep4_plot = ttk.Separator(self.frameright, orient = tk.HORIZONTAL)
            sep4_plot.place(in_ = self.frameright, relwidth = 1, rely = 0.445 )
            sep5_plot = ttk.Separator(self.frameright, orient = tk.VERTICAL)
            sep5_plot.place(in_ = self.frameright, relx = 0, relheight = 1, rely = 0)

            self.paramcanvas.update()

    def show_output(self):
        if self.full_output[self.selecteddataset]:
            tk.messagebox.showinfo('FULL OUTPUT', self.full_output[self.selecteddataset])
        else:
            tk.messagebox.showwarning('ERROR', 'Fit not yet done.')

    def adjust_canvas(self, event):
        canvas_width = event.width
        self.paramcanvas.itemconfig(self.windows_item, width = canvas_width)
        self.paramcanvas.configure(scrollregion = self.paramcanvas.bbox("all"))

    def update(self):
        "Update the canvas and the scrollregion"
        self.update_idletasks()
        self.paramcanvas.config(scrollregion=self.paramcanvas.bbox(self.windows_item))

    def fit_data(self, data, init_params, max_iter, dataset_number):
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
        r2: R^2 para o fit

        """
        self.dataset_to_fit = dataset_number
        func = odr.Model(self.fit_function)

        for i in range(len(self.clean_functions)):
            if self.clean_functions[i] == '':
                tk.messagebox.showwarning('ERROR','Fitting function for dataset {} is not defined. Make sure it is compiled without errors.'.format(i+1))
                return 0

        x_points = []
        y_points = []
        x_err    = []
        y_err    = []

        # vamos começar por testar se todos os pontos têm as mesmas dimensões, e se não há pontos repetidos
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

        if (x_err and np.any(np.array(x_err)==0)):
            tk.messagebox.showwarning('ERROR','At least one point in dataset {} has a null x uncertainty. It is not possible to fit data with null uncertainty.'.format(self.currentselection))
            return 0
        if (y_err and np.any(np.array(y_err)==0)):
            tk.messagebox.showwarning('ERROR','At least one point in dataset {} has a null y uncertainty. It is not possible to fit data with null uncertainty.'.format(self.currentselection))
            return 0

        if (len(data[0])==3):
            fit_data = odr.RealData(x_points, y_points, sy=y_err, fix=[0]*len(x_points))
        else:
            fit_data = odr.RealData(x_points, y_points, sx=x_err, sy=y_err, fix=[0]*len(x_points))

        my_odr = odr.ODR(fit_data, func, beta0=init_params, maxit=max_iter)
        fit = my_odr.run()
        self.full_output[dataset_number] = ''
        self.full_output[dataset_number] += 'Beta:' + str(fit.beta) + '\n'
        self.full_output[dataset_number] += 'Beta Std Error:' + str(fit.sd_beta) + '\n'
        self.full_output[dataset_number] += 'Beta Covariance:' + str(fit.cov_beta) + '\n'
        self.full_output[dataset_number] += 'Residual Variance:' + str(fit.res_var) + '\n'
        self.full_output[dataset_number] += 'Inverse Condition #:' +str(fit.inv_condnum) + '\n'
        self.full_output[dataset_number] += 'Reason(s) for Halting:' + '\n'
        for r in fit.stopreason:
            self.full_output[dataset_number] += str(r) + '\n'

        # calcular o R^2
        ss_tot = sum([(y - np.average(y_points))**2 for y in y_points])
        ss_res =sum([(y_points[i] - self.fit_function(fit.beta,x_points[i]))**2 for i in range(len(y_points))])

        return (fit.beta, fit.sd_beta, fit.res_var, 1 - ss_res/ss_tot)

    def fit_function(self, B, _x):
        # try:
        #     out = eval(self.clean_functions[self.dataset_to_fit])
        # except FloatingPointError:
        #     return np.array([0]*len(_x))
        # return out
        return eval(self.clean_functions[self.dataset_to_fit])

    def open_file(self):

        self.import_window.destroy()

        file = tk.filedialog.askopenfilename()

        if not file:
            return

        if(self.samex.get() == 1):
            new_data = read_file(file,str,True,0)

        if(self.difx.get() == 1 and self.difxerror.get()== 0):
            new_data = read_file(file,str,True,1)

        if(self.difxerror.get() == 1 and self.difx.get() == 1 and self.samex.get() == 0):
            new_data = read_file(file,str,True,2)
        for x in range(len(new_data)):
            self.add_dataset(new_data[x])

root = tk.Tk()
app = MainWindow(master=root)
app.mainloop()
