#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DIR}"

make

echo "[1/3] mmap churn"
./mmap_churn 50000 2097152

echo "[2/3] mprotect churn"
./mprotect_churn 25000 67108864

echo "[3/3] threaded mmap churn"
./threaded_mmap_churn 4 20000 1048576
