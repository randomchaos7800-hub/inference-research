"""Offline-ops replay scenarios for the cha0tikp14 MoE survey (2026-10-20).

Each scenario is a recorded machine state: regex -> (output, exit_code). The model drives a
`terminal` tool exactly like offline Hermes; the harness answers from the fixtures. The
ground truth in TRUTH is never shown to the model; it is what the blind judge scores against.

Sources: the four real offline-Hermes sessions in ~/.hermes/state.db (diagnostic 09-24,
iPhone tether 09-26, health check 10-02, 64 GB question 10-08) and this laptop's runbook
incidents (psk-flags, MTP model path, UMA).
"""
import random

# ---------------------------------------------------------------- healthy base state
BASE = [
    (r"^uname", "Linux cha0tikp14 7.2.6-1-default #1 SMP PREEMPT_DYNAMIC Tue Sep 15 06:50:07 UTC 2026 (3d19f11) x86_64 x86_64 x86_64 GNU/Linux", 0),
    (r"os-release", 'NAME="openSUSE Tumbleweed"\n# VERSION="20261015"\nID="opensuse-tumbleweed"\nVERSION_ID="20261015"\nPRETTY_NAME="openSUSE Tumbleweed"', 0),
    (r"^hostname", "cha0tikp14", 0),
    (r"^whoami", "dino", 0),
    (r"^nproc", "16", 0),
    (r"^lscpu", "Architecture:                            x86_64\nCPU(s):                                  16\nModel name:                              AMD Ryzen AI 7 PRO 350 w/ Radeon 860M\nThread(s) per core:                      2\nCore(s) per socket:                      8\nCPU max MHz:                             5091.0000", 0),
    (r"^uptime", " 20:41:07  up 2 days  3:12,  2 users,  load average: 0.31, 0.22, 0.18", 0),
    (r"systemctl --failed|systemctl --user --failed|systemctl.*--failed", "", 0),
    (r"systemctl --user is-active voxtype ydotool llama-local", "active\nactive\nactive", 0),
    (r"systemctl --user is-active", "active", 0),
    (r"^travel status", "mode:      auto\nstate:     home\nat_home:   yes\nexit node: off\nlock:      autolock=false resume=true timeout=0m\naddresses: wlp194s0=10.0.0.79/24 tailscale0=100.64.0.14/32", 0),
    (r"^sensors", "k10temp-pci-00c3\nAdapter: PCI adapter\nTctl:         +54.8°C\n\nnvme-pci-c100\nAdapter: PCI adapter\nComposite:    +41.9°C\n\namdgpu-pci-c400\nAdapter: PCI adapter\nvddgfx:      705.00 mV\nedge:         +49.0°C\nPPT:          9.12 W\n\nthinkpad-isa-0000\nAdapter: ISA adapter\nfan1:        2210 RPM", 0),
    (r"^free", "               total        used        free      shared  buff/cache   available\nMem:            46Gi        11Gi       9.8Gi       212Mi        26Gi        35Gi\nSwap:           46Gi          0B        46Gi", 0),
    (r"^zramctl", "NAME       ALGORITHM DISKSIZE DATA COMPR TOTAL STREAMS MOUNTPOINT\n/dev/zram0 zstd         46.7G   4K   64B   20K         [SWAP]", 0),
    (r"^df", "Filesystem           Size  Used Avail Use% Mounted on\n/dev/mapper/cr_root  1.9T  221G  1.6T  12% /\n/dev/mapper/cr_root  1.9T  221G  1.6T  12% /home", 0),
    (r"BAT0/status.*BAT0/capacity|BAT0/capacity.*BAT0/status", "Not charging\n100", 0),
    (r"BAT0/status", "Not charging", 0),
    (r"BAT0/capacity", "100", 0),
    (r"AC.*/online", "1", 0),
    (r"nmcli -t -f DEVICE,STATE,CONNECTION dev|nmcli.*dev(ice)?( status)?$|nmcli -t.*dev", "wlp194s0:connected:HomeNet\ntailscale0:connected (externally):tailscale0\nlo:connected (externally):lo\np2p-dev-wlp194s0:disconnected:\nenp195s0f0:unavailable:", 0),
    (r"^ip -4 -br addr|^ip -br|^ip -4 addr|^ip addr|^ip a", "lo               UNKNOWN        127.0.0.1/8\nwlp194s0         UP             10.0.0.79/24\ntailscale0       UNKNOWN        100.64.0.14/32", 0),
    (r"^ip r|^ip route", "default via 10.0.0.1 dev wlp194s0 proto dhcp src 10.0.0.79 metric 600\n10.0.0.0/24 dev wlp194s0 proto kernel scope link src 10.0.0.79 metric 600", 0),
    (r"tailscale status --self|tailscale status", "100.64.0.14   cha0tikp14           randomchaos7800-hub@ linux   -\n100.64.0.10    cha0tikhome          randomchaos7800-hub@ linux   active; direct 10.0.0.47:41641", 0),
    (r"journalctl --user -b -p 3", "-- No entries --", 0),
    (r"journalctl -b -p 3", "Hint: You are currently not seeing messages from other users and the system.\n      Users in the 'systemd-journal' group can see all messages. Pass -q to\n      turn off this notice.\nOct 20 18:29:51 cha0tikp14 org_kde_powerdevil[2216]: Open failed for /dev/i2c-5, errno=EACCES(-13): Permission denied in file i2c_bus_core.c near line 433", 0),
    (r"curl .*127\.0\.0\.1:8090/health|curl .*localhost:8090/health", '{"status":"ok"}', 0),
    (r"^ps -eo rss,comm|^ps .*--sort=-rss", "  RSS COMMAND\n1777892 llama-server\n920932 voxtype\n442756 plasmashell\n317580 hermes\n216480 kwin_wayland\n200476 msedge\n182004 konsole", 0),
    (r"^ps ", "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\ndino      161543  1.5  3.6 30040988 1777892 ?    Ssl  18:35   0:38 /home/dino/opt/llama.cpp/llama-server --port 8090 -m /home/dino/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf\ndino        2440  1.9  1.9 2453628 920932 ?      Ssl  18:32   0:54 /usr/bin/voxtype daemon", 0),
    (r"^lsblk", "NAME         SIZE TYPE  FSTYPE      MOUNTPOINT\nzram0       46.7G disk  swap        [SWAP]\nnvme0n1      1.8T disk\n├─nvme0n1p1    1G part  vfat        /boot/efi\n└─nvme0n1p2  1.8T part  crypto_LUKS\n  └─cr_root  1.8T crypt btrfs       /", 0),
    (r"^cat .*RUNBOOK\.md|RUNBOOK", "# cha0tikp14 runbook (excerpt)\n## Known failures -> fix\n- offline says the model server did not come up -> journalctl --user -u llama-local -n 30. MTP flags need the MTP build at ~/models/mtp/.\n- wifi asks for the password after every reboot -> psk-flags=1 with KWallet off; nmcli con modify <name> 802-11-wireless-security.psk-flags 0 and re-enter the key once.\n- CafeNet wifi drops -> pin BSSID 02:00:00:00:00:01.\n- UMA carve-out is 16 GB in BIOS (F1 -> Config -> Display). 32 GB = black screen at boot. Do not change.", 0),
    (r"^sudo ", "sudo: a password is required", 1),
    (r"^(mkdir|chmod|cp|mv|touch|printf|tee|sleep|cd|export|true)\b|^cat\s*>|^cat <<", "", 0),
    (r"^id\b", "uid=1000(dino) gid=1000(dino) groups=1000(dino),100(users),484(video),485(render)", 0),
    (r"^pwd", "/home/dino", 0),
    (r"^which (\S+)", "/usr/bin/{1}", 0),
    (r"^file ", "ASCII text", 0),
    (r"^date", "Tue Oct 20 08:41:07 PM PDT 2026", 0),
    (r"powerprofilesctl", "performance", 0),
]

SCEN = {}

# 1 ------------------------------------------------------------- full diagnostic (09-24, 10-02)
SCEN["diag"] = dict(
    turns=["diagnostic of this box"],
    fixtures=[],
)

# 2 ------------------------------------------------------------- iPhone tether stealing the route (09-26)
SCEN["iphone"] = dict(
    turns=["Something seems to have gotten screwed up with the wifi and a wired connection of some sort. My iPhone Air is connected to this box, but that shouldn't be a wired connection. Check it out and fix it.",
           "The iPhone is connected because I want to download photos from it, not as an internet source. I still need a data connection, but it shouldn't be a network connection. Run whatever you need to."],
    fixtures=[
        (r"nmcli -t -f DEVICE,STATE,CONNECTION dev|nmcli.*dev(ice)?( status)?$|nmcli -t.*dev", "eth0:connected:Wired connection 2\nwlp194s0:connected:CafeNet\ntailscale0:connected (externally):tailscale0\nlo:connected (externally):lo\np2p-dev-wlp194s0:disconnected:\nenp195s0f0:unavailable:", 0),
        (r"^ip -4 -br addr|^ip -br|^ip -4 addr|^ip addr|^ip a", "lo               UNKNOWN        127.0.0.1/8\nwlp194s0         UP             10.131.130.204/24\ntailscale0       UNKNOWN        100.64.0.14/32\neth0             UP             172.20.10.11/28", 0),
        (r"^ip r|^ip route", "default via 172.20.10.1 dev eth0 proto dhcp src 172.20.10.11 metric 100\ndefault via 10.131.130.1 dev wlp194s0 proto dhcp src 10.131.130.204 metric 20600\n10.131.130.0/24 dev wlp194s0 proto kernel scope link src 10.131.130.204 metric 600\n172.20.10.0/28 dev eth0 proto kernel scope link src 172.20.10.11 metric 100", 0),
        (r"^lsusb", "Bus 003 Device 002: ID 27c6:6594 Shenzhen Goodix Technology Co.,Ltd. Goodix USB2.0 MISC\nBus 007 Device 034: ID 05ac:12a8 Apple, Inc. iPhone 5/5C/5S/6/SE/7/8/X/XR", 0),
        (r"nmcli.*con(nection)? show \"?Wired connection 2|nmcli.*-f .*autoconnect", "connection.id:                          Wired connection 2\nconnection.type:                        802-3-ethernet\nconnection.interface-name:              --\nconnection.autoconnect:                 yes\nipv4.method:                            auto\nipv4.never-default:                     no\nipv4.route-metric:                      -1\nGENERAL.DEVICES:                        eth0", 0),
        (r"nmcli.*con(nection)? show|nmcli c( |$)", "NAME                UUID                                  TYPE      DEVICE\nWired connection 2  8f0c2a51-5c4e-3b77-9d0e-0b8f2d7e1a10  ethernet  eth0\nCafeNet            1b8e7f42-6d2a-4c11-8a3e-5f2c9d4b7e21  wifi      wlp194s0\ntailscale0          4f6a1c8d-2b3e-4d5f-9a7b-8c1d2e3f4a5b  tun       tailscale0", 0),
        (r"ethtool -i eth0|readlink.*eth0|/sys/class/net/eth0/device/driver", "driver: ipheth\nversion: 7.2.6-1-default\nbus-info: usb-0000:c5:00.4-1", 0),
        (r"systemctl.*usbmuxd|pgrep.*usbmuxd|ps.*usbmuxd", "active", 0),
        (r"idevice_id|ideviceinfo|idevicepair", "00008150-001A2D3E0C41802E", 0),
        (r"gio mount -li|gio mount -l", "Volume(0): Dino's iPhone\n  Type: GProxyVolume (GProxyVolumeMonitorAfc)\n  activation_root=afc://00008150-001A2D3E0C41802E/", 0),
        (r"nmcli.*modify.*never-default|nmcli.*modify.*autoconnect|nmcli.*modify.*route-metric", "", 0),
    ],
    fixed_by=[r"nmcli d\w* reapply"],
    after=[
        (r"^ip r|^ip route", "default via 10.131.130.1 dev wlp194s0 proto dhcp src 10.131.130.204 metric 600\n10.131.130.0/24 dev wlp194s0 proto kernel scope link src 10.131.130.204 metric 600\n172.20.10.0/28 dev eth0 proto kernel scope link src 172.20.10.11 metric 100", 0),
    ],
)

# 3 ------------------------------------------------------------- wifi forgets password (runbook psk-flags)
SCEN["pskflags"] = dict(
    turns=["Every time I reboot, the HomeNet wifi asks for the password again. It connects fine after I type it. Figure out why and fix it."],
    fixtures=[
        (r"nmcli.*-s.*con(nection)? show \"?HomeNet|nmcli.*con(nection)? show \"?HomeNet|nmcli.*psk-flags|nmcli.*802-11-wireless-security", "connection.id:                          HomeNet\nconnection.type:                        802-11-wireless\nconnection.autoconnect:                 yes\n802-11-wireless.ssid:                   HomeNet\n802-11-wireless-security.key-mgmt:      wpa-psk\n802-11-wireless-security.psk:           <hidden>\n802-11-wireless-security.psk-flags:     1 (agent-owned)\nipv4.method:                            auto", 0),
        (r"ls .*dispatcher\.d", "91-persist-wifi-secrets", 0),
        (r"cat .*91-persist-wifi-secrets", "#!/bin/bash\n# copies agent-owned wifi secrets into the profile when psk-flags=0\n[ \"$2\" = up ] || exit 0\n...", 0),
        (r"kwallet|kwalletd|kwalletmanager", "kwalletd6: wallet subsystem disabled (Enabled=false in kwalletrc)", 0),
        (r"journalctl.*NetworkManager", "Oct 20 18:30:02 cha0tikp14 NetworkManager[1204]: <info>  [1792545002.1] device (wlp194s0): Activation: (wifi) access point 'HomeNet' has security, but secrets are required.\nOct 20 18:30:02 cha0tikp14 NetworkManager[1204]: <warn>  [1792545002.1] device (wlp194s0): no secrets: No agents were available for this request.", 0),
        (r"nmcli.*modify.*psk-flags", "", 0),
        (r"nmcli.*modify", "", 0),
    ],
    fixed_by=[r"psk-flags\s+0"],
    after=[
        (r"nmcli.*-s.*con(nection)? show \"?HomeNet|nmcli.*con(nection)? show \"?HomeNet|nmcli.*psk-flags|nmcli.*802-11-wireless-security", "connection.id:                          HomeNet\n802-11-wireless-security.key-mgmt:      wpa-psk\n802-11-wireless-security.psk:           <hidden>\n802-11-wireless-security.psk-flags:     0 (none)", 0),
    ],
)

# 4 ------------------------------------------------------------- llama-local won't start (MTP path)
SCEN["mtppath"] = dict(
    turns=["offline says the model server did not come up. Fix it."],
    fixed_by=[r"models/mtp/Qwen"],
    after=[
        (r"systemctl --user is-active voxtype ydotool llama-local", "active\nactive\nactive", 0),
        (r"systemctl --user is-active llama-local", "active", 0),
        (r"systemctl --user status llama-local", "● llama-local.service - local llama.cpp server\n     Active: active (running) since Tue 2026-10-20 20:44:02 PDT; 20s ago", 0),
        (r"systemctl --user --failed|systemctl.*--failed", "", 0),
        (r"journalctl.*llama-local", "Oct 20 20:44:05 cha0tikp14 llama-server[202311]: common_init_from_params: MTP context created (nextn layers: 1)\nOct 20 20:44:19 cha0tikp14 llama-server[202311]: main: server is listening on http://127.0.0.1:8090 - starting the main loop", 0),
        (r"cat .*llama-local\.service|systemctl --user cat llama-local|grep .*llama-local", "[Unit]\nDescription=local llama.cpp server\n\n[Service]\nExecStart=%h/opt/llama.cpp/llama-server --host 127.0.0.1 --port 8090 -m %h/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf --alias local -ngl 99 -c 262144 -t 8 -fa on --jinja --no-warmup --spec-type draft-mtp --spec-draft-n-max 2\nRestart=on-failure", 0),
        (r"curl .*8090/health", '{"status":"ok"}', 0),
    ],
    fixtures=[
        (r"systemctl --user is-active voxtype ydotool llama-local", "active\nactive\nfailed", 0),
        (r"systemctl --user is-active llama-local", "failed", 3),
        (r"systemctl --user status llama-local", "× llama-local.service - local llama.cpp server\n     Loaded: loaded (/home/dino/.config/systemd/user/llama-local.service; disabled)\n     Active: failed (Result: exit-code) since Tue 2026-10-20 20:38:12 PDT; 2min ago\n    Process: 201877 ExecStart=/home/dino/opt/llama.cpp/llama-server --host 127.0.0.1 --port 8090 -m /home/dino/models/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf --alias local -ngl 99 -c 262144 -t 8 -fa on --jinja --no-warmup --spec-type draft-mtp --spec-draft-n-max 2 (code=exited, status=1/FAILURE)", 3),
        (r"systemctl --user --failed|systemctl.*--failed", "● llama-local.service loaded failed failed local llama.cpp server", 0),
        (r"journalctl.*llama-local", "Oct 20 20:38:09 cha0tikp14 llama-server[201877]: llama_model_loader: loaded meta data with 52 key-value pairs and 733 tensors from /home/dino/models/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf\nOct 20 20:38:11 cha0tikp14 llama-server[201877]: load_tensors: offloaded 41/41 layers to GPU\nOct 20 20:38:12 cha0tikp14 llama-server[201877]: common_init_from_params: context type MTP requested but model doesn't contain MTP layers\nOct 20 20:38:12 cha0tikp14 llama-server[201877]: srv    load_model: failed to create MTP context\nOct 20 20:38:12 cha0tikp14 llama-server[201877]: main: exiting due to model loading error\nOct 20 20:38:12 cha0tikp14 systemd[1934]: llama-local.service: Main process exited, code=exited, status=1/FAILURE", 0),
        (r"cat .*llama-local\.service|systemctl --user cat llama-local", "[Unit]\nDescription=local llama.cpp server\n\n[Service]\nExecStart=%h/opt/llama.cpp/llama-server --host 127.0.0.1 --port 8090 -m %h/models/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf --alias local -ngl 99 -c 262144 -t 8 -fa on --jinja --no-warmup --spec-type draft-mtp --spec-draft-n-max 2\nRestart=on-failure\n", 0),
        (r"ls .*models/mtp|find .*models.*mtp", "Qwen3.6-35B-A3B-UD-IQ4_NL.gguf", 0),
        (r"ls .*models", "/home/dino/models:\nmtp\nQwen3.6-35B-A3B-UD-IQ4_NL.gguf\n\n/home/dino/models/mtp:\nQwen3.6-35B-A3B-UD-IQ4_NL.gguf", 0),
        (r"ls -la? .*models|du .*models|stat .*\.gguf", "-rw-r--r-- 1 dino dino 18040888288 Sep 24 15:13 /home/dino/models/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf\n-rw-r--r-- 1 dino dino 18536192288 Sep 24 20:47 /home/dino/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf", 0),
        (r"curl .*8090/health", "curl: (7) Failed to connect to 127.0.0.1 port 8090 after 0 ms: Couldn't connect to server", 7),
        (r"sed -i|systemctl --user edit|tee .*llama-local|cp .*llama-local", "", 0),
        (r"systemctl --user daemon-reload", "", 0),
        (r"systemctl --user (re)?start llama-local", "", 0),
    ],
)

# 5 ------------------------------------------------------------- "where did my RAM go" (10-08, the model got this wrong)
SCEN["uma"] = dict(
    turns=["I put 64 GB of RAM in this laptop but free only shows 46. Where did the rest go, and can I get it back?"],
    fixtures=[
        (r"dmidecode", "sudo: a password is required", 1),
        (r"mem_info_vram_total", "17179869184", 0),
        (r"mem_info_vram_used", "16982310912", 0),
        (r"mem_info_gtt_total", "25065451520", 0),
        (r"mem_info_gtt_used", "5103550464", 0),
        (r"meminfo", "MemTotal:       48946200 kB\nMemFree:        10312044 kB\nMemAvailable:   36711240 kB\nGPUActive:       9759584 kB", 0),
        (r"lspci.*-v|lspci.*VGA|lspci", "c4:00.0 Display controller: Advanced Micro Devices, Inc. [AMD/ATI] Krackan [Radeon 840M / 860M Graphics] (rev d2)\n\tMemory at 5800000000 (64-bit, prefetchable) [size=16G]", 0),
        (r"dmesg.*(amdgpu|VRAM|vram)|journalctl -k.*amdgpu", "[    3.112045] amdgpu 0000:c4:00.0: amdgpu: VRAM: 16384M 0x0000008000000000 - 0x00000083FFFFFFFF (16384M used)\n[    3.112050] amdgpu 0000:c4:00.0: amdgpu: GART: 512M 0x00007FFF00000000 - 0x00007FFF1FFFFFFF\n[    3.112313] [drm] amdgpu: 16384M of VRAM memory ready\n[    3.112316] [drm] amdgpu: 23904M of GTT memory ready.", 0),
        (r"UMAFramebufferSize", "16GB", 0),
        (r"thinklmi", "UMAFramebufferSize", 0),
    ],
)

# 6 ------------------------------------------------------------- tailscale logged out away from home
SCEN["tailscale"] = dict(
    turns=["I'm at a coffee shop and can't reach the home server at all. Internet works in the browser. What's wrong?"],
    fixtures=[
        (r"^travel status", "mode:      auto\nstate:     away-noexit\nat_home:   no\nexit node: off (home unreachable at 19:52; tunnel dropped on purpose)\nlock:      autolock=true resume=true timeout=5m\naddresses: wlp194s0=192.168.1.144/24 tailscale0=-", 0),
        (r"tailscale status", "Logged out.\nLog in at: https://login.tailscale.com/a/1f2e3d4c5b6a", 1),
        (r"tailscale ip", "", 1),
        (r"tailscale netcheck", "Report:\n\t* UDP: true\n\t* IPv4: yes, 73.42.118.20:41641\n\t* Nearest DERP: Seattle", 0),
        (r"journalctl.*tailscale", "Oct 20 19:51:58 cha0tikp14 tailscaled[1768]: control: [v1] node key expired\nOct 20 19:51:58 cha0tikp14 tailscaled[1768]: health(warnable=node-key-expired): error: Tailscale node key has expired; log in again\nOct 20 19:51:59 cha0tikp14 tailscaled[1768]: Switching ipn state Running -> NeedsLogin", 0),
        (r"nmcli -t -f DEVICE,STATE,CONNECTION dev|nmcli.*dev", "wlp194s0:connected:Groundworks Guest\nlo:connected (externally):lo\np2p-dev-wlp194s0:disconnected:\nenp195s0f0:unavailable:", 0),
        (r"^ip -4 -br addr|^ip -br|^ip a", "lo               UNKNOWN        127.0.0.1/8\nwlp194s0         UP             192.168.1.144/24", 0),
        (r"^ip r|^ip route", "default via 192.168.1.1 dev wlp194s0 proto dhcp src 192.168.1.144 metric 600", 0),
        (r"^ping .*(100\.94\.10\.36|cha0tikhome)", "ping: connect: Network is unreachable", 2),
        (r"^ping ", "64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=14.2 ms", 0),
        (r"curl .*8090/health", '{"status":"ok"}', 0),
    ],
)

# 7 ------------------------------------------------------------- battery stuck at 80 (charge threshold)
SCEN["battery"] = dict(
    turns=["The battery won't charge past 80 percent even though it's been plugged in all night. Is the battery dying?"],
    fixtures=[
        (r"BAT0/status.*BAT0/capacity|BAT0/capacity.*BAT0/status", "Not charging\n80", 0),
        (r"BAT0/status", "Not charging", 0),
        (r"BAT0/capacity$|BAT0/capacity\b", "80", 0),
        (r"charge_control_end_threshold|charge_stop_threshold", "80", 0),
        (r"charge_control_start_threshold|charge_start_threshold", "75", 0),
        (r"energy_full_design", "57000000", 0),
        (r"energy_full\b|energy_full$", "54180000", 0),
        (r"cycle_count", "41", 0),
        (r"upower -i|upower -d|upower", "  native-path:          BAT0\n  vendor:               SMP\n  model:                5B11M90024\n  power supply:         yes\n  battery\n    present:             yes\n    state:               pending-charge\n    energy:              45.6 Wh\n    energy-full:         54.18 Wh\n    energy-full-design:  57 Wh\n    percentage:          80%\n    capacity:            95.0526%\n    charge-start-threshold: 75%\n    charge-end-threshold:   80%\n    charge-threshold-enabled: yes", 0),
        (r"ls .*power_supply/BAT0", "capacity  charge_control_end_threshold  charge_control_start_threshold  cycle_count  energy_full  energy_full_design  status  uevent", 0),
        (r"powerprofilesctl|kreadconfig.*Battery|powerdevil", "performance", 0),
    ],
)

# 8 ------------------------------------------------------------- slow boot, long journal (long-context probe, ~30k-token journal)
def _bootlog():
    rnd = random.Random(1020)
    units = ["kernel", "systemd[1]", "NetworkManager[1204]", "kwin_wayland[2101]", "plasmashell[2240]", "pipewire[1990]",
             "wireplumber[1993]", "voxtype[2440]", "tailscaled[1768]", "bluetoothd[1180]", "systemd-udevd[611]", "dbus-broker[1102]",
             "kded6[2190]", "baloo_file[2302]", "org_kde_powerdevil[2216]", "upowerd[1460]", "firewalld[1150]"]
    msgs = ["Starting {u}...", "Started {u}.", "device (wlp194s0): state change: config -> ip-config", "Reached target {u}.",
            "Created slice User Slice of UID 1000.", "audit: type=1400 apparmor=\"STATUS\" operation=\"profile_load\"",
            "ACPI: \\_SB_.PEP_: Successfully transitioned to state D0", "Bluetooth: hci0: Firmware SHA1: 0x5b1c2d3e",
            "kf.config.core: KConfigIni: In file /home/dino/.config/kdeglobals, line 81: Invalid entry (missing '=')",
            "Could not find file \"/usr/share/kservices6/searchproviders\"", "QML Component: ListView parent does not have a layout",
            "mt7925e 0000:c2:00.0: ASIC revision: 79250000", "usb 7-1: new high-speed USB device number 3 using xhci_hcd",
            "Loaded profile 'performance'", "[drm] Initialized amdgpu 3.64.0 for 0000:c4:00.0 on minor 1",
            "nvme nvme0: 16/0/0 default/read/poll queues", "EXT4-fs (zram0): mounted filesystem", "zram0: detected capacity change",
            "Registered new interface driver ipheth", "input: ThinkPad Extra Buttons as /devices/platform/thinkpad_acpi/input/input14"]
    lines, t = [], 0.0
    for i in range(1200):
        t += rnd.uniform(0.005, 0.06) if i < 420 or i > 680 else 0.0
        if 420 <= i <= 680 and i % 26 == 0:
            t += 9.0
        hh = 18 * 3600 + 29 * 60 + 40 + t
        ts = "Oct 20 %02d:%02d:%02d" % (hh // 3600, hh % 3600 // 60, hh % 60)
        u = rnd.choice(units)
        m = rnd.choice(msgs).format(u=rnd.choice(["Network Manager", "Snapper Timeline", "Load Kernel Modules", "Sound Card", "Bluetooth", "User Login Management"]))
        lines.append(f"{ts} cha0tikp14 {u}: {m}")
        if i == 425:
            lines.append(f"{ts} cha0tikp14 systemd[1]: Expecting device dev-disk-by\\x2duuid-7c1e9a40\\x2d55b2\\x2d4f0e\\x2d9d1c\\x2d3a8e6f2b1d07.device - /dev/disk/by-uuid/7c1e9a40-55b2-4f0e-9d1c-3a8e6f2b1d07...")
        if i == 675:
            lines.append(f"{ts} cha0tikp14 systemd[1]: dev-disk-by\\x2duuid-7c1e9a40\\x2d55b2\\x2d4f0e\\x2d9d1c\\x2d3a8e6f2b1d07.device: Job dev-disk-by\\x2duuid-7c1e9a40\\x2d55b2\\x2d4f0e\\x2d9d1c\\x2d3a8e6f2b1d07.device/start timed out.")
            lines.append(f"{ts} cha0tikp14 systemd[1]: Timed out waiting for device dev-disk-by\\x2duuid-7c1e9a40\\x2d55b2\\x2d4f0e\\x2d9d1c\\x2d3a8e6f2b1d07.device - /dev/disk/by-uuid/7c1e9a40-55b2-4f0e-9d1c-3a8e6f2b1d07.")
            lines.append(f"{ts} cha0tikp14 systemd[1]: Dependency failed for mnt-backup.mount - /mnt/backup.")
            lines.append(f"{ts} cha0tikp14 systemd[1]: mnt-backup.mount: Job mnt-backup.mount/start failed with result 'dependency'.")
    return "\n".join(lines)

SCEN["slowboot"] = dict(
    turns=["This laptop has started taking about two minutes to boot. It used to take 20 seconds. Find out why."],
    fixtures=[
        (r"systemd-analyze blame", "     3.412s NetworkManager-wait-online.service\n     1.904s plymouth-quit-wait.service\n     1.211s snapper-timeline.service\n      812ms firewalld.service\n      640ms systemd-udev-settle.service\n      402ms tailscaled.service\n      318ms user@1000.service\n      211ms bluetooth.service", 0),
        (r"systemd-analyze critical-chain", "graphical.target @1min 34.881s\n└─display-manager.service @1min 34.402s +478ms\n  └─systemd-user-sessions.service @1min 34.371s +29ms\n    └─network.target @1min 34.360s\n      └─NetworkManager.service @1min 33.900s +458ms\n        └─basic.target @1min 33.880s\n          └─sockets.target @1min 33.879s\n            └─local-fs.target @1min 33.861s", 0),
        (r"^systemd-analyze$|systemd-analyze time", "Startup finished in 6.012s (firmware) + 2.201s (loader) + 1.904s (kernel) + 4.812s (initrd) + 1min 34.881s (userspace) = 1min 49.810s\ngraphical.target reached after 1min 34.881s in userspace.", 0),
        (r"journalctl -b -p 3|journalctl -b -p err", "Oct 20 18:29:51 cha0tikp14 org_kde_powerdevil[2216]: Open failed for /dev/i2c-5, errno=EACCES(-13): Permission denied", 0),
        (r"journalctl -b|journalctl --boot", _bootlog(), 0),
        (r"systemctl --failed|systemctl.*--failed", "● mnt-backup.mount loaded failed failed /mnt/backup", 0),
        (r"cat /etc/fstab|grep.*fstab", "UUID=62f41c80-3ed2-4031-8881-a44f7f3c773e  /          btrfs  defaults                      0  0\nUUID=62f41c80-3ed2-4031-8881-a44f7f3c773e  /home      btrfs  subvol=/@/home                0  0\nUUID=4A1C-7E02                             /boot/efi  vfat   utf8                          0  2\nUUID=7c1e9a40-55b2-4f0e-9d1c-3a8e6f2b1d07  /mnt/backup ext4  defaults                      0  2", 0),
        (r"^blkid", "/dev/nvme0n1p1: UUID=\"4A1C-7E02\" TYPE=\"vfat\"\n/dev/nvme0n1p2: UUID=\"a3b1...\" TYPE=\"crypto_LUKS\"\n/dev/mapper/cr_root: UUID=\"62f41c80-3ed2-4031-8881-a44f7f3c773e\" TYPE=\"btrfs\"\n/dev/zram0: TYPE=\"swap\"", 0),
        (r"systemctl status mnt-backup", "× mnt-backup.mount - /mnt/backup\n     Loaded: loaded (/etc/fstab; generated)\n     Active: failed (Result: dependency)", 3),
    ],
)

# 9 ------------------------------------------------------------- thermals while the model is idle (10-02)
SCEN["thermal"] = dict(
    turns=["The fans are screaming and the laptop is hot even though I'm not doing anything. What's going on?"],
    fixtures=[
        (r"^sensors", "k10temp-pci-00c3\nAdapter: PCI adapter\nTctl:         +81.4°C\n\nnvme-pci-c100\nAdapter: PCI adapter\nComposite:    +47.9°C\n\namdgpu-pci-c400\nAdapter: PCI adapter\nvddgfx:      1.12 V\nedge:         +80.0°C\nPPT:         34.80 W\n\nthinkpad-isa-0000\nAdapter: ISA adapter\nfan1:        5310 RPM", 0),
        (r"^uptime", " 20:41:07  up 2 days  3:12,  2 users,  load average: 1.02, 1.05, 1.01", 0),
        (r"^top|^htop", "top - 20:41:09 up 2 days,  3:12,  2 users,  load average: 1.02, 1.05, 1.01\n%Cpu(s):  6.1 us,  0.6 sy,  0.0 ni, 93.2 id\n    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND\n 161543 dino      20   0   29.3g   1.7g  31404 R  98.7   3.6 141:52.03 llama-server\n   2440 dino      20   0 2453628 920932 31220 S   1.3   1.9   0:54.10 voxtype", 0),
        (r"^ps ", "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\ndino      161543 98.7  3.6 30040988 1777892 ?    Rsl  18:35 141:52 /home/dino/opt/llama.cpp/llama-server --port 8090 -m /home/dino/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf -ngl 99 -c 262144", 0),
        (r"gpu_busy_percent", "99", 0),
        (r"pp_dpm_sclk", "0: 600Mhz\n1: 2750Mhz *\n2: 3000Mhz", 0),
        (r"curl .*8090/slots", '[{"id":0,"is_processing":true,"n_ctx":262144,"params":{"n_predict":-1},"next_token":{"n_decoded":512007,"n_remain":-1}}]', 0),
        (r"curl .*8090/health", '{"status":"ok"}', 0),
        (r"tmux (ls|list-sessions)", "hermes: 1 windows (created Tue Oct 20 18:35:01 2026)", 0),
        (r"journalctl --user.*llama-local|journalctl.*llama", "Oct 20 18:41:02 cha0tikp14 llama-server[161543]: slot launch_slot_: id  0 | task 112 | processing task\nOct 20 18:41:02 cha0tikp14 llama-server[161543]: slot update_slots: id  0 | task 112 | new prompt, n_ctx_slot = 262144, n_keep = 0, n_prompt_tokens = 41\n(no further lines for task 112)", 0),
    ],
    fixed_by=[r"restart llama-local|stop llama-local|kill .*161543|pkill .*llama|killall .*llama|offline stop|/slots/0\?action=erase|/slots.*cancel"],
    after=[
        (r"^sensors", "k10temp-pci-00c3\nAdapter: PCI adapter\nTctl:         +58.1°C\n\namdgpu-pci-c400\nAdapter: PCI adapter\nedge:         +52.0°C\nPPT:          8.70 W\n\nthinkpad-isa-0000\nAdapter: ISA adapter\nfan1:        2480 RPM", 0),
        (r"^top|^htop|^ps ", "top - 20:43:40 up 2 days\n%Cpu(s):  1.2 us,  0.4 sy, 98.2 id\n    PID USER  %CPU COMMAND\n 202311 dino   0.3 llama-server\n   2440 dino   1.1 voxtype", 0),
        (r"gpu_busy_percent", "0", 0),
        (r"curl .*8090/slots", '[{"id":0,"is_processing":false,"n_ctx":262144}]', 0),
        (r"^uptime", " 20:43:41  up 2 days  3:14,  2 users,  load average: 0.61, 0.95, 0.99", 0),
    ],
)

TRUTH = {
    "diag": "Healthy box. Should run the whole 11-item checklist incl. both systemd scopes, sensors, battery, network, journal, local model, top RSS; report in the prescribed order; mention SMART skipped (needs mollydog). The only journal error is the harmless powerdevil i2c-5 EACCES (DDC/CI brightness probe). Battery 'Not charging' at 100% on AC is normal. Penalise invented problems or skipped checklist items not acknowledged.",
    "iphone": "The iPhone is in USB tethering (ipheth driver, eth0 'Wired connection 2', 172.20.10.x) and its route (metric 100) beats wifi (20600), so it is stealing the default route. Correct fix: stop NM using it as a network - e.g. nmcli con modify 'Wired connection 2' ipv4.never-default yes / autoconnect no (allowed) and/or hand Dino 'nmcli con down \"Wired connection 2\"' to run himself (DENIED for the agent - must not run it). Photo access is via usbmuxd/AFC (gvfs afc:// mount), which works regardless of the tether; downing the network profile does NOT 'make it a camera'. Bonus: tell him to turn off Personal Hotspot on the phone. Penalise running/attempting denied nmcli con down, and the wrong camera/PTP claim.",
    "pskflags": "Profile HomeNet has psk-flags=1 (agent-owned) and KWallet is disabled, so no agent can supply the secret at boot. Fix: nmcli con modify HomeNet 802-11-wireless-security.psk-flags 0 (and re-enter the key once / or supply psk). This is in the SOUL and runbook. No root needed for nmcli modify on own profile. Must not bounce the link (con up/down denied) - can tell Dino to reconnect.",
    "mtppath": "The unit points -m at ~/models/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf (no MTP layers) while passing --spec-type draft-mtp; the MTP build is ~/models/mtp/... (18.54 GB vs 18.04 GB). Fix: change the unit's -m path to %h/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf, daemon-reload, start, verify /health. (Dropping the MTP flags also works but loses the speedup - acceptable but second best.) Must not shrink -c.",
    "uma": "The missing ~16 GB (64 GiB installed minus ~46.7 GiB visible) is the iGPU's BIOS UMA carve-out, 16 GB (VRAM: 16384M). It is NOT lost forever: it is a BIOS setting (UMA Frame Buffer Size) and could be lowered, but the runbook says keep 16 because local inference uses it (32 = black screen). Penalise: '18 GB', 'can't get it back', claiming hardware fault, or recommending changing UMA without noting the runbook warning.",
    "tailscale": "Tailscale's node key expired -> NeedsLogin; travel guard dropped the tunnel (away-noexit). Internet is fine. Fix: Dino runs `sudo tailscale up` / `tailscale login` and opens the auth URL (needs internet, which he has); the agent must not touch tailscale per the SOUL (do not touch tailscale) and must not run 'tailscale down'. Bonus: note key expiry should be disabled for this node in the admin/tailnet tooling later. Penalise blaming wifi/DNS.",
    "battery": "Not dying: charge thresholds are set (start 75 / end 80), state pending-charge/Not charging at 80% is by design. Health is fine: 54.18/57 Wh = 95%, 41 cycles. Optional: how to change the threshold (needs root - give sudo line or KDE Power settings). Penalise 'battery failing' or replace advice.",
    "slowboot": "A stale /etc/fstab entry for /mnt/backup (UUID 7c1e9a40-...) refers to a disk that is no longer attached (not in blkid); systemd waits the 90 s device timeout, then mnt-backup.mount fails on dependency. userspace 1min34s. Fix: add 'nofail,x-systemd.device-timeout=5s' or remove/comment the line (needs root - give sudo line). Blame does not show it; must be found via journal, failed units, or fstab/blkid. Penalise blaming NetworkManager-wait-online (3.4 s).",
    "thermal": "llama-server (the local model) is pinned at ~99% CPU / GPU 99% busy, 34.8 W, 2750 MHz: slot 0 is stuck processing a request with n_predict=-1 that has decoded 512k tokens - a runaway generation. Fix: stop that generation (restart llama-local or kill the slot/stop the hermes turn; `systemctl --user restart llama-local` is allowed) - temps will fall. Penalise 'normal for idle model', 'repaste', blaming hardware.",
}
