SOURCES := workload.py

.PHONY: all
all: out

out: ${SOURCES}
	mkdir -p out
	pip install --only-binary :all: --target out/ --platform linux_x86_64 --implementation cp --python 3.9 requests
	cp ${SOURCES} out

.PHONY: clean
clean:
	rm -rf out
