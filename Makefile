include data/crates.d

data/crates.d:
	unrust build-crates-dependencies $@ dataset.csv --top $(top) --sort downloads

data/%.csv:
	unrust build-crate-csv $* --outdir data
