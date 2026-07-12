"""Pure, GUI-independent helpers for CHIMERA: expression parsing/validation,
LaTeX generation and data-file reading. Kept separate from the Tkinter
application (main.py) so they can be imported and unit-tested in isolation.
"""
from io import StringIO
from typing import cast

import numpy as np
import pandas as pd

from expr_eval import UnsafeExpressionError, safe_eval


def take_first(elem: str) -> float:
    return float(elem.split('&')[0].split('$\\pm$')[0])

def latexify_data(data: list[str], mode: int) -> str:
    """
    Given a batch of datasets, generate the LaTeX text for a table.

    Parameters
    ----------
    data : array
        The set of datasets to generate the LaTeX table from.
    mode : int
        0: Use the same x column for all sets.
        1: Use a new x column for each of the sets.

    Returns
    -------
    str
        The LaTeX source for the table.
    """
    datasets = [[point.split(' ') for point in dataset.split('\n')] for dataset in data]

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
        latex_table += 'c' * len(datasets)
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
        latex_table += 'cc|' * len(datasets)
        latex_table = latex_table[:-1] + '}\n\\hline\n'
        for i in range(len(datasets)):
            latex_table += 'X%d & Y%d & ' % (i+1,i+1)
        latex_table = latex_table[:-2] + '\\\\ \\hline \n'
        max_size = max(len(dataset) for dataset in datasets)
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

def math_2_latex(expr: str, params: str, indep: str) -> str:

    # gather all relevant variables (input is assumed already validated)
    variables = cast('list[str]', process_params(params, indep)[1])
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

    # replace all Greek letters in the parameters
    for var in variables:
        # if the variable has a number, we only care about the non-numeric part
        if ''.join([i for i in var if not i.isdigit()]) in greek_letters:
            latex = latex.replace(var,'\\'+var)

    # subscript all indices
    for var in variables:
        pos=0
        # check how far the trailing digits go, in order to subscript them
        while pos<len(var):
            try:
                int(var[len(var)-pos-1])
            except ValueError:
                break
            pos+=1
        # if there is any number, perform the replacement
        if pos != 0:
            latex = latex.replace(var, var[:(len(var)-pos)]+'_{'+var[(len(var)-pos):]+'}')

    # handle powers
    latex = latex.replace('**','^')
    i=0
    while i<len(latex):
        if latex[i]=='^':
            if latex[i+1]!='(':
                latex = latex[:i+1]+'{'+latex[i+1:]
                # the exponent starts after the just-inserted '{' (index i+2);
                # advance to the end of the exponent (an operator or ')') and close
                # the brace immediately before that point
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

    # handle fractions
    i=0
    while i<len(latex):
        correction_after = 0
        correction_pre = 0
        if latex[i]=='/':
            # search backwards
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

            # search forwards
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

    # Finally, handle the functions
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

    # remove the * since no one writes it in LaTeX
    latex = latex.replace('*','')

    # and size the parentheses correctly
    latex = latex.replace('(','\\left(')
    latex = latex.replace(')','\\right)')

    return latex

def process_params(params: str, indep: str) -> tuple[bool, list[str] | str]:
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

    # Clean up the params
    # Assuming they are separated by commas or spaces
    # The cleaned parameters will be stored in this array
    clean_split = []
    # Split along all the spaces
    first_split = params.split(' ')
    for val in first_split:
        # Split each result of the previous division, now along the commas
        for param in val.split(','):
            # If param != ''
            if param:
                clean_split.append(param)

    # Check whether any parameter was given
    if not clean_split:
        return (False, 'No parameters were found.')
    # Check whether the independent variable was given
    # But first remove any spaces in the variable
    indep=indep.replace(' ','')
    if indep == '':
        return (False, 'No independent variable was found.')
    # Check whether any parameter has forbidden characters
    for val in clean_split:
        for char in val:
            if char not in allowed:
                return (False, 'Parameter \''+val+'\' contains the character \''+char+'\'. Only letters or numbers allowed.')
    # Check whether the independent variable has forbidden characters
    for char in indep:
        if char not in allowed:
            return (False, 'Independent variable \''+indep+'\' contains the character \''+char+'\'. Only letters or numbers allowed.')

    # Check that none of the variable names are functions
    for val in clean_split:
        if val in functions:
            return (False, 'Name \''+val+'\' is already binded to a function. Provide a different name.')
    # Check that the independent variable is not a function
    if indep in functions:
        return (False, 'Name \''+indep+'\' is already associated to a function. Provide a different name.')

    # Check that none of the variable names are reserved
    for val in clean_split:
        if val in forbidden:
            return (False, 'Name \''+val+'\' is a reserved keyword. Provide a different name.')
    # Check that the independent variable is not a reserved word
    if indep in forbidden:
        return (False, 'Name \''+indep+'\' is a reserved keyword. Provide a different name.')

    # Check that no parameter is repeated
    for val in clean_split:
        if clean_split.count(val) > 1:
            return (False, 'Parameter \''+val+'\' was provided more than once. Give different names to each parameter.')

    # Check that the independent variable is not among the parameters
    if indep in clean_split:
        return (False, 'Name \''+indep+'\' was given to the independent variable and to a parameter. Change one of them.')

    # Check that none of the parameters are numbers
    for val in clean_split:
        try:
            float(val)
        except ValueError:
            pass
        # If it does not raise an error it is a number, which we do not want
        else:
            return (False, 'Parameter \''+val+'\' given is a number. Use a different name.')
    # And check that the independent variable is not one either
    try:
        float(indep)
    except ValueError:
        pass
    # Same as above
    else:
        return (False, 'Independent variable \''+indep+'\' given is a number. Use a different name.')

    return (True, clean_split)

def parser(expr: str, params: str, indep: str) -> tuple[bool, str]:
    np.seterr(divide='warn', invalid='warn', under='warn', over='warn')
    # numpy functions to use
    # Statistics functions still need to be added
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


    # Check that the function is not empty
    expr=expr.replace(' ','')
    if expr == '':
        return (False, 'No fitting function was found.')

    process = process_params(params, indep)

    if process[0]:
        clean_split = cast('list[str]', process[1])
    else:
        return (False, cast('str', process[1]))

    # Check that the function contains the independent variable
    if indep not in expr:
        return (False, "Independent variable is not present in fit function.")

    # Replace the functions with their numpy equivalent
    # First a temporary substitution to avoid conversion errors
    for func_idx, func_name in enumerate(functions):
        expr = ('['+str(len(clean_split)+func_idx)+']').join(expr.split(func_name))
    # Replace the reserved words
    for keyword in forbidden:
        if keyword == 'PI':
            expr = '[3.14]'.join(expr.split(keyword))
        if keyword == 'E':
            expr = '[2.72]'.join(expr.split(keyword))

    # Replace the parameter names with unique temporary markers.
    # A NUL-byte marker is used (impossible in the input, which only allows
    # letters and digits) so a parameter named 'B' does not collide with the
    # 'B[i]' notation and so already-inserted tokens are not re-substituted.
    # The longest names are substituted first, avoiding collisions between
    # names that are prefixes of others (e.g. 'a' and 'ab').
    for pos in sorted(range(len(clean_split)), key=lambda k: len(clean_split[k]), reverse=True):
        expr = ('\x00'+str(pos)+'\x00').join(expr.split(clean_split[pos]))

    # Replace the independent variable
    expr = '_x'.join(expr.split(indep))

    # Substitute the markers back with the functions
    for func_idx, func_name in enumerate(functions):
        expr = ('np.'+func_name).join(expr.split('['+str(func_idx+len(clean_split))+']'))

    # Put back the numbers associated with the reserved words
    expr = 'np.pi'.join(expr.split('[3.14]'))
    expr = 'np.e'.join(expr.split('[2.72]'))

    # Convert the parameter markers into the final 'B[i]' notation
    for pos in range(len(clean_split)):
        expr = ('B['+str(pos)+']').join(expr.split('\x00'+str(pos)+'\x00'))

    # Finally, test whether the function works
    # Arbitrary test values
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

def rederive_clean_functions(
    functions: list[str], params: list[str], indeps: list[str]
) -> list[str]:
    """Re-derive the evaluatable expression for each dataset from its raw fit
    function.

    Used when loading a project: the pre-compiled expression stored in the file
    or database record is never trusted. Each raw function is re-validated
    through :func:`parser`, and any that fails validation yields an empty string
    (which the application treats as "no valid fit function"). This is what
    prevents a tampered project from smuggling in an arbitrary expression to
    evaluate.
    """
    clean = []
    for raw_func, raw_params, raw_indep in zip(functions, params, indeps):
        ok, result = parser(raw_func, raw_params, raw_indep)
        clean.append(result if ok else '')
    return clean

def read_file(src: "str | StringIO", out: type, mode: bool, datatype: int) -> "list | int":
    """
    Read the data from text or Excel files.

    Parameters
    ----------
    src : string
        Path to the file.
    out : type
        str/float - return all elements in this format.
    mode : bool
        true: join each dataset's points into a single text block.

    Returns
    -------
    data : array of array of array
        The data read from the file.
    """
    formats = [['xls', 'xlsx', 'xlsm', 'xlsb', 'odf', 'ods', 'odt'],
               ['csv', 'txt', 'dat']
              ]
    form = -1
    # Determine which type of file we are dealing with
    if isinstance(src, StringIO):
        form = 1
    else:
        for form_idx, exts in enumerate(formats):
            for ext in exts:
                if src.split('.')[-1] == ext:
                    form = form_idx
    # If it is none of the considered types, return -1 to signal the error
    if form == -1:
        return -1
    # If it is a text file
    if form:
        data = pd.read_csv(src, sep=r"\s+|;|:|None|,", engine='python', dtype="object", header=None)
    # If it is an Excel file
    else:
        data = pd.read_excel(src, dtype="object",header=None)


    # Split into the provided datasets
    # If there is no x uncertainty, the number of columns is odd
    full_sets: list = []

    # Datatype 0 is used within the program; the other two are only called when coming from Excel
    if(datatype == 0):
        if (data.shape[1]%2)!=0:
            for i in range(1,int((data.shape[1]+1)/2)):
                points = []
                for j in range(len(data[i].to_numpy())):
                    x = data[0].to_numpy(out)[j]
                    y = data[2*i-1].to_numpy(out)[j]
                    ey = data[2*i].to_numpy(out)[j]
                    # Look for inconsistencies in the rows
                    if (
                            (out==float and np.isnan(y)!=np.isnan(ey)) or
                            (out==str and y=='nan' and ey!='nan') or
                            (out==str and y!='nan'and ey=='nan')
                        ):
                        return -2
                    # If the row is empty, do not add it
                    if (
                            not (out==float and np.isnan(x)) and
                            not (out==str and x=='nan') and
                            not (out==float and np.isnan(y) and np.isnan(ey)) and
                            not (out==str and y=='nan' and ey=='nan')
                        ):
                        points.append([x, y, ey])
                full_sets.append(points)
        # If there is x uncertainty the handling is slightly different
        else:
            for i in range(1,int((data.shape[1])/2)):
                points = []
                for j in range(len(data[2*i].to_numpy())):
                    x = data[0].to_numpy(out)[j]
                    ex = data[1].to_numpy(out)[j]
                    y = data[2*i].to_numpy(out)[j]
                    ey = data[2*i+1].to_numpy(out)[j]
                    # Look for inconsistencies in the rows
                    if (
                            (out==float and np.isnan(x)!=np.isnan(ex)) or
                            (out==float and np.isnan(y)!=np.isnan(ey)) or
                            (out==str and y=='nan' and ey!='nan') or
                            (out==str and y!='nan'and ey=='nan')
                        ):
                        return -2
                    # If the row is empty, do not add it
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

    # If there is x uncertainty the handling is slightly different
    if(datatype == 2):
        for i in range(0,int((data.shape[1])/4)):
            points = []
            for j in range(len(data[4*i].to_numpy())):
                x = data[4*i].to_numpy(out)[j]
                ex = data[4*i+1].to_numpy(out)[j]
                y = data[4*i+2].to_numpy(out)[j]
                ey = data[4*i+3].to_numpy(out)[j]
                # If the row is empty, do not add it
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
