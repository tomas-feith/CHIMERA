# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 16:36:00 2021

@author: tsfeith
"""
import pandas as pd
import numpy as np

def read_file(src, out):
    """
    Função para ler os dados de ficheiros de texto ou excel

    Parameters
    ----------
    src : string
        Caminho para o ficheiro.
    out : type
        str/float - devolver os elementos todos neste formato.

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
    print(data)

    # Fazer a divisão nos datasets fornecidos
    # Se não houver incerteza no x, então o número de colunas é ímpar
    full_sets = []
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
                ex = data[1].to_numpt(out)[j]
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
                    return -3
                # Se a linha estiver vazia não se acrescenta
                if (
                        not (out==float and np.isnan(x) and np.isnan(ex)) and 
                        not (out==str and x=='nan' and ex=='nan') and
                        not (out==float and np.isnan(y) and np.isnan(ey)) and
                        not (out==str and y=='nan' and ey=='nan')
                    ):
                    points.append([x, ex, y, ey])
            full_sets.append(points)
    
    print(full_sets[0])
    print(full_sets[1])
    return full_sets

if __name__ == '__main__':
    # read_file('../../test_data.txt', float)
    read_file('../../test_data.xlsx', float)
    