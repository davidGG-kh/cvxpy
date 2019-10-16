"""
Copyright, the CVXPY authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import cvxpy as cp
import numpy as np
from cvxpy.reductions.dcp2cone import atom_canonicalizers
from cvxpy.expressions.expression import Expression

def perspective_canon(expr, args):
    """
    perspective(f)(x, t) = {
        tf(x/t)            if t > 0,
        lim_{a->0} af(x/a) if t = 0
        +infinity          otherwise
    }     

    If we have:
        f(x) <= s <==> Ax + bs + c \in \mathcal K
    Then:
        perspective(f)(x, t) <= s <==> Ax + bs + c + c(t-1) \in \mathcal K
    See https://web.stanford.edu/~boyd/papers/pdf/sw_aff_ctrl.pdf
    """

    x = args[:-1]
    t = args[-1].flatten()

    try:
        underlying_canonicalizer = atom_canonicalizers.CANON_METHODS[type(expr._atom_initialized)]
    except KeyError:
        raise ValueError(f"Cannot take perspective of {expr._atom}. "
                         f"Must be able to canonicalize {expr.atom}.")
    s, constraints_underlying = underlying_canonicalizer(
        expr._atom_initialized,
        expr._atom_initialized.args
    )

    # set s (or all variables inside s) to zero
    if isinstance(s, cp.Variable):
        s.value = np.zeros(s.shape)
    elif isinstance(s, Expression):
        for var in s.variables():
            var.value = np.zeros(var.shape)
    else:
        raise ValueError(f"perspective canon does not support {expr._atom}.")

    # For each constraint, find the offset, and create a new constraint:
    #   Ax + bs + c + c(t-1) \in \mathcal K 
    constraints = []
    for constraint in constraints_underlying:
        constraint_arguments = []

        for arg in constraint.args:
            # set all variables to zero, save values
            var_values = []
            for var in arg.variables():
                if var.is_constant():
                    continue
                var_values.append(var.value[:])
                var.value = np.zeros(var.shape)
            
            # create new constraint for perspective
            c = arg.value[:]
            constraint_arguments.append(arg + c * (t - 1.0))

            # reset variables to previous values
            for var, value in zip(arg.variables(), var_values):
                if var.is_constant():
                    continue
                var.value = value
        
        constraints += [type(constraint)(*constraint_arguments)]

    return s, constraints
