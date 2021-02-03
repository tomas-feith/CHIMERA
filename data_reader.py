# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 16:36:00 2021

@author: tsfeith
"""

def reader (data, src):
    """
    Parameters
    ----------
    data : string
        Esta string pode ser <nome_ficheiro> ou os dados brutos dados pelo utilizador
    src : int
        0 ou 1. Se 0: nome de ficheiro; Se 1: dados brutos.

    Returns
    -------
    matrix : array of array
        Dados no formato de uma matriz Nx3
    """
    
    # Nota: Temos de pensar numa generalização para mais colunas, por exemplo,
    # permitir x ex y ey
    
    # Dividr em linhas
    data = data.split("\n")

    # Eliminar eventuais linhas vazias
    data = [datum for datum in data if datum]    
    
    # Admitindo que os valores podem estar separados por espaços ou vírgulas
    for i in range(len(data)):
        data[i] = data[i].split(' ')
        for j in range(len(data[i])):
            data[i][j] = data[i][j].split(',')
            
    # Fazer testes de funcionamento
    controlo = len(data[0])
    for datum in data:
        # Se houver linhas com tamanho diferente
        if len(datum) != controlo:
           return []
        # Se houver elementos não numéricos
        for pair in enumerate(datum):
            try:
                datum[pair[0]] = float(datum[pair[0]][0])
            except Exception:
                return []    
            
    matrix = [[data[i][j] for j in range(len(data[i]))] for i in range(len(data)) ]
    return matrix    

points = "1 2 0.1\n1 2 0.1\n1 2 0.1\n\n1 2 0.1"
if __name__ == '__main__':
    print(reader(points,1))