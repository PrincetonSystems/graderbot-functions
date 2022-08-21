UTILS = str.cma unix.cma $(SHARED)/utils326.ml

.PHONY: all grader
all: grader

grader:
	ocamlc -noassert -I $(SHARED) a1.ml $(UTILS) grade.ml
