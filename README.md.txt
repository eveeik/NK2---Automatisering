NK2---Automatisering/
│
├── del1_python/
│ └── ssh-config.py
│
├── del2_ansible/
│ ├── R1.yml
│ ├── R2.yml
│ ├── SW2.yml
│ ├── SW3.yml
│ └── SW4.yml
│
└── README.md
---

## Del 1 – Python SSH-konfigurasjon

Python-skriptet `ssh-config.py` brukes til å kjøre første oppsett på nye Cisco-enheter.

### Funksjonalitet
- Setter hostname, domain-name og RSA-nøkler
- Oppretter administrator-bruker
- Setter `enable secret`
- Konfigurerer management VLAN (99)
- Setter IP-adresse (10.99.1.x), maske og default gateway
- Konfigurerer porter som access eller trunk
- Bruker `netmiko` eller `paramiko` for SSH-tilkobling

Etter at grunnoppsettet er på plass, brukes Ansible til å konfigurere resten av nettverket.

---

##  Del 2 – Ansible Automatisering

I denne delen brukes **Ansible** til å konfigurere rutere og switcher automatisk basert på `.yml`-filer.

###  Krav
- En kontrollmaskin med **Ansible** installert (Linux, macOS, eller WSL på Windows)
- Cisco-enheter med SSH aktivert (f.eks. på VLAN 99)
- Python 3 og `paramiko` installert (hvis du bruker Python-skriptet først)

---

## YAML-konfigurasjonene

###  R1.yml
- Oppretter subinterfaces for VLAN 10 og 20  
- Konfigurerer **HSRP (v2)** for VLAN 10 og 20  
- Setter opp DHCP-pooler (split-scope delt med R2)  
- IP-plan:
  - VLAN 10: `10.10.0.0/24`  
  - VLAN 20: `10.20.0.0/24`  
  - VLAN 99: `10.99.1.0/24` (management)
- R1 er **HSRP Active** (priority 110)  
- DHCP-range: `.51–.200`

---

###  R2.yml
- Samme oppsett som R1, men lavere HSRP-prioritet (100)  
- Samme VLAN og subinterfaces  
- DHCP-range: `.201–.254`  
- R2 fungerer som **HSRP Standby**

---

###  SW2.yml
- Trunker **Fa0/1–2** med VLAN 10, 20, 99  
- Oppretter **LACP EtherChannel (Fa0/23–24)** mot SW3  
- Port-Channel 1 fungerer som trunk mellom SW2 og SW3  

---

###  SW3.yml
- Samme oppsett som SW2  
- EtherChannel mot SW2 med LACP (active)  
- VLAN 10, 20 og 99 trunkes på alle relevante porter  

---

###  SW4.yml
- **Access-layer switch**
- Fa0/1 = trunk (VLAN 10, 20, 99)  
- Fa0/2–12 = Access VLAN 10  
- Fa0/13–24 = Access VLAN 20  

---

##  Kjøre Ansible-konfigurasjonene

1. Gå til mappen med YAML-filene:
   ```bash
   cd del2_ansible
