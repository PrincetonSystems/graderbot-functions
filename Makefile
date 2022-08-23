FUNCTIONS=start_assignment gh_repo go_grader grades generate_report cos326_grader cos326_parse_results cos326_parse_comment
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

output/%.tgz: examples/%/*
	tar -C examples/$* -czf $@ .

output/%_submission.tgz: examples/%_submission/*
	tar --owner=0 --group=0 -C examples -czf $@ $*_submission/

.PHONY: prepdb
prepdb: output/example_cos316_grader.tgz output/example_cos316_submission.tgz output/example_cos326_grader.tgz output/example_cos326_submission.tgz
	sfdb cos316/example/grading_script - < output/example_cos316_grader.tgz
	sfdb github/cos316/example/submission.tgz - < output/example_cos316_submission.tgz
	sfdb cos326-f22/assignments '{"example": {"grading_script": "cos326-f22/example/grading_script"}}'
	sfdb cos326-f22/limits '{"example": 1}'
	sfblob < output/example_cos326_grader.tgz | tr -d '\n' | sfdb cos326-f22/example/grading_script -
	sfblob < output/example_cos326_submission.tgz | tr -d '\n' | sfdb github/cos326-f22/example/submission.tgz -

run/%: output/%.img payloads/%.jsonl
	@singlevm --mem_size 1024 --kernel vmlinux-4.20.0 --rootfs python3.ext4 --appfs output/$*.img < payloads/$*.jsonl
	@touch $@

.PHONY: clean
clean:
	rm -f $(OUTPUTS) $(RUNS)
