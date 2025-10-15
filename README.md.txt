# NK2 – Arbeidskrav 2 – Del 1: Python via konsoll

Dette repoet inneholder et **Python-script** som automatisk setter opp SSH-tilgang på en Cisco-enhet (switch eller router) via **konsollkabel**.  
Scriptet brukes til å konfigurere en *blank* enhet slik at du etterpå kan logge inn via SSH.

---

## 🧩 Funksjoner
- Setter hostname, enable secret og lokal admin-bruker
- Aktiverer SSH v2 og genererer RSA-nøkler
- Konfigurerer management-IP (SVI på switch / interface på router)
- Støtter valg av access- eller trunk-port på switch
- Skriver konfigurasjon til minnet

---

## ⚙️ Krav
- Python 3.10 eller nyere
- `pyserial`-bibliotek (`pip install pyserial`)
- Konsollkabel (USB ↔ RJ45 / mini-USB)
- En Cisco-switch eller -router med standard IOS

---

## 💻 Bruk
1. Koble PC til enheten med konsollkabel.
2. Finn riktig COM-port i **Enhetsbehandling** (f.eks. `COM3`).
3. Åpne PowerShell og gå til denne mappa:
   ```powershell
   cd "C:\Users\<brukernavn>\Documents\GitHub\NK2---Automatisering\del1_python"
