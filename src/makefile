#! /usr/bin/env make
# ftag/makefile

.PHONY: what
what:
	@echo makefile: for ftag testing
	@echo   make clean         - cleanup all generated files
	@echo   make test_loopback - run a host loopback test via InMemoryRadio
	@echo   make test_pipeline - run a host pipeline test via stdstreams

#----- PROGRAMS ----------------------------------------------------------------
DTCLI    = ./dtcli.py
SEND     = $(DTCLI) --send
RECEIVE  = $(DTCLI) --receive
BIN2HEX  = $(DTCLI) --bin2hex
HEX2BIN  = $(DTCLI) --hex2bin
NOISE    = $(DTCLI) --noise
DIFF     = diff
PYTHON   = python3
LOOPBACK = $(PYTHON) ftag.py

#----- DIRS --------------------------------------------------------------------
TESTDATA = .

#----- FILES -------------------------------------------------------------------
TX_FILE = $(TESTDATA)/test35k.jpg
RX_FILE = received.jpg

#----- TARGETS -----------------------------------------------------------------
#DEFAULT
.PHONY: test_pipeline
test_pipeline: test_pipeline_bin

# LOOPBACK TEST - in memory radio, showing tasking use
test_loopback:
	$(LOOPBACK) $(TX_FILE) $(RX_FILE)
	$(DIFF) -q $(TX_FILE) $(RX_FILE)

# BINARY TRANSFER VIA STDSTREAMS - tests packetiser and throughput
.PHONY: test_pipeline_bin
test_pipeline_bin:
	$(SEND) $(TX_FILE) | $(RECEIVE) -p $(RX_FILE)
	$(DIFF) -q $(TX_FILE) $(RX_FILE)

# HEXASCII TRANSFER VIA STDSTREAMS - useful for encoding on text-only links
.PHONY: test_pipeline_hex
test_pipeline_hex:
	$(SEND) $(TX_FILE) | $(BIN2HEX) | $(HEX2BIN) | $(RECEIVE) -p $(RX_FILE)
	$(DIFF) -q $(TX_FILE) $(RX_FILE)

# BINARY TRANSFER WITH INSERTED NOISE - tests error detection and correction
.PHONY: test_pipeline_bin_noise
test_pipeline_bin_noise:
	$(SEND) $(TX_FILE) | $(NOISE) --prob=1 --ebit=1,9 | $(RECEIVE) -p $(RX_FILE)
	$(DIFF) -q $(TX_FILE) $(RX_FILE)

#----- UTILITIES ---------------------------------------------------------------
.PHONY: clean
clean:
	$(RM) $(RX_FILE) received.txt

#END: ftag/makefile
