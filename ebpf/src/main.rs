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
pub static EVENTS: PerfEventArray<ProcessExecEvent> = PerfEventArray::with_max_entries(1024, 0);

#[map]
pub static FILE_EVENTS: PerfEventArray<FileAccessEvent> = PerfEventArray::with_max_entries(1024, 0);

#[map]
pub static NET_EVENTS: PerfEventArray<NetworkConnEvent> = PerfEventArray::with_max_entries(1024, 0);

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
    let mut comm: [u8; 16] = [0; 16];
    bpf_get_current_comm(&mut comm).unwrap_or(0);

    let filename_ptr: *const u8 = unsafe { ctx.arg(1) };
    let mut filename: [u8; 256] = [0; 256];
    let _ = unsafe { aya_ebpf::helpers::bpf_probe_read_user_str_bytes(filename_ptr, &mut filename) };

    let event = FileAccessEvent {
        tgid: (pid_tgid >> 32) as u32,
        pid: pid_tgid as u32,
        comm,
        filename,
    };
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

// Minimal sockaddr_in for eBPF parsing
#[repr(C)]
struct SockAddrIn {
    sin_family: u16,
    sin_port: u16,
    sin_addr: u32,
    sin_zero: [u8; 8],
}

fn try_sys_enter_connect(ctx: TracePointContext) -> Result<u32, u32> {
    let pid_tgid = bpf_get_current_pid_tgid();
    let mut comm: [u8; 16] = [0; 16];
    bpf_get_current_comm(&mut comm).unwrap_or(0);

    let sockaddr_ptr: *const SockAddrIn = unsafe { ctx.arg(1) };
    
    // Only proceed if it's not null
    if sockaddr_ptr.is_null() {
        return Ok(0);
    }
    
    let mut addr = SockAddrIn {
        sin_family: 0,
        sin_port: 0,
        sin_addr: 0,
        sin_zero: [0; 8],
    };
    
    // Read the struct safely
    let res = unsafe { aya_ebpf::helpers::bpf_probe_read_user(sockaddr_ptr as *const core::ffi::c_void, core::mem::size_of::<SockAddrIn>() as u32) };
    
    // As a workaround since bpf_probe_read_user returns c_long we must manually do memory copies or simpler: we use pointer casting if verified
    // To be perfectly safe, we'll cast directly and read
    let family = unsafe { aya_ebpf::helpers::bpf_probe_read_user(&((*sockaddr_ptr).sin_family) as *const u16 as *const core::ffi::c_void, 2) };
    
    let mut sin_family: u16 = 0;
    let mut sin_port: u16 = 0;
    let mut sin_addr: u32 = 0;
    
    // Read family
    unsafe { aya_ebpf::helpers::bpf_probe_read_user(&mut sin_family as *mut _ as *mut core::ffi::c_void, sockaddr_ptr as *const core::ffi::c_void, 2) };
    
    if sin_family == 2 { // AF_INET
        unsafe { 
            aya_ebpf::helpers::bpf_probe_read_user(&mut sin_port as *mut _ as *mut core::ffi::c_void, (sockaddr_ptr as usize + 2) as *const core::ffi::c_void, 2);
            aya_ebpf::helpers::bpf_probe_read_user(&mut sin_addr as *mut _ as *mut core::ffi::c_void, (sockaddr_ptr as usize + 4) as *const core::ffi::c_void, 4);
        }
        
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
