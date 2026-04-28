#!/usr/bin/env python3
"""
tlb_ebpf_collector.py - Non-invasive TLB invalidation collector using BCC.

This tool uses eBPF kprobes to hook into the kernel's TLB flushing paths
without requiring custom kernel patches. 

Target: native_flush_tlb_multi (x86-64)
"""

try:
    from bcc import BPF
except ImportError:
    print("Error: BCC (python3-bpfcc) not found. This tool requires eBPF support.")
    exit(1)

import argparse
import time
import signal

# BPF Program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <linux/cpumask.h>

struct data_t {
    u32 pid;
    u32 tgid;
    char comm[TASK_COMM_LEN];
    unsigned long start;
    unsigned long end;
    int cpu_count;
    int node;
};

BPF_PERF_OUTPUT(events);

/* 
 * Hook into native_flush_tlb_multi
 * Prototype: void native_flush_tlb_multi(const struct cpumask *cpumask, const struct flush_tlb_info *info)
 */
void kprobe__native_flush_tlb_multi(struct pt_regs *ctx, const struct cpumask *cpumask, void *info_ptr) {
    struct data_t data = {};
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    
    data.pid = bpf_get_current_pid_tgid();
    data.tgid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    /* 
     * Note: accessing 'info' fields requires knowing the struct flush_tlb_info layout
     * which can vary across kernel versions. In a production tool, we would use
     * BPF CO-RE (Compile Once, Run Everywhere). 
     * For this lab, we capture the base event.
     */
    
    // Approximating node
    data.node = bpf_get_numa_node_id();

    events.perf_submit(ctx, &data, sizeof(data));
}
"""

def print_event(cpu, data, size):
    event = b["events"].event(data)
    print(f"{time.time():.6f},{event.pid},{event.tgid},{event.comm.decode()},{event.node}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="eBPF TLB Collector")
    parser.add_argument("--output", default="ebpf_trace.csv", help="Output CSV file")
    args = parser.parse_args()

    print("Attaching eBPF kprobes to native_flush_tlb_multi...")
    print("Press Ctrl+C to stop.")

    b = BPF(text=bpf_text)
    
    with open(args.output, "w") as f:
        f.write("timestamp,pid,tgid,comm,node\n")
        
        def handle_event(cpu, data, size):
            event = b["events"].event(data)
            row = f"{time.time():.6f},{event.pid},{event.tgid},{event.comm.decode()},{event.node}\n"
            f.write(row)
            f.flush()
            print(row.strip())

        b["events"].open_perf_buffer(handle_event)
        
        try:
            while True:
                b.perf_buffer_poll()
        except KeyboardInterrupt:
            print("\nDetaching and exiting...")
