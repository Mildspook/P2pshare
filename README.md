# P2Pshare

P2Pshare is a lightweight file-sharing application that lets you quickly share files and folders over your local network or across the internet.

## Features

* 📁 Share files and folders with ease
* 🌐 Works on both local networks and the internet
* 🖥️ Simple Windows And Linux executable
* ⚡ Legacy Python version available for headless servers and terminal use
* 🔌 Optional automatic UPnP port forwarding for internet sharing

---

## Sharing Outside Your Local Network

To allow devices outside your local network to connect, **UPnP must be enabled on your router**. P2Pshare can use UPnP to automatically configure port forwarding when supported by your router.

If your router does not support UPnP or it is disabled, you will need to manually forward the required port.

---

## Downloads

### Windows (.exe)

The Windows executable is designed to be as simple as possible just launch it, choose the folder you want to share, and you're ready to go.

### Legacy Python Version

The original Python version requires **Python 3**.

It can be run entirely from the terminal without the GUI, making it ideal for headless systems or servers. By default, it shares the directory that it is run from.

---

## ⚠️ Antivirus False Positives

Some antivirus products most commonly Microsoft Defender may flag the Windows executable as **`Trojan:Win32/Sabsik.FL.A!ml`** or a similar generic detection.

This is a **false positive** and is **not** evidence that P2Pshare contains malware. These detections are caused by how the application is packaged and how it behaves, rather than malicious code.

### Why does this happen?

* **PyInstaller packaging.**
  The Windows executable is built using **PyInstaller** in `--onefile` mode. This bundles Python, all dependencies, and the application into a single executable that extracts itself to a temporary directory at runtime. This behavior resembles how many legitimate installers and unfortunately some malware operate, so heuristic and machine-learning scanners often flag it.

* **Unsigned executable.**
  P2Pshare is not digitally signed with a code-signing certificate. Without a trusted publisher identity, antivirus reputation systems are more likely to treat the executable as suspicious.

* **Low reputation.**
  Since P2Pshare is an independent open-source project with relatively few downloads, cloud reputation systems have little history to determine that the executable is trustworthy. New builds are especially prone to false positives.

* **Networking behavior.**
  P2Pshare opens a local HTTP server to share files and can optionally use **UPnP** to automatically forward a port on your router. Applications that listen for incoming connections and interact with networking hardware are commonly flagged by heuristic scanners, even when their behavior is legitimate.

### Verify it yourself

You don't have to take our word for it.

* Scan the executable with VirusTotal before running it.
* Review the source code P2Pshare is completely open source.
* If you prefer complete transparency, run the **Legacy Python Version** instead of the prebuilt executable.

---

## Redistribution

Redistribution, modification, and reuse are permitted, provided that appropriate credit is given to the original authors.

---

## Screenshots

### Main Interface

<img width="677" height="663" alt="Main Interface" src="https://github.com/user-attachments/assets/6e6dd3f3-b9f4-47f7-b036-8622b5a04bbd" />

### File Browser

<img width="1919" height="913" alt="File Browser" src="https://github.com/user-attachments/assets/365a4e38-9e3f-4c0e-aad6-6c47aea0914f" />

---

## Licence

**MSOS**

---

## Credits

### Primary Developer

* **Mild_spook**

### Contributor

* **Totally_ligit**


