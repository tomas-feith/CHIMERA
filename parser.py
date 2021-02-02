# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 14:04:36 2021

@author: tsfei
"""

import numpy as np

def parser(expr, params, indep):
    """
    Parameters
    ----------
    expr : string
        Expressão dada pelo utilizador
    params : string
        Variáveis dadas pelo utilizador
    indep : string
        Nome da variável independente dada pelo utilizador

    Returns
    -------
    cleanExpr : string
        Clean expression, ready to be interpreted

    """
    
    functions = ['sin',
                 'cos',
                 'tan',
                 'exp']
    
    # Fazer limpeza dos params
    # Assumindo que estão separados por virgulas ou espaços
    firstSplit = params.split(' ')
    cleanSplit = []
    for val in firstSplit:
        for param in val.split(','):
            if param:
                cleanSplit.append(param)
    # print(cleanSplit)
    
    # Verificar se nenhum dos nomes das variáveis não são funções
    for val in cleanSplit:
        if val in functions:
            return -1
    
    # Aproveitar e verificar se a variável independente não é uma função
    if indep in functions:
        return -2
    
    # E já agora verificar se não está nos parâmetros
    if indep in cleanSplit:
        return -3
    
    # Substituir as funções pelo equivalente numpy
    # Primeira substituição temporária para não haver erros de conversão
    for function in enumerate(functions):
        expr = expr.split(function[1])
        expr = ('['+str(len(cleanSplit)+function[0])+']').join(expr)
    
    # Substituir os nomes dos parâmetros
    for pair in enumerate(cleanSplit):
        expr = expr.split(pair[1])
        expr = ('B['+str(pair[0])+']').join(expr)
    
    # Substituir a variável independente
    expr = expr.split(indep)
    expr = 'x'.join(expr)
    
    # Voltar a substituir os elementos pelas funções
    for function in enumerate(functions):
        expr = expr.split('['+str(function[0]+len(cleanSplit))+']')
        expr = function[1].join(expr)
    print(expr)

    # # Vamos finalmente testar se a função funciona
    # # B = []
    # # for val in cleanSplit:
    # #     B.append(1)
    # # x=1
    # # print(eval(expr))
        
    # try:
    #     eval(expr)
    # except:
    #     print('Error?')
    
if __name__=='__main__':
    print(parser('a+b*sin(c*t+d)+e*cos(f*t+g)+h*tan(i*t+j)', 'a, b, c, d, e, f, g, h, i, j','t'))
    