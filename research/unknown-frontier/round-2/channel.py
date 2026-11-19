"""Independent finite noisy-channel and generic graph-colouring baseline."""
from itertools import combinations

def gate(word,pair):
    control,target=pair
    return word^(((word>>control)&1)<<target)

def star(n):
    forward=[(0,target) for target in range(1,n)]
    return forward+list(reversed(forward))

def propagate(word,gates,window,bit):
    for index,pair in enumerate(gates):
        if index==window and bit is not None:word^=1<<bit
        word=gate(word,pair)
    if window==len(gates) and bit is not None:word^=1<<bit
    return word

def matrix_error(n,gates,window,bit):
    # Compose row matrices, independently of the word-level gate simulator.
    rows=[1<<i for i in range(n)]
    for control,target in gates[window:]:rows[target]^=rows[control]
    return sum(((row>>bit)&1)<<i for i,row in enumerate(rows))

def error_set(n):return {0,(1<<n)-1,*[1<<i for i in range(n)]}

def graph(n):
    errors=error_set(n)
    differences={a^b for a in errors for b in errors}-{0}
    return [{x^d for d in differences} for x in range(1<<n)]

def colour(n,target):
    adjacency=graph(n)
    # Every two members of E are confusable. Fix this clique's colour names.
    clique=sorted(error_set(n))
    colours={vertex:index for index,vertex in enumerate(clique)}
    assert len(clique)<=target
    nodes=0
    def solve():
        nonlocal nodes
        nodes+=1
        if len(colours)==len(adjacency):return True
        options=[]
        for vertex in range(len(adjacency)):
            if vertex in colours:continue
            used={colours[u] for u in adjacency[vertex] if u in colours}
            allowed=set(range(target))-used
            if not allowed:return False
            options.append((len(used),sum(u not in colours for u in adjacency[vertex]),-vertex,vertex,allowed))
        _,_,_,vertex,allowed=max(options,key=lambda item:item[:3])
        for value in sorted(allowed):
            colours[vertex]=value
            if solve():return True
            del colours[vertex]
        return False
    assert solve(),'No colour assignment found at the proved threshold'
    result=[colours[x] for x in range(1<<n)]
    assert all(result[x]!=result[y] for x in range(1<<n) for y in adjacency[x])
    return result,nodes

def generic_decode(observed,saved,colours,errors):
    possibilities=[observed^error for error in errors if colours[observed^error]==saved]
    assert len(possibilities)==1,'Ambiguous generic codebook'
    return possibilities[0]

def linear_valid(n,rows):
    values=[sum(((row&e).bit_count()%2)<<i for i,row in enumerate(rows)) for e in error_set(n)]
    return len(set(values))==len(values)

def check_all_smaller_linear(n,bits):
    # An encoder with dependent/duplicate rows can be padded to independent
    # rows; thus all unordered distinct nonzero row subsets cover the search.
    total=valid=0
    for rows in combinations(range(1,1<<n),bits):
        total+=1;valid+=linear_valid(n,rows)
    return dict(rows=bits,checked=total,valid=valid)
