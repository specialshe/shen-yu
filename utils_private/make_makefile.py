import sys

path_prefix, nb_hyp, target_prefix, makefilename = sys.argv[1:]
nb_hyp = int(nb_hyp)
makefile = open(makefilename, "w")
path_to_convert_hyp = "/home/fabien/progs/EBMT_BB/utils/convert_hyp.py"
filename_in_list = []
filename_out_list = []
for i in range(nb_hyp):
    filename_in = path_prefix + "%05i"%i+".hyp"
    filename_out = target_prefix + "%i"%i
    filename_in_list.append(filename_in)
    filename_out_list.append(filename_out)
makefile.write("all: %s\n\n"%" ".join(filename_out_list))
for filename_in, filename_out in zip(filename_in_list, filename_out_list):
    makefile.write("%s: %s\n\tpython -O %s %s %s\n\n"%(filename_out, filename_in, path_to_convert_hyp, filename_in, filename_out))