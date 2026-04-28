CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -std=c11 -pthread

TARGETS := mmap_churn mprotect_churn threaded_mmap_churn

all: $(TARGETS)

mmap_churn: mmap_churn.c
	$(CC) $(CFLAGS) -o $@ $<

mprotect_churn: mprotect_churn.c
	$(CC) $(CFLAGS) -o $@ $<

threaded_mmap_churn: threaded_mmap_churn.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGETS)

.PHONY: all clean
