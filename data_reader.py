# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 16:36:00 2021

@author: tsfeith
"""

def reader (data, src, form):
    """
    Parameters
    ----------
    data : string
        Esta string pode ser <nome_ficheiro> ou os dados brutos dados pelo utilizador
    src : int
        0 ou 1. Se 0: nome de ficheiro; Se 1: dados brutos.
    form : int
        0 ou 1. Se 0: devolve em string; Se 1: devolve em float

    Returns
    -------
    matrix : array of array
        Dados no formato de uma matriz Nxm (N pontos, m dimensões)
    """
    if src == 0:
        try:
            file = open(data, "r")
        except FileNotFoundError:
            return []
        data = file.read()
        file.close()
    
    # Admitimos que os valores podem estar separados por espaços, vírgulas ou tabs
    # Vamos limpar isso tudo para espaços
    data = data.replace(","," ")
    data = data.replace("\t"," ")
    
    # Dividir em linhas
    data = data.split("\n")
    
    # Eliminar eventuais linhas vazias
    data = [datum for datum in data if datum] 
    
    # Fazer a divisão pelos espaços
    for i in range(len(data)):
        data[i] = data[i].split(' ')
    # Fazer testes de funcionamento
    controlo = len(data[0])
    for datum in data:
        # Se houver linhas com tamanho diferente
        if len(datum) != controlo:
           return []
        # Se houver elementos não numéricos
        for pair in enumerate(datum):
            try:
                if form:
                    datum[pair[0]] = float(datum[pair[0]])
                else:
                    float(datum[pair[0]])
            except Exception:
                return []
            
    matrix = [[data[i][j] for j in range(len(data[i]))] for i in range(len(data)) ]
    return matrix    

points = """400	201	14
401	215	15
402	199	14
403	203	14
404	211	15
405	202	14
406	238	15
407	215	15
408	231	15
409	240	15
410	250	16
411	260	16
412	247	16
413	289	17
414	307	18
415	323	18
416	325	18
417	356	19
418	395	20
419	419	20
420	490	22
421	502	22
422	510	23
423	584	24
424	637	25
425	652	26
426	640	25
427	641	25
428	632	25
429	568	24
430	538	23
431	504	22
432	483	22
433	463	22
434	430	21
435	419	20
436	452	21
437	457	21
438	466	22
439	475	22
440	504	22
441	633	25
442	607	25
443	722	27
444	757	28
445	841	29
446	1079	33
447	1229	35
448	1227	35
449	1596	40
450	1771	42
451	2286	48
452	2509	50
453	2809	53
454	3299	57
455	3408	58
456	3477	59
457	3471	59
458	3352	58
459	2991	55
460	2705	52
461	2436	49
462	2131	46
463	1929	44
464	1816	43
465	1770	42
466	1988	45
467	2326	48
468	2666	52
469	3333	58
470	3988	63
471	4852	70
472	6145	78
473	7490	87
474	9326	97
475	11246	106
476	13148	115
477	15278	124
478	17110	131
479	18805	137
480	19119	138
481	18832	137
482	17977	134
483	15684	125
484	12961	114
485	9868	99
486	7189	85
487	4814	69
488	2971	55
489	1811	43
490	1021	32
491	575	24
492	381	20
493	268	16
494	246	16
495	199	14
496	191	14
497	210	14
498	168	13
499	197	14
500	146	12
501	177	13
502	154	12
503	151	12
504	116	11
505	120	11
506	103	10
507	91	10
508	112	11
509	104	10
510	107	10
511	125	11
512	119	11
513	101	10
514	80	9
515	100	10
516	94	10
517	80	9
518	36	6
519	45	7
520	17	4
521	23	5
522	10	3
523	5	2
524	2	1
525	2	1
526	1	1
527	2	1
528	0	0
529	0	0
530	1	1
531	1	1"""
if __name__ == '__main__':
    print(reader(points,1,1))
    print(reader("../test_data.txt",0,1))

    