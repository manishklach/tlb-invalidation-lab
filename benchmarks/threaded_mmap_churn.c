#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

struct worker_args {
	unsigned long iterations;
	size_t region_size;
};

static double elapsed_seconds(const struct timespec *start,
			      const struct timespec *end)
{
	double sec = (double)(end->tv_sec - start->tv_sec);
	double nsec = (double)(end->tv_nsec - start->tv_nsec) / 1e9;

	return sec + nsec;
}

static void *worker(void *arg)
{
	struct worker_args *cfg = arg;
	unsigned long i;

	for (i = 0; i < cfg->iterations; i++) {
		void *p = mmap(NULL, cfg->region_size, PROT_READ | PROT_WRITE,
			       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED) {
			fprintf(stderr, "thread mmap failed at %lu: %s\n",
				i, strerror(errno));
			return (void *)1;
		}

		memset(p, 0x5a, cfg->region_size);

		if (munmap(p, cfg->region_size) != 0) {
			fprintf(stderr, "thread munmap failed at %lu: %s\n",
				i, strerror(errno));
			return (void *)1;
		}
	}

	return NULL;
}

int main(int argc, char **argv)
{
	unsigned int threads = 4;
	unsigned long iterations = 50000;
	size_t region_size = 1UL * 1024UL * 1024UL;
	pthread_t *tids;
	struct worker_args cfg;
	struct timespec start, end;
	double secs;
	unsigned int i;

	if (argc > 1)
		threads = strtoul(argv[1], NULL, 0);
	if (argc > 2)
		iterations = strtoul(argv[2], NULL, 0);
	if (argc > 3)
		region_size = strtoull(argv[3], NULL, 0);

	tids = calloc(threads, sizeof(*tids));
	if (!tids) {
		perror("calloc");
		return 1;
	}

	cfg.iterations = iterations;
	cfg.region_size = region_size;

	if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
		perror("clock_gettime");
		return 1;
	}

	for (i = 0; i < threads; i++) {
		if (pthread_create(&tids[i], NULL, worker, &cfg) != 0) {
			fprintf(stderr, "pthread_create failed for thread %u\n", i);
			return 1;
		}
	}

	for (i = 0; i < threads; i++) {
		void *ret;

		if (pthread_join(tids[i], &ret) != 0) {
			fprintf(stderr, "pthread_join failed for thread %u\n", i);
			return 1;
		}
		if (ret != NULL)
			return 1;
	}

	if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
		perror("clock_gettime");
		return 1;
	}

	secs = elapsed_seconds(&start, &end);
	printf("benchmark=threaded_mmap_churn threads=%u iterations_per_thread=%lu region_size=%zu total_ops=%lu ops_per_sec=%.2f elapsed_sec=%.6f\n",
	       threads, iterations, region_size, iterations * (unsigned long)threads,
	       (iterations * (double)threads) / secs, secs);

	free(tids);
	return 0;
}
