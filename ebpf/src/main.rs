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

#[repr(C)]
pub struct FileAccessEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
    pub filename: [u8; 256],
}

#[repr(C)]
pub struct NetworkConnEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
    pub dst_addr: u32,
    pub dst_port: u16,
}

#[map]
pub static EVENTS: PerfEventArray<ProcessExecEvent> = PerfEventArray::new(0);

#[map]
pub static FILE_EVENTS: PerfEventArray<FileAccessEvent> = PerfEventArray::new(0);

#[map]
pub static NET_EVENTS: PerfEventArray<NetworkConnEvent> = PerfEventArray::new(0);

#[tracepoint]
pub fn sys_enter_execve(ctx: TracePointContext) -> u32 {
    match try_sys_enter_execve(ctx) {
        Ok(ret) => ret,
        Err(ret) => ret,
    }
}

fn try_sys_enter_execve(ctx: TracePointContext) -> Result<u32, u32> {
    let pid_tgid = bpf_get_current_pid_tgid();
    let comm = bpf_get_current_comm().unwrap_or([0; 16]);
    
    let event = ProcessExecEvent {
        tgid: (pid_tgid >> 32) as u32,
        pid: pid_tgid as u32,
        comm,
    };
    EVENTS.output(&ctx, &event, 0);
    Ok(0)
}

#[tracepoint]
pub fn sys_enter_openat(ctx: TracePointContext) -> u32 {
    match try_sys_enter_openat(ctx) {
        Ok(ret) => ret,
        Err(ret) => ret,
    }
}

fn try_sys_enter_openat(ctx: TracePointContext) -> Result<u32, u32> {
    let pid_tgid = bpf_get_current_pid_tgid();
    
    let mut event = unsafe { core::mem::MaybeUninit::<FileAccessEvent>::zeroed().assume_init() };
    event.tgid = (pid_tgid >> 32) as u32;
    event.pid = pid_tgid as u32;
    event.comm = bpf_get_current_comm().unwrap_or([0; 16]);

     
    let filename_ptr_val: usize = unsafe { ctx.read_at(24).unwrap_or(0) };
    let filename_ptr = filename_ptr_val as *const u8;
    
    if !filename_ptr.is_null() {
        let _ = unsafe { aya_ebpf::helpers::bpf_probe_read_user_str_bytes(filename_ptr, &mut event.filename) };
    }

    FILE_EVENTS.output(&ctx, &event, 0);
    Ok(0)
}

#[tracepoint]
pub fn sys_enter_connect(ctx: TracePointContext) -> u32 {
    match try_sys_enter_connect(ctx) {
        Ok(ret) => ret,
        Err(ret) => ret,
    }
}

 
#[repr(C)]
struct SockAddrIn {
    sin_family: u16,
    sin_port: u16,
    sin_addr: u32,
    sin_zero: [u8; 8],
}

fn try_sys_enter_connect(ctx: TracePointContext) -> Result<u32, u32> {
    let pid_tgid = bpf_get_current_pid_tgid();
    let comm = bpf_get_current_comm().unwrap_or([0; 16]);

     
    let sockaddr_ptr_val: usize = unsafe { ctx.read_at(24).unwrap_or(0) };
    let sockaddr_ptr = sockaddr_ptr_val as *const SockAddrIn;
    
     
    if sockaddr_ptr.is_null() {
        return Ok(0);
    }
    
    let (sin_family, sin_port, sin_addr) = unsafe {
        let base = sockaddr_ptr as *const u8;
        (
            aya_ebpf::helpers::bpf_probe_read_user(base as *const u16).unwrap_or(0),
            aya_ebpf::helpers::bpf_probe_read_user(base.add(2) as *const u16).unwrap_or(0),
            aya_ebpf::helpers::bpf_probe_read_user(base.add(4) as *const u32).unwrap_or(0)
        )
    };
    
    if sin_family == 2 {  
        let event = NetworkConnEvent {
            tgid: (pid_tgid >> 32) as u32,
            pid: pid_tgid as u32,
            comm,
            dst_addr: sin_addr,
            dst_port: u16::from_be(sin_port),
        };
        NET_EVENTS.output(&ctx, &event, 0);
    }
    
    Ok(0)
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    unsafe { core::hint::unreachable_unchecked() }
}
