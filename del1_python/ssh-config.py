#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Én-fil ssh-config (pySerial).
# Switch: mgmt-VLAN + valgt port (access/trunk) + trunk "alt annet" via interface range.
# Router: flere fysiske interfaces ELLER flere parent-if hver med flere sub-interfaces (dot1Q). Norsk kommentert.

import time, getpass, serial

DELAY, LONG = 0.35, 1.2
PRESS_RETURN = b"press return to get started"
INIT_TOKENS  = (b"initial configuration dialog", b"system configuration dialog", b"autoinstall")

def send(ser, cmd, wait=DELAY): ser.write((cmd+"\r\n").encode()); time.sleep(wait)
def run_list(ser, cmds, wait=DELAY): [send(ser,c,wait) for c in cmds]

def wake_console(ser):
    for _ in range(8):
        ser.write(b"\r\n"); time.sleep(0.15)
        if PRESS_RETURN in ser.read(ser.in_waiting or 1).lower(): ser.write(b"\r\n"); time.sleep(0.4)

def skip_init_dialog(ser):
    time.sleep(0.6); out = ser.read(ser.in_waiting or 1).lower()
    if any(t in out for t in INIT_TOKENS): run_list(ser, ["no","no"], wait=0.6)

def enter_enable(ser):
    send(ser,"");  out = ser.read(ser.in_waiting or 1)
    if b">" in out: send(ser,"enable",0.5)

def base_cmds(host, enable_secret, domain, user, user_pw, role, rsa_bits):
    return [
        "configure terminal",
        f"hostname {host}",
        f"enable secret {enable_secret}",
        f"ip domain-name {domain}",
        f"username {user} privilege {role} secret {user_pw}",
        "line vty 0 15"," transport input ssh"," login local"," exec-timeout 10 0"," exit",
        "ip ssh version 2",
        f"crypto key generate rsa modulus {rsa_bits}",
        "no ip http server","no ip http secure-server","service password-encryption",
    ]

# -------- SWITCH --------
def switch_cmds(vlan, ip, mask, dgw, specific_port, mode, trunk_range):
    cmds = [
        f"vlan {vlan}","exit",
        f"interface vlan {vlan}",
        f" ip address {ip} {mask}",
        " no shutdown"," exit",
    ]
    if dgw: cmds += [f"ip default-gateway {dgw}"]

    # Trunk alle "andre" porter via interface range om oppgitt
    if trunk_range:
        cmds += [
            f"interface range {trunk_range}",
            " switchport",
            " switchport mode trunk",
            f" switchport trunk allowed vlan add {vlan}",
            " no shutdown",
            " exit",
        ]

    # Spesifikk port etter ønske (overstyrer range)
    if mode == "access":
        cmds += [
            f"interface {specific_port}",
            " switchport"," switchport mode access",f" switchport access vlan {vlan}",
            " spanning-tree portfast"," no shutdown"," exit",
        ]
    else:
        cmds += [
            f"interface {specific_port}",
            " switchport"," switchport mode trunk",f" switchport trunk allowed vlan add {vlan}",
            " no shutdown"," exit",
        ]
    return cmds

# -------- ROUTER --------
def router_cmds_phys_multi(if_list, dgw):
    """ if_list=[{'iface':'Gi0/0','ip':'10.0.0.1','mask':'255.255.255.0'}, ...] """
    cmds = []
    for it in if_list:
        cmds += [f"interface {it['iface']}", f" ip address {it['ip']} {it['mask']}", " no shutdown", " exit"]
    if dgw: cmds += [f"ip route 0.0.0.0 0.0.0.0 {dgw}"]
    return cmds

def router_cmds_subs_multi(parents, dgw):
    """
    parents = [
      {'parent':'Gi0/0','subs':[{'sub':'10','vlan':'10','ip':'10.10.10.254','mask':'255.255.255.0'}, {...}]},
      {'parent':'Gi0/1','subs':[{'sub':'30','vlan':'30','ip':'10.10.30.254','mask':'255.255.255.0'}]}
    ]
    """
    cmds = []
    for p in parents:
        par = p['parent']
        cmds += [f"interface {par}", " no ip address", " no shutdown", " exit"]
        for s in p['subs']:
            subif = f"{par}.{s['sub']}"
            cmds += [
                f"interface {subif}",
                f" encapsulation dot1Q {s['vlan']}",
                f" ip address {s['ip']} {s['mask']}",
                " no shutdown",
                " exit",
            ]
    if dgw: cmds += [f"ip route 0.0.0.0 0.0.0.0 {dgw}"]
    return cmds

# -------- MAIN --------
def main():
    com   = input("Konsollport (COM3 / /dev/ttyUSB0): ").strip()
    kind  = input("Enhet [s=switch / r=router]: ").strip().lower()

    host  = input("Hostname: ").strip()
    dom   = (input("Domain (ip domain-name) [lab.local]: ").strip() or "lab.local")
    role  = int(input("Admin-privilege [15]: ") or "15")
    bits  = int(input("RSA-bits [2048]: ") or "2048")
    ensec = getpass.getpass("Enable secret: ")
    user  = input("Admin brukernavn: ").strip()
    upw   = getpass.getpass(f"Passord for {user}: ")

    ssh_ip = None  # brukes til slutt-printf

    if kind.startswith("s"):
        vlan = int(input("Mgmt VLAN-ID: ").strip())
        ip   = input("Mgmt IP: ").strip(); ssh_ip = ip
        mask = input("Maske: ").strip()
        dgw  = input("Default-gw (tom=ingen): ").strip()
        specific_port = input("Spesifikk port (f.eks. GigabitEthernet0/1): ").strip()
        mode = input("Port-modus for spesifikk port [access/trunk]: ").strip().lower()
        if mode not in ("access","trunk"): mode = "access"
        trunk_range = input("Interface RANGE for 'alt annet' (f.eks. GigabitEthernet0/1-24, tom=skip): ").strip()
        dev_cmds = switch_cmds(vlan, ip, mask, dgw, specific_port, mode, trunk_range)

    else:
        rmode = input("Router-modus: [p]=flere fysiske IF / [s]=sub-IF på flere parent [s]: ").strip().lower() or "s"
        if rmode == "p":
            # Flere fysiske interfaces
            if_list = []
            while True:
                iface = input(" Interface-navn (tom=ferdig, f.eks. GigabitEthernet0/0): ").strip()
                if not iface: break
                ip    = input("  IP-adresse: ").strip(); ssh_ip = ip
                mask  = input("  Maske: ").strip()
                if_list.append({"iface":iface,"ip":ip,"mask":mask})
            if not if_list:
                print("Ingen interfaces oppgitt – avbryter."); return
            dgw = input("Default-route next-hop (tom=ingen): ").strip()
            dev_cmds = router_cmds_phys_multi(if_list, dgw)
        else:
            # Flere parent + flere sub-IF per parent
            parents = []
            while True:
                parent = input(" Parent-interface (tom=ferdig, f.eks. GigabitEthernet0/0): ").strip()
                if not parent: break
                subs = []
                while True:
                    sub_id = input("  Sub-ID (tom=ferdig for denne, f.eks. 10 for .10): ").strip()
                    if not sub_id: break
                    vlan = input("   VLAN (f.eks. 10): ").strip()
                    ip   = input("   IP-adresse: ").strip(); ssh_ip = ip
                    mask = input("   Maske: ").strip()
                    subs.append({"sub":sub_id,"vlan":vlan,"ip":ip,"mask":mask})
                if not subs:
                    print("  Ingen sub-IF for denne parent – hopper.")
                else:
                    parents.append({"parent":parent,"subs":subs})
            if not parents:
                print("Ingen parent/sub-IF oppgitt – avbryter."); return
            dgw = input("Default-route next-hop (tom=ingen): ").strip()
            dev_cmds = router_cmds_subs_multi(parents, dgw)

    ser = serial.Serial(com, baudrate=9600, timeout=1.0)
    try:
        wake_console(ser); skip_init_dialog(ser); enter_enable(ser)
        run_list(ser, base_cmds(host, ensec, dom, user, upw, role, bits)); time.sleep(LONG)
        run_list(ser, dev_cmds)
        run_list(ser, ["end","write memory"], wait=LONG)
        print("Ferdig.", (" Test SSH mot "+ssh_ip) if ssh_ip else "")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
