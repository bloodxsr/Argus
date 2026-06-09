#![no_std]
#![no_main]

use aya_ebpf::{
    macros::{map, tracepoint},
    maps::PerfEventArray,
    programs::TracePointContext,
    helpers::{bpf_get_current_pid_tgid, bpf_get_current_comm},
};

#[repr(C)]
pub struct ProcessExecEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
}

#[map]
pub static EVENTS: PerfEventArray<ProcessExecEvent> = PerfEventArray::with_max_entries(1024, 0);

#[tracepoint]
pub fn sys_enter_execve(ctx: TracePointContext) -> u32 {
    match try_sys_enter_execve(ctx) {
        Ok(ret) => ret,
        Err(ret) => ret,
    }
}

fn try_sys_enter_execve(ctx: TracePointContext) -> Result<u32, u32> {
    let pid_tgid = bpf_get_current_pid_tgid();
    let mut comm: [u8; 16] = [0; 16];
    
    bpf_get_current_comm(&mut comm).unwrap_or(0);
    
    let event = ProcessExecEvent {
        tgid: (pid_tgid >> 32) as u32, // Top 32 bits is the Thread Group ID (User-space PID)
        pid: pid_tgid as u32,          // Bottom 32 bits is the Thread ID (Kernel PID)
        comm,
    };
    
    EVENTS.output(&ctx, &event, 0);
    Ok(0)
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    unsafe { core::hint::unreachable_unchecked() }
}
