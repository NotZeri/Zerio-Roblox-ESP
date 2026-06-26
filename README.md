# 📖 Roblox External ESP

A simple Windows Python project with configurable hotkeys and Virtual-Key (VK) support.

![Downloads](https://img.shields.io/github/downloads/NotZeri/Zerio-Roblox-ESP/total?color=green)
![Static Badge](https://img.shields.io/badge/verson-1.0.0-blue?label=verson)

## ✨ Features

![Status](https://img.shields.io/badge/Status-In%20Development-orange)
- ⚡ Lightweight
- ⌨️ Configurable hotkeys
- 🛠️ Easy configuration
- 📚 Beginner-friendly code sort of

---

## 📦 Requirements

- Python 3.10+
- Windows 10/11

---

## 🚀 Getting Started

Download the zip, then extract

[Quick Download](https://github.com/NotZeri/Roblox-ESP/archive/refs/heads/main.zip)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the project:

```bash
python MainESP.py
```

---

## ⌨️ Changing Hotkeys

This project uses **Windows Virtual-Key (VK) codes**.

Locate the hotkey section in the source code:

Something like this
```python
V_key = 0x56
```

To change the hotkey, simply replace the Virtual-Key value with another VK code.

**Example**

```python
V_key = 0x42
```

changes the hotkey to **B**.

A full list of Virtual-Key codes can be found in:

- **VirtualKeys.md**

---

## 📚 Virtual-Key Codes

Some common VK codes:

| Key | VK Code |
|------|---------|
| A | `0x41` |
| B | `0x42` |
| C | `0x43` |
| D | `0x44` |
| E | `0x45` |
| F | `0x46` |
| G | `0x47` |
| H | `0x48` |
| I | `0x49` |
| J | `0x4A` |

See **VirtualKeys.md** for the complete list.

---

## 🤝 Contributing

Pull requests are welcome.

If you find a bug or have a suggestion, feel free to open an issue.

---

## 📄 License

This project is licensed under the MIT License.
