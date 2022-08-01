FUNCTIONS=start_assignment gh_repo go_grader grades generate_report
OUTPUTS=$(patsubst %, output/%.img, $(FUNCTIONS))
RUNS=$(patsubst %, run/%, $(FUNCTIONS))

.PHONY: all
all: $(OUTPUTS) #$(RUNS)

output/%.img: functions/%/*
	@truncate -s 500M $@
	@mkfs.ext4 -F $@
	@ \
		if [ -f functions/$*/Makefile ]; then \
			make -C functions/$*; \
			cptofs -t ext4 -i $@ functions/$*/out/* /; \
		else \
			cptofs -t ext4 -i $@ functions/$*/* /; \
		fi
	@e2fsck -f $@
	@resize2fs -M $@

output/example_grader.tgz: example_grader/*
	tar -C example_grader -czf $@ .

output/example_submission.tgz: example_submission/*
	tar -czf $@ example_submission/

.PHONY: prepdb
prepdb: output/example_grader.tgz output/example_submission.tgz
	sfdb -b cos316/example/grading_script - < output/example_grader.tgz
	sfdb -b submission.tgz - < output/example_submission.tgz

run/%: output/%.img payloads/%.jsonl
	@singlevm --mem_size 4096 --network --kernel_args="console=ttyS0" --kernel vmlinux-4.20.0 --rootfs python3.ext4 --appfs output/$*.img < payloads/$*.jsonl
	@touch $@

.PHONY: clean
clean:
	rm -f $(OUTPUTS) $(RUNS)
