import re, codecs

reref = re.compile(r"\[(\d+)\]")
def get_ref_list(line):
    res = []
    for m in reref.finditer(line):
        ref = int(m.groups()[0])
        res.append(ref)
    return res
    
def validate(f):
    num_line = 0
    line0 = f.readline()
    num_line += 1
    assert len(line0)>0
    nb_vertex, nb_edges_total = line0.strip().split()
    nb_vertex = int(nb_vertex)
    nb_edges_total = int(nb_edges_total)
    nb_edges_total_real = 0
    print nb_vertex, nb_edges_total
    for num_vertex in range(nb_vertex):
        line1 = f.readline()
        num_line += 1
        assert len(line1)>0
        nb_edges = int(line1.strip())
        if nb_edges == 0:
            print "warning, vertex ", num_vertex, "has no edge"
        nb_edges_total_real += nb_edges
        for num_edge in range(nb_edges):
            line_edge = f.readline()
            num_line += 1
            assert len(line_edge)>0
            line_edge = line_edge.strip()
            assert "|||" in line_edge
            first, second = line_edge.split("|||")
            ref_list = get_ref_list(first)
            for ref in ref_list:
                assert ref < num_vertex
            for feat in second.split():
                name, val = feat.split("=")
                val = float(val)
    assert nb_edges_total_real == nb_edges_total, "%i != %i"%(nb_edges_total_real, nb_edges_total)
    assert len(f.readline()) == 0
    
    
if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    validate(codecs.open(filename, encoding = "utf8"))
    