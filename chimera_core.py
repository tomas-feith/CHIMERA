"""Pure, GUI-independent helpers for CHIMERA: expression parsing/validation,
LaTeX generation and data-file reading. Kept separate from the Tkinter
application (main.py) so they can be imported and unit-tested in isolation.
"""
from io import StringIO

import numpy as np
import pandas as pd

from expr_eval import UnsafeExpressionError, safe_eval


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
                # o expoente começa depois do '{' recém-inserido (índice i+2);
                # avança-se até ao fim do expoente (operação ou ')') e fecha-se
                # a chaveta imediatamente antes desse ponto
                j = i+2
                while j < len(latex) and latex[j] not in operations and latex[j] != ')':
                    j += 1
                latex = latex[:j]+'}'+latex[j:]
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

    # Substituir os nomes dos parâmetros por marcadores temporários únicos.
    # Usa-se um marcador com '\x00' (impossível no input, que só permite letras
    # e dígitos) para que um parâmetro chamado 'B' não colida com a notação
    # 'B[i]' e para não voltar a substituir tokens já inseridos. Substituem-se
    # primeiro os nomes mais compridos, evitando colisões entre nomes que são
    # prefixo de outros (p.ex. 'a' e 'ab').
    for pos in sorted(range(len(clean_split)), key=lambda k: len(clean_split[k]), reverse=True):
        expr = expr.split(clean_split[pos])
        expr = ('\x00'+str(pos)+'\x00').join(expr)

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

    # Converter os marcadores dos parâmetros na notação final 'B[i]'
    for pos in range(len(clean_split)):
        expr = expr.split('\x00'+str(pos)+'\x00')
        expr = ('B['+str(pos)+']').join(expr)

    # Vamos finalmente testar se a função funciona
    # Valores de teste só porque sim
    B = [np.pi/2]*len(clean_split)  # noqa: F841  # referenced inside eval(expr)
    _x=-1

    try:
        safe_eval(expr, {'np': np, 'B': B, '_x': _x})
    except NameError as error:
        return (False, 'Function \''+str(error).split('\'')[1]+'\' not recognized.')
    except AttributeError as error:
        return (False, 'Function '+str(error).split('attribute ')[1]+' not recognized.')
    except (SyntaxError, UnsafeExpressionError):
        return (False, 'It was not possible to compile your expression. Verify if all your parameters are defined and the expression is written correctly.')
    except Exception:
        # Any other error (TypeError, ValueError, ZeroDivisionError, ...) means
        # the expression is syntactically valid but cannot be evaluated as written.
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
