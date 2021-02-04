# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 19:22:28 2021

@author: tsfeith
"""

def find_digit (number):
    """
    Recebe um número e diz o número de algarismos significativos.
    Por default, se >1, assume-se ordem de grandeza 0.

    Parameters
    ----------
    number : float
        Número a analisar

    Returns
    digit : int
        Ordem de grandeza de number

    """
    number = (number - int(number))
    if number == 0:
        return 0
    
    digit = 0
    while abs(number) < 1:
        digit+=1
        number*=10
    return digit

def adjust_digit (number, order):
    """
    Recebe um número e o número de algarismos significativos a utilizar.
    
    Parameters
    ----------
    number : float
        Número a converter
    order : int
        Número de algarismos significativos
    
    Returns
        clean_number : float / int
            Número limpo
    """
    
    # Primeiro testar se a ordem de grandeza é 0
    if order == 0:
        clean_number = str(round(number))
        return clean_number
    
    clean_number = str(number)
    clean_number = clean_number.split('.')
    if len(clean_number) == 1:
        clean_number.append('0'*order)
    
    while len(clean_number[1]) != order:
        clean_number[1]+='0'
    return '.'.join(clean_number)

def clean (data):
    """
    Função que acerta as casas decimais de cada número de acordo com os 
    algarismos significativos

    Parameters
    ----------
    data : array de array de floats
        Pode ter dimensão Nx3 ou Nx4.

    Returns
    -------
    clean_data : array de array de strings
        dados limpos para os algarismos significativos

    """
    
    dim = len(data[0])
    
    clean_data = [[0]* dim for datum in data]
    
    small_digit = [0]*dim
    
    # Encontrar o maior número de algarismos significativos para cada coluna
    for datum in data:
        for i in range(dim):
            if small_digit[i]<find_digit(datum[i]):
                small_digit[i]=find_digit(datum[i])
    print(small_digit)
                
    # E agora limpar de acordo com o passo anterior
    # Mas agora é relevante se dim = 3 ou dim = 4
    size_x = small_digit[dim-3]
    size_y = small_digit[dim-1]
    # Para limpar como deve ser, temos de converter em strings
    for i in range(len(data)):
        if dim == 3:
            clean_data[i][0] = adjust_digit(data[i][0],size_x)
            clean_data[i][1] = adjust_digit(data[i][1],size_y)
            clean_data[i][2] = adjust_digit(data[i][2],size_y)
        if dim == 4:
            clean_data[i][0] = adjust_digit(data[i][0],size_x)
            clean_data[i][1] = adjust_digit(data[i][1],size_x)
            clean_data[i][2] = adjust_digit(data[i][2],size_y)
            clean_data[i][3] = adjust_digit(data[i][3],size_y)
    
    return clean_data
    