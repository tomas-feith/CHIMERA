# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 14:04:36 2021

@author: tsfeith
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
        else:
            return 'O parâmetro dado \''+str(val)+'\' é um número. Utilize um parâmetro diferente.'
    # E verificar se a variável independente também não é
    try:
        float(indep)
    except ValueError:
        pass
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
        print(error)
        return 'A função \''+str(error).split('\'')[1]+'\' não foi reconhecida.'
    except FloatingPointError:
        return expr
    except SyntaxError:
        return 'Não foi possível compilar a sua expressão. Verifique se todos os parâmetros estão definidos e a expressão está escrita corretamente.'

    return expr
    
if __name__=='__main__':
    print(parser('a+b*sin(c*t+d)+e*cos(f*t+g)+h*tan(i*t+j)', 'a, b, c, d, e, f, g, h, i, j','t'))
    