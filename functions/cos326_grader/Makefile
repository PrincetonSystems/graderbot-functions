SOURCES=workload.py utils326.ml precheck

OCAML_APK=ocaml-4.14.0-r0.apk
OCAMLRUNTIME_APK=ocaml-runtime-4.14.0-r0.apk
OCAMLNUM_APK=ocaml-num-1.4-r1.apk

.PHONY: all
all: out

ocaml-num-%.apk:
	wget https://dl-cdn.alpinelinux.org/alpine/edge/testing/x86_64/$@

%.apk:
	wget https://dl-cdn.alpinelinux.org/alpine/v3.16/community/x86_64/$@

out/usr/bin/ocaml: ${OCAML_APK}
	mkdir -p out
	tar -m -C out -xzf $< 2> /dev/null

out/usr/lib/ocaml/stdlib.cma: ${OCAMLRUNTIME_APK}
	mkdir -p out
	tar -m -C out -xzf $< 2> /dev/null
	echo "/srv/usr/lib/ocaml" > out/usr/lib/ocaml/ld.conf
	echo "/srv/usr/lib/ocaml/stublibs" >> out/usr/lib/ocaml/ld.conf

out/usr/lib/ocaml/nums.cma: ${OCAMLNUM_APK}
	mkdir -p out
	tar -m -C out -xzf $< 2> /dev/null
	mv out/usr/lib/ocaml/num/[a-z]* out/usr/lib/ocaml
	sed '/^package/a \ \ directory = "^"' out/usr/lib/ocaml/num/META > META
	mv META out/usr/lib/ocaml/num/META
	mv out/usr/lib/ocaml/num-top/n* out/usr/lib/ocaml
	rm -rf out/usr/lib/num out/usr/lib/num-top
	mv out/usr/lib/ocaml/num out/usr/lib/ocaml/num-top out/usr/lib

out: ${SOURCES} out/usr/bin/ocaml out/usr/lib/ocaml/stdlib.cma out/usr/lib/ocaml/nums.cma
	mkdir -p out
	cp ${SOURCES} out
