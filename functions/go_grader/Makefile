SOURCES=workload.py


.PHONY: all
all: out

go-1.17.10-r0.apk:
	wget http://dl-cdn.alpinelinux.org/alpine/v3.15/community/x86_64/go-1.17.10-r0.apk

out/usr/lib/go/bin/go: go-1.17.10-r0.apk
	mkdir -p out
	tar -C out -xzf go-1.17.10-r0.apk usr/lib 2> /dev/null

out: ${SOURCES} out/usr/lib/go/bin/go
	mkdir -p out
	cp ${SOURCES} out
