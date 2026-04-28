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
	size_t region_size = 2UL * 1024UL * 1024UL;
	unsigned long iterations = 100000;
	struct timespec start, end;
	unsigned long i;
	double secs;

	if (argc > 1)
		iterations = strtoul(argv[1], NULL, 0);
	if (argc > 2)
		region_size = strtoull(argv[2], NULL, 0);

	if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
		perror("clock_gettime");
		return 1;
	}

	for (i = 0; i < iterations; i++) {
		void *p = mmap(NULL, region_size, PROT_READ | PROT_WRITE,
			       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED) {
			fprintf(stderr, "mmap failed at iteration %lu: %s\n",
				i, strerror(errno));
			return 1;
		}

		memset(p, 0, region_size);

		if (munmap(p, region_size) != 0) {
			fprintf(stderr, "munmap failed at iteration %lu: %s\n",
				i, strerror(errno));
			return 1;
		}
	}

	if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
		perror("clock_gettime");
		return 1;
	}

	secs = elapsed_seconds(&start, &end);
	printf("benchmark=mmap_churn iterations=%lu region_size=%zu ops_per_sec=%.2f elapsed_sec=%.6f\n",
	       iterations, region_size, iterations / secs, secs);
	return 0;
}
