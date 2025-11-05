# Genie Package Distribution Plan

## Option 1: Shell Script + Homebrew Tap (Recommended) ⭐

This document outlines the complete strategy for distributing genie as a macOS package using Homebrew.

---

## 📦 Final Repository Structure

```
genie/
├── bin/
│   └── genie                    # Main executable script
├── lib/
│   ├── docker-setup.sh         # Docker container management
│   ├── ollama-setup.sh         # Ollama model management
│   └── ui-launcher.sh          # Web UI launcher
├── Formula/
│   └── genie.rb                # Homebrew formula
├── install.sh                   # Direct install script (no Homebrew)
├── uninstall.sh                # Cleanup script
├── README.md                    # Documentation
└── LICENSE
```

---

## 🔧 Component Details

### 1. `bin/genie` (Main Executable)

This becomes the user's command. Clean, simple interface:

```bash
#!/bin/bash
# User runs: genie start, genie stop, genie status

Commands:
  genie start     - Start Docker + Ollama + Web UI
  genie stop      - Stop all services
  genie status    - Check what's running
  genie models    - List/download models
  genie update    - Update genie itself
```

**What it does:**
- Validates dependencies (Docker, Ollama installed)
- Sources helper scripts from `lib/`
- Provides clean CLI interface
- Handles errors gracefully

---

### 2. `Formula/genie.rb` (Homebrew Formula)

This is what Homebrew uses to install your package:

```ruby
class Genie < Formula
  desc "Launch local LLM with Docker + Ollama + Web UI"
  homepage "https://github.com/yourusername/genie"
  url "https://github.com/yourusername/genie/archive/v1.0.0.tar.gz"
  sha256 "..." # Auto-generated

  depends_on "docker"
  depends_on "ollama"

  def install
    bin.install "bin/genie"
    prefix.install "lib"
  end
end
```

**What it does:**
- Tells Homebrew where to download genie
- Declares dependencies
- Installs files to proper locations

---

### 3. `install.sh` (Direct Install - No Homebrew)

For users who don't want Homebrew:

```bash
curl -fsSL https://raw.githubusercontent.com/you/genie/main/install.sh | bash
```

**What it does:**
- Downloads genie to `/usr/local/bin/`
- Checks for dependencies
- Adds to PATH if needed
- Provides feedback

---

## 👤 End User Experience

### Installation (3 options)

**Option A: Homebrew Tap (Recommended)**
```bash
brew tap yourusername/genie
brew install genie
```

**Option B: Homebrew URL**
```bash
brew install yourusername/genie/genie
```

**Option C: Direct Install**
```bash
curl -fsSL https://install-genie.sh | bash
```

---

### Usage

```bash
# First time setup
$ genie start
⏳ Checking dependencies...
✓ Docker found
✓ Ollama found
🚀 Starting Ollama service...
📦 Pulling llama3.2:latest...
🌐 Launching Web UI at http://localhost:8080
✨ Genie is ready!

# Check status
$ genie status
✓ Docker: Running
✓ Ollama: Running (llama3.2:latest)
✓ Web UI: http://localhost:8080

# Stop everything
$ genie stop
🛑 Stopping services...
✓ All stopped

# Update genie itself
$ genie update
📥 Updating to v1.1.0...
✓ Updated successfully
```

---

## 🏗️ How Homebrew Taps Work

### What's a "Tap"?
A tap is just a GitHub repository with formulas. Homebrew reads formulas from:
- **Official:** `homebrew/core` (brew install wget)
- **Your Tap:** `yourusername/genie` (brew install yourusername/genie/genie)

### Setting Up Your Tap

1. **Create repo:** `github.com/yourusername/homebrew-genie`
   - Must be named `homebrew-*` for Homebrew to recognize it

2. **Add Formula:** `Formula/genie.rb`

3. **Users install:**
   ```bash
   brew tap yourusername/genie    # Adds your tap
   brew install genie             # Installs from your tap
   ```

---

## 🔄 Update & Release Workflow

### When you make changes:

1. **Update code** in your repo
2. **Tag release:** `git tag v1.1.0 && git push --tags`
3. **Update formula:** Change version + URL in `Formula/genie.rb`
4. **Users update:** `brew update && brew upgrade genie`

### Automatic updates:
Users get updates whenever they run `brew upgrade`

---

## ✅ Dependency Management

### Approach 1: Homebrew Dependencies (Clean)
```ruby
depends_on "docker"
depends_on "ollama"
```
Homebrew installs these automatically

### Approach 2: Runtime Checks (More Control)
```bash
# In your genie script
check_docker() {
  if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    echo "Install: brew install docker"
    exit 1
  fi
}
```

**Recommended:** Combine both
- Homebrew suggests dependencies
- Script validates at runtime

---

## 📋 Implementation Checklist

If you choose this option, here's what we'd build:

### Phase 1: Core Script
- [ ] Refactor existing script into modular structure
- [ ] Add dependency checking
- [ ] Create start/stop/status commands
- [ ] Add error handling

### Phase 2: Packaging
- [ ] Create Homebrew formula
- [ ] Write install.sh for direct installation
- [ ] Add uninstall script
- [ ] Test installation process

### Phase 3: Documentation
- [ ] Write comprehensive README
- [ ] Add usage examples
- [ ] Document troubleshooting

### Phase 4: Distribution
- [ ] Create GitHub releases
- [ ] Set up tap repository
- [ ] Test end-to-end installation

---

## 🎯 Pros & Cons Summary

### Pros:
✅ Uses your existing shell code
✅ Homebrew is familiar to macOS developers
✅ Simple to maintain and update
✅ Fast to implement (~1-2 days)
✅ Users install with single command
✅ Automatic dependency management

### Cons:
❌ macOS/Linux only (no Windows)
❌ Shell scripts harder to unit test
❌ Less "professional" than compiled binary
❌ Homebrew formula needs manual updates for releases

---

## 💡 Enhanced Features We Could Add

1. **Config file:** `~/.genierc` for user preferences
2. **Model management:** `genie models add llama3.2`
3. **Multiple profiles:** `genie start --profile coding`
4. **Auto-updates:** `genie update` checks for new versions
5. **Health checks:** `genie doctor` diagnoses issues

---

## 🚀 Example: What Users Would See

```bash
# Installation
$ brew install pierredimitrov/genie/genie
🍺 Installing genie from pierredimitrov/genie
==> Downloading https://github.com/pierredimitrov/genie/archive/v1.0.0.tar.gz
==> Installing dependencies: docker, ollama
✓ genie 1.0.0 installed

# First run
$ genie start
🧞 Genie - Local LLM Environment
⏳ First-time setup...
✓ Docker running
✓ Ollama service started
📦 Downloading llama3.2:latest (4.7GB)...
████████████████████ 100%
🌐 Web UI: http://localhost:8080
✨ Ready! Run 'genie status' to check services
```

---

## 🔍 Alternative Options Considered

### Option 2: Go Binary + Homebrew

**Best for:** Professional polish, cross-platform potential

**Pros:**
- Single compiled binary (fast, no runtime needed)
- Better error handling & testing
- Can still distribute via Homebrew
- Easy to add Linux/Windows support later
- Professional appearance

**Cons:**
- Requires learning Go (if unfamiliar)
- More setup overhead for a simple script

---

### Option 3: Python CLI (via pipx/PyPI)

**Best for:** If you prefer Python, want cross-platform

**Pros:**
- Easy to write (Click/Typer frameworks)
- Publish to PyPI: pipx install genie-llm
- Good testing frameworks
- Cross-platform support

**Cons:**
- Python dependency
- Slightly heavier than needed

---

## 🎯 Why Option 1 is Recommended

1. Your logic is already written in shell
2. macOS is your primary target
3. Fastest time to distribution
4. Homebrew taps are trivial to set up
5. You can always rewrite in Go later if needed

---

## 📝 Key Questions Before Implementation

1. Do you want **macOS-only** or should we plan for **Linux/Windows** support?
2. Is the name "**genie**" final? (Important for package naming/conflicts)
3. Should the installer **auto-install** Docker/Ollama, or just **check** for them?
4. What GitHub username/organization will host the tap?

---

## 🚢 Distribution Strategy Summary

- **Primary:** Homebrew tap (`brew install yourname/genie/genie`)
- **Fallback:** Direct install script (`curl -sSL install.sh | bash`)
- **Docs:** Clear README with prerequisites
- **Optional:** Docker image with preconfigured setup

---

## 📚 Additional Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Creating Homebrew Taps](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
- [Homebrew Installation Guide](https://docs.brew.sh/Installation)

---

**Status:** Planning Phase
**Next Steps:** Await approval, then begin Phase 1 implementation
