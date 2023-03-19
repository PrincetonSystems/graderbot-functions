SOURCES=workload.py


.PHONY: all
all: out

go-1.18.7-r0.apk:
	wget https://dl-cdn.alpinelinux.org/alpine/v3.16/community/x86_64/go-1.18.7-r0.apk

out/usr/lib/go/bin/go: go-1.18.7-r0.apk
	mkdir -p out
	tar -C out -xzf go-1.18.7-r0.apk usr/lib 2> /dev/null

out: ${SOURCES} out/usr/lib/go/bin/go
	mkdir -p out
	cp ${SOURCES} out
