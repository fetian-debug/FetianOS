"""Exact geometry oracle, separate from the certificate and interval algorithms."""
from fractions import Fraction
from itertools import combinations
A=((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1))


def feasible(b, matrix=A):
    for i,j in combinations(range(len(matrix)),2):
        a,c=matrix[i];d,e=matrix[j]
        determinant=a*e-c*d
        if determinant==0:
            continue
        x=Fraction(b[i]*e-c*b[j],determinant)
        y=Fraction(a*b[j]-b[i]*d,determinant)
        if all(p*x+q*y<=r for (p,q),r in zip(matrix,b)):
            return True
    return False


def grid_feasible(b):
    return any(all(p*x+q*y<=r for (p,q),r in zip(A,b))
               for x in range(-2,3) for y in range(-2,3))
