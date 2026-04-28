#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

static double elapsed_seconds(const struct timespec *start,
			      const struct timespec *end)
{
	double sec = (double)(end->tv_sec - start->tv_sec);
	double nsec = (double)(end->tv_nsec - start->tv_nsec) / 1e9;

	return sec + nsec;
}

int main(int argc, char **argv)
{
	size_t region_size = 64UL * 1024UL * 1024UL;
	unsigned long iterations = 50000;
	struct timespec start, end;
	unsigned long i;
	void *p;
	double secs;

	if (argc > 1)
		iterations = strtoul(argv[1], NULL, 0);
	if (argc > 2)
		region_size = strtoull(argv[2], NULL, 0);

	p = mmap(NULL, region_size, PROT_READ | PROT_WRITE,
		 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) {
		perror("mmap");
		return 1;
	}

	memset(p, 0xaa, region_size);

	if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
		perror("clock_gettime");
		return 1;
	}

	for (i = 0; i < iterations; i++) {
		if (mprotect(p, region_size, PROT_READ) != 0) {
			fprintf(stderr, "mprotect(PROT_READ) failed at %lu: %s\n",
				i, strerror(errno));
			return 1;
		}

		if (mprotect(p, region_size, PROT_READ | PROT_WRITE) != 0) {
			fprintf(stderr, "mprotect(PROT_READ|PROT_WRITE) failed at %lu: %s\n",
				i, strerror(errno));
			return 1;
		}
	}

	if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
		perror("clock_gettime");
		return 1;
	}

	secs = elapsed_seconds(&start, &end);
	printf("benchmark=mprotect_churn iterations=%lu region_size=%zu toggles_per_sec=%.2f elapsed_sec=%.6f\n",
	       iterations, region_size, (iterations * 2.0) / secs, secs);

	munmap(p, region_size);
	return 0;
}
