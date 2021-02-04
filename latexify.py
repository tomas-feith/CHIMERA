# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 18:45:02 2021

@author: tsfei
"""

from data_reader import reader

def latex (data, adjust_size):
    """
    Converte dados brutos numa tabela LaTeX já formatada. Há dois casos a considerar:
        3 colunas - x y ey
        4 colunas - x ex y ey
    
    Parameters
    ----------
    data : array of array
        Conjuntos de pontos armazenados numa matriz
    adjust_size : int
        0: não ajustar o tamanho para textwidth; 1: ajustar o tamanho para textwidth

    Returns
    -------
    table : str
        string em latex com todos os pontos
    """
    
    # IMPORTANTE: AINDA NÃO TOMA EM CONTA ALGARISMOS SIGNIFICATIVOS
    
    dim = len(data[0])
    
    table = r"""
\begin{table}[h]
\centering
"""
    if adjust_size:
        table += r"\resizebox{\textwidth}{!}{"
    table += r"""
{\renewcommand{\arraystretch}{1.1}
\begin{tabular}{c|c}\hline
Coluna 1 & Coluna 2 \\\hline
"""
    for i in range(len(data)):
        if dim == 3:
            table += str(data[i][0])+" & "+str(data[i][1])+r"$\pm$"+str(data[i][2])+r" \\"
        if dim == 4:
            table += str(data[i][0])+r"$\pm$"+str(data[i][1])+" & "+str(data[i][2])+r"$\pm$"+str(data[i][3])+r" \\"
        if i != len(data)-1:
            table += "\n"
        else:
            table += r"\hline"+"\n"
    table += r"""\end{tabular}
}
"""
    if adjust_size:
        table += "}"
    table += r"""
\caption{}
\label{tab:my-table}
\end{table}"""    

    return table

if __name__ == '__main__':
    data =reader("../test_data.txt",0)
    print(latex (data, 1))
    
    